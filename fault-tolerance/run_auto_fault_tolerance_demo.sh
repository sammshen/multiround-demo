#!/bin/bash

# Check if HF_TOKEN is set
if [ -z "$HF_TOKEN" ]; then
  echo "Error: HF_TOKEN environment variable is not set."
  echo "Please set it by running: export HF_TOKEN=your_hugging_face_token"
  exit 1
fi

# Function to check if port forwarding is active
check_port_forwarding() {
  local port=$1
  if lsof -i :$port -t &> /dev/null; then
    return 0  # Port forwarding is active
  else
    return 1  # Port forwarding is not active
  fi
}

# Ensure port forwarding is set up
if ! check_port_forwarding 30080; then
  echo "Port forwarding not detected for Production Stack (port 30080)."
  echo "Setting up port forwarding..."

  # Check if the setup script exists
  if [ -f "./setup_port_forwarding.sh" ]; then
    ./setup_port_forwarding.sh
  else
    echo "Error: setup_port_forwarding.sh script not found."
    echo "Please run 'kubectl port-forward svc/vllm-router-service 30080:80' manually in another terminal."
    exit 1
  fi
fi

# Make the script executable
chmod +x auto_fault_tolerance_demo.py

echo "===== AUTOMATED Fault Tolerance Test ====="
echo "This script will:"
echo "1. Send an initial request to identify the session"
echo "2. Automatically identify which SERVING ENGINE pod is handling your session"
echo "3. Send a long request and kill the SERVING ENGINE (not the router) while it's processing"
echo "4. Test if the system recovers and routes to another serving engine"
echo ""
echo "This is a fully automated test that will properly test fault tolerance"
echo "by killing the serving engine, not the router."
echo ""

read -p "Press Enter to start the test..."

# Run the automated fault tolerance demo
python3 auto_fault_tolerance_demo.py