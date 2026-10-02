import numpy as np
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.calibration import calibration_curve

def calculate_calibration_metrics(y_true, y_prob, n_bins=10):
    """Calculate Brier, Log Loss, ECE, MCE, and curve."""
    if len(np.unique(y_true)) < 2:
        raise ValueError("Evaluation data must contain both classes.")

    brier = float(brier_score_loss(y_true, y_prob))
    
    # log loss with small clipping
    p = np.clip(y_prob, 1e-15, 1 - 1e-15)
    ll = float(log_loss(y_true, p))
    
    # Curve
    fraction_pos, mean_pred = calibration_curve(y_true, y_prob, n_bins=n_bins, strategy="uniform")
    
    # Bins for ECE and MCE (Adaptive or Uniform)
    # We will compute manually to get sample counts per bin
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    binids = np.digitize(y_prob, bins) - 1
    
    bin_sums = np.bincount(binids, weights=y_prob, minlength=n_bins)
    bin_true = np.bincount(binids, weights=y_true, minlength=n_bins)
    bin_total = np.bincount(binids, minlength=n_bins)
    
    nonzero = bin_total > 0
    
    bin_means = bin_sums[nonzero] / bin_total[nonzero]
    bin_actuals = bin_true[nonzero] / bin_total[nonzero]
    bin_counts = bin_total[nonzero]
    
    gaps = np.abs(bin_means - bin_actuals)
    
    ece = float(np.sum(gaps * bin_counts) / np.sum(bin_counts))
    mce = float(np.max(gaps))
    
    curve_data = []
    idx = 0
    for i in range(n_bins):
        if bin_total[i] > 0:
            curve_data.append({
                "lower_bound": float(bins[i]),
                "upper_bound": float(bins[i+1]),
                "mean_predicted_probability": float(bin_means[idx]),
                "observed_positive_rate": float(bin_actuals[idx]),
                "sample_count": int(bin_counts[idx]),
                "calibration_gap": float(gaps[idx])
            })
            idx += 1
            
    return {
        "brier_score": brier,
        "log_loss": ll,
        "expected_calibration_error": ece,
        "maximum_calibration_error": mce
    }, curve_data
