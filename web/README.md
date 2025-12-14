# IndexMaker Web Platform

A full-stack web application for building and managing custom financial indices, powered by the `indexmaker` Python library.

## 🏗️ Architecture

```
web/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # REST API endpoints
│   │   ├── core/        # Config, security, settings
│   │   ├── db/          # Database session & models
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── services/    # Business logic
│   │   └── tests/       # Unit & integration tests
│   ├── alembic/         # Database migrations
│   └── Dockerfile
│
├── frontend/            # React frontend
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── hooks/       # Custom React hooks
│   │   ├── lib/         # Utilities & API client
│   │   ├── pages/       # Page components
│   │   ├── store/       # Zustand state management
│   │   └── types/       # TypeScript types
│   └── Dockerfile
│
└── docker-compose.yml   # Local development setup
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.10+ (for backend development)
- PostgreSQL 16 (via Docker)
- Redis (via Docker)

### Development Setup

1. **Clone and navigate:**
   ```bash
   cd indexmaker/web
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/api/docs

### Manual Setup (without Docker)

#### Backend

```bash
cd backend
poetry install
cp .env.example .env  # Configure environment variables

# Start PostgreSQL and Redis locally or via Docker
docker-compose up -d db redis

# Run migrations
poetry run alembic upgrade head

# Start server
poetry run uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## 📚 API Documentation

The API documentation is available at:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | User registration |
| `/api/v1/auth/login` | POST | User login |
| `/api/v1/auth/me` | GET | Current user info |
| `/api/v1/indices` | GET/POST | List/create indices |
| `/api/v1/indices/{id}` | GET/PATCH/DELETE | Index CRUD |
| `/api/v1/indices/{id}/components` | POST | Add component |
| `/api/v1/indices/{id}/calculate` | POST | Calculate index |
| `/api/v1/backtests` | GET/POST | List/create backtests |
| `/api/v1/market-data/quote/{ticker}` | GET | Get stock quote |

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific tests
poetry run pytest tests/unit/test_auth.py -v
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run with UI
npm run test:ui
```

## 🎨 Features

### Index Builder
- **Weighting Methods**: Equal weight, market cap, free-float, custom
- **Rebalancing**: Daily, weekly, monthly, quarterly, semi-annual, annual
- **Constraints**: Max weight caps, sector limits, country limits
- **Universe Filters**: Market cap, volume, sector, country

### Backtesting
- **Historical Analysis**: Up to 10 years of data
- **Benchmarks**: Compare against SPY, QQQ, or custom
- **Metrics**: Total return, Sharpe ratio, max drawdown, volatility
- **Visualizations**: Performance charts, drawdown curves

### Real-Time Data
- **Market Data**: Via Yahoo Finance API
- **Auto Updates**: Daily index recalculation
- **Alerts**: Price and weight drift notifications

## 🔒 Security

- **Authentication**: JWT tokens with refresh mechanism
- **Password Hashing**: bcrypt
- **CORS**: Configurable origins
- **Rate Limiting**: Per-user limits
- **Input Validation**: Pydantic schemas

## 📦 Tech Stack

### Backend
- **FastAPI**: High-performance async API framework
- **SQLAlchemy 2.0**: Async ORM with PostgreSQL
- **Pydantic v2**: Data validation
- **Celery**: Background task processing
- **Redis**: Caching and task queue
- **Alembic**: Database migrations

### Frontend
- **React 18**: UI library
- **TypeScript**: Type safety
- **Vite**: Build tool
- **TanStack Query**: Data fetching & caching
- **Zustand**: State management
- **Tailwind CSS**: Styling
- **shadcn/ui**: Component library
- **Recharts**: Charts & visualizations

## 🚢 Deployment

### Production Checklist

1. Set secure `SECRET_KEY` in environment
2. Configure proper database credentials
3. Set up SSL/TLS certificates
4. Configure CORS for your domain
5. Set up monitoring (e.g., Sentry)
6. Enable rate limiting
7. Set up database backups

### Docker Production Build

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

---

Built with ❤️ using the [indexmaker](https://github.com/your-repo/indexmaker) library.

