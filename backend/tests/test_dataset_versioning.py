
def test_existing_dataset_version_contract_materializes_version_signature(registered):
    versions = list_versions(registered.id)
    assert versions
    assert all(len(version.version_signature) == 64 for version in versions)
    with session_scope() as session:
        columns = {
            row[1]
            for row in session.execute(select(text("name")).select_from(text("pragma_table_info('dataset_versions')")))
        }
        assert "version_signature" in columns

import copy
import hashlib
import json
import time

import pytest
from sqlalchemy import select, text

from app.api.schemas import DatasetUploadMetadata, TrainingConfig
from app.config import get_settings
from app.data.service import delete_dataset
from app.database import session_scope
from app.dataset_versions.service import (
    compare_versions,
    create_version,
    dataset_card,
    get_version,
    list_versions,
    verify_version,
)
from app.manifests.service import get_manifest
from app.storage.entities import Dataset, DatasetVersion, Experiment, Run
from app.utils.errors import AppError


def metadata(name="Synthetic test fixture", target="observed_class", positive="positive", version="source-2"):
    return DatasetUploadMetadata(
        name=name, target=target, positive_label=positive, version=version,
        source="Synthetic test source", deidentified=True,
    )


def poll(client, job_id, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"/api/training/jobs/{job_id}").json()
        if body["status"] not in {"queued", "running", "cancel_requested"}:
            return body
        time.sleep(0.05)
    pytest.fail("Version-aware training did not finish.")


def test_registration_creates_immutable_v1_with_integrity_and_schema(registered):
    versions = list_versions(registered.id)
    assert len(versions) == 1
    version = versions[0]
    assert version.version_number == 1 and version.version_label == "v1"
    assert version.content_sha256 == registered.sha256
    assert len(version.schema_fingerprint) == 64
    assert version.immutable is True and version.status == "ready"
    assert verify_version(registered.id, version.id)["valid"] is True
    with session_scope() as session:
        dataset = session.get(Dataset, registered.id)
        assert dataset.current_version_id == version.id


def test_duplicate_content_reuses_version_and_changed_content_creates_v2(registered, biomedical_frame):
    original = biomedical_frame.to_csv(index=False).encode()
    existing, created = create_version(registered.id, original, "same.csv", metadata())
    assert created is False
    assert existing.version_label == "v1"

    changed = biomedical_frame.copy()
    changed.loc[0, "biomarker_0"] += 0.125
    second, created = create_version(
        registered.id, changed.to_csv(index=False).encode(), "changed.csv", metadata(version="source-3")
    )
    assert created is True and second.version_label == "v2"
    assert second.content_sha256 != existing.content_sha256
    assert second.schema_fingerprint == existing.schema_fingerprint
    assert compare_versions(registered.id, existing.id, second.id)["classification"] == "SAME_SCHEMA_DIFFERENT_DATA"


def test_schema_and_target_semantics_create_distinct_version_states(registered, biomedical_frame):
    base = list_versions(registered.id)[0]
    changed_schema = biomedical_frame.rename(columns={"biomarker_5": "renamed_marker"})
    schema_version, _ = create_version(
        registered.id, changed_schema.to_csv(index=False).encode(), "schema.csv", metadata(version="schema-change")
    )
    assert compare_versions(registered.id, base.id, schema_version.id)["classification"] == "SCHEMA_CHANGED"

    same_bytes = biomedical_frame.to_csv(index=False).encode()
    target_version, created = create_version(
        registered.id, same_bytes, "target-semantics.csv",
        metadata(positive="negative", version="reversed-positive-class"),
    )
    assert created is True
    assert target_version.content_sha256 == base.content_sha256
    assert target_version.version_signature != base.version_signature
    assert target_version.positive_label == "negative"
    target_comparison = compare_versions(registered.id, base.id, target_version.id)
    assert target_comparison["classification"] == "IDENTICAL_CONTENT"
    assert target_comparison["differences"]["target_changed"] is True
    from app.data.splitting import prepare_data
    exact = prepare_data(TrainingConfig(
        dataset_id=registered.id, dataset_version_id=base.id, max_samples=None
    ))
    assert exact.provenance["positive_label"] == "positive"
    assert int(exact.y.sum()) == base.class_distribution["positive"]


def test_dataset_card_is_version_specific_safe_and_non_clinical(registered):
    version = list_versions(registered.id)[0]
    card = dataset_card(registered.id, version.id)
    assert card["identity"]["dataset_version_id"] == version.id
    assert card["provenance"]["content_sha256"] == version.content_sha256
    assert set(card["data"]) == {"rows", "features", "feature_types", "target", "positive_class", "negative_class", "class_distribution"}
    assert any("not clinical validation" in item for item in card["limitations"])
    assert "storage_reference" not in json.dumps(card)


def test_integrity_tampering_is_detected_without_repair(registered):
    version = list_versions(registered.id)[0]
    path = get_settings().root / version.storage_reference
    original = path.read_bytes()
    try:
        path.write_bytes(original + b"\n")
        result = verify_version(registered.id, version.id)
        assert result["valid"] is False
        assert result["errors"] == ["dataset_version_hash_mismatch"]
        assert path.read_bytes() != original
    finally:
        path.write_bytes(original)


def test_version_records_have_no_mutation_or_delete_api(client, registered):
    version = list_versions(registered.id)[0]
    assert client.patch(f"/api/datasets/{registered.id}/versions/{version.id}", json={}).status_code == 405
    assert client.delete(f"/api/datasets/{registered.id}/versions/{version.id}").status_code == 405


def test_version_api_listing_card_provenance_verify_compare_and_security(client, registered, monkeypatch):
    version = list_versions(registered.id)[0]
    base = f"/api/datasets/{registered.id}/versions"
    assert client.get(base).json()[0]["id"] == version.id
    assert client.get(f"{base}/{version.id}").json()["immutable"] is True
    assert client.get(f"{base}/{version.id}/card").json()["identity"]["version"] == "v1"
    assert client.get(f"{base}/{version.id}/provenance").json()["schema_fingerprint"] == version.schema_fingerprint
    assert client.get(f"{base}/{version.id}/verify").json()["valid"] is True
    assert client.get(f"{base}/compare", params={"left": version.id, "right": version.id}).json()["classification"] == "IDENTICAL_CONTENT"
    assert client.get(f"/api/datasets/{registered.id}/versions/not-a-uuid").status_code == 422

    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "api_token", "dataset-version-secret")
    assert client.get(base).status_code == 401
    assert client.get(base, headers={"Authorization": "Bearer dataset-version-secret"}).status_code == 200


def test_run_and_manifest_reference_exact_dataset_version(client, registered):
    version = list_versions(registered.id)[0]
    config = TrainingConfig(
        dataset_id=registered.id, dataset_version_id=version.id,
        models=["logistic_regression"], max_samples=None,
    )
    response = client.post("/api/training/jobs", json=config.model_dump(mode="json"))
    assert response.status_code == 202
    result = poll(client, response.json()["job"]["id"])
    assert result["status"] == "succeeded"
    with session_scope() as session:
        run = session.scalar(select(Run).where(Run.id == response.json()["job"]["run_id"]))
        assert run.dataset_id == registered.id
        assert run.dataset_version_id == version.id
    _, _, manifest = get_manifest(run.id)
    assert manifest["dataset"]["dataset_id"] == registered.id
    assert manifest["dataset"]["dataset_version_id"] == version.id
    assert manifest["dataset"]["dataset_version"] == "v1"
    assert manifest["dataset"]["sha256"] == version.content_sha256
    assert manifest["dataset"]["schema_fingerprint"] == version.schema_fingerprint


def test_dataset_version_from_other_dataset_is_rejected(registered, biomedical_frame):
    from app.data.service import register_csv
    other = register_csv(
        biomedical_frame.to_csv(index=False).encode(), "other.csv",
        metadata(name="Other logical dataset"),
    )
    other_version = list_versions(other.id)[0]
    with pytest.raises(AppError, match="does not belong"):
        from app.data.splitting import prepare_data
        prepare_data(TrainingConfig(dataset_id=registered.id, dataset_version_id=other_version.id, max_samples=None))


def test_referenced_dataset_version_is_protected_from_destructive_delete(registered):
    version = list_versions(registered.id)[0]
    with session_scope() as session:
        experiment = Experiment(
            dataset_id=registered.id, status="completed", config={}, summary={}
        )
        session.add(experiment)
        session.flush()
        session.add(Run(
            experiment_id=experiment.id, dataset_id=registered.id,
            dataset_version_id=version.id, status="completed",
            operation_key=f"dataset-version-delete-test:{version.id}",
            config={}, execution_metadata={}, reproducibility_metadata={},
            result_summary={},
        ))
    with pytest.raises(AppError, match="retained for reproducibility"):
        delete_dataset(registered.id)
    assert (get_settings().root / version.storage_reference).is_file()
    assert verify_version(registered.id, version.id)["valid"] is True
