from fastapi import FastAPI

from app import models  # noqa: F401  (importing this registers the tables)
from app.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}