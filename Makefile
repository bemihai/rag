# Check if .env file exists
ifneq (,$(wildcard .env))
    include .env
    export
endif

# Default shell
SHELL := /bin/bash

# Default goal
.DEFAULT_GOAL := help

# Default values (can be overridden in .env)
CHROMA_NAME ?= chroma-db
CHROMA_PORT ?= 8000
CHROMA_VOLUME ?= ./chroma-data

.PHONY: help
help:
	@echo "ChromaDB Management Commands:"
	@echo "  db-up           - Start the ChromaDB Docker container"
	@echo "  db-down         - Stop the ChromaDB Docker container"
	@echo "  db-restart      - Restart the ChromaDB Docker container"
	@echo "  db-status       - Check ChromaDB container status"
	@echo "  db-logs         - Show ChromaDB container logs"
	@echo "  db-shell        - Access ChromaDB container shell"
	@echo "  db-backup       - Create backup of ChromaDB data"
	@echo "  db-restore      - Restore ChromaDB data from backup"
	@echo "  db-clean        - Remove ChromaDB data (destructive)"
	@echo "  db-pull         - Pull latest ChromaDB image"
	@echo "  db-load         - Load external data into ChromaDB"
	@echo ""
	@echo "Wine Cellar Database Commands:"
	@echo "  cellar-init     - Initialize wine cellar database"
	@echo "  cellar-reset    - Drop and recreate wine cellar database"
	@echo "  cellar-backup   - Backup wine cellar database"
	@echo "  cellar-restore  - Restore wine cellar database from backup"
	@echo "  cellar-info     - Show wine cellar database info"

.PHONY: check-env
check-env:
	@if [ -z "$(CHROMA_NAME)" ]; then \
		echo "Error: CHROMA_NAME not set"; exit 1; \
	fi
	@if [ -z "$(CHROMA_PORT)" ]; then \
		echo "Error: CHROMA_PORT not set"; exit 1; \
	fi
	@if [ -z "$(CHROMA_VOLUME)" ]; then \
		echo "Error: CHROMA_VOLUME not set"; exit 1; \
	fi

.PHONY: db-pull
db-pull:
	@echo "Pulling latest ChromaDB image..."
	@docker pull chromadb/chroma:latest

.PHONY: db-up
db-up: check-env db-down
	@echo "Starting ChromaDB container..."
	@mkdir -p $(CHROMA_VOLUME)
	@docker run --name $(CHROMA_NAME) \
		-v $(CHROMA_VOLUME):/chroma/chroma \
		-d \
		-p $(CHROMA_PORT):8000 \
		--restart unless-stopped \
		chromadb/chroma:latest
	@echo "ChromaDB started on port $(CHROMA_PORT)"

.PHONY: db-down
db-down:
	@echo "Stopping ChromaDB container..."
	@docker stop $(CHROMA_NAME) 2>/dev/null || true
	@docker rm $(CHROMA_NAME) 2>/dev/null || true
	@echo "ChromaDB stopped"

.PHONY: db-restart
db-restart: db-down db-up

.PHONY: db-status
db-status: check-env
	@echo "ChromaDB Container Status:"
	@docker ps -a --filter "name=$(CHROMA_NAME)" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "Container not found"

.PHONY: db-logs
db-logs: check-env
	@echo "ChromaDB Logs:"
	@docker logs $(CHROMA_NAME) --tail 50 || echo "Container not running"

.PHONY: db-logs-follow
db-logs-follow: check-env
	@echo "Following ChromaDB Logs (Ctrl+C to exit):"
	@docker logs -f $(CHROMA_NAME) || echo "Container not running"

.PHONY: db-shell
db-shell: check-env
	@echo "Accessing ChromaDB container shell..."
	@docker exec -it $(CHROMA_NAME) /bin/bash || echo "Container not running"

.PHONY: db-backup
db-backup: check-env
	@echo "Creating backup of ChromaDB data..."
	@if [ ! -d "$(CHROMA_VOLUME)" ]; then \
		echo "No data directory found at $(CHROMA_VOLUME)"; exit 1; \
	fi
	@mkdir -p backups
	@tar -czf backups/chroma-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz -C $(CHROMA_VOLUME) .
	@echo "Backup created in backups/ directory"

.PHONY: db-restore
db-restore: check-env
	@echo "Available backups:"
	@ls -la backups/ 2>/dev/null || (echo "No backups directory found" && exit 1)
	@echo "Warning: This will overwrite existing data!"
	@echo "Usage: make db-restore BACKUP_FILE=backups/filename.tar.gz"
	@if [ -n "$(BACKUP_FILE)" ]; then \
		echo "Restoring from $(BACKUP_FILE)..."; \
		$(MAKE) db-down; \
		rm -rf $(CHROMA_VOLUME)/*; \
		tar -xzf $(BACKUP_FILE) -C $(CHROMA_VOLUME); \
		$(MAKE) db-up; \
	fi

.PHONY: db-clean
db-clean: check-env
	@echo "WARNING: This will permanently delete all ChromaDB data!"
	@read -p "Are you sure? Type 'yes' to continue: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		$(MAKE) db-down; \
		rm -rf $(CHROMA_VOLUME)/*; \
		echo "ChromaDB data cleaned"; \
	else \
		echo "Operation cancelled"; \
	fi

.PHONY: db-stats
db-stats: check-env
	@echo "ChromaDB Statistics:"
	@if docker ps --filter "name=$(CHROMA_NAME)" --format "{{.Names}}" | grep -q $(CHROMA_NAME); then \
		echo "Status: Running"; \
		echo "Port: $(CHROMA_PORT)"; \
		echo "Data Volume: $(CHROMA_VOLUME)"; \
		echo "Container Size:"; \
		docker exec $(CHROMA_NAME) du -sh /chroma/chroma 2>/dev/null || echo "N/A"; \
		echo "Memory Usage:"; \
		docker stats $(CHROMA_NAME) --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "N/A"; \
	else \
		echo "Status: Not Running"; \
	fi

.PHONY: install-deps
install-deps:
	@echo "Installing Python dependencies for ChromaDB..."
	@pip install chromadb langchain-chroma

.PHONY: test-connection
test-connection: check-env
	@echo "Testing ChromaDB connection..."
	@python3 -c "import chromadb; client = chromadb.HttpClient(host='localhost', port=$(CHROMA_PORT)); print('✓ Connection successful'); print('Version:', client.get_version())" 2>/dev/null || echo "✗ Connection failed"

# Wine Cellar Database Commands
CELLAR_DB_PATH ?= data/wine_cellar.db
CELLAR_BACKUP_DIR ?= backups/wine_cellar

.PHONY: cellar-init
cellar-init:
	@echo "Initializing wine cellar database..."
	@python3 -c "from src.database import initialize_database; success = initialize_database('$(CELLAR_DB_PATH)'); exit(0 if success else 1)"
	@echo "✅ Wine cellar database initialized at $(CELLAR_DB_PATH)"

.PHONY: cellar-reset
cellar-reset:
	@echo "WARNING: This will drop all wine cellar tables and recreate them!"
	@read -p "Are you sure? Type 'yes' to continue: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo "Dropping all tables..."; \
		python3 -c "from src.database.db import drop_all_tables; drop_all_tables('$(CELLAR_DB_PATH)')"; \
		echo "Reinitializing database..."; \
		$(MAKE) cellar-init; \
		echo "✅ Wine cellar database reset complete"; \
	else \
		echo "Operation cancelled"; \
	fi

.PHONY: cellar-backup
cellar-backup:
	@echo "Creating backup of wine cellar database..."
	@if [ ! -f "$(CELLAR_DB_PATH)" ]; then \
		echo "Error: Database not found at $(CELLAR_DB_PATH)"; exit 1; \
	fi
	@mkdir -p $(CELLAR_BACKUP_DIR)
	@cp $(CELLAR_DB_PATH) $(CELLAR_BACKUP_DIR)/wine_cellar_$(shell date +%Y%m%d_%H%M%S).db
	@echo "✅ Backup created in $(CELLAR_BACKUP_DIR)/"
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
		mkdir -p data; \
		cp $(BACKUP_FILE) $(CELLAR_DB_PATH); \
		echo "✅ Database restored from backup"; \
	fi

.PHONY: cellar-info
cellar-info:
	@echo "Wine Cellar Database Information:"
	@echo "=================================="
	@if [ -f "$(CELLAR_DB_PATH)" ]; then \
		echo "Status: Initialized"; \
		echo "Location: $(CELLAR_DB_PATH)"; \
		echo "Size: $$(du -h $(CELLAR_DB_PATH) | cut -f1)"; \
		echo ""; \
		echo "Schema Version:"; \
		sqlite3 $(CELLAR_DB_PATH) "SELECT version, applied_at, description FROM schema_version;" 2>/dev/null || echo "N/A"; \
		echo ""; \
		echo "Tables:"; \
		sqlite3 $(CELLAR_DB_PATH) "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;" 2>/dev/null || echo "N/A"; \
		echo ""; \
		echo "Statistics:"; \
		sqlite3 $(CELLAR_DB_PATH) "SELECT 'Producers: ' || COUNT(*) FROM producers UNION ALL SELECT 'Regions: ' || COUNT(*) FROM regions UNION ALL SELECT 'Wines: ' || COUNT(*) FROM wines UNION ALL SELECT 'Bottles: ' || COUNT(*) FROM bottles;" 2>/dev/null || echo "N/A"; \
	else \
		echo "Status: Not initialized"; \
		echo "Run 'make cellar-init' to create the database"; \
	fi

.PHONY: db-load
db-load: db-up install-deps
	@echo "Loading external data into ChromaDB..."
	@PYTHONPATH=$(shell pwd) python3 src/data/load_data.py