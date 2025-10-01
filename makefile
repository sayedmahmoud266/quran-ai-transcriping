.PHONY: start setup test clean help install dev

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

start: ## Start the API server (recommended)
	@echo "$(GREEN)Starting Quran AI Transcription API...$(NC)"
	@if [ ! -d "venv" ]; then \
		echo "$(RED)Virtual environment not found. Run 'make setup' first.$(NC)"; \
		exit 1; \
	fi
	@. venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

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

dev: ## Start server in development mode with auto-reload
	@echo "$(GREEN)Starting in development mode...$(NC)"
	@. venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

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

clean-all: clean ## Clean everything including virtual environment
	@echo "$(YELLOW)Removing virtual environment...$(NC)"
	@rm -rf venv
	@echo "$(GREEN)Full cleanup complete!$(NC)"

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