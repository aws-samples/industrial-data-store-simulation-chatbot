"""
MES Analysis Agent using Strands Agents SDK (modern API).

Key design decisions:
- NO module-global agent — each Streamlit session creates its own Agent stored
  in st.session_state, preventing cross-user context bleed behind ALB.
- stream_async() for real-time token + tool-call display in the Streamlit UI.
- BedrockModel for explicit region, max_tokens, guardrail support.
- SlidingWindowConversationManager to bound memory without manual reset.
"""

import logging
from datetime import datetime

from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.models import BedrockModel

from .config import AgentConfig, default_config
from .tools.database_tools import run_sqlite_query, get_database_schema
from .tools.visualization_tools import create_intelligent_visualization

_logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are an MES (Manufacturing Execution System) Analysis Agent for an e-bike manufacturing facility. You help users understand production performance, quality issues, equipment efficiency, and inventory management through multi-step data analysis.

**CURRENT DATE**: {current_date}

You maintain conversation context. When users ask follow-ups, build on earlier findings.

## Expertise Areas
- Production: work orders, scheduling, throughput, bottlenecks, capacity
- Quality: defect patterns, root cause, SPC, yield optimization
- Equipment: OEE, predictive maintenance, downtime analysis
- Inventory: stock optimization, demand forecasting, supplier performance

## Available Tools
1. **run_sqlite_query** — execute SQL on the MES SQLite database (read-only)
2. **get_database_schema** — retrieve table/column info
3. **create_intelligent_visualization** — generate Plotly charts

## Approach
1. Understand what the user needs
2. Query the schema if table/column names are unclear
3. Write and execute SQL to get the data
4. Synthesize results into clear insights with recommendations
5. Create a visualization when the data warrants one

Be concise and actionable. Use manufacturing terminology while remaining accessible."""


def _get_system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        current_date=datetime.now().strftime("%Y-%m-%d")
    )


def create_agent(config: AgentConfig | None = None) -> Agent:
    """Create a new MES analysis agent.

    Call this once per Streamlit session and store the result in
    st.session_state. Do NOT store at module level.
    """
    config = config or default_config

    model = BedrockModel(
        model_id=config.default_model,
        max_tokens=config.max_tokens,
    )

    agent = Agent(
        system_prompt=_get_system_prompt(),
        model=model,
        tools=[run_sqlite_query, get_database_schema, create_intelligent_visualization],
        conversation_manager=SlidingWindowConversationManager(
            window_size=40,
        ),
    )
    _logger.info(f"Created MES agent with model {config.default_model}")
    return agent
