import numpy as np
import pandas as pd
import pytest
from sklearn.base import clone
from app.api.schemas import PipelineConfig, TrainingConfig
from app.data.splitting import prepare_data
from app.feature_engineering.pipeline import build_preprocessor, describe_preprocessor, preview
from app.feature_engineering.transformers import BiomedicalFeatures, FeatureSelector, QuantileClipper
from app.models.factory import build_estimator
from app.utils.errors import AppError

def test_reproducible_disjoint_holdout_and_cv(config):
    first, second = prepare_data(config), prepare_data(config)
    assert first.split_hash == second.split_hash
    assert set(first.train).isdisjoint(first.test)
    assert set(first.train) | set(first.test) == set(range(len(first.frame)))
    for train, val in first.cv:
        assert set(train).isdisjoint(val)
        assert set(first.train[train]).isdisjoint(first.test)
        assert set(first.train[val]).isdisjoint(first.test)
    other = prepare_data(config.model_copy(update={"seed": 20}))
    assert other.split_hash != first.split_hash

def test_imputation_fits_only_training():
    train = pd.DataFrame({"a": [1.0, np.nan, 3.0], "b": [2.0, 3.0, 4.0]})
    holdout = pd.DataFrame({"a": [10000.0], "b": [5.0]})
    settings = PipelineConfig(imputer="mean", scaler="none", selection="none", pca_components=None, angle_scaling=False)
    pipe = build_preprocessor(settings, ["a", "b"], ["a", "b"], 42)
    pipe.fit(train, [0, 1, 0])
    imputer = pipe.named_steps["columns"].named_transformers_["numeric"].named_steps["impute"]
    np.testing.assert_allclose(imputer.statistics_, [2.0, 3.0])
    before = imputer.statistics_.copy()
    pipe.transform(holdout)
    np.testing.assert_array_equal(before, imputer.statistics_)

def test_full_pipeline_clonable_and_cv_refits(config):
    data = prepare_data(config)
    estimator = build_estimator("logistic_regression", config, data.features, data.numeric)
    assert clone(estimator) is not estimator
    fitted_imputers = []
    for tr, val in data.cv:
        local = clone(estimator).fit(data.X.iloc[data.train[tr]], data.y[data.train[tr]])
        fitted_imputers.append(local.named_steps["preprocessor"].named_steps["columns"].named_transformers_["numeric"].named_steps["impute"])
        assert local.predict(data.X.iloc[data.train[val]]).shape == (len(val),)
    assert len({id(item) for item in fitted_imputers}) == len(data.cv)

def test_pca_preview_is_training_only(config):
    data = prepare_data(config)
    result = preview(config)
    assert result["train_count"] == len(data.train)
    assert result["test_count"] == len(data.test)
    assert len(result["pca_explained_variance"]) == config.pipeline.pca_components
    assert result["split_hash"] == data.split_hash

def test_quantum_configuration_cannot_use_different_dimensions(config):
    values = config.model_dump(mode="json")
    values["models"] = ["vqc", "logistic_regression"]
    values["pipeline"]["pca_components"] = 3
    with pytest.raises(ValueError):
        TrainingConfig.model_validate(values)

def test_target_excluded_from_engineering(config, registered):
    values = config.model_dump(mode="json")
    values["pipeline"]["log_features"] = [registered.provenance["target"]]
    with pytest.raises(AppError, match="target"):
        prepare_data(TrainingConfig.model_validate(values))

def test_feature_selection_and_scaling(config):
    data = prepare_data(config)
    p = build_preprocessor(config.pipeline, data.features, data.numeric, config.seed)
    transformed = p.fit_transform(data.X.iloc[data.train], data.y[data.train])
    assert transformed.shape[1] == config.pipeline.pca_components
    assert np.isfinite(transformed).all()
    assert transformed.min() >= -1e-10 and transformed.max() <= np.pi + 1e-10

def test_category_labels_redacted_in_public_pipeline_description():
    X = pd.DataFrame({"number": [1., 3., 2., 4.], "category": ["private-one", "private-two", "private-one", "private-two"]})
    p = build_preprocessor(PipelineConfig(selection="none", pca_components=None, angle_scaling=False), list(X), ["number"], 42)
    p.fit(X, [0, 1, 1, 0])
    description = describe_preprocessor(p)
    assert "private-one" not in str(description) and "private-two" not in str(description)
