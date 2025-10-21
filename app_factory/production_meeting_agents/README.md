# Production Meeting Agents - AI-Powered Manufacturing Dashboard Enhancement

A sophisticated agent system that enhances manufacturing dashboards with intelligent AI-powered analysis using the Strands SDK, specifically designed for daily production meetings and lean manufacturing operations.

## Quick Start

1. **Install Dependencies**
   ```bash
   uv sync
   ```

2. **Configure Environment**
   ```bash
   # Create .env file
   echo "AWS_REGION=us-east-1" >> .env
   echo "AWS_PROFILE=your-profile" >> .env
   ```

3. **Run Production Meeting Dashboard**
   ```bash
   uv run streamlit run app_factory/production_meeting/app.py
   ```

4. **Try Enhanced AI Insights**
   - Navigate to the "AI Insights" tab
   - Ask questions like: "What are today's critical production issues?" or "Analyze quality trends from this week"
   - Experience intelligent multi-step reasoning and contextual insights

## What's New

### 🤖 Intelligent Agent Enhancement
- **Sophisticated Analysis**: Agents replace direct Bedrock calls with multi-step reasoning
- **Domain Expertise**: Specialized agents for production, quality, equipment, and inventory
- **Contextual Insights**: Dashboard-aware analysis that enhances existing visualizations
- **Meeting Focus**: Optimized for lean daily meetings and quick decision-making

### 🛠️ Enhanced Error Handling
- **Smart Recovery**: Automatic error diagnosis and intelligent recovery strategies
- **Graceful Degradation**: Maintains dashboard functionality when agents are unavailable
- **Educational Guidance**: Learn better ways to interact with manufacturing data

### 📊 Improved Visualizations
- **AI-Selected Charts**: Agents recommend optimal visualizations for manufacturing data
- **Streamlit Integration**: Uses default color palette for consistent theming
- **Meeting-Focused**: Charts optimized for quick understanding in meeting contexts

### 🏭 Manufacturing-Specific Features
- **Daily Briefings**: Automated generation of critical issues and priorities
- **Multi-Domain Analysis**: Coordinated analysis across production, quality, equipment, and inventory
- **Proactive Insights**: Intelligent identification of patterns and trends
- **Action-Oriented**: Recommendations focused on immediate manufacturing decisions

## Key Features

- **Natural Language**: Ask complex manufacturing questions in plain English
- **Progress Tracking**: See what agents are analyzing in real-time
- **Error Recovery**: Intelligent handling of database and system errors
- **Dashboard Integration**: Seamless enhancement of existing dashboard tabs
- **Meeting Efficiency**: Optimized for lean manufacturing meeting workflows

## Architecture

```
production_meeting_agents/
├── production_meeting_agent.py    # Main agent tools and orchestration
├── agent_manager.py              # Agent lifecycle and UI integration
├── error_handling.py             # Manufacturing-specific error recovery
├── config.py                     # Agent configuration and settings
└── tools/                        # Specialized agent tools
    ├── database_tools.py         # Enhanced SQLite database access
    └── visualization_tools.py    # Intelligent chart generation
```

## Agent Specialization

### Production Analysis Agent
- Daily production performance analysis
- Bottleneck identification and recommendations
- Work order status and scheduling insights
- Production trend analysis and forecasting

### Quality Analysis Agent
- Defect pattern analysis and root cause identification
- Quality metrics trending and threshold monitoring
- Product-specific quality issue analysis
- Work center quality performance assessment

### Equipment Analysis Agent
- OEE analysis and equipment performance insights
- Downtime analysis and maintenance recommendations
- Equipment bottleneck identification
- Predictive maintenance suggestions

### Inventory Analysis Agent
- Stock level analysis and shortage predictions
- Consumption pattern analysis
- Supplier performance assessment
- Reorder recommendations and inventory optimization

### Main Orchestration Agent
- Query routing to appropriate specialized agents
- Multi-domain analysis coordination
- Daily briefing generation
- Comprehensive meeting insights

## Example Queries

### Daily Meeting Queries
- "What are today's critical production issues?"
- "Give me a daily briefing for the production meeting"
- "What quality issues should we prioritize today?"
- "Which equipment needs immediate attention?"

### Analysis Queries
- "Analyze production efficiency trends this week"
- "What's causing the quality issues in Product Line A?"
- "Compare equipment performance across work centers"
- "Predict inventory shortages for next week"

### Multi-Domain Queries
- "How do equipment downtimes correlate with quality issues?"
- "What's the impact of inventory shortages on production?"
- "Analyze the relationship between shift performance and defect rates"

## Configuration

### Basic Configuration

```python
from app_factory.production_meeting_agents.config import ProductionMeetingConfig

# Standard daily meeting configuration
config = ProductionMeetingConfig(
    meeting_focus='daily',
    analysis_depth='standard',
    enable_proactive_insights=True
)
```

### Performance Optimization

```python
# Fast response configuration for quick meetings
config = ProductionMeetingConfig(
    default_model='us.anthropic.claude-3-5-haiku-20241022-v1:0',
    quick_briefing_timeout=20,
    max_concurrent_agents=2
)
```

### Comprehensive Analysis

```python
# Detailed analysis configuration for problem-solving
config = ProductionMeetingConfig(
    default_model='us.anthropic.claude-sonnet-4-20250514-v1:0',
    analysis_depth='comprehensive',
    detailed_analysis_timeout=300
)
```

## Integration with Existing Dashboards

### Enhanced Dashboard Tabs

The agents enhance existing dashboard functionality without replacing it:

- **Production Tab**: Enhanced with intelligent production analysis
- **Quality Tab**: Enhanced with quality pattern recognition
- **Equipment Tab**: Enhanced with OEE insights and maintenance recommendations
- **Inventory Tab**: Enhanced with shortage predictions and optimization suggestions
- **AI Insights Tab**: Completely powered by agent orchestration

### Backward Compatibility

- All existing dashboard functionality is preserved
- Hardcoded queries for data presentation remain unchanged
- Agent functionality can be disabled without breaking dashboards
- Graceful degradation when agents are unavailable

## Deployment

### Development Environment

```bash
# Install dependencies
uv sync

# Set up environment
echo "AWS_REGION=us-east-1" >> .env
echo "AWS_PROFILE=dev-profile" >> .env

# Generate test database
uv run python app_factory/data_generator/sqlite-synthetic-mes-data.py

# Run application
uv run streamlit run app_factory/production_meeting/app.py
```

### Production Environment

```bash
# Production configuration
export AWS_REGION="us-east-1"
export AWS_PROFILE="production-profile"
export PRODUCTION_MEETING_DEFAULT_MODEL="us.anthropic.claude-haiku-4-5-20251001-v1:0"

# Run with production settings
uv run streamlit run app_factory/production_meeting/app.py --server.port 8501
```

## Monitoring and Troubleshooting

### Health Checks

```python
from app_factory.production_meeting_agents.agent_manager import ProductionMeetingAgentManager
from app_factory.production_meeting_agents.config import default_config

# Check agent system health
manager = ProductionMeetingAgentManager(default_config)
if manager.is_ready():
    print("✅ Production Meeting Agents are ready")
    status = manager.get_agent_status()
    print(f"Success rate: {status.get('success_rate', 'N/A')}%")
else:
    print("❌ Agents not available - using fallback functionality")
```

### Performance Monitoring

```python
# Monitor agent performance
status = manager.get_agent_status()
print(f"Last response time: {status.get('last_response_time', 'N/A')}s")
print(f"Average response time: {status.get('avg_response_time', 'N/A')}s")
print(f"Total queries processed: {status.get('total_queries', 0)}")
```

### Common Issues

1. **Slow Response Times**
   - Use faster models (Claude Haiku)
   - Reduce analysis depth to 'standard'
   - Limit concurrent agents

2. **Agent Not Responding**
   - Check AWS credentials and Bedrock access
   - Verify model availability in your region
   - Check network connectivity

3. **Database Errors**
   - Ensure `mes.db` exists and is readable
   - Regenerate database if corrupted
   - Check file permissions

See [CONFIGURATION.md](CONFIGURATION.md) for detailed troubleshooting guide.

## Comparison with MES Agents

| Feature | MES Agents | Production Meeting Agents |
|---------|------------|---------------------------|
| **Purpose** | General MES data exploration | Daily production meeting enhancement |
| **Interface** | Standalone chat application | Integrated dashboard enhancement |
| **Focus** | Exploratory data analysis | Meeting-focused insights and briefings |
| **Integration** | Independent application | Enhances existing dashboards |
| **Meeting Support** | General queries | Optimized for lean manufacturing meetings |
| **Visualization** | Standalone charts | Dashboard-integrated insights |

## Demo Limitations

This is a demonstration system with:
- SQLite database (not production-scale)
- Simulated manufacturing data
- Basic agent implementations
- Limited to manufacturing domain

## Next Steps

For production deployment, consider:
- Real database integration (PostgreSQL, SQL Server)
- Advanced agent specialization and customization
- User authentication and role-based permissions
- Performance optimization and caching
- Integration with existing MES/ERP systems
- Custom visualization and reporting capabilities

## License

This project is licensed under the MIT License - see the LICENSE file for details.