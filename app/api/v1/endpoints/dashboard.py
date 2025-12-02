"""
Dashboard endpoints.
Business statistics and analytics.
"""

from fastapi import APIRouter, Query

from app.api.deps import DbSession, CurrentUser
from app.services.dashboard import DashboardService


router = APIRouter()


@router.get(
    "",
    summary="Dashboard complet",
    description="Obtenir toutes les statistiques du dashboard",
)
async def get_full_dashboard(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Obtenir le dashboard complet."""
    service = DashboardService(db)
    return await service.get_full_dashboard(current_user.id)


@router.get(
    "/stats",
    summary="Statistiques pour mobile",
    description="Statistiques formatées pour l'application mobile",
)
async def get_stats_for_mobile(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Obtenir les statistiques formatées pour le mobile."""
    service = DashboardService(db)
    
    # Get all data
    overview = await service.get_overview(current_user.id)
    invoice_dist = await service.get_invoice_status_distribution(current_user.id)
    quote_dist = await service.get_quote_status_distribution(current_user.id)
    recent = await service.get_recent_activity(current_user.id, limit=5)
    
    return {
        "total_revenue": overview.get("total_revenue", 0),
        "pending_amount": overview.get("pending_amount", 0),
        "client_count": overview.get("client_count", 0),
        "product_count": overview.get("product_count", 0),
        "invoice_count": overview.get("invoice_count", 0),
        "quote_count": overview.get("quote_count", 0),
        "invoices_by_status": invoice_dist,
        "quotes_by_status": quote_dist,
        "recent_activity": recent,
    }


@router.get(
    "/overview",
    summary="Vue d'ensemble",
    description="Obtenir les statistiques générales",
)
async def get_overview(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Obtenir la vue d'ensemble."""
    service = DashboardService(db)
    return await service.get_overview(current_user.id)


@router.get(
    "/revenue",
    summary="Chiffre d'affaires mensuel",
    description="Obtenir le CA par mois",
)
async def get_revenue_by_month(
    current_user: CurrentUser,
    db: DbSession,
    year: int | None = Query(None, description="Année (défaut: année courante)"),
) -> list:
    """Obtenir le chiffre d'affaires mensuel."""
    service = DashboardService(db)
    return await service.get_revenue_by_month(current_user.id, year)


@router.get(
    "/invoices/distribution",
    summary="Distribution des factures",
    description="Répartition des factures par statut",
)
async def get_invoice_distribution(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Obtenir la distribution des factures."""
    service = DashboardService(db)
    return await service.get_invoice_status_distribution(current_user.id)


@router.get(
    "/quotes/distribution",
    summary="Distribution des devis",
    description="Répartition des devis par statut",
)
async def get_quote_distribution(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Obtenir la distribution des devis."""
    service = DashboardService(db)
    return await service.get_quote_status_distribution(current_user.id)


@router.get(
    "/top-clients",
    summary="Meilleurs clients",
    description="Top clients par chiffre d'affaires",
)
async def get_top_clients(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(5, ge=1, le=20, description="Nombre de clients"),
) -> list:
    """Obtenir les meilleurs clients."""
    service = DashboardService(db)
    return await service.get_top_clients(current_user.id, limit)


@router.get(
    "/top-products",
    summary="Produits les plus vendus",
    description="Top produits par ventes",
)
async def get_top_products(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(5, ge=1, le=20, description="Nombre de produits"),
) -> list:
    """Obtenir les produits les plus vendus."""
    service = DashboardService(db)
    return await service.get_top_products(current_user.id, limit)


@router.get(
    "/recent-activity",
    summary="Activité récente",
    description="Dernières factures et devis",
)
async def get_recent_activity(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(10, ge=1, le=50, description="Nombre d'éléments"),
) -> list:
    """Obtenir l'activité récente."""
    service = DashboardService(db)
    return await service.get_recent_activity(current_user.id, limit)


@router.get(
    "/low-stock",
    summary="Produits en rupture",
    description="Produits avec stock bas",
)
async def get_low_stock_products(
    current_user: CurrentUser,
    db: DbSession,
) -> list:
    """Obtenir les produits en rupture de stock."""
    service = DashboardService(db)
    return await service.get_low_stock_products(current_user.id)

