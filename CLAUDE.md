# CLAUDE.md - Codebase Guide for Claude Code

This file provides essential information for Claude Code instances working in this Amazon product tracking system repository.

## Project Overview

This is a **multi-tenant SaaS platform** for Amazon product tracking and analysis. The system:
- Tracks 1000+ products with price, BSR, ratings monitoring
- Uses Apify actors for web scraping
- Provides AI-driven competitor analysis via LangChain + OpenAI
- Implements microservices architecture with FastAPI
- Uses APISIX gateway for multi-tenant routing

## Quick Start Commands

```bash
# Complete development environment setup
make dev-setup

# Start development environment
./dev.sh start  # or make dev

# Check environment health
make dev-check

# Run tests
make test

# Code quality checks
make check  # Runs lint + type-check + security-check
```

## Architecture Overview

### Service Structure
- **User Service** (port 8001): Authentication, tenant management
- **Core Service** (port 8002): Product tracking, analysis
- **Crawler Service** (port 8003): Apify integration, data scraping
- **APISIX Gateway** (port 9080): API routing, JWT auth
- **Background Services**: Celery workers + Redis + PostgreSQL

### Key Components
- **Database**: Supabase PostgreSQL with multi-tenant schema
- **Cache**: Redis (24-48h TTL for product data)
- **Task Queue**: Celery + AWS SQS for async operations
- **Monitoring**: OpenTelemetry + Prometheus + Grafana

## Important Patterns

### Multi-tenancy
- All models inherit from `TenantMixin` with `tenant_id` field
- APISIX routes by subdomain: `tenant-a.domain.com` → tenant filtering
- Database isolation via tenant_id in all queries

### Authentication
- JWT tokens with refresh mechanism
- API Keys for programmatic access
- RBAC with roles: superadmin, tenant_admin, user, viewer
- Demo account: `admin@demo.com` / `admin123456`

### Data Models
Key models in `amazon_tracker/common/database/models/`:
- `Product`: Core product tracking (ASIN, prices, BSR, ratings)
- `ProductTrackingData`: Time-series data (partitioned by date)
- `CompetitorData`: Competitor relationships and analysis
- `User`, `Tenant`: Multi-tenant user management

## Development Workflow

### Starting Services
```bash
# Terminal 1: Infrastructure
make docker-up

# Terminal 2: User Service
make dev-user

# Terminal 3: Core Service  
make dev-core

# Terminal 4: Crawler Service
make dev-crawler

# Terminal 5: Celery Workers
make dev-worker
```

### Common Development Tasks
```bash
# Database migrations
make db-migrate
make db-migration  # Create new migration

# Code quality
make format     # Black + Ruff formatting
make lint      # Ruff linting with auto-fix
make type-check # MyPy type checking

# Testing
make test-unit        # Unit tests only
make test-integration # Integration tests
```

## Critical Technical Details

### Apify Integration
- **Primary Actor**: `ZhSGsaq9MHRnWtStl` (94.6% BSR availability)
- **BSR Field**: Data found in `bestsellerRanks` array, not `bestseller_rank`
- **Rate Limits**: Configured for sustainable scraping
- **Data Processing**: ApifyAmazonScraper returns `data.products` list

### BSR (Best Seller Rank) Discovery
- Initially thought missing, found 94.6% availability through research
- Located in `bestsellerRanks` field as array of category rankings
- Headphones category has 100% BSR availability (optimal for demos)

### Celery Tasks
Located in `amazon_tracker/common/task_queue/`:
- `crawler_tasks.py`: Product data scraping
- `monitoring_tasks.py`: Daily updates, anomaly detection
- Beat schedule in `celery_beat_config.py`

### Configuration Management
- **Environment**: Use `.env.local` for development secrets
- **Settings**: Pydantic-based config in `common/config/settings.py`
- **Multi-env**: Separate configs for dev/staging/prod

## Common Issues & Solutions

### Database Issues
```python
# Always use tenant-aware queries
session.query(Product).filter(Product.tenant_id == current_tenant.id)

# Avoid metadata field name (reserved in SQLAlchemy)
# Use extra_metadata instead
```

### Apify Authentication
```bash
# Ensure token is loaded from .env.local
APIFY_API_TOKEN=your_apify_token_here
```

### Import Scripts Location
All demo/utility scripts in `scripts/` directory:
- `import_headphones_demo.py`: Complete 20-product demo
- `comprehensive_bsr_research.py`: BSR data research
- `test_auth_system.py`: Authentication testing

## Testing Strategy

### Test Structure
```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Service integration tests  
└── e2e/           # End-to-end workflow tests
```

### Key Test Areas
- Multi-tenant data isolation
- Authentication flows (JWT + API keys)
- Apify data processing pipeline
- Celery task execution
- API endpoint security

## Production Deployment

```bash
# Build and deploy
make deploy-prod

# Health checks
make deploy-check
curl http://localhost:9080/health
```

### Monitoring Endpoints
- **Swagger Docs**: http://localhost:8001/docs (per service)
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **APISIX Admin**: http://localhost:9180

## Package Management

Using **UV** for fast Python package management:
```bash
# Install dependencies
uv pip install -e ".[dev]"

# Add new dependency
uv add package-name

# Virtual environment
uv venv --python 3.11
source .venv/bin/activate
```

## Key Files to Understand

### Configuration
- `pyproject.toml`: Dependencies, dev tools, quality settings
- `Makefile`: Development workflow automation
- `docker-compose.dev.yml`: Development infrastructure
- `alembic.ini`: Database migration configuration

### Core Application
- `amazon_tracker/common/database/models/`: Data models
- `amazon_tracker/services/*/main.py`: Service entry points
- `amazon_tracker/common/auth/`: Authentication system
- `amazon_tracker/common/crawlers/`: Apify integration

### Documentation
- `README.md`: User-facing project documentation
- `ARCHITECTURE.md`: Detailed technical architecture
- `docs/headphones-demo-specification.md`: Demo product catalog

## Development Philosophy

1. **Multi-tenant First**: Every feature must support tenant isolation
2. **Async by Default**: Use FastAPI async patterns for I/O operations  
3. **Test-Driven**: Maintain >80% test coverage
4. **Type Safety**: Full MyPy type checking enabled
5. **API-First**: OpenAPI/Swagger documentation for all endpoints
6. **Observability**: Comprehensive logging, metrics, and tracing

## Next Phase Priorities

Based on current progress:
1. **Phase 3** (In Progress): Complete Apify crawler service
2. **Phase 4** (Planned): Core business features (competitor analysis)
3. **Phase 5** (Planned): Production monitoring and optimization

## Emergency Contacts & Resources

- **Architecture docs**: See `ARCHITECTURE.md` for system design
- **API testing**: Use Swagger UI at service `/docs` endpoints
- **Database schema**: Check `alembic/versions/` for migrations
- **Task monitoring**: Celery flower UI (if configured)

---

**Note**: This system is designed for scalability from MVP to enterprise. Always consider multi-tenant implications when making changes.
- 所有apify的请求，使用apify client，也就是官方的sdk