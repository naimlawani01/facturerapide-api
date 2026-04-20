#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# FactureRapide — Railway Setup Script
# Run this once locally to create all Railway infrastructure.
# ============================================================

PROJECT_NAME="${1:-facturerapide}"
SERVICE_NAME="facturerapide-api"
REPO="naimlawani01/facturerapide-api"

# --- Pre-checks ---
if ! command -v railway &> /dev/null; then
  echo "❌ Railway CLI not found. Install: npm i -g @railway/cli"
  exit 1
fi

if ! railway whoami &> /dev/null; then
  echo "❌ Not logged in. Run: railway login"
  exit 1
fi

echo "👤 Logged in as: $(railway whoami 2>&1 | head -1)"
echo ""

# --- Create project ---
echo "🚀 Creating project '${PROJECT_NAME}'..."
railway init --name "${PROJECT_NAME}" 2>/dev/null || echo "   ↳ Project already exists or linked, continuing."
echo ""

# --- Add PostgreSQL ---
echo "🗄️  Adding PostgreSQL..."
railway add --database postgres 2>/dev/null || echo "   ↳ PostgreSQL already exists, continuing."
echo ""

# --- Create backend service ---
echo "⚙️  Creating service '${SERVICE_NAME}' linked to ${REPO}..."
railway add --service "${SERVICE_NAME}" --repo "${REPO}" 2>/dev/null || echo "   ↳ Service already exists, continuing."
echo ""

# --- Link to backend service ---
echo "🔗 Linking to ${SERVICE_NAME}..."
railway service link "${SERVICE_NAME}"
echo ""

# --- Set environment variables ---
echo "📝 Configuring environment variables..."
SECRET_KEY=$(openssl rand -hex 32)

railway variables set \
  "ENVIRONMENT=production" \
  "DEBUG=false" \
  "APP_NAME=FactureRapide API" \
  "APP_VERSION=1.0.0" \
  'DATABASE_URL=${{Postgres.DATABASE_URL}}' \
  'DATABASE_URL_SYNC=${{Postgres.DATABASE_URL}}' \
  "SECRET_KEY=${SECRET_KEY}" \
  "ALGORITHM=HS256" \
  "ACCESS_TOKEN_EXPIRE_MINUTES=30" \
  "REFRESH_TOKEN_EXPIRE_DAYS=7" \
  'CORS_ORIGINS=["*"]' \
  "PDF_STORAGE_PATH=./storage/invoices" \
  "PDF_RECEIPTS_PATH=./storage/receipts" \
  "HOST=0.0.0.0" \
  "PORT=8000"
echo ""

# --- Generate domain ---
echo "🌐 Generating public domain..."
railway domain
echo ""

# --- Summary ---
echo "✅ Railway setup complete!"
echo ""
railway status
echo ""
echo "📋 Variables:"
railway variables
