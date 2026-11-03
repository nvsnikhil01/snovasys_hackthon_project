from fastapi import FastAPI

from app import models  # noqa: F401  (importing this registers the tables)
from app.database import Base, engine
from app.routes import admin, auth

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(auth.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok"}