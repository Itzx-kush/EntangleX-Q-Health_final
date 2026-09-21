import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, RobustScaler, StandardScaler
from ..api.schemas import PipelineConfig, TrainingConfig
from ..utils.errors import AppError
from ..utils.serialization import clean_json
from .transformers import BiomedicalFeatures, FeatureSelector, QuantileClipper

def build_preprocessor(config: PipelineConfig, features: list[str], numeric: list[str], seed: int) -> Pipeline:
    ratio_definitions = tuple(r.model_dump() for r in config.ratios)
    numeric_all = numeric + [r.name for r in config.ratios]
    categorical = [f for f in features if f not in numeric]
    numeric_steps = [("impute", SimpleImputer(strategy=config.imputer, keep_empty_features=True))]
    if config.outlier_strategy == "clip_quantiles":
        numeric_steps.append(("outliers", QuantileClipper(config.lower_quantile, config.upper_quantile)))
    scalers = {"standard": StandardScaler, "minmax": MinMaxScaler, "robust": RobustScaler}
    if config.scaler != "none":
        numeric_steps.append(("scale", scalers[config.scaler]()))
    transforms = []
    if numeric_all:
        transforms.append(("numeric", Pipeline(numeric_steps), numeric_all))
    if categorical:
        transforms.append(("categorical", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False, max_categories=32)),
        ]), categorical))
    stages = [
        ("engineer", BiomedicalFeatures(tuple(config.log_features), ratio_definitions)),
        ("columns", ColumnTransformer(transforms, remainder="drop", sparse_threshold=0)),
        ("select", FeatureSelector(config.selection, config.k_features, config.variance_threshold, seed)),
    ]
    if config.pca_components is not None:
        stages.append(("pca", PCA(n_components=config.pca_components, whiten=config.pca_whiten, svd_solver="full", random_state=seed)))
    if config.angle_scaling:
        # Applied to ALL models in a comparison; fitted only on training data.
        stages.append(("angles", MinMaxScaler(feature_range=(0.0, np.pi), clip=True)))
    return Pipeline(stages)

def describe_preprocessor(pipe: Pipeline) -> dict:
    raw_names = pipe.named_steps["columns"].get_feature_names_out()
    # Encoded categorical vocabulary can contain sensitive values. Preserve axis
    # ordering without revealing those values in public PCA/selection metadata.
    names = np.asarray([f"categorical_feature_{i + 1:04d}" if str(name).startswith("categorical__") else str(name)
                        for i, name in enumerate(raw_names)], dtype=object)
    selector = pipe.named_steps["select"]
    selected = selector.get_feature_names_out(names).tolist()
    scores = []
    if selector.scores_ is not None:
        scores = [{"feature": str(n), "score": float(v), "selected": bool(s)} for n, v, s in zip(names, selector.scores_, selector.support_)]
    pca = pipe.named_steps.get("pca")
    if pca is not None and not np.isfinite(pca.explained_variance_ratio_).all():
        raise AppError("degenerate_pca", "PCA explained variance is undefined for the selected training representation. Review constant features and dimensionality.")
    output = [f"PC{i+1}" for i in range(pca.n_components_)] if pca is not None else selected
    return clean_json({"selected_features": selected, "output_features": output, "selection_scores": scores, "pca_explained_variance": pca.explained_variance_ratio_.tolist() if pca is not None else [], "pca_loadings": pca.components_.tolist() if pca is not None else [], "stages": list(pipe.named_steps)})

def preview(config: TrainingConfig) -> dict:
    from ..data.splitting import prepare_data
    data = prepare_data(config)
    transformer = build_preprocessor(config.pipeline, data.features, data.numeric, config.seed)
    try:
        transformer.fit(data.X.iloc[data.train], data.y[data.train])
    except ValueError as exc:
        raise AppError("pipeline_configuration", "The training-only pipeline could not be fitted. Check log domains, ratio definitions, selected feature count, and PCA dimensions.") from exc
    return {**describe_preprocessor(transformer), "input_features": data.features, "train_count": len(data.train), "test_count": len(data.test), "split_hash": data.split_hash, "warnings": data.quality["warnings"] + ["Preview statistics are fitted on the training partition only. CV refits a fresh pipeline in every fold."]}
