from fastapi import FastAPI

from app.middlewares.exception_handler_middleware import handle_exceptions
from app.middlewares.request_logging_middleware import log_requests


def setup_middlewares(app: FastAPI) -> None:
    app.middleware("http")(handle_exceptions)
    app.middleware("http")(log_requests)
