# Verified Instant Demo and Dataset Readiness

## Authoritative selection

`app.demo_readiness.READY_DEMO_DATASETS` is the single backend source of truth:

- `wdbc` — **Verified Demo Ready**
- `early-stage-diabetes` — **Verified Demo Ready**
- `cleveland-heart-disease` — **Requires Processing**
- `chronic-kidney-disease` — **Requires Processing**
- `ilpd-liver` — **Requires Processing**

The two ready datasets were chosen for bounded judge-demo availability and compact reproducible execution. The selection does **not** assert better data, a better model, clinical validity, or scientific superiority. Startup and tests reject configurations that do not contain exactly five catalog datasets, two ready slugs, and three processing-required slugs.

`is_demo` remains the legacy demo marker. Instant-demo readiness is derived independently from the built-in catalog slug and the verified package.

## Genuine controlled benchmark experiments

`scripts/build_demo_artifacts.py` uses the production built-in registration service and `TrainingManager`/training pipeline. Each selected dataset is trained with:

- seed `2026`; stratified 80/20 holdout; 3-fold stratified CV;
- maximum common sample budget `160`;
- manifest-recommended duplicate policy (`reject` for WDBC, `drop_exact` for Early Stage Diabetes);
- median imputation, standard scaling, ANOVA selection (`k=12`), PCA (`4` components), angle scaling enabled;
- logistic regression and random forest (`80` trees, maximum depth `8`);
- threshold `0.5`; no probability calibration.

The committed metrics are the outputs measured by that existing backend workflow. No placeholder models, metrics, explanations, reports, or experiments are generated. Explainability and reports are generated on demand only after the exact verified model package is validated.

## Deployment-safe package

```text
backend/app/demo_artifacts/
├── manifest.json
└── models/
    ├── <real-model-id>.dill
    └── ...
```

The versioned manifest contains each dataset slug and SHA-256, immutable dataset registry record, real experiment metadata and configuration, real model metadata and metrics, model artifact filename/SHA-256, prediction-sample policy, explanation mode, and report mode. It contains no filesystem paths, secrets, uploaded data, or runtime SQLite database.

On a fresh process, the backend validates the package and idempotently hydrates the normal SQLite registry and normal runtime artifact locations. Startup never trains models, downloads resources, or depends on a pre-seeded database. Models are loaded only on demand.

## Integrity and isolation

Before installation or use, the backend checks:

1. supported manifest schema and artifact version;
2. canonical manifest SHA-256;
3. configured slug and packaged dataset byte SHA-256;
4. dataset ID, catalog slug, target/label provenance, and experiment dataset relationship;
5. exact `TrainingConfig` compatibility and dataset ID;
6. model-to-experiment and model-to-dataset relationships;
7. SHA-256 of every serialized model artifact;
8. serialized bundle dataset ID, dataset hash, and exact experiment configuration;
9. runtime model SHA-256 and registry relationships again before model loading.

Any mismatch prevents instant-demo loading and degrades that dataset to unavailable/requires-processing metadata. There is no cross-dataset fallback. Live training remains available.

## Frontend behavior

The Medical Dataset Library, Demo Center, Training, Prediction, and Experiments views consume backend readiness metadata. The Demo Center computes its ready/processing counts from the returned five records. Ready records are labeled **Verified Demo Ready** and **Precomputed research result**; other records say **Requires Processing** and retain the live Training action.

Public benchmark sample policy remains provenance-based: built-in public benchmarks and the legacy demo are allowed; uploaded/custom datasets are blocked. `BrowserRouter` and the Render `/* -> /index.html` rewrite remain unchanged.

## Regeneration

From the repository root, with pinned backend dependencies installed:

```bash
python scripts/build_demo_artifacts.py
```

Regeneration replaces only the intentional public benchmark artifacts and manifest. Review all changed IDs, hashes, configurations, metrics, and package sizes before commit.
