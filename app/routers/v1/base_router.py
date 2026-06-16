from fastapi import APIRouter

from app.globals.others_constants import OtherConstants
from app.routers.v1.auth_router import router as auth_router
from app.routers.v1.message_router import router as message_router
from app.routers.v1.thread_router import router as thread_router

v1_api_router = APIRouter(prefix="/v1", responses=OtherConstants.COMMON_API_RESPONSES)


@v1_api_router.get("/hello")
async def hello():
    return {"message": "Hello World!"}


v1_api_router.include_router(auth_router)
v1_api_router.include_router(thread_router)
v1_api_router.include_router(message_router)
