import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_database, close_pool

from routes.auth import router as auth_router
from routes.complaints import router as complaints_router
from routes.staff import router as staff_router
from routes.admin import router as admin_router


# =========================================================
# CREATE FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="CampusCare API",
    description="Campus Maintenance Management System",
    version="1.0.0"
)


# =========================================================
# CORS CONFIGURATION
# =========================================================


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:5501,http://localhost:5501,http://127.0.0.1:5502,http://localhost:5502"
    ).split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
# =========================================================
# INITIALIZE DATABASE
# =========================================================

init_database()


# =========================================================
# REGISTER ROUTERS
# =========================================================

app.include_router(auth_router)
app.include_router(complaints_router)
app.include_router(staff_router)
app.include_router(admin_router)


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return {
        "message": "CampusCare Backend is running!"
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "CampusCare API"
    }


@app.on_event("shutdown")
def on_shutdown():
    close_pool()