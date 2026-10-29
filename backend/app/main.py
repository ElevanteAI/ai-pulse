from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import ALLOWED_ORIGINS, AUTO_SEED
from .db import Base, engine
from .routes import auth_routes, diagnostic, reports, dashboard

Base.metadata.create_all(bind=engine)
if AUTO_SEED:
    from .seed import run_if_empty
    run_if_empty()  # only fills an empty database; never drops existing data

app = FastAPI(title="AI Pulse API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(diagnostic.router)
app.include_router(reports.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok"}
