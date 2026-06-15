from fastapi import APIRouter

from app.globals.others_constants import OtherConstants
from app.routers.v1.auth_router import router as auth_router

v1_api_router = APIRouter(prefix="/v1", responses=OtherConstants.COMMON_API_RESPONSES)


@v1_api_router.get("/hello")
async def hello():
    return {"message": "Hello World!"}


v1_api_router.include_router(auth_router)
