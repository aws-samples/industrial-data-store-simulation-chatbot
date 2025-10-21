# Daily Analysis Caching Setup

This document explains how to set up automated daily analysis generation to improve the performance of your MES Production Dashboard.

## Overview

The AI Insights tab in your production dashboard can take 2+ minutes to generate comprehensive analysis. To improve user experience, we've implemented a caching system that:

1. **Runs comprehensive analysis daily** (outside Streamlit)
2. **Caches results** for instant retrieval
3. **Provides MES Chat integration** for follow-up questions

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Daily Scheduler│    │   Cache Manager  │    │  Streamlit UI   │
│                 │    │                  │    │                 │
│ • Data Gen      │───▶│ • Stores JSON    │───▶│ • Fast Loading  │
│ • AI Analysis   │    │ • 30-day history │    │ • Chat Fallback │
│ • Runs at 6 AM  │    │ • Smart cleanup  │    │ • Live Analysis │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Daily Workflow:
1. **6:00 AM**: Generate fresh synthetic MES data (90 days back, 14 days ahead)
2. **6:01 AM**: Run comprehensive AI analysis on all contexts
3. **6:03 AM**: Cache results as JSON files
4. **All day**: Dashboard loads cached results instantly (<1 second)

## Prerequisites

### System Requirements
- **Linux with systemd** (Amazon Linux 2023, Ubuntu 16.04+, CentOS 7+, etc.)
- **Python 3.10+** with `uv` package manager

### Setup
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync
```

## Quick Setup

### 1. Test the Daily Analysis

```bash
# Run once manually to test
uv run python scripts/run_daily_analysis.py
# Or use the Makefile shortcut
make run-analysis
```

### 2. Set Up Automation

#### Option A: Using the Setup Script (Recommended)
```bash
uv run python scripts/setup_daily_analysis.py
# Or use the Makefile shortcut
make setup-automation
```

The setup script will:
- **Check systemd availability** (required for this setup)
- **Create systemd service and timer files**
- **Guide you through installation**

#### Option B: Manual Systemd Setup
```bash
# The setup script creates these files, but you can also create them manually:

# /etc/systemd/system/daily-mes-analysis.service
# /etc/systemd/system/daily-mes-analysis.timer

sudo systemctl daemon-reload
sudo systemctl enable daily-mes-analysis.timer
sudo systemctl start daily-mes-analysis.timer
```

### 3. Verify Setup

Check that the cache directory is created and populated:
```bash
ls -la reports/daily_analysis/
```

## File Structure

```
project/
├── app_factory/
│   └── production_meeting/
│       ├── ai_insights.py              # Updated UI with caching
│       ├── daily_analysis_scheduler.py # Core scheduler
│       └── analysis_cache_manager.py   # Cache management
├── reports/
│   └── daily_analysis/                 # Cache storage
│       ├── daily_analysis_2024-01-15.json
│       ├── daily_analysis_2024-01-16.json
│       └── ...
├── scripts/
│   └── setup_daily_analysis.py        # Setup automation
├── scripts/
│   ├── setup_daily_analysis.py        # Setup automation
│   └── run_daily_analysis.py          # Manual run script
└── logs/
    └── daily_analysis.log             # Scheduler logs
```

## Usage

### In the Streamlit Dashboard

1. **Fast Mode (Cached)**: Loads pre-generated analysis instantly
2. **Live Mode**: Runs real-time analysis (2+ minutes)
3. **MES Chat Integration**: Click follow-up suggestions to dive deeper

### Cache Management

The system automatically:
- Generates fresh analysis daily at 6 AM
- Keeps 30 days of history
- Cleans up old files
- Handles errors gracefully

### Manual Operations

```bash
# Generate analysis now (includes fresh data generation)
uv run python scripts/run_daily_analysis.py
# Or: make run-analysis

# Check cache status
uv run python -c "
from app_factory.production_meeting.analysis_cache_manager import AnalysisCacheManager
cache = AnalysisCacheManager()
print(cache.get_cache_status())
"
# Or: make check-cache

# View available dates
uv run python -c "
from app_factory.production_meeting.analysis_cache_manager import AnalysisCacheManager
cache = AnalysisCacheManager()
dates = cache.list_available_dates()
for date in dates[:5]:
    print(f'{date[\"date\"]}: {date[\"analysis_count\"]} analyses')
"
# Or: make list-cache
```

## Configuration

### Scheduler Settings

Edit `daily_analysis_scheduler.py` to customize:

```python
# Enable/disable data generation
scheduler = DailyAnalysisScheduler(generate_data=True)

# Data generation parameters (in generate_fresh_data method)
"--lookback", "90",    # Days of historical data
"--lookahead", "14"    # Days of future projections

# Cache retention (days)
self.cleanup_old_cache_files(days_to_keep=30)

# Analysis types to generate
analysis_types = [
    {"name": "production_summary", "context": "production"},
    {"name": "quality_insights", "context": "quality"},
    {"name": "equipment_status", "context": "equipment"},
    {"name": "inventory_analysis", "context": "inventory"}
]

# Freshness threshold (hours)
if datetime.now() - file_time < timedelta(hours=6):
```

### Cache Manager Settings

Edit `analysis_cache_manager.py` to customize:

```python
# Maximum age for "fresh" analysis
def get_latest_analysis(self, max_age_hours: int = 24)

# Cache directory location
def __init__(self, cache_dir: str = "reports/daily_analysis")
```

## Troubleshooting

### Common Issues

1. **No cached analysis available**
   ```bash
   # Check if scheduler ran
   tail -f logs/daily_analysis.log
   
   # Run manually
   uv run python scripts/run_daily_analysis.py
   ```

2. **Agent initialization fails**
   ```bash
   # Check environment variables
   echo $BEDROCK_REGION
   
   # Verify agent configuration
   uv run python -c "
   from app_factory.production_meeting_agents.config import default_config
   print(default_config.__dict__)
   "
   ```

3. **Systemd service not running**
   ```bash
   # Check service status
   sudo systemctl status daily-mes-analysis.timer
   sudo systemctl status daily-mes-analysis.service
   
   # View service logs
   sudo journalctl -u daily-mes-analysis.service -f
   
   # Test service manually
   sudo systemctl start daily-mes-analysis.service
   ```

4. **Data generation fails**
   ```bash
   # Check if data generator script exists
   ls -la app_factory/data_generator/sqlite-synthetic-mes-data.py
   
   # Test data generation manually
   uv run python app_factory/data_generator/sqlite-synthetic-mes-data.py --config app_factory/data_generator/data_pools.json --lookback 90 --lookahead 14
   
   # Check database permissions
   ls -la mes.db
   ```

### Performance Optimization

1. **Reduce analysis scope** for faster generation
2. **Adjust cache retention** to save disk space
3. **Monitor execution time** and optimize queries
4. **Use SSD storage** for cache directory

## Integration with MES Chat

The cached analysis includes follow-up suggestions that seamlessly integrate with your MES Chat interface:

1. User views cached daily summary
2. Clicks on a follow-up suggestion
3. System switches to MES Chat mode
4. Chat agent provides deeper analysis

This provides the best of both worlds: fast initial insights and comprehensive follow-up analysis.

## Monitoring

### Log Files

- `logs/daily_analysis.log`: Scheduler execution logs
- `logs/daily_analysis_cron.log`: Cron job logs (if using cron)

### Health Checks

```bash
# Check if today's analysis exists and is fresh
uv run python -c "
from app_factory.production_meeting.analysis_cache_manager import AnalysisCacheManager
cache = AnalysisCacheManager()
print('Fresh analysis available:', cache.is_analysis_fresh())
"

# View cache status in Streamlit
# Go to AI Insights tab → Cache Management expander
```

## Security Considerations

1. **File permissions**: Ensure cache directory is properly secured
2. **Log rotation**: Set up log rotation to prevent disk space issues
3. **Error handling**: Monitor for failed analysis runs
4. **Backup**: Consider backing up cache files for critical deployments

## Makefile Shortcuts

For convenience, you can use these Makefile commands:

```bash
# View all available commands
make help

# Generate analysis manually
make run-analysis

# Set up automation
make setup-automation

# Check cache status
make check-cache

# List available cached analyses
make list-cache

# Start the dashboard
make start-dashboard

# View logs
make logs
```

## Future Enhancements

1. **Multiple time periods**: Generate weekly/monthly summaries
2. **Custom triggers**: Run analysis on data changes
3. **Distributed caching**: Use Redis for multi-instance deployments
4. **Real-time updates**: Hybrid approach with incremental updates