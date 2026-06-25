from fastapi import FastAPI

from app.api.routes import router
from app.core.config import PROJECT_DESCRIPTION, PROJECT_NAME, PROJECT_VERSION
from app.db.database import create_db_and_tables
from app.db import models

app = FastAPI(
    title=PROJECT_NAME,
    description=PROJECT_DESCRIPTION,
    version=PROJECT_VERSION,
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


app.include_router(router)