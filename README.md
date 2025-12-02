# 🧾 FactureRapide Backend API

API backend pour le mini-SaaS de facturation destiné aux artisans et PME.

## 🎯 Fonctionnalités

- **👤 Authentification** - Inscription, connexion, JWT tokens (access + refresh)
- **👥 Gestion des Clients** - CRUD complet pour les clients
- **📦 Gestion des Produits** - Produits, services et gestion de stock
- **🧾 Facturation** - Création et gestion des factures avec lignes
- **💳 Paiements** - Suivi des paiements (espèces, carte, virement, etc.)
- **📄 PDF** - Génération de factures PDF professionnelles

## 🛠️ Stack Technique

- **Framework**: FastAPI
- **Base de données**: PostgreSQL + SQLAlchemy (async)
- **Authentification**: JWT (python-jose)
- **Validation**: Pydantic v2
- **Migrations**: Alembic
- **PDF**: ReportLab

## 📁 Structure du Projet

```
backend/
├── alembic/                 # Migrations de base de données
│   ├── versions/           # Fichiers de migration
│   └── env.py              # Configuration Alembic
├── app/
│   ├── api/                # Endpoints API
│   │   ├── deps.py         # Dépendances (auth, db)
│   │   └── v1/
│   │       ├── endpoints/  # Routers par domaine
│   │       └── router.py   # Agrégateur de routes
│   ├── core/               # Configuration centrale
│   │   ├── config.py       # Settings applicatifs
│   │   ├── database.py     # Configuration BDD
│   │   └── security.py     # JWT & hashing
│   ├── models/             # Modèles SQLAlchemy
│   │   ├── user.py
│   │   ├── client.py
│   │   ├── product.py
│   │   ├── invoice.py
│   │   └── payment.py
│   ├── schemas/            # Schémas Pydantic
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── client.py
│   │   ├── product.py
│   │   ├── invoice.py
│   │   └── payment.py
│   ├── services/           # Logique métier
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── client.py
│   │   ├── product.py
│   │   ├── invoice.py
│   │   ├── payment.py
│   │   └── pdf.py
│   └── main.py             # Point d'entrée FastAPI
├── storage/                # Stockage des PDFs générés
├── requirements.txt        # Dépendances Python
├── alembic.ini            # Configuration Alembic
└── README.md
```

## 🚀 Installation

### Prérequis

- Python 3.11+
- PostgreSQL 14+

### 1. Cloner et créer l'environnement virtuel

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Configurer les variables d'environnement

Copier `env.example` vers `.env` et modifier les valeurs:

```bash
cp env.example .env
```

Variables importantes:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/facturerapide
SECRET_KEY=votre-cle-secrete-minimum-32-caracteres
```

### 4. Créer la base de données

```bash
# Se connecter à PostgreSQL
psql -U postgres

# Créer la base
CREATE DATABASE facturerapide;
\q
```

### 5. Appliquer les migrations

```bash
# Générer une migration initiale
alembic revision --autogenerate -m "Initial migration"

# Appliquer les migrations
alembic upgrade head
```

### 6. Lancer le serveur

```bash
# Mode développement avec rechargement automatique
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ou directement
python -m app.main
```

## 📚 Documentation API

Une fois le serveur lancé, la documentation est disponible:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔐 Authentification

L'API utilise JWT pour l'authentification:

1. **S'inscrire**: `POST /api/v1/auth/register`
2. **Se connecter**: `POST /api/v1/auth/login`
3. **Utiliser le token**: Header `Authorization: Bearer <token>`
4. **Rafraîchir**: `POST /api/v1/auth/refresh`

Exemple d'inscription:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "artisan@example.com",
    "password": "motdepasse123",
    "full_name": "Jean Dupont",
    "business_name": "Dupont Services"
  }'
```

## 📋 Endpoints Principaux

### Clients
- `GET /api/v1/clients` - Lister les clients
- `POST /api/v1/clients` - Créer un client
- `GET /api/v1/clients/{id}` - Détails d'un client
- `PATCH /api/v1/clients/{id}` - Modifier un client
- `DELETE /api/v1/clients/{id}` - Supprimer un client

### Produits
- `GET /api/v1/products` - Lister les produits
- `POST /api/v1/products` - Créer un produit
- `GET /api/v1/products/{id}` - Détails d'un produit
- `PATCH /api/v1/products/{id}` - Modifier un produit
- `POST /api/v1/products/{id}/stock` - Ajuster le stock

### Factures
- `GET /api/v1/invoices` - Lister les factures
- `POST /api/v1/invoices` - Créer une facture
- `GET /api/v1/invoices/{id}` - Détails d'une facture
- `POST /api/v1/invoices/{id}/items` - Ajouter une ligne
- `POST /api/v1/invoices/{id}/send` - Marquer comme envoyée
- `GET /api/v1/invoices/{id}/pdf` - Télécharger le PDF

### Paiements
- `GET /api/v1/payments` - Lister les paiements
- `POST /api/v1/payments` - Enregistrer un paiement
- `GET /api/v1/payments/invoice/{id}` - Paiements d'une facture

## 🧪 Tests

```bash
# Installer les dépendances de test
pip install pytest pytest-asyncio httpx

# Lancer les tests
pytest tests/ -v
```

## 📊 Modèle de Données

### User (Utilisateur/Entreprise)
- Informations d'authentification
- Informations business (nom, adresse, SIRET, logo)

### Client
- Rattaché à un User
- Nom, adresse, email, téléphone, numéro fiscal

### Product (Produit/Service)
- Rattaché à un User
- Prix HT, taux TVA, unité
- Gestion de stock (pour les produits physiques)

### Invoice (Facture)
- Rattachée à un User et un Client
- Statut: brouillon, envoyée, payée, partiellement payée, en retard, annulée
- Lignes de facture (InvoiceItem)

### Payment (Paiement)
- Rattaché à une Invoice
- Montant, date, méthode (espèces, carte, virement, chèque, mobile)

## 🔧 Configuration Avancée

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `DATABASE_URL` | URL de connexion PostgreSQL (async) | - |
| `SECRET_KEY` | Clé secrète pour JWT | - |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de validité du token | 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Durée du refresh token | 7 |
| `CORS_ORIGINS` | Origines autorisées (JSON array) | localhost |
| `PDF_STORAGE_PATH` | Chemin de stockage des PDFs | ./storage/invoices |

## 🤝 Contribution

1. Fork le projet
2. Créer une branche (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Commit (`git commit -am 'Ajout nouvelle fonctionnalité'`)
4. Push (`git push origin feature/nouvelle-fonctionnalite`)
5. Créer une Pull Request

## 📄 Licence

MIT License - voir le fichier LICENSE pour plus de détails.

