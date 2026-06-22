import pandas as pd
import joblib
import json
import os
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

@lru_cache(maxsize=1)
def load_system():
    pipeline_path = os.path.join(MODELS_DIR, "model_pipeline.pkl")
    features_path = os.path.join(MODELS_DIR, "feature_columns.json")
    
    if not os.path.exists(pipeline_path):
        raise FileNotFoundError(f"Model pipeline not found at {pipeline_path}. Please run src/model.py first.")
        
    pipeline = joblib.load(pipeline_path)
    with open(features_path, "r") as f:
        feature_columns = json.load(f)
        
    return pipeline, feature_columns

def predict_student(input_data):
    pipeline, feature_columns = load_system()
    
    input_df = pd.DataFrame([input_data])
    
    for col in feature_columns:
        if col not in input_df.columns:
            input_df[col] = 0
            
    input_df = input_df[feature_columns]
    
    prediction = pipeline.predict(input_df)[0]
    probability = pipeline.predict_proba(input_df)[0][1]
    
    return {
        "prediction": int(prediction),
        "success_probability": float(probability),
        "input_df": input_df,
        "pipeline": pipeline,
        "feature_columns": feature_columns
    }
