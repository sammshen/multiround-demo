#!/bin/bash
set -e

# Default to chat API if not specified
API_TYPE=${1:-chat}

if [[ "$API_TYPE" != "chat" && "$API_TYPE" != "completion" ]]; then
  echo "Invalid API type. Must be either 'chat' or 'completion'."
  echo "Usage: ./prod_fault_tolerance_demo.sh [chat|completion]"
  exit 1
fi

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
  echo "kubectl could not be found. Please install kubectl and configure it."
  exit 1
fi

# Verify that the vLLM router service exists
ROUTER_SERVICE=$(kubectl get svc | grep "vllm.*router" | awk '{print $1}')
if [ -z "$ROUTER_SERVICE" ]; then
  echo "vLLM router service not found. Make sure you've deployed the Production Stack."
  echo "Available services:"
  kubectl get svc
  echo "See production-stack/helm-deploy.sh for deployment instructions."
  exit 1
fi
echo "Found router service: $ROUTER_SERVICE"

# Check if Python and required packages are installed
if ! command -v python3 &> /dev/null; then
  echo "Python 3 is not installed. Please install Python 3."
  exit 1
fi

# Install required packages
echo "Installing required Python packages..."
pip install openai requests kubernetes

# Check if port forwarding is already active
if ! lsof -i :30080 > /dev/null 2>&1; then
  echo "Setting up port forwarding for vLLM router service..."
  kubectl port-forward svc/$ROUTER_SERVICE 30080:80 &
  PORT_FORWARD_PID=$!

  # Give it more time to establish
  echo "Waiting for port forwarding to stabilize..."
  sleep 5

  # Verify port forwarding is working
  if ! lsof -i :30080 > /dev/null 2>&1; then
    echo "Failed to set up port forwarding. Please check your connection to the cluster."
    if [ -n "$PORT_FORWARD_PID" ]; then
      kill $PORT_FORWARD_PID 2>/dev/null || true
    fi
    exit 1
  fi

  echo "Port forwarding active (PID: $PORT_FORWARD_PID)"
else
  echo "Port forwarding already active for port 30080"
  PORT_FORWARD_PID=""
fi

# Make sure we clean up port forwarding on exit
cleanup() {
  if [ -n "$PORT_FORWARD_PID" ]; then
    echo "Stopping port forwarding (PID: $PORT_FORWARD_PID)..."
    kill $PORT_FORWARD_PID 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# Verify serving engine pods are running
echo "Checking for vLLM serving engine pods..."
SERVING_PODS=$(kubectl get pods | grep "vllm-.*engine.*" | wc -l)
if [ "$SERVING_PODS" -lt "1" ]; then
  echo "No vLLM serving engine pods found. Make sure your deployment is running."
  echo "Available pods:"
  kubectl get pods
  exit 1
fi

echo "Found $SERVING_PODS serving engine pods running"
echo "Starting Production Stack fault tolerance demonstration using $API_TYPE API..."

# Wait a moment for everything to be ready
sleep 2

# Run the demo script
python3 k8s_fault_demo.py $API_TYPE

echo "Demo completed!"