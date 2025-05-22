#!/bin/bash

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "kubectl could not be found. Please install kubectl first."
    exit 1
fi

# Function to check if port forwarding is already running
check_port_forwarding() {
    local port=$1
    if lsof -i :$port -t &> /dev/null; then
        echo "Port forwarding is already active on port $port"
        return 0
    else
        return 1
    fi
}

# Function to set up port forwarding for Production Stack
setup_production_stack_forwarding() {
    echo "Setting up port forwarding for Production Stack..."

    # Check if port forwarding is already active
    if check_port_forwarding 30080; then
        echo "Production Stack port forwarding is already active. Skipping."
        return
    fi

    # Start port forwarding in the background
    kubectl port-forward svc/vllm-router-service 30080:80 &

    # Save PID to a file for later cleanup
    echo $! > .production_stack_port_forwarding.pid

    echo "Production Stack port forwarding started on port 30080"
    echo "To manually stop port forwarding: kill $(cat .production_stack_port_forwarding.pid)"
}

# Function to set up port forwarding for Ray Serve (if needed)
setup_ray_serve_forwarding() {
    echo "Setting up port forwarding for Ray Serve..."

    # Check if port forwarding is already active
    if check_port_forwarding 30081; then
        echo "Ray Serve port forwarding is already active. Skipping."
        return
    fi

    # Ray Serve might already be running on this port without Kubernetes
    # Add your Ray Serve specific port forwarding command here if necessary
    echo "Ray Serve is expected to be already running on port 30081"
    echo "If you need to start Ray Serve, please refer to ray-serve/DEPLOY.md"
}

# Function to check if services are accessible
check_services() {
    echo "Checking if Production Stack is accessible..."
    if curl -s http://localhost:30080/v1/health &> /dev/null; then
        echo "✅ Production Stack is accessible at http://localhost:30080"
    else
        echo "❌ Production Stack is not accessible at http://localhost:30080"
    fi

    echo "Checking if Ray Serve is accessible..."
    if curl -s http://localhost:30081/v1/health &> /dev/null; then
        echo "✅ Ray Serve is accessible at http://localhost:30081"
    else
        echo "❌ Ray Serve is not accessible at http://localhost:30081"
    fi
}

# Main execution
echo "Setting up port forwarding for fault tolerance testing..."
setup_production_stack_forwarding
setup_ray_serve_forwarding

# Wait a moment for port forwarding to establish
sleep 2

# Check if services are accessible
check_services

echo ""
echo "Port forwarding has been set up."
echo "You can now run the fault tolerance tests."
echo ""
echo "To stop port forwarding when you're done:"
echo "  kill $(cat .production_stack_port_forwarding.pid 2>/dev/null || echo 'N/A')"