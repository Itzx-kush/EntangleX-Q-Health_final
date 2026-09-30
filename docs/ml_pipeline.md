# Biomedical ML pipeline and leakage boundaries

## Fixed source and class semantics

Source bytes are immutable through the application API. A SHA-256 integrity check precedes loading. Target validation requires exactly two observed labels and an explicit positive label. Internally the positive label is 1 and the other label 0. In the public WDBC demonstration, sklearn's source value 0 means malignant; the loader deliberately maps the label string `malignant` to this application's positive class. Sensitivity therefore does not accidentally measure the benign class.

Potential identifier names and near-perfect target proxies block training. Whole-source descriptive quality statistics are not learned preprocessing parameters. They must not become an excuse to tune feature selection against observed holdout outcomes: preregister schema decisions and use independent confirmation after exploratory research.

## Split before learning

The order is source quality -> explicit duplicate handling -> optional seeded stratified subset -> seeded stratified holdout -> CV inside training -> final training fit -> one held-out evaluation. Every model in the experiment uses the exact same sampled rows and partition arrays. The split fingerprint incorporates the dataset hash, train/test indices and CV fold indices. Indices remain private in trusted model bundles.

Duplicate policy defaults to rejection. `drop_exact` deduplicates selected input features plus target **before** splitting and records the removed count. Identical selected feature vectors with conflicting targets or residual duplicates are rejected. This conservative rule may reject legitimate repeated measurements; the proper solution for dependent observations is group-aware evaluation, which this MVP does not implement.

## Fold-local full pipeline

`BiomedicalFeatures -> ColumnTransformer -> FeatureSelector -> PCA? -> angle scaler? -> classifier`.

Ratios and nonnegative log1p transforms are deterministic. Imputation statistics, clipping quantiles, category vocabularies, scaling parameters, feature-selection scores, PCA loadings and angle-scaling bounds are fitted on the relevant training fold only. Final fit uses only the outer training partition. No shared globally prefit PCA or feature selector is reused across CV folds.

Original numeric features and configured ratios are imputed with median, mean or mode. Optional quantile clipping is a winsorization-style transform, not clinical outlier removal. Scaling supports standard, min-max, robust or none. Categorical values use mode imputation and a capped one-hot vocabulary with unknown categories ignored. Public encoded category feature names are neutralized; category values remain inside the protected artifact only.

Feature selection is ANOVA F-score, mutual information, variance threshold or none. K is capped to available encoded width. PCA requires enough retained dimensions and training samples in every fold; failures are reported, not silently replaced by fake components. Angle scaling clips to `[0, pi]` using training bounds and applies equally to classical and quantum comparators. It can suppress beyond-training-range variation; record this limitation when interpreting predictions.

## Cross-validation and final evaluation

`StratifiedKFold(shuffle=True, random_state=seed)` acts on the outer training partition. Each fold produces calculated metrics. Validation mean and sample standard deviation (`ddof=1`) are reported with the number of valid folds. This standard deviation is not a confidence interval or significance test.

The final estimator is fitted once on the complete training partition. Training resubstitution metrics are explicitly separate from held-out metrics. The holdout is not used to tune model C, forest settings, feature counts, probability thresholds, qubits or optimizer settings. Users can still overfit research choices by repeatedly inspecting a holdout across reruns; reports disclose this and recommend untouched external validation for later scientific claims.

## Metrics and undefined values

Sensitivity/recall = TP/(TP+FN); specificity = TN/(TN+FP); precision = TP/(TP+FP); accuracy = (TP+TN)/N; F1 = 2TP/(2TP+FP+FN). Confusion matrix rows are observed labels, columns predicted labels, both ordered negative then positive. ROC-AUC uses positive-class probability or the decision margin. Undefined denominators/one-class AUC yield null, not fabricated scores. Actual ROC points and false-negative counts are exposed.

Measured timings distinguish final fit, CV including validation work, and held-out inference. Simulator computation on a classical CPU is not a real quantum-hardware execution time. Timing comparisons are descriptive and not controlled hardware-resource benchmarks.

## Probability calibration

Raw LR/RF/VQC probability is a model output, not externally validated clinical probability. SVM and QSVC deliberately use margin-only scoring unless an explicitly supported classical calibration wrapper is selected. No sigmoid is silently applied to QSVC margins.

Optional sigmoid/isotonic `CalibratedClassifierCV` wraps the **entire** sklearn pipeline with inner stratified CV and `ensemble=False`; preprocessing is refitted inside each inner training fold. Class support is checked before submission. The final model is trained on the outer training partition and calibrated using internally generated training out-of-fold scores. Holdout reliability curves and Brier scores are reported separately. Neither establishes clinical calibration. Quantum calibration is intentionally disabled pending a validated adapter strategy.

## Research operating-point selection

`threshold_strategy=fixed` preserves the established configured probability
threshold and the zero decision-score boundary for margin-only estimators.
`threshold_strategy=target_sensitivity` instead collects the already-computed
out-of-fold validation scores from the training-partition CV loop.

The sensitivity-first selector considers every OOF threshold meeting the
requested sensitivity, then maximizes specificity, sensitivity, F1, and finally
the higher threshold as a deterministic tie-break. The result is locked before
the final fit and before the untouched holdout is evaluated. Test labels and
scores are never inputs to threshold selection.

The persisted record includes the curve, units, feasibility, selected
threshold, validation and holdout metrics, OOF sample count, fold count, and
threshold source. An infeasible validation result never silently lowers the
target or invents a threshold. These are research operating points, not
clinically validated screening cutoffs.

## Controlled robustness and degradation evaluation

The Robustness Lab evaluates already-fitted artifacts on a deterministic,
bounded subset of the original held-out partition. It never refits a model,
changes preprocessing, reselects the research operating threshold, or feeds
perturbed samples into training, CV, feature selection, calibration, or
hyperparameter selection. Paired classical and quantum models must share the
dataset hash, selected feature schema, and held-out indices.

Supported original-feature-space conditions are approximately 5%/10%
missingness, Gaussian noise scaled by 0.05/0.10 of each numeric feature's
training-partition standard deviation, controlled numerical outliers at
plus-or-minus three training standard deviations, and categorical corruption
to another category observed in the training partition. Seeds, bounded sample
indices, condition metadata, and fingerprints are persisted. A condition that
does not apply returns `not_applicable` with a reason rather than disappearing.

For each condition, the service reports baseline and perturbed accuracy,
sensitivity, specificity, precision, recall, F1, and ROC-AUC when defined.
`degradation_delta` is always `perturbed - baseline`; relative change is null
when the baseline is zero. These synthetic perturbations are off-manifold
stress tests, not external validation, hospital/population shift evidence,
patient-safety evidence, clinical robustness, model ranking, or quantum
advantage.

## Resource advice does not alter model selection

The quantum resource advisor is a pre-execution engineering aid. It does not
inspect labels, CV outputs, holdout metrics, operating-point curves, robustness
results, or prediction quality when assigning resource labels. Consequently it
cannot select a model, threshold, clinical operating point, or quantum
advantage. Applying a recommendation updates only the existing quantum
configuration, matching PCA dimension, and common sample budget after an
explicit user action; normal `TrainingConfig` validation and the complete
training pipeline still apply.
