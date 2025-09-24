# Check if .env file exists
ifneq (,$(wildcard .env))
    include .env
    export
endif

# Default shell
SHELL := /bin/bash

# Default goal
.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Available commands:"
	@echo "  db-up        - Start the ChromaDB Docker container"
	@echo "  db-down      - Stop the ChromaDB Docker container"
	@echo "  db-restart      - Restart the ChromaDB Docker container"


.PHONY: db-up
db-up: db-down
	@docker run --name ${CHROMA_NAME} -v ${CHROMA_VOLUME}:/data -d -p ${CHROMA_PORT}:8000 chromadb/chroma:latest

.PHONY: db-down
db-down:
	@docker stop ${CHROMA_NAME} || true
	@docker rm ${CHROMA_NAME} || true

.PHONY: db-restart
db-restart: db-down db-up