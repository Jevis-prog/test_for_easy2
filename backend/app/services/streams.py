from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.models import StreamDraft


TOTAL_TRAFFIC_SHARE = 100
ACTIVE_STATE = "active"


def normalized(offers):
    return sorted([{"offer_id": int(o["offer_id"]), "share": int(o.get("share", 0)), "state": o.get("state", ACTIVE_STATE)} for o in offers if o.get("state", ACTIVE_STATE) == ACTIVE_STATE], key=lambda x: x["offer_id"])


def distribute(offers):
    active = [o for o in offers if not o["removed"]]
    pinned = [o for o in active if o.get("pinned")]
    free = [o for o in active if not o.get("pinned")]
    remaining = TOTAL_TRAFFIC_SHARE - sum(o["share"] for o in pinned)
    if remaining < 0 or (not free and remaining != 0 and active):
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Pinned shares prevent distribution of 100%")
    if free:
        share, remainder = divmod(remaining, len(free))
        for i, offer in enumerate(free):
            offer["share"] = share + (i < remainder)
    for offer in offers:
        if offer["removed"]:
            offer["share"] = 0
            offer["pinned"] = False
    return offers


def serialize(d):
    return {"stream_id": d.stream_id, "campaign_id": d.campaign_id, "name": d.name, "offers": d.offers, "dirty": d.dirty, "conflict": d.conflict}


def fetch_streams(db: Session, client, campaign_id):
    streams = client.get(f"/campaigns/{campaign_id}/streams")
    offers = client.get("/offers")
    names = {int(o["id"]): o.get("name", str(o["id"])) for o in offers}
    result = []
    for stream in streams:
        remote = normalized(stream.get("offers") or [])
        draft = db.get(StreamDraft, int(stream["id"]))
        if not draft:
            draft = StreamDraft(stream_id=stream["id"], campaign_id=campaign_id, name=stream["name"], baseline=remote, offers=[{"offer_id": o["offer_id"], "name": names.get(o["offer_id"], str(o["offer_id"])), "share": o["share"], "removed": False, "pinned": False} for o in remote], dirty=False, conflict=False)
            db.add(draft)
        elif draft.dirty:
            draft.conflict = remote != draft.baseline
            draft.name = stream["name"]
        else:
            old = {o["offer_id"]: o for o in draft.offers}
            remote_ids = {o["offer_id"] for o in remote}
            merged = [{"offer_id": o["offer_id"], "name": names.get(o["offer_id"], old.get(o["offer_id"], {}).get("name", str(o["offer_id"]))), "share": o["share"], "removed": False, "pinned": old.get(o["offer_id"], {}).get("pinned", False)} for o in remote]
            merged += [{**o, "share": 0, "removed": True, "pinned": False, "archived": True} for o in draft.offers if o["offer_id"] not in remote_ids]
            draft.offers, draft.baseline, draft.conflict, draft.name = merged, remote, False, stream["name"]
        result.append((draft, stream.get("schema")))
    db.commit()
    return [{**serialize(d), "schema": schema} for d, schema in result]


def find_draft(db, stream_id):
    draft = db.get(StreamDraft, stream_id)
    if not draft:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Load the campaign streams first")
    return draft


def mutate(db, draft, operation, offer_id, name=None):
    offers = [dict(o) for o in draft.offers]
    offer = next((o for o in offers if o["offer_id"] == offer_id), None)
    if operation == "add":
        if offer and not offer["removed"]:
            raise HTTPException(HTTPStatus.CONFLICT, "Offer has already been added")
        if offer:
            offer["was_archived"] = offer.get("archived", False)
            offer["removed"] = False
        else:
            offers.append({"offer_id": offer_id, "name": name, "share": 0, "pinned": False, "removed": False})
    elif not offer:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Offer not found in the stream")
    elif operation == "remove":
        offer["removed"] = True
    elif operation == "restore":
        offer["was_archived"] = offer.get("archived", False)
        offer["removed"] = False
    elif operation == "pin":
        if offer["removed"]:
            raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Cannot pin a removed offer")
        offer["pinned"] = not offer["pinned"]
        draft.offers = offers
        db.commit()
        return serialize(draft)
    draft.offers = distribute(offers)
    draft.dirty = True
    db.commit()
    return serialize(draft)


def cancel(db, draft):
    active = {o["offer_id"]: o for o in draft.baseline}
    restored = []
    for o in draft.offers:
        if o["offer_id"] in active:
            restored.append({**o, "share": active[o["offer_id"]]["share"], "removed": False})
        elif o.get("archived", False) or o.get("was_archived", False):
            restored.append({**o, "share": 0, "removed": True, "pinned": False})
    draft.offers, draft.dirty, draft.conflict = restored, False, False
    db.commit()
    return serialize(draft)


def publish(db, client, draft):
    remote = normalized(client.get(f"/streams/{draft.stream_id}").get("offers") or [])
    if remote != draft.baseline:
        draft.conflict = True
        db.commit()
        raise HTTPException(HTTPStatus.CONFLICT, "The stream changed in Keitaro. Cancel the draft, refresh the streams, and apply your changes again.")
    payload = [{"offer_id": o["offer_id"], "share": o["share"], "state": ACTIVE_STATE} for o in draft.offers if not o["removed"]]
    if payload and sum(o["share"] for o in payload) != TOTAL_TRAFFIC_SHARE:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Active offer shares must add up to 100%")
    client.put(f"/streams/{draft.stream_id}", {"offers": payload})
    actual = normalized(client.get(f"/streams/{draft.stream_id}").get("offers") or [])
    if actual != normalized(payload):
        draft.conflict = True
        db.commit()
        raise HTTPException(HTTPStatus.BAD_GATEWAY, "Keitaro saved a different offer list or shares. Refresh the stream and check the data.")
    draft.offers = [{**o, "archived": o["removed"], "was_archived": False} for o in draft.offers]
    draft.baseline, draft.dirty, draft.conflict = actual, False, False
    db.commit()
    return serialize(draft)



