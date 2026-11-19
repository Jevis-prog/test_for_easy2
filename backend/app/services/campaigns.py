from http import HTTPStatus

import secrets
import pycountry
from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator
from app.integrations.keitaro import KeitaroClient


MAX_CAMPAIGN_NAME_LENGTH = 255
COUNTRY_CODE_LENGTH = 2
ALIAS_RANDOM_BYTES = 5
GOOGLE_REDIRECT_URL = "https://google.com"
TOTAL_TRAFFIC_SHARE = 100
FIRST_STREAM_POSITION = 1
SECOND_STREAM_POSITION = 2


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_CAMPAIGN_NAME_LENGTH)
    geo: str = Field(min_length=COUNTRY_CODE_LENGTH, max_length=COUNTRY_CODE_LENGTH)
    offer_id: int = Field(gt=0)
    domain_id: int = Field(gt=0)
    group_id: int = Field(gt=0)
    traffic_source_id: int = Field(gt=0)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError("Enter a campaign name")
        return value.strip()

    @field_validator("geo")
    @classmethod
    def valid_geo(cls, value):
        value = value.upper()
        if not pycountry.countries.get(alpha_2=value):
            raise ValueError("Enter an ISO alpha-2 country code")
        return value


def create_campaign(client: KeitaroClient, data: CampaignCreate):
    client.get(f"/offers/{data.offer_id}")
    campaign = client.post("/campaigns", {"name": data.name, "alias": secrets.token_hex(ALIAS_RANDOM_BYTES), "type": "position", "domain_id": data.domain_id, "group_id": data.group_id, "traffic_source_id": data.traffic_source_id, "state": "disabled"})
    campaign_id = campaign["id"]
    try:
        client.post("/streams", {"campaign_id": campaign_id, "name": "Geo → Google", "type": "regular", "position": FIRST_STREAM_POSITION, "schema": "redirect", "action_type": "http", "action_payload": GOOGLE_REDIRECT_URL, "filters": [{"name": "country", "mode": "accept", "payload": [data.geo]}]})
        client.post("/streams", {"campaign_id": campaign_id, "name": "Offers", "type": "default", "position": SECOND_STREAM_POSITION, "schema": "landings", "action_type": "http", "offers": [{"offer_id": data.offer_id, "share": TOTAL_TRAFFIC_SHARE, "state": "active"}]})
        client.put(f"/campaigns/{campaign_id}", {"state": "active"})
    except HTTPException as exc:
        raise HTTPException(HTTPStatus.BAD_GATEWAY, f"Campaign #{campaign_id} was created disabled, but setup did not finish. Check it in Keitaro. {exc.detail}") from exc
    return campaign
