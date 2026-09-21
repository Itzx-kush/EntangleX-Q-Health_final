# Reproducibility and scientific integrity

## What is preserved

Each experiment records the source dataset UUID/SHA-256, source URL/name/version, sample/feature counts, class distribution, explicit positive label, full pipeline/model/quantum configuration, seed, holdout fraction, CV folds, common subset size, removed duplicates, evaluated sample counts, split fingerprint, software versions, measured results and limitations. Models additionally record their artifact hash and link to the experiment/source dataset.

Model bundles contain private partition indices and the fitted entire pipeline. Reruns create a new immutable experiment with a parent link. Original configuration and outcomes remain available, including failed model entries. There is no invented training status, timing or performance file before actual execution.

## Reproducing an experiment

Retain exact source CSV bytes, database and matching model artifacts. Record the successfully resolved Python environment and frontend lockfile. Use the existing experiment's rerun action for the same configuration. Review the new run's source/split fingerprints, actual software versions, warnings and outcomes; identical configuration is not a promise of identical floating-point results across platforms or package versions.

The single-process worker, explicit seeds, fixed train/test partitions and deterministic preprocessing reduce uncontrolled variation. Finite-shot simulation, optimizer behavior and dependency implementations may still vary. A reproducibility claim needs repeated real execution in the target environment; generated code alone is insufficient.

## Fair comparison rules

Only models from the same experiment are compared. All share the same source, target, selected input features, sampled rows, holdout, CV partitions and preprocessing configuration. There is no quantum-only truncation of the training set. If a quantum sample budget is needed, it reduces the common benchmark for every comparator and is disclosed.

Classical class weighting and probability calibration are disallowed when quantum models are selected because the implemented VQC adapter does not provide equivalent mechanisms. SVM/QSVC margin decision boundaries and probability-model thresholds are explicitly identified. Comparisons are descriptive rather than a claim of equally optimized model families or matched training compute.

Every successful classical/quantum pair is shown. Sensitivity, specificity, ROC-AUC, F1, accuracy, precision, recall, CV dispersion and measured cost are not selectively filtered for favorable quantum results. Reports say higher/lower/equal only based on calculated differences, without significance or clinical-utility language.

## Holdout reuse and generalization

CV is inside training. All fitted preprocessing is inside each relevant fold. Calibration uses inner training folds. Nevertheless, repeated manual selection after reading held-out reports can overfit the holdout indirectly. Use a genuinely untouched external cohort after exploratory work. This MVP supplies neither cohort discovery nor external validation.

Fold standard deviation is not a confidence interval. A benchmark label is not prospective clinical disease onset. No subgroup/fairness claim, uncertainty interval, clinical calibration or deployment effectiveness is derived without an appropriate study. No general quantum advantage is established by a single predictive comparison or local simulator timing.

## Scientific result status

Generated source != tested code. Implemented pipeline != runtime-verified pipeline. Measured benchmark != clinically validated system. Simulation != real quantum hardware. The application retains those distinctions in its interface, reports and documentation.
