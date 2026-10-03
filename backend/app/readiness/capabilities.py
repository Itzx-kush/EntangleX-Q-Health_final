from backend.app.readiness.schemas import ModelCapabilityResponse

def get_model_capabilities() -> dict[str, ModelCapabilityResponse]:
    return {
        "logistic_regression": ModelCapabilityResponse(
            model_type="logistic_regression",
            binary_classification="supported",
            grouped_validation="supported",
            calibration="supported",
            threshold_analysis="supported",
            external_validation="supported",
            limitations=[]
        ),
        "random_forest": ModelCapabilityResponse(
            model_type="random_forest",
            binary_classification="supported",
            grouped_validation="supported",
            calibration="supported",
            threshold_analysis="supported",
            external_validation="supported",
            limitations=[]
        ),
        "svm": ModelCapabilityResponse(
            model_type="svm",
            binary_classification="supported",
            grouped_validation="supported",
            calibration="supported",
            threshold_analysis="supported",
            external_validation="supported",
            limitations=["Platt scaling is used for calibration probabilities"]
        ),
        "vqc": ModelCapabilityResponse(
            model_type="vqc",
            binary_classification="supported",
            grouped_validation="supported",
            calibration="supported",
            threshold_analysis="supported",
            external_validation="supported",
            limitations=["Quantum hardware constraints apply", "Long execution times expected"]
        ),
        "qsvc": ModelCapabilityResponse(
            model_type="qsvc",
            binary_classification="supported",
            grouped_validation="supported",
            calibration="supported",
            threshold_analysis="supported",
            external_validation="supported",
            limitations=["Quantum hardware constraints apply", "Calibration uses Platt scaling over quantum kernel matrix"]
        ),
        "qnn": ModelCapabilityResponse(
            model_type="qnn",
            binary_classification="supported",
            grouped_validation="supported",
            calibration="supported",
            threshold_analysis="supported",
            external_validation="supported",
            limitations=["Quantum hardware constraints apply"]
        ),
        "hybrid_pennylane_torch": ModelCapabilityResponse(
            model_type="hybrid_pennylane_torch",
            binary_classification="supported",
            grouped_validation="supported",
            calibration="supported",
            threshold_analysis="supported",
            external_validation="supported",
            limitations=["Quantum advantage not established"]
        )
    }
