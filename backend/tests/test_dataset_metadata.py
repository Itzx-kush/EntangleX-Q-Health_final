import numpy as np
import pandas as pd

from app.api.schemas import DatasetUploadMetadata
from app.data.catalog import get_benchmark
from app.data.metadata import suggest_metadata
from app.data.quality import inspection_report
from app.data.service import register_file


def profile(frame, filename="dataset.csv", **kwargs):
    target = kwargs.pop("target", None)
    positive_label = kwargs.pop("positive_label", None)
    report = inspection_report(frame, target, positive_label)
    return suggest_metadata(filename, report, content_hash="abcdef1234567890", **kwargs)


def test_filename_name_target_classes_and_conservative_ambiguity():
    frame = pd.DataFrame({"biomarker": np.arange(20), "diagnosis": ["M", "B"] * 10})
    suggestions, warnings = profile(frame, "breast_cancer_data.csv")
    assert suggestions["name"] == "Breast Cancer Data"
    assert suggestions["target"] == "diagnosis"
    assert suggestions["target_classes"] == ["M", "B"]
    assert suggestions["positive_label"] is None
    assert suggestions["negative_label"] is None
    assert suggestions["domain"] == "oncology"
    assert suggestions["source"] == "User-provided"
    assert suggestions["version_source"] == "generated_snapshot"
    assert "positive class" in " ".join(warnings)


def test_positive_class_rules_and_negative_derivation():
    numeric, _ = profile(pd.DataFrame({"feature": np.arange(20), "outcome": [0, 1] * 10}))
    assert numeric["positive_label"] == "1"
    assert numeric["negative_label"] == "0"
    assert numeric["positive_label_source"] == "binary_numeric_rule"

    semantic, _ = profile(pd.DataFrame({"feature": np.arange(20), "result": ["positive", "negative"] * 10}))
    assert semantic["positive_label"] == "positive"
    assert semantic["negative_label"] == "negative"
    assert semantic["positive_label_source"] == "semantic_label_rule"

    ambiguous, warnings = profile(pd.DataFrame({"feature": np.arange(20), "group": ["case", "control"] * 10}), target="group", positive_label=None, selected_target="group")
    assert ambiguous["positive_label"] is None
    assert ambiguous["negative_label"] is None
    assert any("positive class" in warning for warning in warnings)


def test_version_domain_and_source_origins():
    suggestions, warnings = profile(pd.DataFrame({"feature": np.arange(20), "outcome": [0, 1] * 10}), "patient_outcomes_v2.1.csv")
    assert suggestions["version"] == "v2.1"
    assert suggestions["version_source"] == "filename"
    assert suggestions["domain_source"] == "fallback_biomedical"
    assert suggestions["source_source"] == "default_user_upload"
    assert not any("generated snapshot" in warning for warning in warnings)


def test_curated_catalog_overrides_filename_inference():
    catalog = get_benchmark("wdbc")
    report = inspection_report(pd.DataFrame({"diagnosis": ["malignant", "benign"] * 10, "feature": range(20)}))
    suggestions, warnings = suggest_metadata("random_name.csv", report, catalog=catalog)
    assert suggestions["name"] == "Breast Cancer Wisconsin Diagnostic"
    assert suggestions["target"] == "diagnosis"
    assert suggestions["positive_label"] == "malignant"
    assert suggestions["negative_label"] == "benign"
    assert suggestions["domain_source"] == "catalog"
    assert suggestions["version_source"] == "catalog"
    assert warnings == []


def test_registration_preserves_suggestion_provenance():
    frame = pd.DataFrame({"feature": range(20), "outcome": [0, 1] * 10})
    report = inspection_report(frame, "outcome", "1")
    suggestions, warnings = suggest_metadata("pima_diabetes.csv", report, content_hash="abcdef1234567890", selected_target="outcome", selected_positive="1")
    metadata = DatasetUploadMetadata(
        name=suggestions["name"], domain=suggestions["domain"], source=suggestions["source"], version=suggestions["version"],
        target="outcome", positive_label="1", negative_label="0", deidentified=True, metadata_confirmed=True,
        metadata_sources={key: value for key, value in suggestions.items() if key.endswith("_source")},
        metadata_suggestions=suggestions, metadata_warnings=warnings,
    )
    record = register_file(frame.to_csv(index=False).encode(), "pima_diabetes.csv", metadata)
    assert record.provenance["metadata_suggestions"]["positive_label"] == "1"
    assert record.provenance["metadata_sources"]["positive_label_source"] == "user_selected"
    assert record.provenance["metadata_confirmed"] is True
    assert record.provenance["dataset_hash"] == record.sha256


def test_inspection_first_register_route_requires_metadata_review(client):
    frame = pd.DataFrame({"feature": range(20), "outcome": [0, 1] * 10})
    content = frame.to_csv(index=False).encode()
    metadata = {"name": "Pima Diabetes", "domain": "endocrinology", "source": "User-provided", "version": "upload-snapshot-test", "target": "outcome", "positive_label": "1", "negative_label": "0", "deidentified": True}
    blocked = client.post("/api/datasets/register", data={"metadata_json": __import__('json').dumps(metadata)}, files={"file": ("pima_diabetes.csv", content, "text/csv")})
    assert blocked.status_code == 422
    assert blocked.json()["error"]["code"] == "metadata_confirmation_required"
    metadata["metadata_confirmed"] = True
    registered = client.post("/api/datasets/register", data={"metadata_json": __import__('json').dumps(metadata)}, files={"file": ("pima_diabetes.csv", content, "text/csv")})
    assert registered.status_code == 201, registered.text
    assert registered.json()["provenance"]["negative_label"] == "0"
    assert registered.json()["provenance"]["metadata_confirmed"] is True
