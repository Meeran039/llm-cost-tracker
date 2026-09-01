from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, keys, usage_log, advisor, api_keys

settings.validate()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LLM Cost Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ledger.v0.build",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(keys.router)
app.include_router(usage_log.router)
app.include_router(advisor.router)
app.include_router(api_keys.router)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "llm-cost-tracker-api"}