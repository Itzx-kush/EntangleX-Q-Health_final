# API reference

Base path: `/api`. The Vite frontend and Nginx deployment proxy this same base. All application endpoints except `GET /health` use the optional configured Bearer token dependency and origin allowlist. Example authorization header: `Authorization: Bearer <your-locally-generated-token>`; no credential is included in the repository.

All IDs are generated UUIDs. Lists support `limit` (default 100, maximum 500) and `offset` where noted. Current frontend registry lists load the first 100 records; use API pagination for a larger local registry. No raw dataset download endpoint exists.

## Routes

| Method | Path | Request / response |
|---|---|---|
| GET | `/health` | Reachability, software mode, token-required flag and quantum package presence; not execution verification |
| GET | `/summary` | Registry counts and recent experiments |
| GET | `/datasets` | Paginated `DatasetOut[]`; provenance and aggregate quality, no raw table |
| POST | `/datasets/upload` | Multipart `file` plus JSON string `metadata_json`; returns `DatasetOut` |
| POST | `/datasets/demo` | Register public sklearn WDBC benchmark, or return existing matching hash |
| GET | `/datasets/{id}` | `DatasetOut` |
| GET | `/datasets/{id}/provenance` | Provenance metadata |
| POST | `/datasets/{id}/validate` | `{"features": null}` or explicit feature list; aggregate quality |
| DELETE | `/datasets/{id}` | 204 only when not referenced by any experiment |
| POST | `/preprocessing/preview` | Full `TrainingConfig`; training-only fitted preprocessing description |
| POST | `/feature-selection/preview` | Same shared preview contract, selection-oriented screen |
| POST | `/pca/preview` | Same shared preview contract, explained variance and loadings |
| POST | `/training/jobs` | `TrainingConfig`; 202 with `job` and `experiment` |
| GET | `/training/jobs` | Paginated persisted jobs |
| GET | `/training/jobs/{id}` | Status, coarse progress, current state and safe model failures |
| POST | `/training/jobs/{id}/cancel` | Cooperative cancellation request |
| GET | `/models` | Paginated registry, including failed models |
| GET | `/models/{id}` | Configuration, source traceability and calculated metrics |
| GET | `/models/{id}/input-schema` | Exact raw features, types, nullable flags and class mapping |
| GET | `/models/{id}/demo-sample` | One public benchmark feature record only; rejects uploaded datasets |
| POST | `/models/{id}/predict` | Anonymous sample maps; class, probability/score, research category, disclaimer |
| POST | `/models/{id}/explain` | Method and bounded budgets; persisted aggregate explanation |
| GET | `/models/{id}/explanations` | Saved aggregate explanations |
| GET | `/models/{id}/circuit` | Fitted quantum model's parameterized circuit structure |
| GET | `/experiments` | Paginated immutable experiment configurations |
| GET | `/experiments/{id}` | `{experiment, models, jobs}` |
| GET | `/experiments/{id}/comparison` | Shared-split metadata, all model records and completed classical/quantum pairs |
| POST | `/experiments/{id}/rerun` | 202; a new experiment/job using original config and parent link |
| GET | `/experiments/{id}/report?format=html` | Escaped downloadable HTML research report |
| GET | `/experiments/{id}/report?format=json` | JSON research report |
| GET | `/quantum/capabilities` | Presence of optional modules and non-verification statement |
| POST | `/quantum/circuit` | `CircuitRequest`; calculated logical circuit structure, no execution |

## Dataset metadata

`name`, `target`, `positive_label` and `deidentified: true` are required. `domain`, `source`, `source_url`, `version`, and `sampling_unit` record source context. The only supported sampling unit is `independent_samples`. `source_url` is stored, never fetched by the upload service. Positive label must match an observed target string exactly after metadata trimming; labels are not inferred from numeric magnitude.

```json
{
  "name": "My de-identified biomedical study",
  "domain": "biomedical",
  "source": "Authorized research dataset",
  "version": "study-v1",
  "target": "outcome",
  "positive_label": "positive",
  "deidentified": true,
  "sampling_unit": "independent_samples"
}
```

This is configuration, not a fictional dataset/result. Substitute metadata that accurately describes your authorized data.

## Training configuration

`dataset_id` is required. `features: null` uses every non-target source input after quality checks. Allowed models: `logistic_regression`, `svm`, `random_forest`, `vqc`, `qsvc`. Defaults are three classical models, seed 42, `test_size=0.2`, three CV folds, `max_samples=160`, probability threshold 0.5 and no calibration. Set `max_samples=null` for all eligible records in a classical-only experiment; quantum experiments obey the configured sample cap.

`pipeline` defines imputer, scaler, quantile clipping, original-feature log transforms, ratios, selection, PCA and angle scaling. `parameters` defines LR/SVM C, SVM kernel, forest tree count/depth and class weight. `quantum` defines backend, qubits, feature map/ansatz repetitions, entanglement, optimizer, iteration cap, shots and optional noise probability. `calibration` is `none`, `sigmoid` or `isotonic`; calibrated quantum experiments are rejected, not silently approximated.

Quantum comparison requires shared `pipeline.pca_components == quantum.qubits`, `angle_scaling=true` and `class_weight=null`. The backend enforces these even when requests bypass the UI.

## Prediction and explanation contracts

Prediction body: `samples` is one to 32 maps with **exactly** the trained raw feature keys. Numeric nulls are allowed and imputed by the stored training-fitted pipeline; invalid numeric strings, infinities, targets and unknown keys are rejected. Optional `risk_thresholds` must satisfy `0 < low < high < 1`. `include_influence=true` requires exactly one sample and adds bounded original-feature perturbation. No user prediction payload is stored.

Probability output is `probability_positive` for the configured positive label, not confidence in whichever class was predicted. Margin-only models return `decision_score` with null probability/category. The persisted model threshold, not the presentation risk boundaries, determines predicted class.

Explanation body: `method` (`permutation`, `shap`, `perturbation`), `max_samples` (2-32), `repeats` (1-10), and `max_features` (1-60, applied to perturbation). Quantum accepts only perturbation. All explanation results disclose sample count, units, method, limitations and measured elapsed seconds.

## Errors and confidentiality

Errors use `{"error": {"code": "...", "message": "...", ...}}`. Validation errors identify invalid schema locations/types without echoing input values. Common statuses: 401 missing/wrong configured token, 403 disallowed origin or raw uploaded-demo access, 404 unknown resource, 409 dataset-in-use/integrity/not-ready, 413 oversized request, 422 invalid data/configuration, 429 queue full, 503 optional component unavailable. Internal exceptions are sanitized; logs contain IDs and exception type rather than raw records.

Request bodies are bounded before multipart parsing. Reports and API responses set no-store behavior; report HTML escapes source-controlled strings. See `backend/app/api/schemas.py` and generated OpenAPI for complete authoritative field definitions.
