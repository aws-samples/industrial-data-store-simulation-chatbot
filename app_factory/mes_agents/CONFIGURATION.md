# MES Agents Configuration

Configuration for the MES Chat agents lives in `config.py`.

## AgentConfig

```python
from app_factory.mes_agents.config import AgentConfig

# Defaults (recommended for the demo)
config = AgentConfig()

# Or customize
config = AgentConfig(
    default_model='us.anthropic.claude-sonnet-5',  # any entry from SUPPORTED_MODELS
    timeout_seconds=120,          # max time for one analysis
    max_tokens=4096,              # response token cap
    analysis_depth='standard',    # 'standard' or 'comprehensive'
)
```

## Available Models

All entries are Bedrock cross-region (geo) inference profiles (see `SUPPORTED_MODELS` in `config.py`):

| Inference Profile ID | Notes |
|---|---|
| `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Default — fast, best for interactive chat |
| `us.anthropic.claude-sonnet-5` | Advanced analysis |
| `us.anthropic.claude-sonnet-4-20250514-v1:0` | Advanced analysis |
| `us.amazon.nova-lite-v1:0` | Fast |
| `us.amazon.nova-pro-v1:0` | Balanced |

The model is also selectable at runtime in the chat sidebar. Models must be enabled in the Bedrock model access console for your account/region.

## AWS Environment

Set in `.env`:

```bash
AWS_REGION=us-east-1
AWS_PROFILE=your-profile
```

## Safety

Agent database access is read-only: SQL is validated as SELECT-only (`shared/sql_safety.py`) and executed on a read-only SQLite connection (`shared/database.py` with `read_only=True`).

## Demo Limitations

This is a proof-of-concept:
- SQLite database only
- Basic error recovery
- Per-session agents (no persistence across browser sessions)
