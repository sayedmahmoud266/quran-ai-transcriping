.PHONY: start setup test clean help install dev build-frontend install-frontend run dev-frontend dev-backend

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Quran AI Transcription API - Makefile Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

start: build-frontend ## Start the API server with UI (recommended)
	@echo "$(GREEN)Starting Quran AI Transcription API...$(NC)"
	@if [ ! -d "venv" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(NC)"; \
		exit 1; \
	fi
	@. venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run: start ## Alias for start

setup: ## Install dependencies and setup virtual environment
	@echo "$(GREEN)Setting up virtual environment...$(NC)"
	@if [ ! -d "venv" ]; then \
		python3 -m venv venv; \
		echo "$(GREEN)Virtual environment created.$(NC)"; \
	else \
		echo "$(YELLOW)Virtual environment already exists.$(NC)"; \
	fi
	@echo "$(GREEN)Installing dependencies...$(NC)"
	@. venv/bin/activate && pip install --upgrade pip
	@. venv/bin/activate && pip install -r requirements.txt
	@echo "$(GREEN)Setup complete! Run 'make start' to start the server.$(NC)"

install: setup ## Alias for setup

install-frontend: ## Install frontend dependencies
	@echo "$(GREEN)Installing frontend dependencies...$(NC)"
	@if [ ! -d "frontend/node_modules" ]; then \
		cd frontend && npm install; \
		echo "$(GREEN)Frontend dependencies installed.$(NC)"; \
	else \
		echo "$(YELLOW)Frontend dependencies already installed.$(NC)"; \
	fi

build-frontend: ## Build the frontend UI
	@echo "$(GREEN)Building frontend...$(NC)"
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "$(YELLOW)Frontend dependencies not found. Installing...$(NC)"; \
		cd frontend && npm install; \
	fi
	@if [ ! -d "app/static" ] || [ "frontend/src" -nt "app/static" ]; then \
		cd frontend && npm run build; \
		echo "$(GREEN)Frontend built successfully!$(NC)"; \
	else \
		echo "$(YELLOW)Frontend already built and up to date.$(NC)"; \
	fi

dev: build-frontend ## Start server in development mode with auto-reload
	@echo "$(GREEN)Starting in development mode...$(NC)"
	@. venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

dev-backend: ## Start backend only (without building frontend)
	@echo "$(GREEN)Starting backend in development mode...$(NC)"
	@if [ ! -d "venv" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(NC)"; \
		exit 1; \
	fi
	@. venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

dev-frontend: install-frontend ## Start frontend dev server with hot-reload
	@echo "$(GREEN)Starting frontend development server...$(NC)"
	@echo "$(YELLOW)Make sure backend is running on port 8000$(NC)"
	@echo "$(YELLOW)Run 'make dev-backend' in another terminal$(NC)"
	@echo ""
	@cd frontend && npm run dev

test: ## Run tests (placeholder - add tests in future)
	@echo "$(YELLOW)Running tests...$(NC)"
	@if [ ! -d "venv" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(NC)"; \
		exit 1; \
	fi
	@. venv/bin/activate && python -m pytest tests/ -v || echo "$(YELLOW)No tests found. Add tests in tests/ directory.$(NC)"

clean: ## Clean up temporary files and cache
	@echo "$(GREEN)Cleaning up...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	@rm -f quran_simple.txt 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete!$(NC)"

clean-frontend: ## Clean frontend build artifacts
	@echo "$(GREEN)Cleaning frontend build...$(NC)"
	@rm -rf app/static
	@echo "$(GREEN)Frontend build cleaned!$(NC)"

clean-all: clean clean-frontend ## Clean everything including virtual environment and frontend
	@echo "$(YELLOW)Removing virtual environment...$(NC)"
	@rm -rf venv
	@echo "$(YELLOW)Removing frontend dependencies...$(NC)"
	@rm -rf frontend/node_modules
	@echo "$(GREEN)Full cleanup complete!$(NC)"

clean-debug: ## Clean debug files
	@echo "$(GREEN)Cleaning debug files...$(NC)"
	@rm -rf .debug
	@mkdir .debug
	@echo "$(GREEN)Debug files cleaned!$(NC)"

clean-logs: ## Clean logs
	@echo "$(GREEN)Cleaning logs...$(NC)"
	@rm -rf logs
	@mkdir logs
	@echo "$(GREEN)Logs cleaned!$(NC)"

clean-data:
	@echo "$(GREEN)Cleaning data...$(NC)"
	@rm -rf data
	@mkdir data
	@echo "$(GREEN)Data cleaned!$(NC)"

refresh-state: clean clean-debug clean-logs clean-data ## Refresh state
	@echo "$(GREEN)State refreshed!$(NC)"

freeze: ## Generate requirements.txt from current environment
	@echo "$(GREEN)Generating requirements.txt...$(NC)"
	@. venv/bin/activate && pip freeze > requirements.txt
	@echo "$(GREEN)requirements.txt updated!$(NC)"

check: ## Check if all dependencies are installed
	@echo "$(GREEN)Checking dependencies...$(NC)"
	@. venv/bin/activate && pip check
	@echo "$(GREEN)All dependencies are satisfied!$(NC)"

logs: ## Show recent server logs (if running in background)
	@echo "$(YELLOW)Recent logs:$(NC)"
	@tail -n 50 server.log 2>/dev/null || echo "$(RED)No log file found. Server might not be running.$(NC)"

info: ## Show project information
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║         Quran AI Transcription API - v2.0.0               ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)Repository:$(NC) https://github.com/sayedmahmoud266/quran-ai-transcriping"
	@echo "$(GREEN)License:$(NC)    MIT"
	@echo "$(GREEN)Python:$(NC)     3.8+"
	@echo "$(GREEN)Model:$(NC)      tarteel-ai/whisper-base-ar-quran"
	@echo ""
	@echo "$(YELLOW)Quick Start:$(NC)"
	@echo "  1. make setup"
	@echo "  2. make start"
	@echo "  3. Visit http://localhost:8000"
	@echo ""