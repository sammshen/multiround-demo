#!/bin/bash

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "Streamlit is not installed. Installing..."
    pip install streamlit pandas altair
fi

# Install other dependencies if needed
pip install openai transformers

# Run the Streamlit app
echo "Starting the LLM Performance Comparison Demo..."
echo "Comparing Production Stack (localhost:30080) with Ray Serve (localhost:30081)"
echo "Ensure both endpoints are running before proceeding."
echo ""

# Run the app
streamlit run frontend.py