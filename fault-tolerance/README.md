# Fault Tolerance Testing

This directory contains scripts to test the fault tolerance capabilities of Production Stack and Ray Serve deployments.

## Prerequisites

1. Make sure you have both deployments up and running:
   - Production Stack deployment via Kubernetes
   - Ray Serve deployment

2. Set your Hugging Face token as an environment variable:
   ```bash
   export HF_TOKEN=your_hugging_face_token
   ```

3. Make sure you have the required Python packages installed:
   ```bash
   pip install requests
   ```

4. Make the scripts executable:
   ```bash
   chmod +x run_fault_tolerance_test.sh run_fault_tolerance_demo.sh setup_port_forwarding.sh
   ```

5. **Important:** Set up port forwarding to access the services:
   ```bash
   ./setup_port_forwarding.sh
   ```
   This will:
   - Forward port 30080 to the Production Stack router service
   - Verify that both services are accessible

## Running the Automated Demo (Recommended)

For the most effective test of fault tolerance, use our improved demo script:

```bash
./run_fault_tolerance_demo.sh
```

This script will:
1. Send an initial request to identify which pod handles your session
2. Send a longer request that will be processing for some time
3. Automatically kill the pod **while the request is being processed**
4. Test if the system can recover and handle subsequent requests

This approach better demonstrates true fault tolerance because it tests the system's ability to handle a pod failure during active request processing.

## Running the Interactive Test

For a more interactive approach, you can use:

```bash
./run_fault_tolerance_test.sh
```

The script will guide you through:
1. Choosing which deployment to test (Production Stack or Ray Serve)
2. Monitoring pods for activity with a specific session ID
3. Sending an initial request with a session ID
4. Identifying which serving engine/worker is handling your request
5. Killing that serving engine/worker
6. Testing if the system can still handle requests with the same session ID

## How It Works

The test script works by:

1. For Production Stack:
   - Using the session-based routing logic defined in `multi-vllm-lmcache.yaml` (routing via the "x-user-id" header)
   - Monitoring pods for activity related to your session ID
   - Identifying which serving engine pod is handling requests for a specific session ID
   - Killing that pod to see if another pod can take over

2. For Ray Serve:
   - Sending a request to Ray Serve
   - Monitoring Ray workers for activity related to your session ID
   - Identifying which Ray worker is handling the request
   - Killing that worker to see how Ray Serve handles the failover

## Tools Included

### Fault Tolerance Demo (`fault_tolerance_demo.py`)

Our newest and most recommended tool for testing fault tolerance:
- Automatically identifies which pod is handling your session
- Sends a long-running request and kills the pod while the request is in progress
- Tests the true fault tolerance capabilities of the system under active load
- Requires minimal user intervention

You can run this tool separately if needed:
```bash
python3 fault_tolerance_demo.py --endpoint "http://localhost:30080/v1/chat/completions" --session-id "9999" --pod-pattern "vllm-deployment-router"
```

### Pod Log Monitor (`pod_log_monitor.py`)

This tool helps identify which pod is handling requests for a specific session ID by:
- Monitoring logs from all pods matching a pattern (e.g., "vllm-" for Production Stack)
- Detecting when logs contain the specified session ID
- Highlighting activity in real-time

You can run this tool separately if needed:
```bash
python3 pod_log_monitor.py --pod-pattern "vllm-" --session-id "9999"
```

Options:
- `--pod-pattern`: Pattern to match pod names (default: "vllm-")
- `--session-id`: Session ID to look for in logs (default: "9999")
- `--duration`: Duration to monitor in seconds, 0 means indefinitely (default: 0)

### Fault Tolerance Test (`test_fault_tolerance.py`)

This script:
- Sends requests to the specified endpoint with a session ID
- Helps identify which pod is handling the request
- Guides you through killing that pod
- Tests if the system can still handle requests for the same session ID

You can run this tool separately if needed:
```bash
python3 test_fault_tolerance.py --endpoint "http://localhost:30080/v1/chat/completions" --session-id "9999"
```

### Port Forwarding Setup (`setup_port_forwarding.sh`)

This script:
- Sets up port forwarding from localhost:30080 to the Kubernetes vllm-router-service
- Verifies that both Production Stack and Ray Serve endpoints are accessible
- Runs the port forwarding in the background so tests can access the services

## Expected Results

- **Production Stack**: Should maintain session state and properly route requests even after a serving engine failure due to its fault-tolerant architecture. The automated demo should show how it handles a failure during active processing.
- **Ray Serve**: Will show how Ray Serve handles failures in comparison, particularly during active request processing.

## Troubleshooting

If you have issues:

1. Make sure both deployments are running:
   ```bash
   kubectl get pods  # For Production Stack
   ray status       # For Ray Serve
   ```

2. Check that port forwarding is active:
   ```bash
   lsof -i :30080  # For Production Stack
   lsof -i :30081  # For Ray Serve
   ```
   If not active, run `./setup_port_forwarding.sh` again.

3. Check that your HF_TOKEN is set correctly and has access to the Llama model

4. Check the logs of the pods/workers for any errors:
   ```bash
   kubectl logs <pod-name>
   ```

5. If the pod log monitor isn't detecting activity, try adjusting the pod pattern:
   ```bash
   kubectl get pods  # Look at the actual pod names to determine the right pattern
   ```

6. If you're having trouble with the automated demo, try the interactive test instead to manually identify which pod is handling your requests