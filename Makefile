# Check if .env file exists
ifneq (,$(wildcard .env))
    include .env
    export
endif

# Default shell
SHELL := /bin/bash

# Default goal
.DEFAULT_GOAL := help

# Configuration variables
CELLAR_DB_PATH ?= cellar-data/wine_cellar.db
CELLAR_BACKUP_DIR ?= backups/wine_cellar

.PHONY: help
help:
	@echo "Pour Decisions Wine RAG - Available Commands"
	@echo ""
	@echo "Docker Compose Commands:"
	@echo "  up              - Start all services (app + ChromaDB)"
	@echo "  down            - Stop all services"
	@echo "  restart         - Restart all services"
	@echo "  logs            - View all service logs"
	@echo "  logs-app        - View app logs only"
	@echo "  logs-chroma     - View ChromaDB logs only"
	@echo "  status          - Check service status"
	@echo "  build           - Rebuild Docker images"
	@echo "  rebuild         - Stop, rebuild, and start services"
	@echo "  shell-app       - Access app container shell"
	@echo "  shell-chroma    - Access ChromaDB container shell"
	@echo ""
	@echo "Development Commands:"
	@echo "  install         - Install Python dependencies with uv"
	@echo "  populate-chroma - Populate ChromaDB with wine knowledge"
	@echo "  chroma-up       - Start only ChromaDB (for local development)"
	@echo "  chroma-down     - Stop ChromaDB container"
	@echo "  chroma-backup   - Backup ChromaDB data directory"
	@echo "  chroma-restore  - Restore ChromaDB from backup (BACKUP_FILE=path/to/backup.tar.gz)"
	@echo ""
	@echo "Wine Cellar Database Commands:"
	@echo "  cellar-init     - Initialize wine cellar database"
	@echo "  cellar-info     - Show wine cellar database info"
	@echo "  cellar-backup   - Backup wine cellar database"
	@echo "  cellar-restore  - Restore from backup (BACKUP_FILE=path/to/backup.db)"
	@echo ""
	@echo "Data Import Commands:"
	@echo "  import-vivino   - Import Vivino CSV data"
	@echo "  import-ct       - Import from CellarTracker API"
	@echo "  sync            - Sync all sources (with auto-backup)"

# ============================================================================
# Docker Compose Commands
# ============================================================================

.PHONY: up
up:
	@echo "Starting all services with Docker Compose..."
	@if [ ! -f .env ]; then \
		echo "WARNING: .env file not found. Create one with GOOGLE_API_KEY"; \
		exit 1; \
	fi
	@docker compose up -d
	@echo "Services started!"
	@echo "Access app at: http://localhost:8501"

.PHONY: down
down:
	@echo "Stopping all services..."
	@docker compose down
	@echo "Services stopped"

.PHONY: restart
restart:
	@echo "Restarting all services..."
	@docker compose restart
	@echo "Services restarted"

.PHONY: logs
logs:
	@echo "Viewing logs (Ctrl+C to exit)..."
	@docker compose logs -f --tail=100

.PHONY: logs-app
logs-app:
	@echo "Viewing app logs (Ctrl+C to exit)..."
	@docker compose logs -f --tail=100 app

.PHONY: logs-chroma
logs-chroma:
	@echo "Viewing ChromaDB logs (Ctrl+C to exit)..."
	@docker compose logs -f --tail=100 chromadb

.PHONY: status
status:
	@echo "Service Status:"
	@docker compose ps

.PHONY: build
build:
	@echo "Building Docker images..."
	@docker compose build --no-cache
	@echo "Build complete"

.PHONY: rebuild
rebuild: down build up

.PHONY: shell-app
shell-app:
	@echo "Accessing app container shell..."
	@docker compose exec app /bin/bash

.PHONY: shell-chroma
shell-chroma:
	@echo "Accessing ChromaDB container shell..."
	@docker compose exec chromadb /bin/bash

# ============================================================================
# Development Commands
# ============================================================================

.PHONY: install
install:
	@echo "Installing Python dependencies with uv..."
	@uv sync
	@echo "Dependencies installed"

.PHONY: populate-chroma
populate-chroma:
	@echo "Populating ChromaDB with wine knowledge..."
	@PYTHONPATH=$(shell pwd) python3 src/rag/load_data.py
	@echo "ChromaDB populated"

.PHONY: chroma-up
chroma-up:
	@echo "Starting ChromaDB container for local development..."
	@docker compose up chromadb -d
	@echo "ChromaDB started on http://localhost:8000"
	@echo "Run your app locally with: streamlit run src/ui/app.py"

.PHONY: chroma-down
chroma-down:
	@echo "Stopping ChromaDB container..."
	@docker compose stop chromadb
	@echo "ChromaDB stopped"

.PHONY: chroma-backup
chroma-backup:
	@echo "Creating backup of ChromaDB data..."
	@if [ ! -d "chroma-data" ]; then \
		echo "Error: chroma-data directory not found"; exit 1; \
	fi
	@mkdir -p backups/chroma
	@tar -czf backups/chroma/chroma-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz -C chroma-data .
	@echo "Backup created in backups/chroma/"
	@ls -lh backups/chroma/ | tail -5

.PHONY: chroma-restore
chroma-restore:
	@echo "Available ChromaDB backups:"
	@ls -lht backups/chroma/ 2>/dev/null || (echo "No backups found in backups/chroma/" && exit 1)
	@echo ""
	@echo "Usage: make chroma-restore BACKUP_FILE=backups/chroma/chroma-backup-YYYYMMDD-HHMMSS.tar.gz"
	@if [ -n "$(BACKUP_FILE)" ]; then \
		if [ ! -f "$(BACKUP_FILE)" ]; then \
			echo "Error: Backup file not found: $(BACKUP_FILE)"; exit 1; \
		fi; \
		echo "WARNING: This will overwrite existing ChromaDB data!"; \
		read -p "Are you sure? Type 'yes' to continue: " confirm; \
		if [ "$$confirm" = "yes" ]; then \
			echo "Stopping ChromaDB container..."; \
			docker compose stop chromadb 2>/dev/null || true; \
			echo "Clearing existing data..."; \
			rm -rf chroma-data/*; \
			echo "Restoring from $(BACKUP_FILE)..."; \
			tar -xzf $(BACKUP_FILE) -C chroma-data; \
			echo "ChromaDB data restored from backup"; \
			echo "Run 'make chroma-up' to start ChromaDB with restored data"; \
		else \
			echo "Restore cancelled"; \
		fi; \
	fi

# ============================================================================
# Wine Cellar Database Commands
# ============================================================================

.PHONY: cellar-init
cellar-init:
	@echo "Initializing wine cellar database..."
	@python3 -c "from src.database import initialize_database; success = initialize_database('$(CELLAR_DB_PATH)'); exit(0 if success else 1)"
	@echo "Wine cellar database initialized at $(CELLAR_DB_PATH)"

.PHONY: cellar-info
cellar-info:
	@echo "Wine Cellar Database Information:"
	@echo "=================================="
	@if [ -f "$(CELLAR_DB_PATH)" ]; then \
		echo "Status: Initialized"; \
		echo "Location: $(CELLAR_DB_PATH)"; \
		echo "Size: $$(du -h $(CELLAR_DB_PATH) | cut -f1)"; \
		echo ""; \
		echo "Statistics:"; \
		sqlite3 $(CELLAR_DB_PATH) "SELECT 'Producers: ' || COUNT(*) FROM producers UNION ALL SELECT 'Regions: ' || COUNT(*) FROM regions UNION ALL SELECT 'Wines: ' || COUNT(*) FROM wines UNION ALL SELECT 'Bottles: ' || COUNT(*) FROM bottles;" 2>/dev/null || echo "N/A"; \
	else \
		echo "Status: Not initialized"; \
		echo "Run 'make cellar-init' to create the database"; \
	fi

.PHONY: cellar-backup
cellar-backup:
	@echo "Creating backup of wine cellar database..."
	@if [ ! -f "$(CELLAR_DB_PATH)" ]; then \
		echo "Error: Database not found at $(CELLAR_DB_PATH)"; exit 1; \
	fi
	@mkdir -p $(CELLAR_BACKUP_DIR)
	@cp $(CELLAR_DB_PATH) $(CELLAR_BACKUP_DIR)/wine_cellar_$(shell date +%Y%m%d_%H%M%S).db
	@echo "Backup created in $(CELLAR_BACKUP_DIR)/"
	@ls -lh $(CELLAR_BACKUP_DIR)/ | tail -5

.PHONY: cellar-restore
cellar-restore:
	@echo "Available backups:"
	@ls -lht $(CELLAR_BACKUP_DIR)/ 2>/dev/null || (echo "No backups directory found" && exit 1)
	@echo ""
	@echo "Usage: make cellar-restore BACKUP_FILE=$(CELLAR_BACKUP_DIR)/wine_cellar_YYYYMMDD_HHMMSS.db"
	@if [ -n "$(BACKUP_FILE)" ]; then \
		if [ ! -f "$(BACKUP_FILE)" ]; then \
			echo "Error: Backup file not found: $(BACKUP_FILE)"; exit 1; \
		fi; \
		echo "Restoring from $(BACKUP_FILE)..."; \
		mkdir -p cellar-data; \
		cp $(BACKUP_FILE) $(CELLAR_DB_PATH); \
		echo "Database restored from backup"; \
	fi

# ============================================================================
# Data Import Commands
# ============================================================================

.PHONY: import-vivino
import-vivino:
	@echo "Importing Vivino CSV data..."
	@if [ ! -f "$(CELLAR_DB_PATH)" ]; then \
		echo "Error: Database not initialized. Run 'make cellar-init' first."; exit 1; \
	fi
	@PYTHONPATH=$(shell pwd) python3 src/etl/import_vivino.py
	@echo "Import completed!"
	@$(MAKE) cellar-info

.PHONY: import-ct
import-ct:
	@echo "Importing from CellarTracker API..."
	@if [ ! -f "$(CELLAR_DB_PATH)" ]; then \
		echo "Error: Database not initialized. Run 'make cellar-init' first."; exit 1; \
	fi
	@if [ -z "$(CELLAR_TRACKER_USERNAME)" ] || [ -z "$(CELLAR_TRACKER_PASSWORD)" ]; then \
		echo "Error: CellarTracker credentials not set!"; \
		echo "Set CELLAR_TRACKER_USERNAME and CELLAR_TRACKER_PASSWORD in .env file"; exit 1; \
	fi
	@PYTHONPATH=$(shell pwd) python3 -m src.etl.import_cellartracker
	@echo "Import completed!"
	@$(MAKE) cellar-info

.PHONY: sync
sync:
	@echo "Syncing all wine data sources..."
	@$(MAKE) cellar-backup
	@echo ""
	@echo "Importing from CellarTracker..."
	@$(MAKE) import-ct
	@echo ""
	@echo "All sources synced!"
