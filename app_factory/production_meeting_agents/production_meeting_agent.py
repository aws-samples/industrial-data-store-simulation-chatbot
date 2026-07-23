"""
Production Meeting Agents (Strands SDK, agents-as-tools pattern).

An orchestrator agent routes daily-meeting queries to four specialist agents
(production, quality, equipment, inventory), each exposed as a @tool. The
orchestrator's LLM does the routing — no keyword classification needed.

Specialist agents are cached at module level: these run in batch/scheduler
contexts (single-process, no per-user sessions), so reuse across calls saves
agent construction and lets Bedrock prompt caching work across analyses.

For typed daily-briefing output, use generate_executive_summary(), which
returns a validated ExecutiveSummary via Strands structured output.
"""

import logging
from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field
from strands import Agent, tool
from strands.models import BedrockModel

from .config import ProductionMeetingConfig, default_config
from .tools.database_tools import run_sqlite_query, get_database_schema, get_production_context
from .tools.visualization_tools import create_intelligent_visualization

logger = logging.getLogger(__name__)

_config = default_config

SPECIALIST_TOOLS = [run_sqlite_query, get_database_schema, get_production_context]

SPECIALIST_PROMPT_TEMPLATE = """You are a {domain} Analysis Agent for e-bike manufacturing daily meetings.

FOCUS: {focus}

RESPONSE REQUIREMENTS:
- Maximum 3-5 bullet points
- Lead with the most critical issue first
- Include specific numbers only where essential
- Skip explanations - just state findings and recommendations
- Total response should be readable in 15 seconds

RESPONSE STYLE: Ultra-concise, data-driven insights. No introductions or conclusions."""

_SPECIALISTS = {
    'production': {
        'domain': 'Production',
        'focus': 'Work order completion, production throughput, bottleneck identification, and shift performance.',
        'tables': 'WorkOrders, Machines, and related tables',
    },
    'quality': {
        'domain': 'Quality',
        'focus': 'Defect rates, yield analysis, quality control results, and root cause identification.',
        'tables': 'QualityControl and related tables',
    },
    'equipment': {
        'domain': 'Equipment',
        'focus': 'OEE metrics (Availability, Performance, Quality), machine status, downtime analysis, and maintenance needs.',
        'tables': 'Machines, OEE, Downtimes tables',
    },
    'inventory': {
        'domain': 'Inventory',
        'focus': 'Stock levels, material shortages, reorder alerts, and consumption patterns.',
        'tables': 'Inventory, Suppliers, MaterialConsumption tables',
    },
}

_agent_cache: dict = {}


def _make_model() -> BedrockModel:
    return BedrockModel(
        model_id=_config.default_model,
        max_tokens=_config.max_tokens,
    )


def _get_specialist_agent(key: str) -> Agent:
    """Get or create a cached specialist agent."""
    if key not in _agent_cache:
        spec = _SPECIALISTS[key]
        _agent_cache[key] = Agent(
            system_prompt=SPECIALIST_PROMPT_TEMPLATE.format(
                domain=spec['domain'], focus=spec['focus']
            ),
            tools=SPECIALIST_TOOLS,
            model=_make_model(),
        )
    return _agent_cache[key]


def reset_agents():
    """Clear cached agents (e.g. after a model config change)."""
    _agent_cache.clear()


def _run_specialist(key: str, query: str) -> str:
    """Run a specialist agent and return its text response."""
    spec = _SPECIALISTS[key]
    formatted = f"""{spec['domain']} meeting query: {query}

Use get_production_context() for timeframes, then run_sqlite_query() to get relevant data from {spec['tables']}. Provide concise, actionable insights."""
    try:
        response = _get_specialist_agent(key)(formatted)
        return str(response)
    except Exception as e:
        logger.error(f"{spec['domain']} analysis failed: {e}")
        return (
            f"{spec['domain']} analysis unavailable ({e}). "
            f"Try a simpler, more specific {key} question."
        )


@tool
def production_analysis_tool(query: str) -> str:
    """Analyze production performance: work orders, throughput, bottlenecks, shift performance.

    Args:
        query: Production analysis question or request
    """
    return _run_specialist('production', query)


@tool
def quality_analysis_tool(query: str) -> str:
    """Analyze quality metrics: defect rates, yield, QC results, root causes.

    Args:
        query: Quality analysis question or request
    """
    return _run_specialist('quality', query)


@tool
def equipment_analysis_tool(query: str) -> str:
    """Analyze equipment: OEE metrics, machine status, downtime, maintenance needs.

    Args:
        query: Equipment analysis question or request
    """
    return _run_specialist('equipment', query)


@tool
def inventory_analysis_tool(query: str) -> str:
    """Analyze inventory: stock levels, shortages, reorder alerts, consumption.

    Args:
        query: Inventory analysis question or request
    """
    return _run_specialist('inventory', query)


ORCHESTRATOR_PROMPT = """You are a Production Meeting Orchestrator for e-bike manufacturing. Provide FAST, CONCISE analysis for daily meetings.

YOUR JOB:
1. Route the query to the appropriate specialized agent tool(s)
2. Answer the SPECIFIC question asked using the agent responses
3. Focus ONLY on what was asked

TOOL ROUTING:
- production_analysis_tool, quality_analysis_tool, equipment_analysis_tool, inventory_analysis_tool
- Call only the tools relevant to the question; for broad questions like "daily briefing", call all four in parallel

RESPONSE FORMAT:
1. **Critical Issues** (1-2 items related to the question)
2. **Key Metrics** (2-3 numbers related to the question)
3. **Actions** (1-2 recommendations related to the question)

Maximum 5-7 bullet points total. No introductions or summaries. Readable in 20 seconds."""


def _get_orchestrator_agent() -> Agent:
    if 'orchestrator' not in _agent_cache:
        _agent_cache['orchestrator'] = Agent(
            system_prompt=ORCHESTRATOR_PROMPT,
            tools=[
                production_analysis_tool,
                quality_analysis_tool,
                equipment_analysis_tool,
                inventory_analysis_tool,
                run_sqlite_query,
                get_database_schema,
                get_production_context,
                create_intelligent_visualization,
            ],
            model=_make_model(),
        )
    return _agent_cache['orchestrator']


@tool
def production_meeting_analysis_tool(query: str) -> str:
    """
    Main production meeting analysis tool that orchestrates specialized agents.

    Args:
        query: Production meeting analysis question or request

    Returns:
        Analysis results for production meetings
    """
    try:
        logger.info(f"Production meeting orchestrator processing query: {query[:100]}...")
        response = _get_orchestrator_agent()(query)
        content = str(response)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        return f"{content}\n\n---\n*Analysis generated: {timestamp}*"
    except Exception as e:
        logger.error(f"Production meeting orchestration failed: {e}")
        return (
            f'Production meeting analysis failed for: "{query}"\n\n'
            f"**Error**: {e}\n\n"
            "Try a simpler, focused question, e.g. "
            '"What is the current production status?", '
            '"What are today\'s quality issues?", '
            '"Which machines need maintenance?", '
            '"What materials are low in stock?"'
        )


# ----- Structured executive summary ----- #

class BriefingItem(BaseModel):
    """One item in the daily executive summary."""

    severity: Literal['critical', 'warning', 'good'] = Field(
        description="critical = needs action today, warning = monitor, good = positive highlight"
    )
    domain: Literal['production', 'quality', 'equipment', 'inventory'] = Field(
        description="Manufacturing domain this item belongs to"
    )
    headline: str = Field(description="One-line finding with the key number, max 15 words")
    action: str = Field(default="", description="Recommended action if any, max 12 words")


class ExecutiveSummary(BaseModel):
    """Typed daily briefing for the production meeting dashboard."""

    items: List[BriefingItem] = Field(
        description="3-6 items, most critical first", min_length=1, max_length=6
    )
    overall_status: Literal['critical', 'attention_needed', 'normal'] = Field(
        description="Overall plant status for today"
    )
    next_review: str = Field(
        default="", description="What to re-check at the next meeting, one line"
    )

    def to_markdown(self) -> str:
        """Render for dashboard display."""
        icons = {'critical': '[CRITICAL]', 'warning': '[WARNING]', 'good': '[OK]'}
        lines = [
            f"• {icons[item.severity]} **{item.domain.title()}**: {item.headline}"
            + (f" — _{item.action}_" if item.action else "")
            for item in self.items
        ]
        if self.next_review:
            lines.append(f"\n**Next review**: {self.next_review}")
        return "\n".join(lines)


def generate_executive_summary() -> ExecutiveSummary:
    """Generate a typed executive summary for the daily briefing.

    Runs the four specialist analyses via the orchestrator's tools, then uses
    Strands structured output to return a validated ExecutiveSummary — no
    post-hoc regex/emoji parsing needed.
    """
    agent = Agent(
        system_prompt=(
            "You produce the executive summary for an e-bike plant's daily production "
            "meeting. Use the four specialist analysis tools to gather current data "
            "across production, quality, equipment, and inventory, then distill the "
            "findings into the requested structure. Most critical items first."
        ),
        tools=[
            production_analysis_tool,
            quality_analysis_tool,
            equipment_analysis_tool,
            inventory_analysis_tool,
        ],
        model=_make_model(),
    )
    # Run the analysis conversationally first (tool use), then extract typed output
    agent("Gather today's status from all four specialist tools (call them in parallel).")
    return agent.structured_output(
        ExecutiveSummary,
        "Based on the analyses above, produce the executive summary.",
    )
