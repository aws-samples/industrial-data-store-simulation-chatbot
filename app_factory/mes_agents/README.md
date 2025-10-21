# MES Agents - AI-Powered Manufacturing Analysis

A demo implementation of intelligent agents for Manufacturing Execution System (MES) data analysis using the Strands SDK.

## Quick Start

1. **Install Dependencies**
   ```bash
   uv add strands-sdk streamlit plotly pandas
   ```

2. **Run the Demo**
   ```bash
   uv run streamlit run app_factory/mes_chat/chat_interface.py
   ```

3. **Try Agent Chat**
   - Click "🤖 MES Insight Chat - AI Agent Edition"
   - Ask questions like: "Show me recent production data" or "What quality issues occurred this week?"

## What's New

### 🤖 Intelligent Agents
- **Smart Analysis**: Agents break down complex questions into logical steps
- **Multi-Step Reasoning**: Handles queries requiring multiple database operations
- **Domain Expertise**: Specialized knowledge for production, quality, equipment, and inventory
- **Configurable Depth**: Choose quick answers, standard responses, or comprehensive analysis

### 🛠️ Enhanced Error Handling
- **Smart Recovery**: Automatic error diagnosis and correction suggestions
- **Partial Results**: Shows progress even when operations timeout
- **Educational Tips**: Learn better ways to ask questions

### 📊 Better Visualizations
- **AI-Selected Charts**: Agents choose the best visualization for your data
- **Fallback Options**: Always get results, even if charts fail
- **Interactive Elements**: Click suggestions to explore further

## Key Features

- **Natural Language**: Ask questions in plain English
- **Progress Tracking**: See what the agent is doing in real-time
- **Error Recovery**: Intelligent handling of database and system errors
- **Educational**: Learn better query techniques as you use the system

## Architecture

```
mes_agents/
├── mes_analysis_agent.py    # Main intelligent agent
├── agent_manager.py         # Agent lifecycle management
├── error_handling.py        # Smart error recovery
├── config.py               # Agent configuration
└── tools/                  # Agent tools
    ├── database_tools.py   # SQLite database access
    └── visualization_tools.py # Chart generation
```

## Example Queries

- "What's our production efficiency this month?"
- "Show me quality issues by product line"
- "Which machines have the most downtime?"
- "What inventory items are running low?"

## Demo Limitations

This is a proof-of-concept demo with:
- SQLite database (not production-scale)
- Simulated manufacturing data
- Basic agent implementations
- Limited to manufacturing domain

## Next Steps

For production use, consider:
- Real database integration (PostgreSQL, SQL Server)
- Advanced agent specialization
- User authentication and permissions
- Performance optimization
- Extended domain coverage