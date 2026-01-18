from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import endpoints
from app.api.lego_build_endpoint import router as lego_build_router, init_lego_services
from app.api.threejs_pipeline import router as threejs_router, init_threejs_services
from app.services.backboard_lego_memory import BackboardLegoMemory
from app.services.master_builder import MasterBuilder

app = FastAPI(
    title="Reality-to-Brick Pipeline",
    description="Transform 360° video into LEGO sets using Twelve Labs and Blackboard AI.",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the routes
app.include_router(endpoints.router)
app.include_router(lego_build_router)
app.include_router(threejs_router)

# Initialize LEGO services on startup
@app.on_event("startup")
async def startup_event():
    """Initialize services on app startup"""
    try:
        init_lego_services()
        
        # Initialize Three.js pipeline services
        backboard_memory = BackboardLegoMemory()
        master_builder = MasterBuilder()
        init_threejs_services(backboard_memory, master_builder)
        
        print("✅ LEGO Build Generation Services initialized")
        print("✅ Backboard Memory initialized")
        print("✅ Three.js Pipeline services initialized")
        print("✅ Ready for Three.js voxel processing")
    except Exception as e:
        print(f"⚠️ Warning during service initialization: {e}")

@app.get("/")
async def root():
    return {"message": "Welcome to the Reality-to-Brick Pipeline. Send a video to /process-video to begin."}
