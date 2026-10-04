import time
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from fastapi import Request

from app.saved_reports.auth import SupabasePrincipal
from app.utils.errors import AppError


class FakeGateway:
    def __init__(self):
        self.rows = {}
        self.files = {}
        self.users = {"token-a": str(uuid4()), "token-b": str(uuid4())}

    def list(self, owner, *, experiment_id=None):
        return [row.copy() for row in self.rows.values() if row["owner_user_id"] == owner and row["status"] == "active" and (not experiment_id or row["experiment_id"] == experiment_id)]

    def find_existing(self, owner, experiment_id, report_fingerprint, report_version):
        return next((row.copy() for row in self.list(owner, experiment_id=experiment_id) if row["report_fingerprint"] == report_fingerprint and row["report_version"] == report_version), None)

    def get(self, owner, saved_report_id):
        row = self.rows.get(saved_report_id)
        return row.copy() if row and row["owner_user_id"] == owner and row["status"] == "active" else None

    def upload_pdf(self, storage_reference, content):
        self.files[storage_reference] = bytes(content)

    def delete_pdf(self, storage_reference):
        self.files.pop(storage_reference, None)

    def insert(self, record):
        self.rows[record["id"]] = record.copy()
        return record.copy()

    def download_pdf(self, storage_reference):
        return self.files[storage_reference]

    def archive(self, owner, saved_report_id, deleted_at):
        row = self.rows.get(saved_report_id)
        if not row or row["owner_user_id"] != owner or row["status"] != "active":
            return None
        row.update({"status": "deleted", "deleted_at": deleted_at, "updated_at": deleted_at})
        return row.copy()


@pytest.fixture
def saved_report_auth(client, monkeypatch):
    from app.main import app
    from app.saved_reports.auth import require_supabase_user
    from app.saved_reports import service
    from app.experiments import reports

    fake = FakeGateway()

    async def principal(request: Request):
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        if token not in fake.users:
            raise AppError("authentication_required", "A valid session is required.", 401)
        return SupabasePrincipal(fake.users[token], token)

    app.dependency_overrides[require_supabase_user] = principal
    monkeypatch.setattr(service, "gateway", fake)
    monkeypatch.setattr(reports, "verify_installed_model", lambda model: None)
    yield fake
    app.dependency_overrides.pop(require_supabase_user, None)


def create_completed_experiment(config, registered):
    from app.database import session_scope
    from app.storage.entities import Experiment, ModelRecord
    with session_scope() as session:
        experiment = Experiment(name="Saved report test", dataset_id=registered.id, status="completed", config=config.model_dump(mode="json"), summary={"experiment_kind": "live_experiment", "dataset_provenance": registered.provenance})
        session.add(experiment); session.flush()
        model = ModelRecord(experiment_id=experiment.id, dataset_id=registered.id, model_type="logistic_regression", status="ready", details={"limitations": ["No external validation"]}, metrics={"test": {"accuracy": .8, "precision": .75, "recall": .7, "specificity": .9, "f1": .72, "roc_auc": .84}})
        session.add(model); session.flush()
        return experiment.id, model.id



def attach_evidence_package(experiment_id):
    from app.database import session_scope
    from app.storage.entities import Artifact, ResearchEvidencePackage
    with session_scope() as session:
        artifact = Artifact(
            experiment_id=experiment_id, artifact_type="research_evidence_package", name="Saved-report traceability fixture",
            description="Synthetic metadata-only test fixture.", integrity_hash="e" * 64, content_type="application/json",
            details={}, immutable=True, operation_key=f"saved-report-test-package:{experiment_id}",
        )
        session.add(artifact); session.flush()
        package = ResearchEvidencePackage(
            experiment_id=experiment_id, schema_version="research_evidence_package_v1", status="COMPLETE",
            package_fingerprint="f" * 64, configuration_fingerprint="c" * 64, source_context_type="live_run",
            evidence_inventory={}, provenance={"experiment_id": experiment_id}, limitations=[], evidence_gaps=[],
            manifest={"package_fingerprint": "f" * 64}, artifact_id=artifact.id,
        )
        session.add(package); session.flush()
        return package.id, artifact.id

def test_saved_report_end_to_end_owner_isolation_and_scientific_immutability(client, config, registered, saved_report_auth):
    from app.database import session_scope
    from app.storage.entities import Artifact, Experiment, ModelRecord, ResearchEvidencePackage
    from app.experiments.reports import report_data
    from app.saved_reports.service import _source_fingerprint

    experiment_id, model_id = create_completed_experiment(config, registered)
    package_id, package_artifact_id = attach_evidence_package(experiment_id)
    assert client.get("/api/me/research-reports").status_code == 401

    headers_a = {"Authorization": "Bearer token-a"}
    headers_b = {"Authorization": "Bearer token-b"}
    created = client.post("/api/me/research-reports", json={"experiment_id": experiment_id}, headers=headers_a)
    assert created.status_code == 201, created.text
    report = created.json()
    assert report["experiment_id"] == experiment_id
    assert report["already_saved"] is False
    assert report["content_type"] == "application/pdf"
    assert report["evidence_package_id"] == package_id
    assert report["evidence_package_fingerprint"] == "f" * 64
    assert report["report_version"] == "1"
    assert report["size_bytes"] > 5000
    assert "owner_user_id" not in report and "storage_reference" not in report and "access_token" not in report
    saved_id = report["saved_report_id"]
    stored = saved_report_auth.rows[saved_id]
    assert stored["owner_user_id"] == saved_report_auth.users["token-a"]
    assert stored["report_fingerprint"] == _source_fingerprint(report_data(experiment_id))
    assert stored["integrity_hash"] == __import__("hashlib").sha256(saved_report_auth.files[stored["storage_reference"]]).hexdigest()
    assert stored["storage_reference"].startswith(f"{saved_report_auth.users['token-a']}/{experiment_id}/")
    assert "://" not in stored["storage_reference"] and "/runtime" not in stored["storage_reference"]

    duplicate = client.post("/api/me/research-reports", json={"experiment_id": experiment_id}, headers=headers_a)
    assert duplicate.status_code == 201
    assert duplicate.json()["saved_report_id"] == saved_id
    assert duplicate.json()["already_saved"] is True
    assert len(saved_report_auth.rows) == 1

    listing = client.get("/api/me/research-reports", headers=headers_a)
    assert listing.status_code == 200 and [row["saved_report_id"] for row in listing.json()] == [saved_id]
    assert client.get(f"/api/me/research-reports?experiment_id={experiment_id}", headers=headers_a).json()[0]["saved_report_id"] == saved_id
    assert client.get(f"/api/me/research-reports/{saved_id}", headers=headers_a).status_code == 200
    download = client.get(f"/api/me/research-reports/{saved_id}/download", headers=headers_a)
    assert download.status_code == 200 and download.content.startswith(b"%PDF-")
    assert download.headers["content-type"].startswith("application/pdf")

    assert client.get("/api/me/research-reports", headers=headers_b).json() == []
    assert client.get(f"/api/me/research-reports/{saved_id}", headers=headers_b).status_code == 404
    assert client.get(f"/api/me/research-reports/{saved_id}/download", headers=headers_b).status_code == 404
    assert client.delete(f"/api/me/research-reports/{saved_id}", headers=headers_b).status_code == 404

    deleted = client.delete(f"/api/me/research-reports/{saved_id}", headers=headers_a)
    assert deleted.status_code == 200 and deleted.json()["status"] == "deleted"
    assert client.get("/api/me/research-reports", headers=headers_a).json() == []
    with session_scope() as session:
        assert session.get(Experiment, experiment_id) is not None
        assert session.get(ModelRecord, model_id) is not None
        assert session.get(ResearchEvidencePackage, package_id) is not None
        assert session.get(Artifact, package_artifact_id) is not None

    for format_name, content_type in (("html", "text/html"), ("json", "application/json"), ("pdf", "application/pdf")):
        response = client.get(f"/api/experiments/{experiment_id}/report?format={format_name}")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith(content_type)


def test_saved_report_integrity_failure_is_rejected(client, config, registered, saved_report_auth):
    experiment_id, _ = create_completed_experiment(config, registered)
    headers = {"Authorization": "Bearer token-a"}
    report = client.post("/api/me/research-reports", json={"experiment_id": experiment_id}, headers=headers).json()
    row = saved_report_auth.rows[report["saved_report_id"]]
    saved_report_auth.files[row["storage_reference"]] = b"tampered"
    response = client.get(f"/api/me/research-reports/{report['saved_report_id']}/download", headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "saved_report_integrity_failure"


def test_supabase_jwt_verification_validates_signature_issuer_audience_and_expiry(monkeypatch):
    from cryptography.hazmat.primitives.asymmetric import rsa
    from app.saved_reports import auth

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    user_id = str(uuid4())
    issuer = "https://example.supabase.co/auth/v1"
    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(supabase_url="https://example.supabase.co", supabase_jwt_audience="authenticated"))
    monkeypatch.setattr(auth, "_jwk_client", lambda url: SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key=public_key)))

    claims = {"sub": user_id, "role": "authenticated", "iss": issuer, "aud": "authenticated", "iat": int(time.time()) - 1, "exp": int(time.time()) + 60}
    valid = jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test"})
    assert auth.verify_supabase_access_token(valid).user_id == user_id

    for changes in ({"exp": int(time.time()) - 1}, {"aud": "wrong"}, {"iss": "https://forged.example/auth/v1"}):
        invalid = jwt.encode({**claims, **changes}, private_key, algorithm="RS256", headers={"kid": "test"})
        with pytest.raises(AppError) as error:
            auth.verify_supabase_access_token(invalid)
        assert error.value.status == 401

    unsigned = jwt.encode(claims, "not-used", algorithm="HS256")
    with pytest.raises(AppError):
        auth.verify_supabase_access_token(unsigned)
