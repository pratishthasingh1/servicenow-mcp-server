from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("servicenow-mcp")

TABLE = "change_request"
DISPLAY_FIELDS = [
    "sys_id",
    "number",
    "short_description",
    "description",
    "state",
    "type",
    "category",
    "risk",
    "impact",
    "priority",
    "assignment_group",
    "assigned_to",
    "opened_by",
    "start_date",
    "end_date",
    "approval",
    "close_code",
    "close_notes",
    "work_notes",
    "sys_created_on",
    "sys_updated_on",
]


class ServiceNowAuthError(Exception):
    pass


class ServiceNowAPIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"ServiceNow API error {status_code}: {detail}")


class ServiceNowClient:
    """Async client for ServiceNow REST API with OAuth 2.0 and basic auth."""

    def __init__(self) -> None:
        self.instance_url = os.environ["SNOW_INSTANCE_URL"].rstrip("/")
        self.auth_method = os.environ.get("SNOW_AUTH_METHOD", "basic").lower()
        self.username = os.environ["SNOW_USERNAME"]
        self.password = os.environ["SNOW_PASSWORD"]
        self.client_id = os.environ.get("SNOW_CLIENT_ID", "")
        self.client_secret = os.environ.get("SNOW_CLIENT_SECRET", "")

        self._access_token: Optional[str] = None
        self._token_expiry: float = 0
        self._http: Optional[httpx.AsyncClient] = None

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self.instance_url,
                timeout=httpx.Timeout(30.0),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._http

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # ── Authentication ──────────────────────────────────────────────

    async def _ensure_auth(self, client: httpx.AsyncClient) -> None:
        if self.auth_method == "basic":
            client.auth = httpx.BasicAuth(self.username, self.password)
        elif self.auth_method == "oauth":
            await self._ensure_oauth_token(client)
        else:
            raise ServiceNowAuthError(f"Unknown auth method: {self.auth_method}")

    async def _ensure_oauth_token(self, client: httpx.AsyncClient) -> None:
        if self._access_token and time.time() < self._token_expiry:
            client.headers["Authorization"] = f"Bearer {self._access_token}"
            return

        token_url = f"{self.instance_url}/oauth_token.do"
        payload = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
        }

        resp = await client.post(token_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        if resp.status_code != 200:
            raise ServiceNowAuthError(f"OAuth token request failed ({resp.status_code}): {resp.text}")

        token_data = resp.json()
        self._access_token = token_data["access_token"]
        self._token_expiry = time.time() + int(token_data.get("expires_in", 1800)) - 60
        client.headers["Authorization"] = f"Bearer {self._access_token}"
        logger.info("OAuth token acquired, expires in %s seconds", token_data.get("expires_in"))

    # ── Low-level request helpers ────────────────────────────────────

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        client = await self._get_http()
        await self._ensure_auth(client)
        resp = await client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            detail = resp.text
            try:
                error_body = resp.json()
                if "error" in error_body:
                    detail = error_body["error"].get("message", detail)
            except Exception:
                pass
            raise ServiceNowAPIError(resp.status_code, detail)
        return resp.json()

    def _table_url(self, table: str = TABLE, sys_id: str = "") -> str:
        base = f"/api/now/table/{table}"
        if sys_id:
            base = f"{base}/{sys_id}"
        return base

    @staticmethod
    def _format_fields() -> str:
        return ",".join(DISPLAY_FIELDS)

    # ── CRUD Operations ─────────────────────────────────────────────

    async def create_change_request(self, payload: dict) -> dict:
        data = await self._request(
            "POST",
            self._table_url(),
            json=payload,
            params={"sysparm_fields": self._format_fields(), "sysparm_display_value": "true"},
        )
        return data.get("result", data)

    async def get_change_request(self, identifier: str) -> dict:
        """Get a change request by CHG number or sys_id."""
        if identifier.upper().startswith("CHG"):
            params = {
                "sysparm_query": f"number={identifier.upper()}",
                "sysparm_fields": self._format_fields(),
                "sysparm_display_value": "true",
                "sysparm_limit": "1",
            }
            data = await self._request("GET", self._table_url(), params=params)
            results = data.get("result", [])
            if not results:
                raise ServiceNowAPIError(404, f"Change request {identifier} not found")
            return results[0]
        else:
            params = {
                "sysparm_fields": self._format_fields(),
                "sysparm_display_value": "true",
            }
            data = await self._request("GET", self._table_url(sys_id=identifier), params=params)
            return data.get("result", data)

    async def update_change_request(self, identifier: str, payload: dict) -> dict:
        sys_id = await self._resolve_sys_id(identifier)
        data = await self._request(
            "PATCH",
            self._table_url(sys_id=sys_id),
            json=payload,
            params={"sysparm_fields": self._format_fields(), "sysparm_display_value": "true"},
        )
        return data.get("result", data)

    async def list_change_requests(
        self,
        query: str = "",
        limit: int = 20,
        offset: int = 0,
        order_by: str = "-sys_created_on",
    ) -> list[dict]:
        params: dict[str, Any] = {
            "sysparm_fields": self._format_fields(),
            "sysparm_display_value": "true",
            "sysparm_limit": str(limit),
            "sysparm_offset": str(offset),
            "sysparm_orderby": order_by,
        }
        if query:
            params["sysparm_query"] = query
        data = await self._request("GET", self._table_url(), params=params)
        return data.get("result", [])

    async def add_work_note(self, identifier: str, note: str) -> dict:
        sys_id = await self._resolve_sys_id(identifier)
        data = await self._request(
            "PATCH",
            self._table_url(sys_id=sys_id),
            json={"work_notes": note},
            params={"sysparm_fields": self._format_fields(), "sysparm_display_value": "true"},
        )
        return data.get("result", data)

    async def get_approval_status(self, identifier: str) -> dict:
        sys_id = await self._resolve_sys_id(identifier)
        cr = await self.get_change_request(sys_id)

        approvals_data = await self._request(
            "GET",
            self._table_url(table="sysapproval_approver"),
            params={
                "sysparm_query": f"sysapproval={sys_id}",
                "sysparm_fields": "sys_id,approver,state,comments,sys_updated_on",
                "sysparm_display_value": "true",
            },
        )

        return {
            "change_number": cr.get("number", ""),
            "approval_status": cr.get("approval", ""),
            "state": cr.get("state", ""),
            "approvers": approvals_data.get("result", []),
        }

    # ── Helpers ──────────────────────────────────────────────────────

    async def _resolve_sys_id(self, identifier: str) -> str:
        """Resolve a CHG number to a sys_id, or pass through if already a sys_id."""
        if identifier.upper().startswith("CHG"):
            record = await self.get_change_request(identifier)
            sid = record.get("sys_id", "")
            if isinstance(sid, dict):
                return sid.get("value", sid.get("display_value", ""))
            return str(sid)
        return identifier
