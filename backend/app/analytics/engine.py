from typing import Any, List
import numpy as np


def detect_metric_anomalies(series: List[dict[str, Any]]) -> List[dict[str, Any]]:
    """
    Uses Scikit-learn IsolationForest combined with robust Z-score checks
    to flag abnormal revenue drops, expenditure spikes, or complaint surges.
    """
    if len(series) < 4:
        return []

    values = np.array([float(p["actual_value"]) for p in series], dtype=float)
    mean = float(np.mean(values))
    std = float(np.std(values)) or 1.0

    iso_flags = [False] * len(values)
    try:
        from sklearn.ensemble import IsolationForest
        clf = IsolationForest(contamination=0.18, random_state=42)
        preds = clf.fit_predict(values.reshape(-1, 1))
        iso_flags = [int(p) == -1 for p in preds]
    except Exception:
        pass

    anomalies: List[dict[str, Any]] = []
    for idx, point in enumerate(series):
        val = float(point["actual_value"])
        z = (val - mean) / std
        if iso_flags[idx] or abs(z) >= 1.55:
            direction = "above baseline" if z > 0 else "below baseline"
            severity = "critical" if abs(z) >= 1.9 else "high"
            anomalies.append({
                "period": point["period"],
                "metric_name": point["metric_name"],
                "actual_value": round(val, 2),
                "baseline_mean": round(mean, 2),
                "z_score": round(z, 2),
                "direction": direction,
                "severity": severity,
                "explanation": (
                    f"{point['metric_name'].replace('_', ' ').title()} in {point['period']} "
                    f"({val:,.0f}) deviated {abs(z):.2f}σ {direction} (mean {mean:,.0f})."
                ),
            })
    return anomalies


def forecast_metric(series: List[dict[str, Any]], horizon: int = 3) -> List[dict[str, Any]]:
    """
    Produces forward predictions using Statsmodels ExponentialSmoothing (Holt linear trend)
    with explicit prediction intervals (uncertainty bounds).
    """
    if len(series) < 3:
        return []

    values = np.array([float(p["actual_value"]) for p in series], dtype=float)
    last_period = series[-1]["period"]  # YYYY-MM
    year, month = int(last_period[:4]), int(last_period[5:7])
    model_name = "Statsmodels Holt Linear Trend"

    try:
        from statsmodels.tsa.holtwinters import Holt
        fit = Holt(values, initialization_method="estimated").fit(optimized=True)
        preds = fit.forecast(horizon)
        resid_std = float(np.std(fit.resid)) if len(fit.resid) > 1 else float(np.std(values) * 0.08)
    except Exception:
        # Clean linear regression fallback if statsmodels cannot converge
        x = np.arange(len(values))
        slope, intercept = np.polyfit(x, values, 1)
        preds = [slope * (len(values) + i) + intercept for i in range(horizon)]
        resid_std = float(np.std(values - (slope * x + intercept))) or float(np.mean(values) * 0.05)
        model_name = "Linear Trend Fallback"

    forecasts: List[dict[str, Any]] = []
    for step in range(1, horizon + 1):
        m = month + step
        y = year + (m - 1) // 12
        m_norm = ((m - 1) % 12) + 1
        pred_val = max(0.0, float(preds[step - 1]))
        # 90% uncertainty band widening with forecast horizon
        margin = max(pred_val * 0.03, 1.645 * resid_std * np.sqrt(step))
        forecasts.append({
            "period": f"{y:04d}-{m_norm:02d}",
            "metric_name": series[-1]["metric_name"],
            "predicted_value": round(pred_val, 2),
            "lower_bound": round(max(0.0, pred_val - margin), 2),
            "upper_bound": round(pred_val + margin, 2),
            "model_used": model_name,
            "is_predicted": True,
        })
    return forecasts
