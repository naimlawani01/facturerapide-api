"""
FactureRapide API - Main Application Entry Point
Mini-SaaS de facturation pour artisans et PME.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📊 Environment: {settings.ENVIRONMENT}")
    
    # Initialize database tables (for development)
    if settings.is_development:
        await init_db()
        print("✅ Database tables initialized")
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")
    await close_db()
    print("✅ Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
## 🧾 FactureRapide API

API backend pour le mini-SaaS de facturation destiné aux artisans et PME.

### Fonctionnalités principales:

* **👤 Authentification** - Inscription, connexion, JWT tokens
* **👥 Gestion des Clients** - CRUD complet pour les clients
* **📦 Gestion des Produits** - Produits, services et stock
* **🧾 Facturation** - Création et gestion des factures
* **💳 Paiements** - Suivi des paiements
* **📄 PDF** - Génération de factures PDF professionnelles

### Cibles:
Mécaniciens, coiffeurs, boutiquiers, maçons, restaurants, et plus...
    """,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
    lifespan=lifespan,
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with French messages."""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Erreur de validation des données",
            "errors": errors,
        },
    )


# Include API router
app.include_router(api_router, prefix="/api/v1")


# Health check endpoint
@app.get(
    "/health",
    tags=["Santé"],
    summary="Vérification de l'état du serveur",
)
async def health_check():
    """Check if the API is running."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Root endpoint
@app.get(
    "/",
    tags=["Info"],
    summary="Informations de l'API",
)
async def root():
    """Get API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Mini-SaaS de facturation pour artisans et PME",
        "docs": "/docs" if settings.is_development else "Disabled in production",
        "health": "/health",
    }


# For running with uvicorn directly
if __name__ == "__main__":
    import os
    import uvicorn
    
    # Get port from environment (Render sets PORT) or default to 8000
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=port,
        reload=settings.is_development,
    )

