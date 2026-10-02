import pytest
from uuid import uuid4
import numpy as np
import pandas as pd
from app.api.schemas import TrainingConfig
from app.data.splitting import prepare_data, PreparedData
from app.utils.errors import AppError

def make_dummy_data():
    np.random.seed(42)
    # 200 rows, groups 1 to 40 (5 rows per group)
    groups = np.repeat(np.arange(1, 41), 5)
    df = pd.DataFrame({
        "feature1": np.random.randn(200),
        "feature2": np.random.randn(200),
        "patient_id": groups,
        "target": np.random.choice(["Yes", "No"], size=200)
    })
    return df

class MockDataset:
    id = str(uuid4())
    sha256 = "dummy_hash"
    provenance = {
        "target": "target",
        "positive_label": "Yes",
        "negative_label": "No",
        "features": ["feature1", "feature2"]
    }

class MockDatasetVersion:
    content_sha256 = "dummy_version_hash"
    provenance = MockDataset.provenance

@pytest.fixture
def mock_load_versioned_frame(monkeypatch):
    def _mock_load(did, vid):
        df = make_dummy_data()
        return MockDataset(), MockDatasetVersion(), df
    monkeypatch.setattr("app.data.splitting.load_versioned_frame", _mock_load)
    
def test_default_behavior_remains_independent(mock_load_versioned_frame):
    config = TrainingConfig(dataset_id=MockDataset.id, models=["logistic_regression"])
    assert config.sampling_unit == "independent_samples"
    data = prepare_data(config)
    meta = data.split_metadata()
    assert meta["independent_samples_assumed"] is True

def test_missing_group_column_fails(mock_load_versioned_frame):
    with pytest.raises(ValueError, match="group_column is required"):
        TrainingConfig(dataset_id=MockDataset.id, sampling_unit="grouped_samples")

def test_group_column_not_in_dataset(mock_load_versioned_frame):
    config = TrainingConfig(dataset_id=MockDataset.id, sampling_unit="grouped_samples", group_column="missing_col")
    with pytest.raises(AppError, match="Group column 'missing_col' was not found"):
        prepare_data(config)

def test_group_column_equals_target(mock_load_versioned_frame):
    config = TrainingConfig(dataset_id=MockDataset.id, sampling_unit="grouped_samples", group_column="target")
    with pytest.raises(AppError, match="Group column cannot be the target"):
        prepare_data(config)

def test_group_column_in_features(mock_load_versioned_frame):
    config = TrainingConfig(dataset_id=MockDataset.id, sampling_unit="grouped_samples", group_column="feature1")
    with pytest.raises(AppError, match="Group column overlaps with model feature set"):
        prepare_data(config)

def test_group_column_constant(monkeypatch):
    def _mock_load(did, vid):
        df = make_dummy_data()
        df["patient_id"] = 1  # constant
        return MockDataset(), MockDatasetVersion(), df
    monkeypatch.setattr("app.data.splitting.load_versioned_frame", _mock_load)
    config = TrainingConfig(dataset_id=MockDataset.id, sampling_unit="grouped_samples", group_column="patient_id")
    with pytest.raises(AppError, match="Group column has fewer than 2 unique groups"):
        prepare_data(config)

def test_grouped_holdout_and_cv_disjoint(mock_load_versioned_frame):
    config = TrainingConfig(
        dataset_id=MockDataset.id, 
        sampling_unit="grouped_samples", 
        group_column="patient_id",
        test_size=0.2,
        cv_folds=3,
        seed=42,
        max_samples=200
    )
    data = prepare_data(config)
    meta = data.split_metadata()
    
    # Check holdout strategy
    assert "stratified_group_kfold" in meta["holdout_strategy"] or "group_shuffle_split" in meta["holdout_strategy"]
    assert meta["independent_samples_assumed"] is False
    assert meta["group_column"] == "patient_id"
    assert meta["total_groups"] == 40
    
    # Assert disjoint groups between train and test
    train_groups = set(data.frame["patient_id"].iloc[data.train])
    test_groups = set(data.frame["patient_id"].iloc[data.test])
    assert train_groups.isdisjoint(test_groups)
    
    # Assert CV disjoint
    for tr, val in data.cv:
        tr_g = set(data.frame["patient_id"].iloc[data.train[tr]])
        val_g = set(data.frame["patient_id"].iloc[data.train[val]])
        assert tr_g.isdisjoint(val_g)

def test_grouped_downsampling(mock_load_versioned_frame):
    config = TrainingConfig(
        dataset_id=MockDataset.id, 
        sampling_unit="grouped_samples", 
        group_column="patient_id",
        max_samples=100,
        seed=42
    )
    data = prepare_data(config)
    # we requested 100 samples from 200 total, which is 50%. Groups should be subset.
    sampled = len(data.train) + len(data.test)
    # The actual sample count might vary slightly due to group sizes
    assert 50 <= sampled <= 150
    assert data.excluded_by_sampling > 0
    meta = data.split_metadata()
    assert meta["excluded_by_sampling"] > 0
