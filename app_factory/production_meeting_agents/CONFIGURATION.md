# Production Meeting Agents - Configuration Guide

A comprehensive guide for configuring and deploying the Production Meeting Agents system that enhances manufacturing dashboards with intelligent AI-powered analysis.

## Overview

The Production Meeting Agents system replaces direct Bedrock API calls with sophisticated Strands SDK agents, providing intelligent analysis for daily production meetings while maintaining the existing dashboard structure.

## Quick Start

1. **Install Dependencies**
   ```bash
   uv sync
   ```

2. **Configure Environment**
   ```bash
   # Create .env file with AWS configuration
   AWS_REGION="us-east-1"
   AWS_PROFILE="your-profile"
   ```

3. **Run Production Meeting Dashboard**
   ```bash
   uv run streamlit run app_factory/production_meeting/app.py
   ```

## Configuration Options

### Core Agent Configuration

The `ProductionMeetingConfig` class in `config.py` provides comprehensive configuration options:

#### Basic Settings

```python
# Enable/disable the entire agent system
agent_enabled: bool = True

# Default AI model for all agents
default_model: str = 'us.anthropic.claude-haiku-4-5-20251001-v1:0'

# Global timeout for agent operations
timeout_seconds: int = 120

# Maximum steps for multi-step analysis
max_query_steps: int = 5

# Show progress updates during analysis
enable_progress_updates: bool = True
```

#### Meeting-Specific Configuration

```python
# Meeting type: 'daily', 'weekly', 'monthly'
meeting_focus: str = 'daily'

# Analysis depth: 'standard', 'comprehensive'
analysis_depth: str = 'standard'

# Enable proactive insights and recommendations
enable_proactive_insights: bool = True

# Visualization theme (currently 'streamlit_default')
visualization_theme: str = 'streamlit_default'
```

#### Agent Specialization Settings

```python
# Enable/disable individual agent types
enable_production_agent: bool = True
enable_quality_agent: bool = True
enable_equipment_agent: bool = True
enable_inventory_agent: bool = True
```

#### Performance Settings

```python
# Timeout for quick daily briefings (seconds)
quick_briefing_timeout: int = 30

# Timeout for detailed analysis (seconds)
detailed_analysis_timeout: int = 180

# Maximum concurrent agent operations
max_concurrent_agents: int = 3
```

### Supported AI Models

The system supports multiple AI models with different performance characteristics:

| Model | Performance | Use Case |
|-------|-------------|----------|
| `us.amazon.nova-lite-v1:0` | Fast | Quick daily briefings |
| `us.amazon.nova-pro-v1:0` | Balanced | Standard analysis |
| `us.anthropic.claude-3-5-haiku-20241022-v1:0` | Fast | Real-time insights |
| `us.anthropic.claude-3-7-sonnet-20250219-v1:0` | Advanced | Complex analysis |
| `us.anthropic.claude-sonnet-4-20250514-v1:0` | Advanced | Comprehensive reports |
| `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Recommended | Default choice |

### Meeting Focus Options

Configure the system for different meeting types:

- **daily**: Daily Production Meeting (default)
  - Focus on immediate issues and daily metrics
  - Quick insights and actionable recommendations
  - Optimized for 15-30 minute meetings

- **weekly**: Weekly Production Review
  - Trend analysis and weekly performance
  - Deeper investigation of recurring issues
  - Strategic recommendations

- **monthly**: Monthly Performance Analysis
  - Long-term trends and strategic insights
  - Comprehensive performance evaluation
  - Planning and forecasting focus

### Analysis Depth Options

Control the level of analysis detail:

- **standard**: Standard Analysis (default)
  - Quick insights and key findings
  - Suitable for daily meetings
  - Response time: 5-15 seconds

- **comprehensive**: Comprehensive Analysis
  - Detailed investigation and multi-step reasoning
  - Suitable for problem-solving sessions
  - Response time: 30-60 seconds

## Environment Configuration

### AWS Configuration

Create a `.env` file in the project root:

```bash
# Required AWS settings
AWS_REGION="us-east-1"
AWS_PROFILE="your-aws-profile"

# Optional: Override default model
PRODUCTION_MEETING_DEFAULT_MODEL="us.anthropic.claude-haiku-4-5-20251001-v1:0"

# Optional: Enable debug logging
PRODUCTION_MEETING_DEBUG="true"
```

### Required AWS Permissions

Your AWS role needs these permissions for Bedrock access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel",
        "bedrock-runtime:InvokeModel"
      ],
      "Resource": "*"
    }
  ]
}
```

### Model Access Requirements

Enable access to at least one supported model in Amazon Bedrock:

1. Go to Amazon Bedrock console
2. Navigate to "Model access"
3. Enable access to desired models (Claude Haiku 4.5 recommended)
4. Wait for access to be granted (usually immediate)

## Deployment Configuration

### Development Environment

```python
# config.py - Development settings
@dataclass
class ProductionMeetingConfig:
    agent_enabled: bool = True
    default_model: str = 'us.anthropic.claude-3-5-haiku-20241022-v1:0'  # Fast model
    timeout_seconds: int = 60  # Shorter timeout for development
    enable_progress_updates: bool = True  # Show detailed progress
    analysis_depth: str = 'standard'  # Quick responses
```

### Production Environment

```python
# config.py - Production settings
@dataclass
class ProductionMeetingConfig:
    agent_enabled: bool = True
    default_model: str = 'us.anthropic.claude-haiku-4-5-20251001-v1:0'  # Recommended
    timeout_seconds: int = 120  # Standard timeout
    enable_progress_updates: bool = True
    analysis_depth: str = 'standard'
    max_concurrent_agents: int = 3  # Limit concurrent operations
```

### High-Performance Environment

```python
# config.py - High-performance settings
@dataclass
class ProductionMeetingConfig:
    agent_enabled: bool = True
    default_model: str = 'us.anthropic.claude-sonnet-4-20250514-v1:0'  # Advanced model
    timeout_seconds: int = 180  # Extended timeout
    analysis_depth: str = 'comprehensive'  # Detailed analysis
    max_concurrent_agents: int = 5  # Higher concurrency
    enable_proactive_insights: bool = True
```

## Advanced Configuration

### Custom Agent Configuration

You can customize individual agent behavior by modifying the configuration:

```python
# Enable only specific agents for focused meetings
config = ProductionMeetingConfig(
    enable_production_agent=True,
    enable_quality_agent=True,
    enable_equipment_agent=False,  # Disable if not needed
    enable_inventory_agent=False   # Disable if not needed
)
```

### Performance Tuning

```python
# Optimize for meeting efficiency
config = ProductionMeetingConfig(
    quick_briefing_timeout=15,      # Very fast briefings
    detailed_analysis_timeout=90,   # Reasonable detail timeout
    max_concurrent_agents=2,        # Conservative concurrency
    max_query_steps=3              # Limit analysis complexity
)
```

### Meeting-Specific Configurations

```python
# Daily standup configuration
daily_config = ProductionMeetingConfig(
    meeting_focus='daily',
    analysis_depth='standard',
    quick_briefing_timeout=20,
    enable_proactive_insights=True
)

# Weekly review configuration
weekly_config = ProductionMeetingConfig(
    meeting_focus='weekly',
    analysis_depth='comprehensive',
    detailed_analysis_timeout=300,
    max_query_steps=7
)
```

## Integration with Existing Dashboards

### Dashboard Enhancement Configuration

The agents integrate seamlessly with existing dashboard tabs:

- **Production Tab**: Enhanced with production analysis agent insights
- **Quality Tab**: Enhanced with quality analysis agent insights
- **Equipment Tab**: Enhanced with equipment analysis agent insights
- **Inventory Tab**: Enhanced with inventory analysis agent insights
- **AI Insights Tab**: Completely powered by agent orchestration

### Backward Compatibility

The system maintains full backward compatibility:

- All existing dashboard functionality remains unchanged
- Hardcoded queries for data presentation are preserved
- Agent functionality can be disabled without breaking dashboards
- Graceful degradation when agents are unavailable

## Monitoring and Logging

### Enable Debug Logging

```python
import logging

# Enable detailed agent logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('production_meeting_agents')
```

### Performance Monitoring

The system provides built-in performance monitoring:

```python
# Access agent performance metrics
agent_manager = ProductionMeetingAgentManager(config)
status = agent_manager.get_agent_status()

print(f"Agent ready: {status['ready']}")
print(f"Last response time: {status['last_response_time']}s")
print(f"Success rate: {status['success_rate']}%")
```

### Health Checks

```python
# Check agent system health
if agent_manager.is_ready():
    print("✅ Production Meeting Agents are ready")
else:
    print("❌ Production Meeting Agents are not available")
    # Fall back to basic dashboard functionality
```

## Troubleshooting

See the [Troubleshooting Guide](#troubleshooting-guide) section below for common issues and solutions.

---

# Troubleshooting Guide

## Common Issues and Solutions

### Agent Not Responding

**Symptoms:**
- Agents don't respond to queries
- Timeout errors in the dashboard
- "Agent not available" messages

**Solutions:**

1. **Check AWS Configuration**
   ```bash
   # Verify AWS credentials
   aws sts get-caller-identity
   
   # Check Bedrock model access
   aws bedrock list-foundation-models --region us-east-1
   ```

2. **Verify Model Access**
   - Go to Amazon Bedrock console
   - Check "Model access" section
   - Ensure your selected model is enabled
   - Try a different model if current one is unavailable

3. **Check Configuration**
   ```python
   # Verify agent is enabled
   from app_factory.production_meeting_agents.config import default_config
   print(f"Agent enabled: {default_config.agent_enabled}")
   print(f"Default model: {default_config.default_model}")
   ```

4. **Increase Timeout**
   ```python
   # Increase timeout for slow responses
   config = ProductionMeetingConfig(
       timeout_seconds=300,  # 5 minutes
       detailed_analysis_timeout=600  # 10 minutes
   )
   ```

### Slow Agent Performance

**Symptoms:**
- Agents take too long to respond
- Frequent timeout errors
- Poor meeting efficiency

**Solutions:**

1. **Use Faster Model**
   ```python
   config = ProductionMeetingConfig(
       default_model='us.anthropic.claude-3-5-haiku-20241022-v1:0'  # Fastest
   )
   ```

2. **Reduce Analysis Depth**
   ```python
   config = ProductionMeetingConfig(
       analysis_depth='standard',  # Instead of 'comprehensive'
       max_query_steps=3          # Limit complexity
   )
   ```

3. **Optimize for Quick Briefings**
   ```python
   config = ProductionMeetingConfig(
       quick_briefing_timeout=15,
       enable_proactive_insights=False  # Disable for speed
   )
   ```

### Database Connection Issues

**Symptoms:**
- "Database not found" errors
- SQL execution failures
- Empty results from agents

**Solutions:**

1. **Verify Database Exists**
   ```bash
   # Check if mes.db exists
   ls -la mes.db
   
   # Regenerate if missing
   uv run python app_factory/data_generator/sqlite-synthetic-mes-data.py
   ```

2. **Check Database Permissions**
   ```bash
   # Ensure database is readable
   chmod 644 mes.db
   ```

3. **Test Database Connection**
   ```python
   from app_factory.shared.database import get_database_connection
   
   try:
       conn = get_database_connection()
       cursor = conn.cursor()
       cursor.execute("SELECT COUNT(*) FROM work_orders")
       print(f"Work orders count: {cursor.fetchone()[0]}")
   except Exception as e:
       print(f"Database error: {e}")
   ```

### Model Access Denied

**Symptoms:**
- "Access denied" errors from Bedrock
- "Model not available" messages
- Authentication failures

**Solutions:**

1. **Check IAM Permissions**
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "bedrock:ListFoundationModels",
       "bedrock:GetFoundationModel",
       "bedrock-runtime:InvokeModel"
     ],
     "Resource": "*"
   }
   ```

2. **Verify Model Access**
   - Amazon Bedrock Console → Model access
   - Request access to required models
   - Wait for approval (usually immediate)

3. **Try Alternative Model**
   ```python
   # Try different model if current one is unavailable
   config = ProductionMeetingConfig(
       default_model='us.amazon.nova-lite-v1:0'  # Alternative
   )
   ```

### Memory or Performance Issues

**Symptoms:**
- Application crashes during agent operations
- High memory usage
- Slow dashboard loading

**Solutions:**

1. **Limit Concurrent Operations**
   ```python
   config = ProductionMeetingConfig(
       max_concurrent_agents=1,  # Reduce concurrency
       max_query_steps=3        # Limit complexity
   )
   ```

2. **Optimize Database Queries**
   - Agents automatically optimize queries
   - Check for large result sets
   - Consider data archiving for old records

3. **Monitor Resource Usage**
   ```bash
   # Monitor memory usage
   top -p $(pgrep -f streamlit)
   
   # Check disk space
   df -h
   ```

### Agent Configuration Issues

**Symptoms:**
- Agents behave unexpectedly
- Wrong analysis focus
- Missing insights

**Solutions:**

1. **Verify Configuration Loading**
   ```python
   from app_factory.production_meeting_agents.config import default_config
   
   print("Current configuration:")
   print(f"  Meeting focus: {default_config.meeting_focus}")
   print(f"  Analysis depth: {default_config.analysis_depth}")
   print(f"  Enabled agents: {[
       agent for agent in ['production', 'quality', 'equipment', 'inventory']
       if default_config.is_agent_enabled(agent)
   ]}")
   ```

2. **Reset to Default Configuration**
   ```python
   # Use default configuration
   from app_factory.production_meeting_agents.config import ProductionMeetingConfig
   config = ProductionMeetingConfig()  # All defaults
   ```

3. **Validate Configuration Values**
   ```python
   # Check if configuration values are valid
   config = ProductionMeetingConfig()
   
   assert config.default_model in config.SUPPORTED_MODELS
   assert config.meeting_focus in config.MEETING_FOCUS_OPTIONS
   assert config.analysis_depth in config.ANALYSIS_DEPTH_OPTIONS
   ```

## Error Messages and Solutions

### "Agent execution timeout"
- **Cause**: Agent took longer than configured timeout
- **Solution**: Increase timeout or use faster model
- **Code**: `config.timeout_seconds = 300`

### "Model not supported"
- **Cause**: Selected model is not in supported models list
- **Solution**: Choose from supported models list
- **Code**: `config.default_model = 'us.anthropic.claude-haiku-4-5-20251001-v1:0'`

### "Database schema not found"
- **Cause**: Database is missing or corrupted
- **Solution**: Regenerate database
- **Code**: `uv run python app_factory/data_generator/sqlite-synthetic-mes-data.py`

### "Agent not enabled"
- **Cause**: Agent system is disabled in configuration
- **Solution**: Enable agents
- **Code**: `config.agent_enabled = True`

### "Insufficient permissions"
- **Cause**: AWS IAM permissions are missing
- **Solution**: Add required Bedrock permissions to IAM role

## Performance Optimization

### For Daily Meetings (Speed Priority)

```python
config = ProductionMeetingConfig(
    default_model='us.anthropic.claude-3-5-haiku-20241022-v1:0',
    analysis_depth='standard',
    quick_briefing_timeout=20,
    max_query_steps=3,
    max_concurrent_agents=2
)
```

### For Detailed Analysis (Quality Priority)

```python
config = ProductionMeetingConfig(
    default_model='us.anthropic.claude-sonnet-4-20250514-v1:0',
    analysis_depth='comprehensive',
    detailed_analysis_timeout=300,
    max_query_steps=7,
    enable_proactive_insights=True
)
```

### For Resource-Constrained Environments

```python
config = ProductionMeetingConfig(
    default_model='us.amazon.nova-lite-v1:0',
    max_concurrent_agents=1,
    timeout_seconds=60,
    enable_progress_updates=False
)
```

## Getting Help

### Debug Information Collection

When reporting issues, include this debug information:

```python
import sys
import platform
from app_factory.production_meeting_agents.config import default_config

print("=== Debug Information ===")
print(f"Python version: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"Agent enabled: {default_config.agent_enabled}")
print(f"Default model: {default_config.default_model}")
print(f"Meeting focus: {default_config.meeting_focus}")
print(f"Analysis depth: {default_config.analysis_depth}")

# Test agent manager
try:
    from app_factory.production_meeting_agents.agent_manager import ProductionMeetingAgentManager
    manager = ProductionMeetingAgentManager(default_config)
    print(f"Agent manager ready: {manager.is_ready()}")
    print(f"Agent status: {manager.get_agent_status()}")
except Exception as e:
    print(f"Agent manager error: {e}")
```

### Log Collection

Enable detailed logging for troubleshooting:

```python
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('production_meeting_agents.log'),
        logging.StreamHandler()
    ]
)

# Run your application with detailed logs
```

### Support Resources

- **Documentation**: This configuration guide
- **Examples**: See `app_factory/mes_agents/` for similar patterns
- **Code**: Review `app_factory/production_meeting_agents/` implementation
- **Database**: Use `text-to-sql-notebook.ipynb` for database exploration