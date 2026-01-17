from fastapi import FastAPI
from app.api import endpoints

app = FastAPI(
    title="Reality-to-Brick Pipeline",
    description="Transform 360° video into LEGO sets using Twelve Labs and Blackboard AI.",
    version="1.0.0"
)

# Include the routes
app.include_router(endpoints.router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Reality-to-Brick Pipeline. Send a video to /process-video to begin."}