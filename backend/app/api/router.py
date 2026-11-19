from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.config import settings
from app.db.database import get_db
from app.integrations.keitaro import KeitaroClient
from app.services.campaigns import CampaignCreate, create_campaign
from app.services import streams

REFERENCE_PATHS = {"offers": "/offers", "domains": "/domains", "groups": "/groups", "sources": "/traffic_sources"}
CAMPAIGN_GROUP_TYPE = "campaigns"
SEARCH_RESULTS_LIMIT = 100
OFFER_OPERATIONS = frozenset({"add", "remove", "restore", "pin"})

router = APIRouter(prefix="/api")


def client():
    return KeitaroClient()


@router.get("/campaigns")
def campaigns(k=Depends(client)):
    return k.get("/campaigns")


@router.post("/campaigns")
def new_campaign(data: CampaignCreate, k=Depends(client)):
    return create_campaign(k, data)


@router.get("/references/{kind}")
def references(kind: str, q: str = "", k=Depends(client)):
    if kind not in REFERENCE_PATHS:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Reference list not found")
    items = k.get(REFERENCE_PATHS[kind], **({"params": {"type": CAMPAIGN_GROUP_TYPE}} if kind == "groups" else {}))
    if q:
        items = [item for item in items if q.casefold() in str(item.get("name", item.get("domain", ""))).casefold() or q in str(item.get("id", ""))]
    return items[:SEARCH_RESULTS_LIMIT] if q else items


@router.get("/campaigns/{campaign_id}/streams")
def get_streams(campaign_id: int, db: Session = Depends(get_db), k=Depends(client)):
    return streams.fetch_streams(db, k, campaign_id)


class OfferChange(BaseModel):
    offer_id: int = Field(gt=0)


@router.post("/streams/{stream_id}/offers/{operation}")
def change_offer(stream_id: int, operation: str, data: OfferChange, db: Session = Depends(get_db), k=Depends(client)):
    if operation not in OFFER_OPERATIONS:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Operation not found")
    name = None
    if operation == "add":
        offer = k.get(f"/offers/{data.offer_id}")
        name = offer.get("name", str(data.offer_id))
    return streams.mutate(db, streams.find_draft(db, stream_id), operation, data.offer_id, name)


@router.post("/streams/{stream_id}/cancel")
def cancel(stream_id: int, db: Session = Depends(get_db)):
    return streams.cancel(db, streams.find_draft(db, stream_id))


@router.post("/streams/{stream_id}/publish")
def publish(stream_id: int, db: Session = Depends(get_db), k=Depends(client)):
    return streams.publish(db, k, streams.find_draft(db, stream_id))


@router.get("/tracker")
def tracker():
    return {"url": settings.keitaro_url.rstrip("/")}
