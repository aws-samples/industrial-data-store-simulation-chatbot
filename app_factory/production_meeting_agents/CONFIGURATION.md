# Production Meeting Agents - Configuration Guide

Configuration for the Production Meeting agent system lives in `config.py` (`ProductionMeetingConfig` dataclass).

## All Options

```python
from app_factory.production_meeting_agents.config import ProductionMeetingConfig

config = ProductionMeetingConfig(
    # Core
    agent_enabled=True,                              # master switch for the agent system
    default_model='us.anthropic.claude-sonnet-5',    # any entry from SUPPORTED_MODELS
    max_tokens=4096,                                 # response token cap
    timeout_seconds=120,                             # max time for one analysis

    # Meeting behavior
    meeting_focus='daily',            # 'daily', 'weekly', 'monthly'
    analysis_depth='standard',        # 'standard', 'comprehensive'
    enable_proactive_insights=True,

    # Per-domain specialist toggles
    enable_production_agent=True,
    enable_quality_agent=True,
    enable_equipment_agent=True,
    enable_inventory_agent=True,
)
```

The module-level `default_config` instance is what the dashboard and scheduler use — edit `config.py` to change defaults.

## Available Models

All entries are Bedrock cross-region (geo) inference profiles (see `SUPPORTED_MODELS` in `config.py`):

| Inference Profile ID | Notes |
|---|---|
| `us.anthropic.claude-sonnet-5` | Default — best analysis quality for briefings |
| `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Fast — switch here if latency matters more |
| `us.anthropic.claude-sonnet-4-20250514-v1:0` | Advanced analysis |
| `us.amazon.nova-lite-v1:0` | Fast |
| `us.amazon.nova-pro-v1:0` | Balanced |

Models must be enabled in the Bedrock model access console for your account/region. Cross-region profiles also require IAM access to the underlying foundation-model ARNs in each region of the profile.

## AWS Environment

Set in `.env` at the repo root:

```bash
AWS_REGION=us-east-1
AWS_PROFILE=your-profile
```

## Safety

Agent database access is read-only: SQL is validated as SELECT-only (`shared/sql_safety.py`) and executed on a read-only SQLite connection.

## Nightly Cache

The daily analysis scheduler caches agent output as JSON in `reports/daily_analysis/` (keyed by date, 30-day retention). The dashboard loads from cache first and falls back to live agents. Commands:

```bash
make run-analysis    # generate now
make check-cache     # cache status
make logs            # scheduler logs
```

## Troubleshooting

| Symptom | Check |
|---|---|
| `AccessDeniedException` from Bedrock | Model enabled in Bedrock console? IAM covers the inference profile? |
| Slow briefing generation | Switch `default_model` to Haiku 4.5 |
| Empty briefing card | Run `make run-analysis`; check `daily_analysis.log` |
| Database errors | `make setup-db` to (re)generate `mes.db` |
