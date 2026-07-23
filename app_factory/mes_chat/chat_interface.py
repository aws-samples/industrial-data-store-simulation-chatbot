"""
MES Insight Chat — streaming agent interface powered by Strands Agents SDK.

Key improvements over the previous implementation:
- Per-session agent stored in st.session_state (no cross-user context bleed)
- Real-time streaming via agent.stream_async() displayed with st.status
- Plotly figures rendered inline when the viz tool produces them
- st.pills for example questions, st.feedback on answers
- No double-rerun pattern; processing happens inline
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import plotly.io as pio
import streamlit as st

from app_factory.mes_agents import (
    AgentConfig,
    create_agent,
    SUPPORTED_MODELS,
    MODEL_DISPLAY_NAMES,
)

logger = logging.getLogger(__name__)

# ----- Helpers ----- #

def _load_example_questions() -> dict:
    """Load categorized example questions from JSON."""
    try:
        questions_path = Path(__file__).parent.parent / 'data' / 'sample_questions.json'
        if not questions_path.exists():
            questions_path = Path(__file__).parent.parent.parent / 'sample_questions.json'
        with open(questions_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _get_or_create_agent() -> Any:
    """Get the per-session agent, creating one if needed."""
    if 'mes_agent' not in st.session_state:
        config = st.session_state.get('mes_config', AgentConfig())
        st.session_state.mes_agent = create_agent(config)
        st.session_state.mes_agent_model = config.default_model
    return st.session_state.mes_agent


def _reset_agent():
    """Create a fresh agent (new conversation)."""
    st.session_state.pop('mes_agent', None)
    st.session_state.pop('mes_agent_model', None)


def _reset_chat():
    """Clear chat history and agent."""
    st.session_state.mes_messages = [
        {"role": "assistant", "content": "Welcome to MES Insight Chat! I'm your manufacturing analyst. Ask me about production, quality, equipment, or inventory."}
    ]
    _reset_agent()


async def _stream_agent_response(agent, query: str, status_container):
    """Stream agent response, updating status container with tool calls and collecting text."""
    text_chunks: list[str] = []
    plotly_figures: list[str] = []
    current_tool: str | None = None

    async for event in agent.stream_async(query):
        # Text delta
        if 'data' in event:
            text_chunks.append(event['data'])

        # Tool invocation start
        if 'current_tool_use' in event:
            tool_info = event['current_tool_use']
            tool_name = tool_info.get('name', '')
            if tool_name and tool_name != current_tool:
                current_tool = tool_name
                status_container.update(label=f"Running tool: {tool_name}...")

        # Check for plotly_json in tool_stream_event or result
        if 'tool_result' in event:
            result = event['tool_result']
            if isinstance(result, dict) and result.get('plotly_json'):
                plotly_figures.append(result['plotly_json'])

    return ''.join(text_chunks), plotly_figures


# ----- Main UI ----- #

def run_mes_chat():
    """Main MES Chat interface."""
    st.header("🤖 MES Insight Chat")

    # Session state init
    if 'mes_messages' not in st.session_state:
        _reset_chat()
    if 'mes_config' not in st.session_state:
        st.session_state.mes_config = AgentConfig()

    # Handoff from the Production Meeting dashboard (Investigate buttons,
    # follow-up suggestions): queue the question as if the user typed it
    if st.session_state.get('switch_to_chat'):
        handoff_query = st.session_state.pop('switch_to_chat')
        st.session_state.mes_messages.append({"role": "user", "content": handoff_query})
        st.session_state._process_query = handoff_query

    # ----- Sidebar ----- #
    with st.sidebar:
        st.subheader("⚙️ Settings")
        st.button("🔄 New Conversation", on_click=_reset_chat, use_container_width=True)
        if st.button("🏠 Main Menu", use_container_width=True):
            st.session_state.app_mode = None
            st.rerun()

        st.divider()

        # Model picker
        current_config = st.session_state.mes_config
        model_idx = SUPPORTED_MODELS.index(current_config.default_model) if current_config.default_model in SUPPORTED_MODELS else 0
        selected_model = st.selectbox(
            "Model",
            SUPPORTED_MODELS,
            index=model_idx,
            format_func=lambda m: MODEL_DISPLAY_NAMES.get(m, m),
        )
        if selected_model != current_config.default_model:
            current_config.default_model = selected_model
            _reset_agent()

        analysis_depth = st.selectbox(
            "Analysis Depth",
            ['standard', 'comprehensive'],
            index=0 if current_config.analysis_depth == 'standard' else 1,
        )
        current_config.analysis_depth = analysis_depth

        st.divider()
        with st.expander("ℹ️ About"):
            st.markdown("""
            - **Streaming** real-time analysis with tool visibility
            - **Per-session** isolated conversations
            - **Multi-domain** production, quality, equipment, inventory
            - Uses Strands Agents SDK with Amazon Bedrock
            """)

    # ----- Example questions (shown only when conversation is fresh) ----- #
    if len(st.session_state.mes_messages) <= 1:
        question_data = _load_example_questions()
        categories = question_data.get('categories', {})
        if categories:
            all_examples = []
            for cat_questions in categories.values():
                all_examples.extend(cat_questions[:2])
            selected = st.pills(
                "Try an example question",
                all_examples[:8],
                key="example_pills",
            )
            if selected:
                st.session_state.mes_messages.append({"role": "user", "content": selected})
                st.session_state._process_query = selected
                st.rerun()

    # ----- Chat history ----- #
    for i, msg in enumerate(st.session_state.mes_messages):
        with st.chat_message(msg["role"]):
            content = msg["content"]
            if isinstance(content, str):
                st.markdown(content)
            # Render stored plotly figures
            if msg.get("figures"):
                for fig_json in msg["figures"]:
                    fig = pio.from_json(fig_json)
                    st.plotly_chart(fig, use_container_width=True)
            # Feedback widget on assistant messages (skip welcome)
            if msg["role"] == "assistant" and i > 0:
                st.feedback("thumbs", key=f"fb_{i}")

    # ----- Chat input ----- #
    user_input = st.chat_input("Ask about your manufacturing data...")
    query_to_process = None

    if user_input:
        st.session_state.mes_messages.append({"role": "user", "content": user_input})
        query_to_process = user_input
    elif st.session_state.get('_process_query'):
        query_to_process = st.session_state.pop('_process_query')

    if query_to_process:
        # Show user message immediately
        with st.chat_message("user"):
            st.markdown(query_to_process)

        # Stream assistant response
        with st.chat_message("assistant"):
            agent = _get_or_create_agent()
            with st.status("Analyzing...", expanded=True) as status:
                try:
                    response_text, figures = asyncio.run(
                        _stream_agent_response(agent, query_to_process, status)
                    )
                    status.update(label="Done", state="complete", expanded=False)
                except Exception as e:
                    logger.error(f"Agent error: {e}")
                    response_text = f"I encountered an error: {e}\n\nPlease try rephrasing your question or starting a new conversation."
                    figures = []
                    status.update(label="Error", state="error")

            # Render response
            st.markdown(response_text)
            for fig_json in figures:
                fig = pio.from_json(fig_json)
                st.plotly_chart(fig, use_container_width=True)

            st.feedback("thumbs", key=f"fb_latest")

        # Store in history
        st.session_state.mes_messages.append({
            "role": "assistant",
            "content": response_text,
            "figures": figures,
        })
