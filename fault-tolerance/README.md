# Production Stack Fault Tolerance Demo

This directory contains a demonstration of the fault tolerance capabilities of Production Stack with vLLM and LMCache when running in Kubernetes.

## What This Demo Shows

When a serving engine pod is killed during a request, the Production Stack router automatically redirects the request to another healthy serving engine, ensuring uninterrupted service. This is a key advantage over traditional LLM serving architectures that don't offer this fault tolerance.

## Files in This Directory

- `k8s_fault_demo.py`: The main Python script that conducts the fault tolerance test by sending requests and killing pods
- `prod_fault_tolerance_demo.sh`: A wrapper shell script that sets up the environment and calls `k8s_fault_demo.py`
- `pod_log_monitor.py`: A utility Python script for monitoring pod logs to identify which pod is processing requests

## Prerequisites

1. A running Kubernetes cluster with Production Stack deployed (see `production-stack/helm-deploy.sh`)
2. `kubectl` configured to access your cluster
3. Python 3 installed on your system

## Running the Demo

There are two ways to run the demo:

### Option 1: Using the Shell Script (Recommended)

This sets up everything automatically:

```bash
chmod +x prod_fault_tolerance_demo.sh
./prod_fault_tolerance_demo.sh
```

By default, this uses the chat completions API. For completions API:

```bash
./prod_fault_tolerance_demo.sh completion
```

The shell script will:
1. Verify prerequisites (kubectl, router service)
2. Install required Python packages (`openai`, `requests`, `kubernetes`)
3. Set up port forwarding if needed
4. Run the actual fault tolerance demo by calling `k8s_fault_demo.py`

### Option 2: Running the Python Script Directly

If you've already set up port forwarding and installed requirements, you can run:

```bash
python3 k8s_fault_demo.py  # For chat API (default)
python3 k8s_fault_demo.py completion  # For completions API
```

## How the Demo Works

The `k8s_fault_demo.py` script:

1. Determines which model is being used by examining the deployment
2. Sends a test request with user ID "9999" to identify which pod handles this session
3. Examines router logs to determine which pod is processing requests for this session
4. Sends a long-running generation request (a 500-word essay) using the same user ID
5. After 5 seconds of token generation, kills the serving engine pod that's handling the request
6. Monitors token generation before and after the pod kill
7. Reports success if token generation continues after the pod is killed

The key test is whether tokens continue to be generated after the pod is killed. If they do, it demonstrates that the Production Stack router successfully detected the failure and routed the request to another pod.

## Using the Pod Log Monitor

The `pod_log_monitor.py` script is a standalone utility that can help you monitor which pods are handling requests. It's not required for the main demo but can be useful for debugging:

```bash
python3 pod_log_monitor.py --pod-pattern "vllm-" --session-id "9999"
```

Options:
- `--pod-pattern`: Pattern to match pod names (default: "vllm-")
- `--session-id`: Session ID to look for in logs (default: "9999")
- `--duration`: Duration to monitor in seconds, 0 means indefinitely (default: 0)

## Expected Results

A successful demonstration will show:
- Tokens being generated before the pod is killed
- A seamless continuation of token generation after the pod is killed
- A confirmation message: "✅ FAULT TOLERANCE SUCCESS: Response completed successfully despite pod failure!"
- Statistics about tokens received before and after the pod was killed

## Troubleshooting

If you have issues:

1. Make sure your Kubernetes cluster is accessible:
   ```bash
   kubectl get nodes
   ```

2. Verify that the Production Stack pods are running:
   ```bash
   kubectl get pods | grep vllm
   ```

3. Check port forwarding (automatically set up by the shell script if needed):
   ```bash
   lsof -i :30080
   ```

4. Look at the router logs for routing information:
   ```bash
   kubectl logs $(kubectl get pods | grep router | awk '{print $1}')
   ```

5. If the script can't identify which pod is handling your session, it will fall back to using the first available pod