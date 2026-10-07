"""
EnerX Backend - FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, project, investments, user, marketplace

app = FastAPI(
    title="EnerX Backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(project.router)
app.include_router(investments.router)
app.include_router(user.router)
app.include_router(marketplace.router)

@app.get("/", tags=["System"])
def root():
    return {"app": "EnerX Backend", "status": "online", "docs": "/docs"}
