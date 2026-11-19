from http import HTTPStatus

import httpx
from fastapi import HTTPException
from app.config import settings


ADMIN_API_PREFIX = "/admin_api/v1"
REQUEST_TIMEOUT_SECONDS = 20
MAX_ERROR_RESPONSE_LENGTH = 500


class KeitaroClient:
    def __init__(self):
        if not settings.keitaro_url or not settings.keitaro_api_key:
            raise HTTPException(HTTPStatus.SERVICE_UNAVAILABLE, "Set KEITARO_URL and KEITARO_API_KEY in backend/.env")
        self.url = settings.keitaro_url.rstrip("/") + ADMIN_API_PREFIX
        self.headers = {"Api-Key": settings.keitaro_api_key}

    def request(self, method, path, **kwargs):
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, headers=self.headers) as client:
                response = client.request(method, self.url + path, **kwargs)
                response.raise_for_status()
                return response.json() if response.content else None
        except httpx.HTTPStatusError as exc:
            raise HTTPException(HTTPStatus.BAD_GATEWAY, f"Keitaro returned an error {exc.response.status_code}: {exc.response.text[:MAX_ERROR_RESPONSE_LENGTH]}") from exc
        except httpx.RequestError as exc:
            raise HTTPException(HTTPStatus.BAD_GATEWAY, "Could not connect to Keitaro") from exc

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, data):
        return self.request("POST", path, json=data)

    def put(self, path, data):
        return self.request("PUT", path, json=data)
