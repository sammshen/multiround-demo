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

# Make scripts executable
chmod +x test_fault_tolerance.py pod_log_monitor.py

# Function to monitor pods for a specific session ID
monitor_pods() {
  local pod_pattern=$1
  local session_id=$2

  echo "Starting pod log monitor to help identify which pod handles your session..."
  echo "This will run in the background and monitor pods matching '$pod_pattern'"
  echo ""

  # Start the pod log monitor in the background
  python3 pod_log_monitor.py --pod-pattern "$pod_pattern" --session-id "$session_id" &
  MONITOR_PID=$!

  # Save the PID for later cleanup
  echo $MONITOR_PID > .monitor_pid

  # Give the monitor a moment to start
  sleep 2
}

# Function to stop the pod monitor
stop_monitor() {
  if [ -f .monitor_pid ]; then
    MONITOR_PID=$(cat .monitor_pid)
    if ps -p $MONITOR_PID > /dev/null; then
      echo "Stopping pod log monitor..."
      kill $MONITOR_PID
    fi
    rm .monitor_pid
  fi
}

# Cleanup on exit
cleanup() {
  stop_monitor
  echo "Exiting..."
  exit 0
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Function to test Production Stack fault tolerance
test_production_stack() {
  echo "Testing Production Stack fault tolerance..."
  echo "This test will:"
  echo "1. Monitor pods for activity with a specific session ID"
  echo "2. Send a request to Production Stack"
  echo "3. Help you identify which serving engine pod is handling the request"
  echo "4. Kill that pod"
  echo "5. Test if the system can still handle requests for the same session"
  echo ""

  # Start monitoring vllm- pods for the session ID 9999
  monitor_pods "vllm-" "9999"

  # Run the fault tolerance test
  python3 test_fault_tolerance.py --endpoint "http://localhost:30080/v1/chat/completions" --session-id "9999"

  # Stop the monitor
  stop_monitor
}

# Function to test Ray Serve fault tolerance
test_ray_serve() {
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

  echo "Testing Ray Serve fault tolerance..."
  echo "This test will:"
  echo "1. Monitor Ray workers for activity with a specific session ID"
  echo "2. Send a request to Ray Serve"
  echo "3. Help you identify which Ray worker is handling the request"
  echo "4. Kill that worker"
  echo "5. Test if the system can still handle requests for the same session"
  echo ""

  # For Ray Serve, we need to use a different pattern to identify workers
  # You might need to adjust this based on how Ray Serve workers are named
  monitor_pods "ray-" "9999"

  # Run the fault tolerance test
  python3 test_fault_tolerance.py --endpoint "http://localhost:30081/v1/chat/completions" --session-id "9999"

  # Stop the monitor
  stop_monitor
}

# Main menu
echo "Fault Tolerance Test Script"
echo "=========================="
echo "1. Test Production Stack fault tolerance"
echo "2. Test Ray Serve fault tolerance"
echo "3. Exit"
echo ""
read -p "Enter your choice (1-3): " choice

case $choice in
  1)
    test_production_stack
    ;;
  2)
    test_ray_serve
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