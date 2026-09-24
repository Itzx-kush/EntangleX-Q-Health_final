import hashlib
import numpy as np
import pytest
from app.data.quality import quality_report, validate_target
from app.data.service import load_frame, parse_csv, register_demo
from app.utils.errors import AppError

def test_original_bytes_hash_and_provenance(registered, biomedical_frame):
    content = biomedical_frame.to_csv(index=False).encode()
    assert registered.sha256 == hashlib.sha256(content).hexdigest()
    assert registered.provenance["positive_label"] == "positive"
    assert registered.provenance["is_demo"] is False
    record, frame = load_frame(registered.id)
    assert record.sha256 == registered.provenance["dataset_hash"]
    assert len(frame) == len(biomedical_frame)
    assert record.provenance["row_count"] == len(frame)

def test_demo_mapping_and_no_identifiers():
    from sklearn.datasets import load_breast_cancer
    demo = register_demo()
    _, frame = load_frame(demo.id)
    source = load_breast_cancer(as_frame=True)
    assert frame["diagnosis"].tolist() == np.where(source.target == 0, "malignant", "benign").tolist()
    assert demo.provenance["positive_label"] == "malignant"
    assert demo.provenance["is_demo"] is True
    assert "CC BY" in demo.provenance["license"]
    assert "id" not in frame and "name" not in frame
    assert register_demo().id == demo.id

@pytest.mark.parametrize("content", [b"a,a,target\n1,2,yes\n", b" a,b\n1,2\n", b"a,b\x00\n1,2\n", b"a,b\n"])
def test_invalid_csv_rejected(content):
    with pytest.raises(AppError):
        parse_csv(content, "target")

def test_diabetes_readmission_target_derivation():
    content = b"encounter_id,readmitted,age\n1,<30,[30-40)\n2,NO,[40-50)\n3,>30,[50-60)\n4,NO,[60-70)\n"
    frame = parse_csv(content, "readmitted_30d")
    assert frame["readmitted_30d"].tolist() == [1, 0, 0, 0]
    assert "readmitted" not in frame.columns
    assert "encounter_id" in frame.columns

def test_missing_target(biomedical_frame):
    with pytest.raises(AppError, match="absent"):
        validate_target(biomedical_frame, "nonexistent", "positive")

def test_target_not_a_feature(biomedical_frame):
    with pytest.raises(AppError, match="input feature"):
        validate_target(biomedical_frame, "observed_class", "positive", ["biomarker_0", "observed_class"])

def test_binary_target_required(biomedical_frame):
    biomedical_frame["observed_class"] = "positive"
    with pytest.raises(AppError):
        quality_report(biomedical_frame, "observed_class", "positive")

def test_missing_label_not_imputed(biomedical_frame):
    biomedical_frame.loc[0, "observed_class"] = None
    with pytest.raises(AppError, match="missing"):
        quality_report(biomedical_frame, "observed_class", "positive")

def test_quality_catches_imbalance_missing_and_infinity(biomedical_frame):
    biomedical_frame["observed_class"] = ["positive"] * 10 + ["negative"] * 110
    biomedical_frame.loc[0, "biomarker_0"] = np.inf
    report = quality_report(biomedical_frame, "observed_class", "positive")
    assert report["class_imbalance"] is True
    assert report["infinite_values"]["biomarker_0"] == 1
    assert report["missing_values"]["biomarker_2"] == 1
    assert report["blockers"]

def test_identifiers_and_target_proxies_block_training(biomedical_frame):
    biomedical_frame["patient_id"] = np.arange(len(biomedical_frame))
    biomedical_frame["proxy"] = biomedical_frame["observed_class"]
    report = quality_report(biomedical_frame, "observed_class", "positive")
    assert "patient_id" in report["identifier_features"]
    assert "proxy" in report["suspiciously_predictive_features"]
    assert len(report["blockers"]) >= 2

def test_categorical_values_are_not_in_quality_report(biomedical_frame):
    biomedical_frame["assay"] = "private-category-text"
    report = quality_report(biomedical_frame, "observed_class", "positive")
    assert "private-category-text" not in str(report)
