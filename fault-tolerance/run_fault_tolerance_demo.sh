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
chmod +x fault_tolerance_demo.py

# Function to demonstrate Production Stack fault tolerance
demo_production_stack() {
  echo "===== Production Stack Fault Tolerance Demo ====="
  echo "This demo will:"
  echo "1. Send an initial request to the Production Stack router"
  echo "2. Automatically identify which pod is handling your session"
  echo "3. Send a longer request and kill the pod while it's processing"
  echo "4. Test if the system can recover and route your next request correctly"
  echo ""

  # Run the fault tolerance demo for Production Stack
  python3 fault_tolerance_demo.py --endpoint "http://localhost:30080/v1/chat/completions" --session-id "9999" --pod-pattern "vllm-deployment-router"
}

# Function to demonstrate Ray Serve fault tolerance
demo_ray_serve() {
  # Check Ray Serve port forwarding
  if ! check_port_forwarding 30081; then
    echo "Warning: Port forwarding not detected for Ray Serve (port 30081)."
    echo "Ray Serve tests may fail. Please ensure Ray Serve is running and accessible."
    read -p "Do you want to continue anyway? (y/n): " continue_anyway
    if [[ "$continue_anyway" != "y" ]]; then
      echo "Exiting. Please start Ray Serve and try again."
      exit 0
    fi
  fi

  echo "===== Ray Serve Fault Tolerance Demo ====="
  echo "This demo will:"
  echo "1. Send an initial request to Ray Serve"
  echo "2. Automatically identify which pod is handling your session"
  echo "3. Send a longer request and kill the pod while it's processing"
  echo "4. Test if the system can recover and route your next request correctly"
  echo ""

  # For Ray Serve, we need to use a different pattern to identify workers
  # You might need to adjust this based on how Ray Serve workers are named
  python3 fault_tolerance_demo.py --endpoint "http://localhost:30081/v1/chat/completions" --session-id "9999" --pod-pattern "ray-"
}

# Main menu
echo "Fault Tolerance Demo Script"
echo "==========================="
echo "1. Demo Production Stack fault tolerance"
echo "2. Demo Ray Serve fault tolerance"
echo "3. Exit"
echo ""
read -p "Enter your choice (1-3): " choice

case $choice in
  1)
    demo_production_stack
    ;;
  2)
    demo_ray_serve
    ;;
  3)
    echo "Exiting..."
    exit 0
    ;;
  *)
    echo "Invalid choice. Exiting."
    exit 1
    ;;
esac