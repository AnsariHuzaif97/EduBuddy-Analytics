import sys
import os
# Add current directory (backend) to path so relative imports work seamlessly in deployment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import base64
import io
import matplotlib
matplotlib.use('Agg') # Set non-interactive backend for matplotlib
import matplotlib.pyplot as plt

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from predict import analyze_student
from explainer import explain_prediction, get_shap_waterfall_plot

app = FastAPI(title="EduVision Elite API")

# Enable CORS just in case
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StudentInput(BaseModel):
    code_module: str
    code_presentation: str
    gender: str
    region: str
    highest_education: str
    imd_band: str
    age_band: str
    num_of_prev_attempts: int = 0
    studied_credits: int
    disability: str
    module_presentation_length: int = 268
    total_clicks: int
    active_days: int
    avg_clicks_per_day: float
    activity_span: int
    avg_assignment_score: float

@app.post("/api/analyze")
async def analyze(student: StudentInput):
    try:
        # Convert Pydantic model to dict
        input_data = student.dict()
        res = analyze_student(input_data)
        
        # Cannot serialize pipeline and input_df to JSON, so remove them
        res.pop('pipeline', None)
        res.pop('input_df', None)
        
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/telemetry")
async def telemetry(student: StudentInput):
    try:
        input_data = student.dict()
        res = analyze_student(input_data)
        
        pipeline = res.get('pipeline')
        input_df = res.get('input_df')
        
        if pipeline is None or input_df is None:
            raise HTTPException(status_code=400, detail="Telemetry sensors failed to initialize.")
            
        explanation = explain_prediction(pipeline, input_df)
        fig = get_shap_waterfall_plot(explanation)
        
        # Convert plot to Base64 image
        buf = io.BytesIO()
        fig.patch.set_facecolor('white')
        fig.savefig(buf, format="png", bbox_inches='tight', transparent=False, facecolor='white', dpi=300)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        
        return {"image": f"data:image/png;base64,{img_str}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files to serve frontend (Make sure 'frontend' directory exists at the project root)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
