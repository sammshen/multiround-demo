# Kubernetes Fault Tolerance Demo

This demo demonstrates the fault tolerance capabilities of Production Stack with vLLM and LMCache when running in Kubernetes.

## What this Demo Shows

When a serving engine pod is killed during a request, the Production Stack router automatically redirects the request to another healthy serving engine, ensuring uninterrupted service. This is a key advantage over traditional LLM serving architectures that don't offer this fault tolerance.

## Prerequisites

- A running Kubernetes cluster with Production Stack deployed (see `production-stack/helm-deploy.sh`)
- `kubectl` configured to access your cluster
- Python with the OpenAI package installed (`pip install openai`)

## Running the Demo

1. Make the script executable and run it:

```bash
chmod +x run_prodstack_demo.sh
./run_prodstack_demo.sh
```

The script supports both chat completions API (default) and completions API:

```bash
# For completions API instead of chat completions
./run_prodstack_demo.sh completion
```

## How It Works

1. The script sends a request with user ID "9999" to identify which pod handles this user's requests
2. It then sends a long-running generation request using the same user ID
3. While tokens are streaming, it kills the serving engine pod handling the request
4. Production Stack's router detects the failure and routes subsequent tokens to another healthy pod
5. The end user experiences a seamless response despite the backend failure

## Troubleshooting

- If log parsing fails to identify the pod, the script will attempt to use the first available serving engine pod
- Make sure the router configuration in `multi-vllm-lmcache.yaml` has `"routingLogic": "session"` and `"sessionKey": "x-user-id"`
- Check the router logs for routing information using `kubectl logs <router-pod-name>`