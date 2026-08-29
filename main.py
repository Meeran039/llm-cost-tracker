from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, keys, usage, api_keys

settings.validate()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LLM Cost Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(keys.router)
app.include_router(usage.router)
app.include_router(api_keys.router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "llm-cost-tracker-api"}