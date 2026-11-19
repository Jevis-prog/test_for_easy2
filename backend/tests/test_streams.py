import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
from app.services import streams


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session


class Keitaro:
    def __init__(self):
        self.offers = [{"offer_id": 1, "share": 50, "state": "active"}, {"offer_id": 2, "share": 50, "state": "active"}]
    def get(self, path):
        if path == '/offers':
            return [{"id": i, "name": f"Offer {i}"} for i in range(1, 5)]
        if path.startswith('/campaigns/'):
            return [{"id": 10, "name": "Offers", "offers": self.offers}]
        return {"id": 10, "offers": self.offers}
    def put(self, path, data):
        self.offers = data['offers']
        return {"offers": self.offers}


def test_draft_persist_publish_archive_and_restore(db):
    client = Keitaro()
    streams.fetch_streams(db, client, 1)
    draft = streams.find_draft(db, 10)
    streams.mutate(db, draft, 'pin', 1)
    streams.mutate(db, draft, 'add', 3, 'Offer 3')
    assert [o['share'] for o in draft.offers] == [50, 25, 25]
    db.expire_all()
    assert streams.find_draft(db, 10).dirty
    assert len(client.offers) == 2
    streams.publish(db, client, draft)
    streams.mutate(db, draft, 'remove', 2)
    assert [o['share'] for o in draft.offers] == [50, 0, 50]
    streams.publish(db, client, draft)
    assert [o['offer_id'] for o in client.offers] == [1, 3]
    streams.mutate(db, draft, 'restore', 2)
    assert [o['share'] for o in draft.offers] == [50, 25, 25]
    streams.cancel(db, draft)
    assert next(o for o in draft.offers if o['offer_id'] == 2)['removed']


def test_external_change_cannot_overwrite_draft(db):
    client = Keitaro()
    streams.fetch_streams(db, client, 1)
    draft = streams.find_draft(db, 10)
    streams.mutate(db, draft, 'add', 3, 'Offer 3')
    client.offers = [{"offer_id": 1, "share": 100, "state": "active"}]
    with pytest.raises(HTTPException) as err:
        streams.publish(db, client, draft)
    assert err.value.status_code == 409
    streams.fetch_streams(db, client, 1)
    assert draft.conflict and draft.dirty and len(draft.offers) == 3
    streams.cancel(db, draft)
    streams.fetch_streams(db, client, 1)
    assert next(o for o in draft.offers if o['offer_id'] == 2)['removed']


def test_integer_remainder_and_invalid_pinned_weights():
    offers = [{"offer_id": i, "share": 0, "removed": False, "pinned": False} for i in range(3)]
    assert [o['share'] for o in streams.distribute(offers)] == [34, 33, 33]
    with pytest.raises(HTTPException):
        streams.distribute([{"share": 80, "removed": False, "pinned": True}, {"share": 30, "removed": False, "pinned": True}])


def test_publish_empty_stream_and_restore_archived_offer(db):
    client = Keitaro()
    client.offers = [{"offer_id": 1, "share": 100, "state": "active"}]
    streams.fetch_streams(db, client, 1)
    draft = streams.find_draft(db, 10)
    streams.mutate(db, draft, 'remove', 1)
    assert draft.offers[0]['share'] == 0
    streams.publish(db, client, draft)
    assert client.offers == []
    assert draft.offers[0]['removed'] and draft.offers[0]['archived']
    streams.mutate(db, draft, 'restore', 1)
    assert draft.offers[0]['share'] == 100
    streams.publish(db, client, draft)
    assert client.offers == [{"offer_id": 1, "share": 100, "state": "active"}]
