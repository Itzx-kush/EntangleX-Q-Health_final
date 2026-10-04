"""Backend-only Supabase database and private-storage access."""
from __future__ import annotations

from urllib.parse import quote

import httpx

from ..config import get_settings
from ..utils.errors import AppError

_TABLE = "saved_research_reports"
_BUCKET = "saved-research-reports"


class SupabaseSavedReportGateway:
    def _settings(self):
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise AppError("saved_reports_not_configured", "Saved research reports are not configured for this deployment.", 503)
        return settings

    def _headers(self, *, json_response: bool = True) -> dict[str, str]:
        settings = self._settings()
        headers = {"apikey": settings.supabase_service_role_key, "Authorization": f"Bearer {settings.supabase_service_role_key}"}
        if json_response:
            headers["Accept"] = "application/json"
        return headers

    def _database_url(self) -> str:
        return self._settings().supabase_url.rstrip("/") + f"/rest/v1/{_TABLE}"

    def _storage_url(self, suffix: str) -> str:
        return self._settings().supabase_url.rstrip("/") + "/storage/v1" + suffix

    @staticmethod
    def _request(method: str, url: str, message: str, **kwargs) -> httpx.Response:
        try:
            return httpx.request(method, url, **kwargs)
        except httpx.RequestError as error:
            raise AppError("saved_report_storage_failure", message, 502) from error

    @staticmethod
    def _raise(response: httpx.Response, message: str) -> None:
        if response.is_success:
            return
        if response.status_code in (401, 403):
            raise AppError("saved_report_forbidden", "The saved report is unavailable for this account.", 404)
        raise AppError("saved_report_storage_failure", message, 502)

    def list(self, owner_user_id: str, *, experiment_id: str | None = None) -> list[dict]:
        params = {"select": "*", "owner_user_id": f"eq.{owner_user_id}", "status": "eq.active", "order": "saved_at.desc"}
        if experiment_id:
            params["experiment_id"] = f"eq.{experiment_id}"
        response = self._request("GET", self._database_url(), "Saved research reports could not be loaded.", headers=self._headers(), params=params, timeout=15)
        self._raise(response, "Saved research reports could not be loaded.")
        return response.json()

    def find_existing(self, owner_user_id: str, experiment_id: str, report_fingerprint: str, report_version: str) -> dict | None:
        response = self._request("GET", self._database_url(), "Saved-report state could not be checked.", headers=self._headers(), params={
            "select": "*", "owner_user_id": f"eq.{owner_user_id}", "experiment_id": f"eq.{experiment_id}", "report_fingerprint": f"eq.{report_fingerprint}",
            "report_version": f"eq.{report_version}", "status": "eq.active", "limit": "1",
        }, timeout=15)
        self._raise(response, "Saved-report state could not be checked.")
        rows = response.json()
        return rows[0] if rows else None

    def get(self, owner_user_id: str, saved_report_id: str) -> dict | None:
        response = self._request("GET", self._database_url(), "The saved research report could not be loaded.", headers=self._headers(), params={
            "select": "*", "owner_user_id": f"eq.{owner_user_id}", "id": f"eq.{saved_report_id}", "status": "eq.active", "limit": "1",
        }, timeout=15)
        self._raise(response, "The saved research report could not be loaded.")
        rows = response.json()
        return rows[0] if rows else None

    def upload_pdf(self, storage_reference: str, content: bytes) -> None:
        path = quote(storage_reference, safe="/")
        response = self._request(
            "POST", self._storage_url(f"/object/{quote(_BUCKET, safe='')}/{path}"), "The private PDF could not be stored.",
            headers={**self._headers(json_response=False), "Content-Type": "application/pdf", "x-upsert": "false"},
            content=content,
            timeout=30,
        )
        self._raise(response, "The private PDF could not be stored.")

    def delete_pdf(self, storage_reference: str) -> None:
        response = self._request(
            "DELETE", self._storage_url(f"/object/{quote(_BUCKET, safe='')}/{quote(storage_reference, safe='/')}"), "The private PDF could not be cleaned up.",
            headers=self._headers(json_response=False), timeout=30,
        )
        self._raise(response, "The private PDF could not be cleaned up.")

    def insert(self, record: dict) -> dict:
        response = self._request(
            "POST", self._database_url(), "Saved-report metadata could not be stored.", headers={**self._headers(), "Content-Type": "application/json", "Prefer": "return=representation"},
            json=record, timeout=15,
        )
        if response.status_code == 409:
            raise AppError("saved_report_conflict", "This exact research report is already saved.", 409)
        self._raise(response, "Saved-report metadata could not be stored.")
        rows = response.json()
        if not rows:
            raise AppError("saved_report_storage_failure", "Saved-report metadata was not returned by storage.", 502)
        return rows[0]

    def download_pdf(self, storage_reference: str) -> bytes:
        response = self._request(
            "GET", self._storage_url(f"/object/authenticated/{quote(_BUCKET, safe='')}/{quote(storage_reference, safe='/')}"), "The private PDF could not be downloaded.",
            headers=self._headers(json_response=False), timeout=30,
        )
        self._raise(response, "The private PDF could not be downloaded.")
        return response.content

    def archive(self, owner_user_id: str, saved_report_id: str, deleted_at: str) -> dict | None:
        response = self._request(
            "PATCH", self._database_url(), "The saved research report could not be deleted.", headers={**self._headers(), "Content-Type": "application/json", "Prefer": "return=representation"},
            params={"owner_user_id": f"eq.{owner_user_id}", "id": f"eq.{saved_report_id}", "status": "eq.active"}, json={"status": "deleted", "deleted_at": deleted_at, "updated_at": deleted_at}, timeout=15,
        )
        self._raise(response, "The saved research report could not be deleted.")
        rows = response.json()
        return rows[0] if rows else None


gateway = SupabaseSavedReportGateway()
