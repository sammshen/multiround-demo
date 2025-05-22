import time
import os, sys
import numpy as np
import pandas as pd
import streamlit as st

# Prevent Streamlit file watcher from monitoring torch.classes
# This fixes the "no running event loop" error during hot-reloading
import streamlit.watcher.path_watcher
original_watch_file = streamlit.watcher.path_watcher.watch_file

def patched_watch_file(path, callback):
    if "torch/_classes.py" in path or "torch\\_classes.py" in path:
        return None
    return original_watch_file(path, callback)

streamlit.watcher.path_watcher.watch_file = patched_watch_file

from dual_chat_session import DualChatSession
import altair as alt
from transformers import AutoTokenizer
import conversation_generator
import threading

# Set page configuration
st.set_page_config(
    page_title="LLM Performance Comparison",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# App title
st.title("Production Stack vs Ray Serve Performance Comparison")
st.subheader("Comparing Time to First Token (TTFT) with real documentation")

# Initialize session state
if 'dual_session' not in st.session_state:
    with st.spinner("Loading documentation and initializing conversation history..."):
        st.session_state.dual_session = DualChatSession()
        st.session_state.history, st.session_state.docs = st.session_state.dual_session.initialize_with_conversation(5)
        st.session_state.ps_processing = False
        st.session_state.rs_processing = False
        st.session_state.metrics_history = []
        st.session_state.show_docs = False
        st.success("Initialization complete! Ready to start conversation.")
        # Force rerun to ensure UI is updated
        st.rerun()

# Sidebar with information
with st.sidebar:
    st.header("About This Demo")
    st.write("""
    This demo shows the performance difference between Production Stack (localhost:30080)
    and Ray Serve (localhost:30081) when processing the same queries with long context for a single user.
    **Please note that the power of Production Stack + LMCache is highlighted the most when there are many users all doing RAG at the same time.**

    Key metric to compare:
    - **TTFT**: Time to First Token (ms) - How quickly the first response appears
    """)

    st.subheader("Documentation Loaded as Context")
    if st.session_state.docs:
        st.write(f"**Documentation 1**: {st.session_state.docs['doc1']}")
        st.write(f"**Documentation 2**: {st.session_state.docs['doc2']}")
        st.write(f"**Documentation 3**: {st.session_state.docs['doc3']}")
        st.write(f"**Documentation 4**: {st.session_state.docs['doc4']}")
        st.write(f"**Documentation 5**: {st.session_state.docs['doc5']}")
        st.write(f"**Documentation 6**: {st.session_state.docs['doc6']}")
        st.write(f"**Documentation 7**: {st.session_state.docs['doc7']}")

        # Button to show/hide documentation previews
        if st.button("Show/Hide Documentation Previews"):
            st.session_state.show_docs = not st.session_state.show_docs

        if st.session_state.show_docs:
            # Create tabs for documentation
            doc_tabs = st.tabs([
                "Doc 1", "Doc 2", "Doc 3", "Doc 4", "Doc 5", "Doc 6", "Doc 7"
            ])

            with doc_tabs[0]:
                doc1_preview = st.session_state.dual_session.get_doc_preview("doc1", 500)
                st.text_area("Preview", doc1_preview, height=200)

            with doc_tabs[1]:
                doc2_preview = st.session_state.dual_session.get_doc_preview("doc2", 500)
                st.text_area("Preview", doc2_preview, height=200)

            with doc_tabs[2]:
                doc3_preview = st.session_state.dual_session.get_doc_preview("doc3", 500)
                st.text_area("Preview", doc3_preview, height=200)

            with doc_tabs[3]:
                doc4_preview = st.session_state.dual_session.get_doc_preview("doc4", 500)
                st.text_area("Preview", doc4_preview, height=200)

            with doc_tabs[4]:
                doc5_preview = st.session_state.dual_session.get_doc_preview("doc5", 500)
                st.text_area("Preview", doc5_preview, height=200)

            with doc_tabs[5]:
                doc6_preview = st.session_state.dual_session.get_doc_preview("doc6", 500)
                st.text_area("Preview", doc6_preview, height=200)

            with doc_tabs[6]:
                doc7_preview = st.session_state.dual_session.get_doc_preview("doc7", 500)
                st.text_area("Preview", doc7_preview, height=200)

    # Add a reset button
    if st.button("Reset Conversation"):
        with st.spinner("Resetting conversation and reloading documentation..."):
            # Create new session objects
            st.session_state.dual_session = DualChatSession()
            st.session_state.history, st.session_state.docs = st.session_state.dual_session.initialize_with_conversation(5)
            st.session_state.ps_processing = False
            st.session_state.rs_processing = False
            st.session_state.metrics_history = []
            st.success("Conversation reset successfully!")
            st.rerun()

# Create two columns for the chat interfaces
col1, col2 = st.columns(2)

with col1:
    st.header("Production Stack", divider="gray")
    ps_container = st.container(height=600, border=False)

with col2:
    st.header("Ray Serve", divider="gray")
    rs_container = st.container(height=600, border=False)

# Metrics comparison area
st.subheader("Performance Metrics", divider="gray")
metrics_cols = st.columns(2)

# Display metrics
latest_ps_ttft = None
latest_rs_ttft = None

# Find the latest metrics for each endpoint
# Print all history items for debugging
print("All history items:")
for i, msg in enumerate(st.session_state.history):
    if msg.get("role") == "assistant":
        print(f"  {i}. {msg.get('endpoint', 'unknown')}: " +
              f"metrics={msg.get('metrics')}, " +
              f"content_len={len(msg.get('content', ''))}")

# Now search for metrics
for msg in reversed(st.session_state.history):
    if msg.get("role") == "assistant":
        if msg.get("endpoint") == "ProductionStack" and latest_ps_ttft is None:
            metrics = msg.get("metrics", {})
            if metrics and "ttft" in metrics and metrics["ttft"] is not None:
                latest_ps_ttft = metrics["ttft"]
                print(f"Found PS TTFT: {latest_ps_ttft}")

        elif msg.get("endpoint") == "RayServe" and latest_rs_ttft is None:
            metrics = msg.get("metrics", {})
            if metrics and "ttft" in metrics and metrics["ttft"] is not None:
                latest_rs_ttft = metrics["ttft"]
                print(f"Found RS TTFT: {latest_rs_ttft}")

    if latest_ps_ttft is not None and latest_rs_ttft is not None:
        break

# Display current metrics
with metrics_cols[0]:
    if latest_ps_ttft is not None:
        st.metric("Production Stack TTFT", f"{latest_ps_ttft:.2f} ms")
    else:
        st.metric("Production Stack TTFT", "N/A")

with metrics_cols[1]:
    if latest_rs_ttft is not None:
        st.metric("Ray Serve TTFT", f"{latest_rs_ttft:.2f} ms")
    else:
        st.metric("Ray Serve TTFT", "N/A")

# Add a button to show the context information
with st.expander("About this performance test"):
    st.write("""
    ### How this performance test works:

    1. **Long Context Loading**: Seven full documentation files are loaded into both LLM engines' context windows
    2. **Massive Context Size**: The combined size of all docs is over 1.7MB of text (approximately 450,000 tokens)
    3. **Conversation History**: A 5-round conversation about the documentation is pre-loaded to both endpoints
    4. **Full Context Persistence**: All messages and documentation are sent to the backend to ensure context is preserved
    5. **Caching Benefits**: This allows the Production Stack to benefit from its context caching capabilities
    6. **Simultaneous Queries**: When you ask a question, it's sent to both endpoints at exactly the same time
    7. **User ID Tracking**: A custom x-user-id: 0 header is sent to enable user-specific optimizations
    8. **Streaming Responses**: You can watch in real-time which endpoint responds faster

    ### What to look for:

    - **Time to First Token (TTFT)**: How quickly does the first token appear? Lower is better.
    - **Overall Smoothness**: Which endpoint generates text more consistently?
    """)

# Display chart if we have metrics history
metrics_comparison = st.session_state.dual_session.get_metrics_comparison()
if metrics_comparison:
    # Create a DataFrame for the metrics history
    ttft_data = []
    for i, diff in enumerate(metrics_comparison["ttft_diff_history"]):
        ttft_data.append({"index": i, "value": diff, "metric": "TTFT Difference (ms)"})

    all_data = pd.DataFrame(ttft_data)

    if not all_data.empty:
        # Create two charts
        ttft_chart = alt.Chart(pd.DataFrame(ttft_data)).mark_line(point=True).encode(
            x=alt.X('index:O', title='Message Index'),
            y=alt.Y('value:Q', title='TTFT Difference (ms)'),
            tooltip=['index:O', 'value:Q']
        ).properties(
            title='TTFT Difference Over Time (Production Stack - Ray Serve)',
            height=200
        )

        st.altair_chart(ttft_chart, use_container_width=True)

        # Add summary statistics
        st.write(f"Average TTFT Difference: {metrics_comparison['avg_ttft_diff']:.2f} ms")

# Display the chat history
for i, message in enumerate(st.session_state.history):
    if message["role"] == "system":
        # For system messages, display them as notes at the top of both columns
        with ps_container:
            st.info(message["content"])
        with rs_container:
            st.info(message["content"])
    elif message["role"] == "user":
        with ps_container:
            st.chat_message("user").write(message["content"])
        with rs_container:
            st.chat_message("user").write(message["content"])

    elif message["role"] == "assistant":
        # Check if the message is simulated (part of the initial conversation)
        if message.get("simulated"):
            with ps_container:
                st.chat_message("assistant").write(message["content"])
            with rs_container:
                st.chat_message("assistant").write(message["content"])
        # Real responses from endpoints
        elif message.get("endpoint") == "ProductionStack":
            with ps_container:
                st.chat_message("assistant").write(message["content"])
        elif message.get("endpoint") == "RayServe":
            with rs_container:
                st.chat_message("assistant").write(message["content"])

# Create an input field that spans both columns
prompt = st.chat_input("Type your question here")

def process_user_input(prompt):
    # Mark as processing
    st.session_state.ps_processing = True
    st.session_state.rs_processing = True

    # Get the streaming generators from both sessions
    ps_stream, rs_stream, ps_metrics, rs_metrics = st.session_state.dual_session.send_message(prompt)

    # Create placeholder messages for both endpoints
    with ps_container:
        ps_placeholder = st.chat_message("assistant").empty()

    with rs_container:
        rs_placeholder = st.chat_message("assistant").empty()

    # Process both streams
    ps_message = ""
    rs_message = ""

    # Process the Production Stack stream
    for chunk in ps_stream:
        # Check if this is a metric chunk
        if chunk.startswith("<metric:"):
            print(f"Skipping metric chunk in frontend: {chunk}")
            continue

        ps_message += chunk
        ps_placeholder.markdown(ps_message + "▌")

    # Update final message
    ps_placeholder.markdown(ps_message)

    # Process the Ray Serve stream
    for chunk in rs_stream:
        # Check if this is a metric chunk
        if chunk.startswith("<metric:"):
            print(f"Skipping metric chunk in frontend: {chunk}")
            continue

        rs_message += chunk
        rs_placeholder.markdown(rs_message + "▌")

    # Update final message
    rs_placeholder.markdown(rs_message)

    # Print debug info about current metrics state
    print("Current metrics after processing:")
    for msg in reversed(st.session_state.history):
        if msg.get("role") == "assistant":
            print(f"  - {msg.get('endpoint', 'unknown')}: TTFT = {msg.get('metrics', {}).get('ttft')}")

    # Update the processing status
    st.session_state.ps_processing = False
    st.session_state.rs_processing = False

    # Force a rerun to update metrics
    st.rerun()

if prompt and not st.session_state.ps_processing and not st.session_state.rs_processing:
    process_user_input(prompt)