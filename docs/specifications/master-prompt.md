# ENTANGLEX Q-HEALTH — COMPLETE PROJECT GENERATION MASTER PROMPT

## ROLE

Act as a senior full-stack software architect, Python/FastAPI engineer, React/TypeScript engineer, machine-learning engineer, quantum-machine-learning engineer, biomedical data-science engineer, and technical documentation engineer.

Your task is to generate the **complete EntangleX Q-Health software project as actual project files** and package the entire project into **exactly one ZIP archive**.

This is a **source-code generation and packaging task**.

The primary deliverable is the actual project, not an explanation of how to build it.

---

# 1. SOURCE DOCUMENTS — READ EVERYTHING FIRST

I have provided the EntangleX Q-Health specification documents as attachments.

You MUST read the attached specification documents completely before generating the project.

Treat the attached specifications as the **primary source of truth**.

The specifications define the intended:

* architecture
* frontend
* backend
* APIs
* database
* preprocessing
* feature engineering
* feature selection
* PCA
* classical ML
* quantum ML
* benchmarking
* evaluation
* explainability
* prediction
* experiment registry
* model registry
* background jobs
* configuration
* Docker support
* testing
* documentation
* demo mode
* biomedical/health requirements
* medical disclaimer
* security requirements
* scientific-integrity requirements

Preserve the terminology, workflow, intent, and constraints from the specifications.

Where the specifications overlap, combine them into one internally consistent implementation.

Where a biomedical/health requirement is stricter than a generic implementation choice, the biomedical/health requirement takes precedence.

Do not silently remove or weaken a requirement.

Do not replace the requested architecture with a substantially different architecture merely because another architecture would be easier.

You may make reasonable minor implementation decisions where the specification is silent, but document those decisions.

Do not stop and ask for approval about ordinary implementation details.

---

# 2. PRIMARY OBJECTIVE

Generate the complete EntangleX Q-Health project described in the specifications.

The final output MUST be:

```text
ENTANGLEX-Q-HEALTH.zip
```

The ZIP must contain the complete project folder.

The project must include actual implementation files rather than merely:

* pseudocode
* architecture diagrams
* TODO comments
* placeholder page names
* code snippets
* partial implementations
* fictional result files
* an explanation of what could be built

The goal is to generate the project itself.

---

# 3. IMPORTANT EXECUTION BOUNDARY

This task is primarily a **source-generation task**.

Do NOT spend the task performing a long autonomous runtime execution/debugging cycle.

You do NOT need to:

* install dependencies
* run the backend
* run the frontend
* run Docker
* execute the ML pipeline
* execute quantum circuits
* perform complete end-to-end runtime testing
* repeatedly rebuild and debug the application

Generate the code carefully using static reasoning and the specifications.

However, the source code should be written as a coherent, runnable project as far as reasonably possible.

Never claim something is tested simply because you generated it.

Never claim dependency compatibility, Docker compatibility, frontend/backend integration, Qiskit compatibility, or successful runtime execution unless it was actually executed and verified.

---

# 4. STATUS / VERIFICATION RULE

Use these distinctions throughout the project and final response:

**Generated** ≠ tested.

**Implemented** ≠ runtime verified.

**Configured** ≠ successfully executed.

**Documented** ≠ experimentally validated.

Never fabricate verification.

At the end explicitly state that the project source code was generated and packaged, but application runtime, dependency compatibility, frontend/backend integration, Docker execution, tests, and quantum execution were not independently verified in this task unless you actually verified them.

Do NOT claim tests passed.

Do NOT claim Docker works.

Do NOT claim the frontend successfully connects to the backend.

Do NOT claim quantum circuits successfully execute.

---

# 5. REQUIRED PROJECT STRUCTURE

Create a professional modular monorepo similar to:

```text
entanglex-q-health/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── api/
│   │   ├── data/
│   │   ├── feature_engineering/
│   │   ├── models/
│   │   ├── quantum/
│   │   ├── evaluation/
│   │   ├── explainability/
│   │   ├── experiments/
│   │   ├── storage/
│   │   ├── jobs/
│   │   └── utils/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── utils/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
│
├── data/
├── models/
├── experiments/
├── docs/
├── scripts/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

You may add additional files/directories where technically appropriate.

Do NOT create one giant backend file.

Keep the application modular and maintainable.

Do not create unnecessary duplicate abstractions.

---

# 6. FRONTEND

Generate a complete React + TypeScript frontend.

The frontend must be a real implementation, not merely a list of placeholder routes.

Implement interfaces for at least:

* Dashboard
* Dataset Upload / Dataset Management
* Data Quality / Validation
* Preprocessing
* Feature Selection
* PCA / Dimensionality Reduction
* Training
* Model Comparison
* Quantum Circuit
* Explainability
* Prediction
* Experiments
* Experiment Details / Reports

The frontend must communicate with the backend through the defined APIs.

Use a professional scientific / healthcare / quantum-inspired design.

Avoid the appearance of a generic CRUD/admin dashboard.

The UI should emphasize:

* clarity
* scientific transparency
* readable metrics
* dataset provenance
* experiment configuration
* model identity
* prediction-versus-diagnosis distinction
* visible limitations
* visible medical disclaimer

Do not create alarmist medical styling.

Do not use wording such as:

```text
YOU HAVE CANCER
```

Do not present predictions as clinical diagnoses.

---

# 7. BACKEND

Generate a complete Python + FastAPI backend.

Use a modular architecture with:

* routers
* schemas
* services
* repositories/storage
* model modules
* quantum modules
* experiment management
* background-job abstractions
* utilities
* configuration
* structured error handling
* logging

Use:

* FastAPI
* Pydantic
* SQLAlchemy
* SQLite for the MVP

Implement API support for:

* health
* datasets
* dataset provenance
* data validation
* preprocessing
* feature selection
* PCA/dimensionality reduction
* training jobs
* training status
* model comparison
* predictions
* explainability
* experiments
* experiment retrieval
* experiment re-run structure
* quantum circuit retrieval

Use proper request/response schemas.

Avoid exposing raw biomedical records unnecessarily.

---

# 8. HEALTH / BIOMEDICAL POSITIONING

EntangleX Q-Health operates in the MedTech / BioTech / HealthTech domain.

The system is a:

**research and decision-support prototype**

It is NOT a clinically validated diagnostic device.

The primary use case is:

**Early disease-risk classification using biomedical data through hybrid quantum-classical machine learning.**

The intended workflow is:

```text
Biomedical Data
↓
Quality Validation
↓
Preprocessing
↓
Feature Engineering
↓
Dimensionality Reduction
↓
Classical ML / Quantum ML
↓
Risk Classification
↓
Explainability
↓
Benchmarking
```

The output represents a:

**model-generated risk prediction**

It does NOT represent a confirmed diagnosis.

---

# 9. INITIAL DATASET

The preferred first implementation is:

**Breast Cancer Wisconsin Diagnostic dataset**

or another established public biomedical binary-classification benchmark only when technical constraints require it.

The overall application MUST remain disease-agnostic.

Do NOT create hardcoded business logic such as:

```python
if breast_cancer:
    ...
```

Instead, use dataset/task metadata.

For example:

```json
{
  "dataset_name": "Breast Cancer Wisconsin Diagnostic",
  "domain": "oncology",
  "task": "binary_classification",
  "target": "diagnosis"
}
```

The architecture must allow future datasets such as:

* cardiovascular disease
* diabetes
* neurological disorders
* cancer subtypes
* biomarker-based disease prediction
* genomics-derived features
* imaging-derived features
* other biomedical classification tasks

---

# 10. HEALTH TERMINOLOGY

Use terminology such as:

* Disease Risk Prediction
* Risk Classification
* Predicted Class
* Model Probability
* Estimated Risk Score
* Research Prediction
* Decision Support
* Biomedical Prediction
* Observed Model Performance
* Feature Influence
* Model Explanation

Do NOT present predictions as:

* confirmed diagnosis
* clinical diagnosis
* medical diagnosis
* guaranteed disease detection
* medical advice
* treatment recommendation
* clinical decision
* patient prognosis

unless a future version undergoes appropriate clinical validation.

The prototype must never imply that it is a clinical diagnostic system.

---

# 11. MEDICAL DISCLAIMER

Display this disclaimer prominently:

> **Research Prototype:** This platform provides model-generated disease-risk predictions for research and decision-support purposes. Predictions are based on benchmark or user-provided datasets and are not a substitute for professional medical diagnosis, treatment, or clinical validation.

The disclaimer MUST appear on:

1. landing/dashboard screen
2. prediction screen
3. exported experiment reports
4. appropriate README/documentation sections

---

# 12. SENSITIVE BIOMEDICAL DATA

Treat uploaded biomedical datasets as potentially sensitive.

Do not unnecessarily:

* expose raw records
* display all uploaded rows globally
* log raw health records
* place uploaded records into browser console logs
* include raw records in experiment summaries
* expose uploaded files through arbitrary public URLs

Use:

* generated dataset IDs
* validated paths
* path traversal prevention
* upload-size limits
* sanitized filenames
* safe file handling

Never execute uploaded files.

Never include fake or real credentials in generated source code.

---

# 13. NO PATIENT IDENTIFIABLE INFORMATION

The demo system must not contain:

* names
* phone numbers
* addresses
* email addresses
* medical record numbers
* government IDs
* personally identifiable health information

Use public/benchmark data suitable for demonstration.

For generic demonstrations, prefer:

```text
Sample #123
```

rather than implying an identifiable patient.

Use “patient” only when the dataset genuinely represents patient records and such terminology is justified.

---

# 14. DATASET PROVENANCE

Every dataset used in an experiment should record, where available:

* dataset name
* dataset source
* source URL/reference
* dataset version
* dataset hash
* upload timestamp
* row count
* feature count
* target column
* target classes
* preprocessing configuration

For bundled demo datasets, document public source and licensing/provenance information.

The system should be capable of answering:

> Exactly what dataset produced this experiment?

Persist provenance in the experiment/model metadata.

---

# 15. BIOMEDICAL DATA QUALITY

Before training, perform health-oriented quality checks.

### Structural quality

Check:

* missing values
* duplicate rows
* invalid numeric values
* infinite values
* unsupported categorical values
* inconsistent schemas

### Statistical quality

Check:

* class imbalance
* low-variance features
* constant features
* highly correlated features
* suspiciously predictive features
* feature distributions

### Target quality

Verify:

* target exists
* target has at least two classes
* class labels are valid
* target is not accidentally included as an input feature

If the target column is accidentally used as a feature, reject the configuration.

---

# 16. DATA LEAKAGE — CRITICAL REQUIREMENT

Treat data leakage as a critical scientific error.

NEVER perform:

```text
Entire Dataset
↓
PCA
↓
Train/Test Split
```

Instead:

```text
Dataset
↓
Train/Test Split
↓
Training Pipeline
    ├── preprocessing
    ├── feature selection
    └── PCA
↓
Model
```

The test set must remain isolated.

For cross-validation:

```text
Fold
↓
Fit preprocessing on training portion
↓
Transform validation portion
↓
Train model
↓
Evaluate
```

All preprocessing and transformations that learn parameters MUST be fitted only on the relevant training data.

Do not tune hyperparameters on the test set.

Use reproducible seeds.

Use the same benchmark split across comparable models.

---

# 17. CLASSICAL MACHINE LEARNING

Implement at minimum:

* Logistic Regression
* SVM
* Random Forest

Implement:

* preprocessing
* feature engineering
* feature selection
* PCA
* model training
* prediction
* evaluation
* benchmarking
* reproducible configuration
* runtime metric calculation

Use appropriate scikit-learn abstractions and pipelines.

Prefer pipeline-based implementations that reduce leakage risk.

Do not hardcode performance results.

---

# 18. QUANTUM MACHINE LEARNING

Implement the quantum architecture specified in the source documents.

Include, where specified:

* Qiskit integration
* Qiskit Machine Learning integration
* Qiskit Aer simulator
* QuantumBackend abstraction
* VQC
* QSVC where specified
* quantum feature map
* ansatz
* optimizer configuration
* quantum circuit generation
* quantum prediction pipeline
* optional noise-simulation structure

Use lightweight defaults such as the specified 4-qubit configuration where appropriate.

The quantum architecture must be modular.

Do NOT assume quantum models outperform classical models.

Do NOT hardcode quantum advantage.

Do NOT fabricate quantum results.

---

# 19. QISKIT VERSION HANDLING

Because this task does not require full runtime verification:

* use currently appropriate APIs as reasonably determined from the specification
* avoid obviously deprecated patterns where possible
* document assumed dependency versions
* isolate quantum implementation behind modular abstractions
* make version-sensitive portions easy to update

Do not claim that a specific Qiskit version has been successfully verified unless it was actually executed.

If some QNN/Qiskit component cannot be safely implemented without runtime verification, preserve the correct abstraction and clearly document the limitation rather than inventing functionality.

---

# 20. NO FAKE RESULTS

This is a CRITICAL REQUIREMENT.

NEVER hardcode or fabricate:

* accuracy
* precision
* recall
* sensitivity
* specificity
* F1
* ROC-AUC
* confusion matrices
* ROC curves
* feature importance
* feature influence
* predictions
* quantum metrics
* training metrics
* inference metrics
* timing results
* quantum advantage

All such values MUST be calculated dynamically when the project is actually run.

Do not display fictional demo performance as if it were real.

Do not create fake screenshots of results.

Do not include example values in the application that could be mistaken for real measurements.

---

# 21. HEALTH-RELEVANT CLASSIFICATION METRICS

Accuracy alone is insufficient.

Always calculate and expose:

* Accuracy
* Precision
* Recall
* Sensitivity
* Specificity
* F1 Score
* ROC-AUC
* Confusion Matrix

Make **Sensitivity** especially prominent.

Explain:

```text
Sensitivity = ability to correctly identify positive cases.
```

Explain:

```text
Specificity = ability to correctly identify negative cases.
```

The UI should make false negatives clearly visible.

---

# 22. FALSE POSITIVE / FALSE NEGATIVE ANALYSIS

Expose:

```text
True Positive
True Negative
False Positive
False Negative
```

Provide human-readable definitions:

**False Negative**

A sample that is actually positive but predicted as negative.

**False Positive**

A sample that is actually negative but predicted as positive.

Do not imply that these directly correspond to clinical outcomes unless the dataset and study design justify that interpretation.

---

# 23. MODEL PROBABILITIES

When a model supports probability estimation, expose:

```text
Predicted Class
Probability / Score
Risk Category
```

Clearly distinguish:

**Model Probability**

from:

**Actual Clinical Probability**

Do not call classifier probabilities medically calibrated risk unless calibration has actually been performed and validated.

---

# 24. RESEARCH RISK CATEGORIES

The UI may provide:

```text
LOW
MEDIUM
HIGH
```

but these MUST be explicitly labelled:

**Demonstration / Research Risk Category**

Do not imply that example thresholds such as:

```text
0.00–0.33
0.33–0.66
0.66–1.00
```

are medically validated.

Make thresholds configurable.

Document that thresholds are research/demo thresholds unless separately validated.

---

# 25. CALIBRATION ARCHITECTURE

Where probability outputs exist, architect the evaluation system so calibration can be added later.

Potential future methods:

* Platt scaling
* isotonic regression
* calibration curves
* Brier score

Do not claim raw probabilities are clinically calibrated.

If calibration is implemented, report it separately from ordinary classifier evaluation.

---

# 26. GENERALIZATION

Do not judge a biomedical model solely by one test split.

Support:

* train/test evaluation
* stratified cross-validation
* mean CV performance
* CV standard deviation
* held-out test performance

Clearly distinguish:

```text
Training Performance
Validation Performance
Test Performance
```

Never present training accuracy as evidence of real-world clinical performance.

---

# 27. DATASET SIZE AND LIMITATIONS

Display:

* number of samples
* number of features
* class distribution
* training size
* test size

When a dataset is small, make that limitation visible.

Do not imply that strong benchmark performance establishes clinical effectiveness.

---

# 28. CLASSICAL VS QUANTUM COMPARISON

Quantum and classical models MUST be compared under equivalent conditions.

Use:

```text
                     CLASSICAL       QUANTUM

Dataset              SAME            SAME
Target               SAME            SAME
Train/Test Split     SAME            SAME
Preprocessing        SAME            SAME
Feature Selection    SAME            SAME
Test Set             SAME            SAME
```

Then compare at least:

* sensitivity
* specificity
* ROC-AUC
* F1
* accuracy
* computational cost
* generalization

Do not selectively display only metrics where the quantum model performs better.

Provide a scientifically balanced comparison.

---

# 29. QUANTUM ADVANTAGE

NEVER assume quantum models outperform classical models.

Legitimate outcomes include:

### Outcome A

Quantum model performs better on the selected metric.

### Outcome B

Quantum and classical models perform similarly.

### Outcome C

Quantum model improves sensitivity but reduces specificity.

### Outcome D

Quantum model has comparable predictive performance but greater computational cost.

### Outcome E

Classical model performs better.

### Outcome F

No measurable quantum advantage is observed.

All outcomes are valid.

The system must report the actual measured result.

Never write a narrative that presumes quantum superiority.

---

# 30. CLINICAL VALIDATION BOUNDARY

The prototype does NOT establish:

* clinical validity
* clinical utility
* regulatory approval
* patient safety
* treatment efficacy
* diagnostic accuracy in clinical practice

Clearly distinguish:

```text
Machine Learning Benchmark
```

from:

```text
Clinical Validation
```

These are not equivalent.

---

# 31. EXPLAINABILITY

For classical models implement, where appropriate:

* SHAP
* permutation importance

Use the term:

**Model Feature Influence**

rather than implying medical causation.

For example, if Feature X has high model influence, say:

> Feature X had high observed influence on this model's prediction.

Do NOT say:

> Feature X causes the disease.

Feature importance does not automatically establish biological or medical causation.

---

# 32. QUANTUM EXPLAINABILITY

For quantum models use:

**Feature Perturbation / Sensitivity Analysis**

Structure it as:

```text
Baseline prediction
↓
Perturb Feature A
↓
Prediction change

Perturb Feature B
↓
Prediction change

Perturb Feature C
↓
Prediction change
```

Describe this as:

**model sensitivity**

Do NOT claim this provides a complete interpretation of the internal quantum circuit.

---

# 33. PREDICTION SCREEN

Implement a prediction screen with a structure similar to:

```text
BIOMEDICAL RISK PREDICTION

Sample:
Sample #123

Model:
VQC

Predicted Class:
Positive

Model Probability:
82%

Research Risk Category:
HIGH

──────────────────────

MODEL FEATURE INFLUENCE

Feature A       High
Feature B       Medium
Feature C       Low

──────────────────────

INTERPRETATION

The selected model classified this sample as
Positive based on the learned patterns in the
provided biomedical features.

This is a research prediction and is not a
clinical diagnosis.
```

The actual values MUST be dynamically generated when the application is run.

Never generate a medical recommendation.

---

# 34. HEALTHCARE UI PRINCIPLES

The UI should feel:

* trustworthy
* scientific
* transparent
* calm
* precise

Use:

* clear metric labels
* explicit units
* readable charts
* dataset provenance
* experiment configuration
* model identity
* visible disclaimer
* clear prediction/diagnosis distinction

Avoid:

* alarmist red warnings
* emergency-style alerts
* fake hospital dashboards
* exaggerated certainty
* decorative medical claims
* clinical-sounding guarantees

---

# 35. EXPERIMENT REGISTRY

Implement an experiment registry.

Record where applicable:

* experiment ID
* dataset information
* dataset provenance
* preprocessing configuration
* feature-selection configuration
* PCA configuration
* model configuration
* quantum configuration
* metrics
* timing information
* software/version metadata
* model identity
* train/test configuration
* CV configuration
* random seed
* limitations
* disclaimer state where useful

Support experiment re-run structures without overwriting original experiments.

---

# 36. MODEL REGISTRY

Implement a model registry sufficient to identify:

* model ID
* model type
* dataset
* task
* preprocessing configuration
* model configuration
* quantum configuration if applicable
* training metadata
* software metadata
* experiment ID
* created timestamp
* status

Models and experiments should remain traceable to their dataset provenance.

---

# 37. BACKGROUND JOB STRUCTURE

Implement the requested background-job architecture.

Training should have a structure allowing:

* job creation
* job identification
* job status
* progress/state representation
* result persistence
* failure handling

For the MVP, use a reasonable lightweight architecture unless the specification explicitly requires a particular job framework.

Do not pretend asynchronous infrastructure has been production tested.

---

# 38. SECURITY

Implement source-code protections including:

* upload size limits
* extension validation
* safe filenames
* path traversal prevention
* environment variables for secrets
* no credentials hardcoded
* no uploaded-file execution
* structured error handling
* appropriate logging

Create:

```text
.env.example
```

Never insert fake API keys, passwords, tokens, or secrets.

Do not log raw biomedical information unnecessarily.

---

# 39. DEMO MODE

Implement the demo workflow requested in the specifications.

Include safe demo-data handling or deterministic demo-data generation without patient-identifiable information.

Do not hardcode demo performance numbers.

The application must calculate demo metrics dynamically when executed.

---

# 40. DOCKER

Generate:

```text
backend/Dockerfile
frontend/Dockerfile
docker-compose.yml
```

Configure them according to the specification.

Do not claim Docker execution was tested.

Use clear environment/configuration handling.

---

# 41. TESTS

Generate actual automated test code.

Cover, where applicable:

* data loading
* dataset validation
* biomedical quality checks
* target validation
* class imbalance detection
* preprocessing
* leakage prevention
* feature selection
* PCA
* metrics
* sensitivity
* specificity
* false positives/negatives
* classical models
* quantum components
* APIs
* experiments
* model registry
* prediction
* provenance
* security validation
* end-to-end workflow structure

Tests must be actual executable test code.

Do NOT replace tests with comments describing what should be tested.

Do NOT claim the tests passed.

---

# 42. DOCUMENTATION

Generate a complete:

```text
README.md
```

and at least:

```text
docs/
├── architecture.md
├── api.md
├── ml_pipeline.md
├── quantum_pipeline.md
├── explainability.md
├── deployment.md
├── reproducibility.md
└── limitations.md
```

Add other documentation where appropriate.

README must explain:

1. Project overview
2. Problem statement
3. Biomedical use case
4. Architecture
5. Technology stack
6. Prerequisites
7. Python version
8. Node.js version
9. Dependency installation
10. Environment configuration
11. Database setup
12. Backend startup
13. Frontend startup
14. Docker startup
15. Demo workflow
16. Dataset upload
17. Data validation
18. Preprocessing
19. Feature selection
20. PCA
21. Classical ML
22. Quantum ML
23. Benchmarking
24. Evaluation
25. Explainability
26. Prediction
27. Experiment tracking
28. Model registry
29. API usage
30. Security considerations
31. Troubleshooting
32. Known limitations
33. Biomedical limitations
34. Medical disclaimer
35. Dataset provenance

Clearly distinguish:

```text
Quantum Simulation
Quantum Model
Hybrid Quantum-Classical Method
Real Quantum Hardware
```

Do not imply that simulation equals real quantum hardware.

Do not claim quantum advantage unless actual measured execution establishes it.

---

# 43. HEALTH EXPERIMENT REPORTS

Every experiment report should contain:

## Dataset

* source
* provenance
* task
* target
* sample count
* feature count
* class distribution

## Preprocessing

* missing-value strategy
* encoding
* scaling
* outlier strategy
* feature selection
* PCA

## Models

* classical models
* quantum models
* quantum backend

## Evaluation

* accuracy
* sensitivity
* specificity
* precision
* F1
* ROC-AUC
* confusion matrix

## Computational

* training time
* inference time
* qubits
* circuit depth

## Generalization

* CV mean
* CV standard deviation
* test performance

## Interpretation

* feature influence
* quantum perturbation results

## Scientific Conclusion

Automatically generate a conclusion based ONLY on measured results.

Do not insert predetermined conclusions such as:

```text
Quantum ML is better.
```

Instead, calculate and report the actual outcome.

---

# 44. SCIENTIFIC-INTEGRITY RULES

The guiding principle is:

**Scientific validity wins.**

When visual design conflicts with clarity:

**Clarity wins.**

When quantum results conflict with the desired narrative:

**Measured results win.**

When a model performs poorly:

**Report the poor result honestly.**

When the quantum model loses to the classical baseline:

**Display that result clearly.**

The purpose of EntangleX Q-Health is NOT to prove that quantum ML is better.

The purpose is to measure whether and when hybrid quantum-classical ML provides useful value for biomedical prediction.

---

# 45. CODE QUALITY

Generated code must be:

* modular
* readable
* typed appropriately
* logically consistent
* reasonably documented
* maintainable
* organized according to the architecture
* internally consistent across frontend/backend/API/database/model layers

Avoid unnecessary placeholder implementations.

Avoid one-file architectures.

Where runtime verification would be needed, use a clearly documented assumption rather than silently fabricating functionality.

---

# 46. PROJECT CONSISTENCY REQUIREMENT

Before packaging, inspect the generated project conceptually for internal consistency.

Make sure:

* frontend API calls correspond to backend routes
* request/response schemas correspond
* imports correspond to actual modules
* configuration names are consistent
* environment variable names are consistent
* database models correspond to repositories/services
* experiment records correspond to report generation
* model registry references correspond to actual models
* tests reference actual modules/routes
* Docker configuration corresponds to project paths
* README commands correspond to the generated structure
* documentation paths actually exist
* frontend routes correspond to implemented pages
* quantum configuration matches quantum services
* dataset metadata matches experiment metadata

Do not create references to nonexistent modules or endpoints merely to make the architecture look complete.

---

# 47. DEPENDENCY / LOCKFILE RULE

Create the dependency manifest files required by the project.

For the frontend, create a valid lockfile only when it can be generated consistently.

Do not fabricate a misleading `package-lock.json`.

If a valid lockfile cannot be produced in the generation environment, omit it and clearly document that the user should run the appropriate package-manager install command to generate it.

Document assumed dependency versions, especially for:

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* scikit-learn
* SHAP
* Qiskit
* Qiskit Machine Learning
* Qiskit Aer
* React
* TypeScript
* Vite or the chosen frontend build tool

Do not claim those versions were runtime verified unless they were actually executed.

---

# 48. ACCEPTANCE CRITERIA

The generated project should satisfy all of the following conceptually:

```text
[ ] complete frontend exists
[ ] complete backend exists
[ ] APIs exist
[ ] database structure exists
[ ] dataset loading exists
[ ] dataset provenance exists
[ ] data-quality validation exists
[ ] target validation exists
[ ] class imbalance detection exists
[ ] missing-data handling exists
[ ] leakage prevention exists
[ ] preprocessing exists
[ ] feature selection exists
[ ] PCA exists
[ ] Logistic Regression exists
[ ] SVM exists
[ ] Random Forest exists
[ ] quantum backend abstraction exists
[ ] VQC exists where specified
[ ] QSVC exists where specified
[ ] quantum feature map exists
[ ] ansatz exists
[ ] optimizer configuration exists
[ ] quantum circuit generation exists
[ ] prediction pipeline exists
[ ] sensitivity is calculated
[ ] specificity is calculated
[ ] precision is calculated
[ ] recall is calculated
[ ] F1 is calculated
[ ] ROC-AUC is calculated
[ ] confusion matrix is calculated
[ ] false positives are visible
[ ] false negatives are visible
[ ] model probabilities are correctly labelled
[ ] research risk categories are clearly non-clinical
[ ] calibration architecture exists
[ ] cross-validation exists
[ ] held-out test evaluation exists
[ ] classical/quantum comparison uses equivalent conditions
[ ] feature influence is correctly labelled
[ ] quantum perturbation analysis is correctly labelled
[ ] experiment registry exists
[ ] model registry exists
[ ] experiment rerun structure exists
[ ] security protections exist
[ ] upload validation exists
[ ] path traversal prevention exists
[ ] no uploaded-file execution exists
[ ] Docker files exist
[ ] test files exist
[ ] documentation exists
[ ] README exists
[ ] demo mode exists
[ ] no fake metrics exist
[ ] no fabricated predictions exist
[ ] no fabricated quantum advantage exists
[ ] no patient-identifiable demo data exists
[ ] medical disclaimer is displayed
[ ] clinical validation is not claimed
[ ] quantum simulation is distinguished from real quantum hardware
[ ] limitations are documented
```

---

# 49. OUTPUT FILE

After generating the entire project, package it into exactly:

```text
ENTANGLEX-Q-HEALTH.zip
```

The archive MUST contain the complete project folder, not merely selected files.

Do not omit:

* backend
* frontend
* APIs
* database code
* configuration
* tests
* documentation
* Docker files
* demo/data support
* scripts
* README
* required metadata/configuration files

Do not create multiple ZIP archives.

The requested primary artifact is exactly one ZIP archive.

---

# 50. FINAL RESPONSE FORMAT

After creating the ZIP, provide ONLY a concise final response containing:

## 1. Downloadable ZIP

```text
ENTANGLEX-Q-HEALTH.zip
```

with the actual downloadable artifact.

## 2. Project Summary

Briefly state what was generated.

## 3. Installation Steps

Give the exact sequence a user should follow after extracting the ZIP.

## 4. Backend Startup

Give exact commands.

## 5. Frontend Startup

Give exact commands.

## 6. Docker Startup

Give exact commands.

## 7. Important Assumptions

List important assumptions, particularly dependency/version assumptions and any components that could not be runtime verified.

## 8. Verification Disclaimer

Explicitly state:

> The project source code was generated and packaged, but the application was not executed in this task. Therefore runtime compatibility, dependency compatibility, tests, frontend/backend integration, Docker execution, and quantum execution have not been independently verified.

Do NOT claim the project was tested.

Do NOT paste the entire project source code into the final response.

The ZIP is the primary deliverable.

---

# 51. FINAL INSTRUCTION

Do not spend the final response explaining how you would build the project.

Do not give me an architecture-only answer.

Do not give me snippets instead of files.

Do not give me a partial implementation.

Do not wait for section-by-section approval.

Make reasonable implementation decisions when minor details are unspecified.

Prioritize **completeness, internal consistency, scientific validity, biomedical safety, and maintainability**.

Generate the actual project files.

Package them.

Create exactly:

```text
ENTANGLEX-Q-HEALTH.zip
```

That ZIP is the primary deliverable.