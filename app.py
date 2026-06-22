import sys
import os
import uvicorn

# Add backend directory to path so imports work correctly
backend_path = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, backend_path)

from main import app

if __name__ == "__main__":
    # Get port from environment variable for deployment flexibility, default to 8000
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting EduVision Elite server on http://0.0.0.0:{port} ...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
