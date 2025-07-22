# =============================================================================
# Makefile for DSL to PNG MCP Server
# =============================================================================
# Provides convenient commands for development, testing, and deployment
# =============================================================================

.PHONY: help dev prod build test clean setup health logs stop restart

# Default target
.DEFAULT_GOAL := help

# Variables
PROJECT_NAME := dsl-png-mcp
DEV_COMPOSE := docker-compose.yaml
PROD_COMPOSE := docker compose.prod.yaml
VERSION ?= latest

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)DSL to PNG MCP Server - Available Commands$(NC)"
	@echo "==========================================="
	@echo
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make setup-dev     # Setup development environment"
	@echo "  make dev           # Start development environment"
	@echo "  make health        # Run health checks"
	@echo "  make deploy-prod   # Deploy to production"

# =============================================================================
# Development Commands
# =============================================================================

setup-dev: ## Setup development environment
	@echo "$(BLUE)Setting up development environment...$(NC)"
	@chmod +x scripts/setup-dev.sh
	@./scripts/setup-dev.sh

dev: ## Start development environment
	@echo "$(BLUE)Starting development environment...$(NC)"
	@docker compose -f $(DEV_COMPOSE) up -d
	@echo "$(GREEN)Development environment started!$(NC)"
	@echo "Access the application at: http://localhost"

dev-build: ## Build and start development environment
	@echo "$(BLUE)Building and starting development environment...$(NC)"
	@docker compose -f $(DEV_COMPOSE) up -d --build
	@echo "$(GREEN)Development environment started with fresh build!$(NC)"

dev-logs: ## Show development logs
	@docker compose -f $(DEV_COMPOSE) logs -f

dev-stop: ## Stop development environment
	@echo "$(YELLOW)Stopping development environment...$(NC)"
	@docker compose -f $(DEV_COMPOSE) down
	@echo "$(GREEN)Development environment stopped!$(NC)"

dev-restart: ## Restart development environment
	@make dev-stop
	@make dev

dev-clean: ## Clean development environment (remove volumes)
	@echo "$(RED)Cleaning development environment (this will remove data)...$(NC)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	@docker compose -f $(DEV_COMPOSE) down -v
	@docker system prune -f
	@echo "$(GREEN)Development environment cleaned!$(NC)"

# =============================================================================
# Production Commands
# =============================================================================

deploy-prod: ## Deploy to production
	@echo "$(BLUE)Deploying to production...$(NC)"
	@chmod +x scripts/deploy-prod.sh
	@./scripts/deploy-prod.sh

deploy-prod-force: ## Force deploy to production (skip confirmations)
	@echo "$(BLUE)Force deploying to production...$(NC)"
	@chmod +x scripts/deploy-prod.sh
	@./scripts/deploy-prod.sh --force

prod: ## Start production environment
	@echo "$(BLUE)Starting production environment...$(NC)"
	@docker compose -f $(PROD_COMPOSE) up -d
	@echo "$(GREEN)Production environment started!$(NC)"

prod-build: ## Build and start production environment
	@echo "$(BLUE)Building and starting production environment...$(NC)"
	@docker compose -f $(PROD_COMPOSE) up -d --build
	@echo "$(GREEN)Production environment started with fresh build!$(NC)"

prod-logs: ## Show production logs
	@docker compose -f $(PROD_COMPOSE) logs -f

prod-stop: ## Stop production environment
	@echo "$(YELLOW)Stopping production environment...$(NC)"
	@docker compose -f $(PROD_COMPOSE) down
	@echo "$(GREEN)Production environment stopped!$(NC)"

prod-restart: ## Restart production environment
	@make prod-stop
	@make prod

# =============================================================================
# Build Commands
# =============================================================================

build: ## Build all Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	@docker compose -f $(DEV_COMPOSE) build --parallel
	@echo "$(GREEN)Build completed!$(NC)"

build-prod: ## Build production Docker images
	@echo "$(BLUE)Building production Docker images...$(NC)"
	@docker compose -f $(PROD_COMPOSE) build --parallel
	@echo "$(GREEN)Production build completed!$(NC)"

build-no-cache: ## Build all Docker images without cache
	@echo "$(BLUE)Building Docker images without cache...$(NC)"
	@docker compose -f $(DEV_COMPOSE) build --no-cache --parallel
	@echo "$(GREEN)Build completed!$(NC)"

pull: ## Pull latest base images
	@echo "$(BLUE)Pulling latest base images...$(NC)"
	@docker compose -f $(DEV_COMPOSE) pull
	@echo "$(GREEN)Images pulled!$(NC)"

# =============================================================================
# Health and Monitoring Commands
# =============================================================================

health: ## Run health checks
	@echo "$(BLUE)Running health checks...$(NC)"
	@chmod +x scripts/health-check.sh
	@./scripts/health-check.sh

health-prod: ## Run production health checks
	@echo "$(BLUE)Running production health checks...$(NC)"
	@chmod +x scripts/health-check.sh
	@./scripts/health-check.sh --production

status: ## Show service status
	@echo "$(BLUE)Service Status:$(NC)"
	@docker compose -f $(DEV_COMPOSE) ps

status-prod: ## Show production service status
	@echo "$(BLUE)Production Service Status:$(NC)"
	@docker compose -f $(PROD_COMPOSE) ps

logs: ## Show all service logs
	@docker compose -f $(DEV_COMPOSE) logs --tail=100

logs-follow: ## Follow all service logs
	@docker compose -f $(DEV_COMPOSE) logs -f

logs-service: ## Show logs for specific service (usage: make logs-service SERVICE=nginx-proxy)
	@docker compose -f $(DEV_COMPOSE) logs $(SERVICE)

# =============================================================================
# Testing Commands
# =============================================================================

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	@docker compose -f $(DEV_COMPOSE) exec fastapi-server-1 python -m pytest tests/
	@echo "$(GREEN)Tests completed!$(NC)"

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	@docker compose -f $(DEV_COMPOSE) exec fastapi-server-1 python -m pytest tests/unit/
	@echo "$(GREEN)Unit tests completed!$(NC)"

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	@docker compose -f $(DEV_COMPOSE) exec fastapi-server-1 python -m pytest tests/integration/
	@echo "$(GREEN)Integration tests completed!$(NC)"

test-api: ## Test API endpoints
	@echo "$(BLUE)Testing API endpoints...$(NC)"
	@curl -f http://localhost/health || (echo "$(RED)Health check failed$(NC)" && exit 1)
	@curl -f http://localhost/docs || (echo "$(RED)Docs endpoint failed$(NC)" && exit 1)
	@echo "$(GREEN)API tests passed!$(NC)"

# =============================================================================
# Database and Storage Commands
# =============================================================================

redis-cli: ## Access Redis CLI
	@docker compose -f $(DEV_COMPOSE) exec redis redis-cli

redis-info: ## Show Redis information
	@docker compose -f $(DEV_COMPOSE) exec redis redis-cli info

backup: ## Create backup
	@echo "$(BLUE)Creating backup...$(NC)"
	@mkdir -p backups
	@docker compose -f $(DEV_COMPOSE) exec redis redis-cli BGSAVE
	@sleep 5
	@docker cp $$(docker compose -f $(DEV_COMPOSE) ps -q redis):/data/redis/dump.rdb backups/redis-$$(date +%Y%m%d_%H%M%S).rdb
	@echo "$(GREEN)Backup created!$(NC)"

# =============================================================================
# Utility Commands
# =============================================================================

shell-nginx: ## Access nginx container shell
	@docker compose -f $(DEV_COMPOSE) exec nginx-proxy /bin/bash

shell-fastapi: ## Access FastAPI container shell
	@docker compose -f $(DEV_COMPOSE) exec fastapi-server-1 /bin/bash

shell-redis: ## Access Redis container shell
	@docker compose -f $(DEV_COMPOSE) exec redis /bin/bash

shell-celery: ## Access Celery worker shell
	@docker compose -f $(DEV_COMPOSE) exec celery-worker-1 /bin/bash

clean: ## Clean up Docker resources
	@echo "$(YELLOW)Cleaning up Docker resources...$(NC)"
	@docker system prune -f
	@docker volume prune -f
	@echo "$(GREEN)Cleanup completed!$(NC)"

clean-all: ## Clean up all Docker resources (WARNING: removes everything)
	@echo "$(RED)This will remove ALL Docker resources including images$(NC)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	@docker system prune -a -f --volumes
	@echo "$(GREEN)All Docker resources cleaned!$(NC)"

reset: ## Reset development environment completely
	@echo "$(RED)This will completely reset the development environment$(NC)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	@make dev-clean
	@make setup-dev
	@make dev
	@echo "$(GREEN)Development environment reset completed!$(NC)"

# =============================================================================
# Information Commands
# =============================================================================

info: ## Show project information
	@echo "$(BLUE)DSL to PNG MCP Server Information$(NC)"
	@echo "================================="
	@echo "Project: $(PROJECT_NAME)"
	@echo "Version: $(VERSION)"
	@echo "Dev Compose: $(DEV_COMPOSE)"
	@echo "Prod Compose: $(PROD_COMPOSE)"
	@echo
	@echo "$(BLUE)Services:$(NC)"
	@docker compose -f $(DEV_COMPOSE) config --services | sed 's/^/  - /'
	@echo
	@echo "$(BLUE)Networks:$(NC)"
	@docker compose -f $(DEV_COMPOSE) config | grep -A 10 "networks:" | grep "^  [a-z]" | cut -d: -f1 | sed 's/^/  - /'

endpoints: ## Show available endpoints
	@echo "$(BLUE)Available Endpoints (Development):$(NC)"
	@echo "=================================="
	@echo "• Main Application:     http://localhost"
	@echo "• API Documentation:    http://localhost/docs"
	@echo "• ReDoc Documentation:  http://localhost/redoc"
	@echo "• Health Check:         http://localhost/health"
	@echo "• Nginx Status:         http://localhost/nginx-status"
	@echo "• Metrics:              http://localhost/metrics"
	@echo "• Static PNG Files:     http://localhost/static/png/"
	@echo

config: ## Show current configuration
	@echo "$(BLUE)Current Configuration:$(NC)"
	@docker compose -f $(DEV_COMPOSE) config

validate: ## Validate Docker Compose files
	@echo "$(BLUE)Validating Docker Compose files...$(NC)"
	@docker compose -f $(DEV_COMPOSE) config -q && echo "$(GREEN)Development compose file is valid$(NC)"
	@docker compose -f $(PROD_COMPOSE) config -q && echo "$(GREEN)Production compose file is valid$(NC)"

# =============================================================================
# Security Commands
# =============================================================================

security-scan: ## Run security scan on images
	@echo "$(BLUE)Running security scan...$(NC)"
	@for image in $$(docker compose -f $(DEV_COMPOSE) config | grep 'image:' | awk '{print $$2}' | sort -u); do \
		echo "Scanning $$image..."; \
		docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
			aquasec/trivy:latest image $$image; \
	done

secrets-check: ## Check for secrets in code
	@echo "$(BLUE)Checking for secrets in code...$(NC)"
	@grep -r -i "password\|secret\|key\|token" --include="*.py" --include="*.js" --include="*.yaml" --include="*.yml" . || echo "$(GREEN)No obvious secrets found$(NC)"

# =============================================================================
# Documentation Commands
# =============================================================================

docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	@mkdir -p docs/generated
	@docker compose -f $(DEV_COMPOSE) exec fastapi-server-1 python -c "from src.api.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > docs/generated/openapi.json
	@echo "$(GREEN)Documentation generated!$(NC)"

docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Serving documentation at http://localhost:8080$(NC)"
	@python3 -m http.server 8080 --directory docs/

# =============================================================================
# Version Management
# =============================================================================

version: ## Show current version
	@echo "Current version: $(VERSION)"

tag: ## Tag current version (usage: make tag VERSION=1.0.0)
	@git tag -a v$(VERSION) -m "Release version $(VERSION)"
	@echo "$(GREEN)Tagged version $(VERSION)$(NC)"

release: ## Create release (usage: make release VERSION=1.0.0)
	@echo "$(BLUE)Creating release $(VERSION)...$(NC)"
	@git tag -a v$(VERSION) -m "Release version $(VERSION)"
	@docker compose -f $(PROD_COMPOSE) build
	@docker compose -f $(PROD_COMPOSE) push
	@echo "$(GREEN)Release $(VERSION) created!$(NC)"