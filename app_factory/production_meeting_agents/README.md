# Production Meeting Agents

Strands Agents SDK system powering the Production Meeting dashboard's AI features: the nightly daily briefing, the structured executive summary, and live follow-up analysis in the AI Insights tab.

## Quick Start

1. **Install dependencies** (from the repo root)

   ```bash
   make setup
   ```

2. **Configure AWS** — create `.env`:

   ```bash
   AWS_REGION=us-east-1
   AWS_PROFILE=your-profile
   ```

3. **Run the dashboard**

   ```bash
   make start-dashboard   # pick "Daily Production Meeting"
   ```

4. **Pre-generate the daily briefing** (optional — the dashboard also works live):

   ```bash
   make run-analysis
   ```

## Architecture

```
production_meeting_agents/
├── production_meeting_agent.py   # Specialists, orchestrator, structured executive summary
├── agent_manager.py              # Lifecycle wrapper used by the scheduler/UI
├── error_handling.py             # Error recovery
├── config.py                     # ProductionMeetingConfig + model catalog
└── tools/                        # Agent tools (@tool decorated)
    ├── database_tools.py         # Read-only SQLite access
    └── visualization_tools.py    # Chart generation
```

### Agents-as-tools pattern

Four **domain specialists** (production, quality, equipment, inventory) are built from a shared prompt template, each exposed as a Strands `@tool`. An **orchestrator agent** routes queries to them — calling several in parallel for broad questions like "daily briefing".

### Structured executive summary

`generate_executive_summary()` runs the four specialists, then uses Strands `structured_output` to return a validated `ExecutiveSummary` Pydantic model (severity / domain / headline / action per item, plus an overall plant status). The dashboard renders this directly as colored callouts — no free-text parsing.

## Models

Default: **Claude Sonnet 5** via the Bedrock cross-region inference profile `us.anthropic.claude-sonnet-5` — chosen for analysis quality on the flagship daily briefing. Alternatives (see `SUPPORTED_MODELS` in `config.py`): Claude Haiku 4.5, Claude Sonnet 4, Amazon Nova Lite/Pro. Models must be enabled in the Bedrock model access console.

## Example Queries

- "What are today's critical production issues?"
- "Give me a daily briefing for the production meeting"
- "How do equipment downtimes correlate with quality issues?"
- "Predict inventory shortages for next week"

## Configuration

```python
from app_factory.production_meeting_agents.config import ProductionMeetingConfig

config = ProductionMeetingConfig(
    default_model='us.anthropic.claude-sonnet-5',
    max_tokens=4096,
    timeout_seconds=120,
    meeting_focus='daily',        # 'daily', 'weekly', 'monthly'
    analysis_depth='standard',    # 'standard', 'comprehensive'
)
```

See [CONFIGURATION.md](CONFIGURATION.md) for all options.

## Nightly Automation

`production_meeting/daily_analysis_scheduler.py` regenerates synthetic data, runs the four domain analyses and the structured executive summary in parallel, and caches results as JSON for instant dashboard loading. Set it up with `make setup-automation` (systemd) or run manually with `make run-analysis`.

## Troubleshooting

1. **Slow responses** — switch `default_model` to Claude Haiku 4.5
2. **Agent not responding** — check AWS credentials, Bedrock model access, and region
3. **Database errors** — ensure `mes.db` exists (`make setup-db`)

## Comparison with MES Agents

| Feature | MES Agents (`mes_agents/`) | Production Meeting Agents |
|---------|------------|---------------------------|
| **Purpose** | Interactive data exploration chat | Daily briefing + meeting insights |
| **Agent model** | Single agent, per-session | Orchestrator + 4 domain specialists, cached |
| **Default model** | Claude Haiku 4.5 (latency) | Claude Sonnet 5 (analysis quality) |
| **Output** | Streaming text + charts | Structured executive summary + streamed follow-ups |

## Demo Limitations

Demonstration system: SQLite database, simulated data, manufacturing domain only. For production, consider real database integration, authentication/permissions, and integration with existing MES/ERP systems.
