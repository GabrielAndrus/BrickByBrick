from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Load .env file
load_dotenv()

from app.api import endpoints

app = FastAPI(
    title="Reality-to-Brick Pipeline",
    description="Transform 360° video into LEGO sets using Twelve Labs and Blackboard AI.",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API routes
app.include_router(endpoints.router, prefix="/api")

# Serve static files (frontend)
static_dir = Path(__file__).parent.parent.parent / "frontend"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve the frontend HTML page."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(
            str(index_path),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
    return {"message": "Welcome to the Reality-to-Brick Pipeline. Send a video to /api/process-video to begin."}