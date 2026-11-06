import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 (importing this registers the tables)
from app.database import Base, engine
from app.routes import admin, auth, documents

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TrustVault API")

# Allow frontend origins (comma-separated in FRONTEND_ORIGIN env var, or * in dev)
raw_origins = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173")
origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(documents.router)


@app.get("/health")
def health():
    return {"status": "ok"}