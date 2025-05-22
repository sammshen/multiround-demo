# Kubernetes Fault Tolerance Demo

This folder contains the necessary scripts to test the fault tolerance capabilities of a vLLM Production Stack deployment running on Kubernetes.

## Prerequisites

1. A running Kubernetes cluster with the vLLM Production Stack deployed
2. `kubectl` installed and configured to access your cluster
3. Python 3 installed

## Running the Demo

To run the fault tolerance demonstration, simply execute:

```bash
./prod_fault_tolerance_demo.sh
```

This script will:

1. Check if the necessary vLLM services are running
2. Set up port forwarding to access the router service
3. Send a test request to identify which pod is handling your session
4. Send a longer request that will be processing for some time
5. Kill the pod **while the request is being processed**
6. Test if the system can recover and handle subsequent requests

## API Types

You can specify which API type to use:

```bash
./prod_fault_tolerance_demo.sh chat      # For chat completions API (default)
./prod_fault_tolerance_demo.sh completion # For completions API
```

## How It Works

The demo script works by:

1. Using the session-based routing logic defined in the Production Stack
2. Monitoring pods for activity related to a specific session ID
3. Identifying which serving engine pod is handling requests for that session
4. Killing that pod to see if another pod can take over
5. Verifying that the system maintains continuity even during failures

## Interpreting Results

At the end of the test, you'll see one of these messages:

- **✅ FAULT TOLERANCE SUCCESS**: The request completed successfully despite the pod being killed. This means the system properly failed over to another pod.

- **❌ FAULT TOLERANCE FAILED**: The request did not complete after the pod was killed. This means the system did not properly handle the failover.

## Troubleshooting

If the fault tolerance test fails:

1. Make sure you have at least 2 serving engine pods running:
   ```bash
   kubectl get pods | grep engine
   ```

2. Check that port forwarding is active:
   ```bash
   lsof -i :30080
   ```

3. Check the router logs to see how it's handling session routing:
   ```bash
   kubectl logs $(kubectl get pods | grep router | awk '{print $1}') | grep session
   ```

4. If the script has trouble identifying the correct pod:
   - Try modifying the `k8s_fault_demo.py` file to manually specify a serving engine pod
   - Check that your router service is properly configured for session-based routing

5. If you see failures consistently, examine your Production Stack configuration to ensure it's set up for proper fault tolerance with session persistence
