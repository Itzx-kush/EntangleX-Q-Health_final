# Model Feature Influence

Explanations describe a frozen model's behavior, not medical causation, treatment recommendations or complete circuit interpretation. No explanation value is embedded in the source as an application result. Explanations are computed after training on an explicitly bounded subset of the original holdout, without refitting the model.

## Permutation importance

The service uses sklearn permutation importance on the raw-feature pipeline, scoring positive-class ROC-AUC. Shuffled features pass through the already-fitted preprocessing/model. Mean score decrease and standard deviation over actual repeats are returned; negative importances are retained. The explanation subset must contain both classes. Its bounded deterministic first-row selection is disclosed and need not represent the full test distribution.

## SHAP

The implemented SHAP path uses a callable for the fitted full pipeline, `algorithm="permutation"`, a training-only background capped at 20 rows, and the requested bounded holdout subset. It reports mean absolute contribution and signed mean for each original feature. The output is positive-class probability or a decision score, not necessarily log-odds.

This raw-feature implementation supports complete numeric-only inputs. Mixed-type or missing-input datasets receive a clear unsupported message and can use permutation importance instead. This is an explicit implementation boundary, not a claim that SHAP in general cannot handle those data. Approximation budget and seeds are recorded in the request/result context; correlated features can redistribute attribution.

## Quantum and local perturbation

Baseline score/probability is computed for each explained sample. Each numeric feature is perturbed by plus/minus 0.25 training standard deviations; lower perturbations are bounded at zero for nonnegative training features. For categoricals, an alternative observed training category is used without disclosing category text. No observed variation produces an explicitly identified no-perturbation result.

The output includes measured mean score changes and magnitudes. Aggregate explanation metadata includes mean baseline score and whether its units are probability or decision score. Missing numeric sample values cannot be meaningfully perturbed without selecting an imputed baseline; their unchanged missing input yields no effect, which should not be read as biological unimportance. Ratio/log constraints may make a perturbation invalid; the API reports failure rather than inventing a feature influence.

Only the first configured `max_features` original features are perturbed, and evaluated feature count is disclosed. Aggregate explanation requests allow 1-60 features; single-sample prediction influence is bounded at 60. This limits simulator workload but can omit important later columns. The display sorts calculated magnitudes and retains full evaluated results in expandable metadata.

## Interpretation boundary

Perturbations may be off the data manifold. Importance is not stable clinical evidence. No mechanism maps influential features into disease causes or treatment suggestions. Quantum feature perturbation measures model sensitivity, not an exhaustive account of the internal quantum state or circuit. Repeated holdout inspection for model redesign consumes the holdout's role as an untouched evaluation resource.
