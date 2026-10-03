import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_curve, roc_curve

def calculate_threshold_metrics(y_true, y_prob, t_min=0.0, t_max=1.0, t_step=0.01, fp_cost=None, fn_cost=None):
    thresholds = np.arange(t_min, t_max + t_step/2, t_step)
    
    results = []
    roc_points = []
    pr_points = []
    
    # Calculate PR and ROC curves using standard methods for accurate curve tracing
    fpr_curve, tpr_curve, roc_thresh = roc_curve(y_true, y_prob)
    for f, t, th in zip(fpr_curve, tpr_curve, roc_thresh):
        if 0 <= th <= 1:
            roc_points.append({"threshold": float(th), "fpr": float(f), "tpr": float(t)})
            
    prec_curve, rec_curve, pr_thresh = precision_recall_curve(y_true, y_prob)
    for p, r, th in zip(prec_curve, rec_curve, pr_thresh):
        if 0 <= th <= 1:
            pr_points.append({"threshold": float(th), "precision": float(p), "recall": float(r)})
    
    for t in thresholds:
        y_pred = (y_prob >= t).astype(int)
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
        
        sens = tp / (tp + fn) if (tp + fn) > 0 else None
        spec = tn / (tn + fp) if (tn + fp) > 0 else None
        prec = tp / (tp + fp) if (tp + fp) > 0 else None
        npv = tn / (tn + fn) if (tn + fn) > 0 else None
        
        f1 = None
        if prec is not None and sens is not None and (prec + sens) > 0:
            f1 = 2 * (prec * sens) / (prec + sens)
            
        bal_acc = None
        if sens is not None and spec is not None:
            bal_acc = (sens + spec) / 2
            
        acc = (tp + tn) / len(y_true)
        fpr = fp / (fp + tn) if (fp + tn) > 0 else None
        fnr = fn / (fn + tp) if (fn + tp) > 0 else None
        
        prevalence = (tp + fn) / len(y_true)
        predicted_positive_rate = (tp + fp) / len(y_true)
        
        youden_j = None
        if sens is not None and spec is not None:
            youden_j = sens + spec - 1
            
        mcc = None
        denom = np.sqrt(float(tp + fp) * float(tp + fn) * float(tn + fp) * float(tn + fn))
        if denom > 0:
            mcc = (tp * tn - fp * fn) / denom
            
        cost = None
        if fp_cost is not None and fn_cost is not None:
            cost = float(fp * fp_cost + fn * fn_cost)


        results.append({
            "threshold": float(t),
            "tp": int(tp),
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "sensitivity": sens,
            "specificity": spec,
            "precision": prec,
            "npv": npv,
            "f1": f1,
            "balanced_accuracy": bal_acc,
            "accuracy": float(acc),
            "fpr": fpr,
            "fnr": fnr,
            "prevalence": float(prevalence),
            "predicted_positive_rate": float(predicted_positive_rate),
            "youden_j": youden_j,
            "mcc": mcc,
            "expected_cost": cost
        })
        
    return results, roc_points, pr_points

def select_threshold(results, method: str, target: float = None, tie_breaker: str = "closest_to_0.5"):
    candidates = []
    best_val = -float('inf')
    
    if method == "fixed_user_threshold":
        # Find closest threshold
        candidates = sorted(results, key=lambda x: abs(x["threshold"] - target))
        return candidates[0], True, None
        
    for r in results:
        val = None
        if method == "youden_j":
            val = r["youden_j"]
        elif method == "f1_maximization":
            val = r["f1"]
        elif method == "balanced_accuracy_maximization":
            val = r["balanced_accuracy"]
        elif method == "target_sensitivity":
            if r["sensitivity"] is not None and r["sensitivity"] >= target:
                val = r["specificity"] # maximize spec given sens target
        elif method == "target_specificity":
            if r["specificity"] is not None and r["specificity"] >= target:
                val = r["sensitivity"]
        elif method == "target_precision":
            if r["precision"] is not None and r["precision"] >= target:
                val = r["sensitivity"]
        elif method == "target_npv":
            if r["npv"] is not None and r["npv"] >= target:
                val = r["specificity"]

        if val is not None:
            if val > best_val:
                best_val = val
                candidates = [r]
            elif val == best_val:
                candidates.append(r)
                
    if not candidates:
        # Feasibility failed
        return None, False, "Target constraint could not be achieved on the evaluation grid."

    # Tie breaking
    if tie_breaker == "lowest_threshold":
        chosen = min(candidates, key=lambda x: x["threshold"])
    elif tie_breaker == "highest_threshold":
        chosen = max(candidates, key=lambda x: x["threshold"])
    else: # closest_to_0.5
        chosen = min(candidates, key=lambda x: abs(x["threshold"] - 0.5))
        
    return chosen, True, None
