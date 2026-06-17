from fastapi import APIRouter

from app.schemas.globals.api_utils_schemas import ApiUtilsSchemas
from app.routers.v1.message_router import router as message_router
from app.routers.v1.thread_router import router as thread_router

v1_api_router = APIRouter(prefix="/v1", responses=ApiUtilsSchemas.COMMON_API_RESPONSES)


@v1_api_router.get("/hello")
async def hello():
    return {"message": "Hello World!"}


v1_api_router.include_router(thread_router)
v1_api_router.include_router(message_router)
