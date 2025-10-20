# MES Agents Configuration

Simple configuration guide for the MES Agents demo.

## Basic Configuration

The agents use default settings that work out of the box. Configuration is handled in `config.py`:

```python
from mes_agents.config import AgentConfig

# Use defaults (recommended for demo)
config = AgentConfig()

# Or customize settings
config = AgentConfig(
    timeout_seconds=60,           # How long to wait for analysis
    analysis_depth="standard",    # quick, standard, or comprehensive
    max_query_steps=5,           # Maximum reasoning steps
    enable_progress_updates=True  # Show progress in UI
)
```

## Available Models

The system supports multiple Bedrock models. Default is Claude 4.5 Haiku for optimal performance:
- Claude 4.5 Haiku (Recommended - fast and efficient)
- Claude 4 Sonnet (Advanced analysis)
- Claude 3.7 Sonnet (Advanced analysis)
- Amazon Nova models (Pro, Lite)
- Other Bedrock models with tool support

## Agent Settings

### Analysis Depth
- **standard**: Clear answers with key context and metrics (default)
- **comprehensive**: Full analysis with insights, recommendations, and visualizations

### Timeout Settings
- **timeout_seconds**: Maximum time for analysis (default: 120)
- **max_query_steps**: Maximum reasoning steps (default: 5)

### UI Features
- **enable_progress_updates**: Show real-time progress (default: True)
- **show_technical_details**: Display technical error info (default: False)

## Environment Variables

Set these in your `.env` file:

```bash
AWS_REGION=us-east-1
AWS_PROFILE=your-profile
```

## Demo Limitations

This is a proof-of-concept with:
- Single agent type (MES Analysis Agent)
- SQLite database only
- Basic error recovery
- Simplified configuration options

For production use, you would extend:
- Multiple specialized agents
- Database connection pooling
- Advanced error recovery
- User-specific configurations
- Performance monitoring