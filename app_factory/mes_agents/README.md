# MES Agents - AI-Powered Manufacturing Analysis

Strands Agents SDK implementation powering the MES Insight Chat: a streaming, per-session agent for Manufacturing Execution System (MES) data analysis.

## Quick Start

1. **Install dependencies** (from the repo root)

   ```bash
   make setup
   ```

2. **Run the app**

   ```bash
   make start-dashboard   # combined app, pick "MES Insight Chat"
   # or chat only:
   make start-chat
   ```

3. **Try it** — ask questions like "Show me recent production data" or "What quality issues occurred this week?"

## How It Works

- `create_agent(config)` in `mes_analysis_agent.py` builds a Strands `Agent` with a manufacturing-domain system prompt, `BedrockModel`, and `SlidingWindowConversationManager`.
- The chat UI creates **one agent per Streamlit session** (stored in `st.session_state`) — no context bleed between users.
- Responses stream via `agent.stream_async()`; the UI shows each tool call live.
- Database access is **read-only**: SELECT-only SQL validation plus a read-only SQLite connection.

## Key Features

- **Natural language**: Ask questions in plain English
- **Multi-step reasoning**: Queries requiring several database operations
- **Live tool visibility**: See schema lookups, SQL queries, and chart generation as they happen
- **Visualizations**: The agent picks appropriate Plotly charts and renders them inline

## Architecture

```
mes_agents/
├── mes_analysis_agent.py   # Agent factory (create_agent)
├── error_handling.py       # Error recovery
├── config.py               # AgentConfig + SUPPORTED_MODELS catalog
└── tools/                  # Agent tools (@tool decorated)
    ├── database_tools.py   # Read-only SQLite access + schema
    └── visualization_tools.py # Plotly chart generation
```

## Example Queries

- "What's our production efficiency this month?"
- "Show me quality issues by product line"
- "Which machines have the most downtime?"
- "What inventory items are running low?"

## Configuration

See [CONFIGURATION.md](CONFIGURATION.md). Default model: Claude Haiku 4.5 (fast); Claude Sonnet 5 available in the sidebar picker.

## Demo Limitations

This is a proof-of-concept demo with:
- SQLite database (not production-scale)
- Simulated manufacturing data
- Limited to manufacturing domain

For production use, consider real database integration (PostgreSQL, SQL Server), authentication and permissions, and performance optimization.
