from fastapi import APIRouter

router = APIRouter()


# Add your endpoints here
@router.get("/test")
async def test_endpoint():
    """
    Test endpoint
    """
    return {"message": "API endpoints are working"}
