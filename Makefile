# Manufacturing Operations Hub - Makefile

.PHONY: help install dev test run-analysis setup-cron clean

help: ## Show this help message
	@echo "Manufacturing Operations Hub - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync

dev: ## Install development dependencies
	uv sync --group dev

test: ## Run tests
	uv run pytest tests/

run-analysis: ## Generate daily analysis manually (includes fresh data generation)
	uv run python scripts/run_daily_analysis.py

setup-automation: ## Set up automated daily analysis (systemd)
	uv run python scripts/setup_daily_analysis.py

start-dashboard: ## Start the Streamlit dashboard
	uv run streamlit run app_factory/main.py

start-chat: ## Start the MES Chat interface
	uv run streamlit run app_factory/mes_chat/chat_interface.py

clean: ## Clean up cache and temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete

check-cache: ## Check analysis cache status
	@uv run python -c "from app_factory.production_meeting.analysis_cache_manager import AnalysisCacheManager; cache = AnalysisCacheManager(); print('Cache Status:'); import json; print(json.dumps(cache.get_cache_status(), indent=2))"

list-cache: ## List available cached analyses
	@uv run python -c "from app_factory.production_meeting.analysis_cache_manager import AnalysisCacheManager; cache = AnalysisCacheManager(); dates = cache.list_available_dates(7); print('Available Analyses (Last 7 Days):'); [print(f'  {d[\"date\"]}: {d[\"analysis_count\"]} analyses ({d[\"file_size\"]/1024:.1f} KB)') for d in dates]"

logs: ## View daily analysis logs
	@if [ -f logs/daily_analysis.log ]; then tail -f logs/daily_analysis.log; else echo "No log file found. Run 'make run-analysis' first."; fi