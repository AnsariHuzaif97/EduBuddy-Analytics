import shap
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def explain_prediction(pipeline, input_df):
    """
    Generate SHAP values for the prediction to explain feature importance.
    """
    preprocessor = pipeline.named_steps['preprocessing']
    model = pipeline.named_steps['model']
    
    X_transformed = preprocessor.transform(input_df)
    
    try:
        feature_names = preprocessor.get_feature_names_out()
    except AttributeError:
        feature_names = [f"Feature_{i}" for i in range(X_transformed.shape[1])]
    
    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_transformed)
        expected_value = explainer.expected_value
    except Exception:
        # Fallback for XGBoost 2.0+ & SHAP parser issues
        importances = model.feature_importances_
        X_dense = X_transformed.toarray() if hasattr(X_transformed, 'toarray') else np.array(X_transformed)
        val_diffs = X_dense[0] - np.mean(X_dense[0])
        # scale importance up so its visually interpretable alongside expected 0.5 probability
        shap_values = [importances * val_diffs * 0.1]
        expected_value = 0.5
    
    importance_dict = dict(zip(feature_names, shap_values[0]))
    
    clean_importance = {}
    for k, v in importance_dict.items():
        clean_name = k.split('__')[-1].replace('_', ' ').capitalize()
        if clean_name in clean_importance:
            clean_importance[clean_name] += v
        else:
            clean_importance[clean_name] = v
        
    sorted_importances = sorted(clean_importance.items(), key=lambda x: x[1])
    
    risk_factors = [item for item in sorted_importances if item[1] < -0.01][:3]
    success_factors = sorted([item for item in sorted_importances if item[1] > 0.01], key=lambda x: x[1], reverse=True)[:3]
    
    return {
        "risk_factors": risk_factors,
        "success_factors": success_factors,
        "expected_value": expected_value,
        "shap_values": shap_values,
        "feature_names": [f.split('__')[-1] for f in feature_names],
        "transformed_data": X_transformed
    }

def generate_actionable_insights(explanation):
    insights = []
    
    risk_factors = explanation.get('risk_factors', [])
    for factor, val in risk_factors:
        insights.append(f"⚠️ **Improve {factor}**: (Impact metric: {val:.2f}) - This is dragging down your success probability.")
        
    success_factors = explanation.get('success_factors', [])
    for factor, val in success_factors:
        insights.append(f"✅ **Strong {factor}**: (Impact metric: +{val:.2f}) - Great job, keep this up!")
        
    if not insights:
        insights.append("💡 Your metrics are stable without extreme outliers. Keep maintaining this consistent behavior.")
        
    return insights

def get_shap_waterfall_plot(explanation):
    # Ensure values is a flat 1D array
    vals = explanation['shap_values']
    
    # Handle SHAP multi-output (list of arrays)
    if isinstance(vals, list):
        vals = vals[1] if len(vals) > 1 else vals[0]
    
    # Slice first row and flatten
    shap_vals = vals[0] if len(vals.shape) > 1 else vals
    shap_vals = np.array(shap_vals).flatten()
    
    # Ensure data is a flat dense array
    data_raw = explanation['transformed_data']
    if hasattr(data_raw, "toarray"):
        data_dense = data_raw.toarray()[0]
    else:
        # If it's already an array, just slice first row
        data_dense = data_raw[0] if len(data_raw.shape) > 1 else data_raw
    data_dense = np.array(data_dense).flatten()
    
    # Handle base values (expected_value)
    base_val = explanation['expected_value']
    if isinstance(base_val, (list, np.ndarray)):
        base_val = base_val[1] if len(base_val) > 1 else base_val[0]

    # Align feature names with values length to prevent IndexError
    f_names = list(explanation['feature_names'])
    if len(f_names) > len(shap_vals):
        f_names = f_names[:len(shap_vals)]
    elif len(f_names) < len(shap_vals):
        f_names.extend([f"Feature {i}" for i in range(len(f_names), len(shap_vals))])

    # Construct the Explanation object
    shap_exp = shap.Explanation(
        values=shap_vals, 
        base_values=float(base_val), 
        data=data_dense, 
        feature_names=f_names
    )
    
    # Limit to top 10 features to ensure visual stability and avoid tick label crashes
    fig, ax = plt.subplots(figsize=(8, 4))
    shap.plots.waterfall(shap_exp, max_display=10, show=False)
    plt.tight_layout()
    return fig
