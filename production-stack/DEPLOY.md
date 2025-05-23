# Deployment

Run `minikube-setup/install-local-minikube.sh`

Substitute your `hf_token` and desired `modelURL` in `multi-llama8B.yaml`
Modify the number of replicas and lmcache CPU offloading memory you want in `multi-llama8B.yaml`

Change which GPU Devices you want to use when running:

```bash
CUDA_VISIBLE_DEVICES=1,2 ./helm-deploy.sh
```

Test that the router is up:
```bash
curl http://localhost:30080/v1/chat/completions   -H "Content-Type: application/json"   -H "Authorization: Bearer $HF_TOKEN"   -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "messages": [
      {"role": "user", "content": "What is the capital of France?"}
    ],
    "max_tokens": 50,
    "temperature": 0.7
  }'
```

Once you're done:
```bash
helm uninstall vllm
```

# Manual Deployment

```bash
export HF_TOKEN=<YOUR_HF_TOKEN>
sudo chown -R $USER ~/.cache/huggingface
```


`start_engines.sh` will set up *four* Llama 8B vllm instances with LMCache (200 GB CPU Offloading each) on ports 8000-8003 (inclusive) using GPUs 4-7 (inclusive) on your machine.


Test them with:


```bash
PORT=8000 # or 8001, 8002, 8003
curl http://localhost:$PORT/v1/chat/completions   -H "Content-Type: application/json"   -H "Authorization: Bearer $HF_TOKEN"   -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "messages": [
      {"role": "user", "content": "What is the capital of France?"}
    ],
    "max_tokens": 50,
    "temperature": 0.7
  }'
```


#! /bin/bash

# node:
# --gpus all tells Docker to make all GPUs available to the container
# --env "CUDA_VISIBLE_DEVICES=4" controls which GPUs are visible inside the container

HF_TOKEN=<YOUR_HF_TOKEN>

echo "Starting engine on GPU 4 (port 8100)..."
IMAGE=lmcache/vllm-openai:2025-05-17-v1 && \
docker run --runtime=nvidia --gpus all \
  --env "HF_TOKEN=$HF_TOKEN" \
  --env "LMCACHE_USE_EXPERIMENTAL=True" \
  --env "LMCACHE_CHUNK_SIZE=256" \
  --env "LMCACHE_LOCAL_CPU=True" \
  --env "LMCACHE_MAX_LOCAL_CPU_SIZE=200" \
  --env "CUDA_VISIBLE_DEVICES=4" \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --network host \
  $IMAGE \
  meta-llama/Llama-3.1-8B-Instruct \
  --max-model-len 32768 \
  --port 8100 \
  --kv-transfer-config '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}' &

echo "Starting engine on GPU 5 (port 8101)..."
IMAGE=lmcache/vllm-openai:2025-05-17-v1 && \
docker run --runtime=nvidia --gpus all \
  --env "HF_TOKEN=$HF_TOKEN" \
  --env "LMCACHE_USE_EXPERIMENTAL=True" \
  --env "LMCACHE_CHUNK_SIZE=256" \
  --env "LMCACHE_LOCAL_CPU=True" \
  --env "LMCACHE_MAX_LOCAL_CPU_SIZE=200" \
  --env "CUDA_VISIBLE_DEVICES=5" \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --network host \
  $IMAGE \
  meta-llama/Llama-3.1-8B-Instruct \
  --max-model-len 32768 \
  --port 8101 \
  --kv-transfer-config '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}' &

echo "Starting engine on GPU 6 (port 8102)..."
IMAGE=lmcache/vllm-openai:2025-05-17-v1 && \
docker run --runtime=nvidia --gpus all \
  --env "HF_TOKEN=$HF_TOKEN" \
  --env "LMCACHE_USE_EXPERIMENTAL=True" \
  --env "LMCACHE_CHUNK_SIZE=256" \
  --env "LMCACHE_LOCAL_CPU=True" \
  --env "LMCACHE_MAX_LOCAL_CPU_SIZE=200" \
  --env "CUDA_VISIBLE_DEVICES=6" \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --network host \
  $IMAGE \
  meta-llama/Llama-3.1-8B-Instruct \
  --max-model-len 32768 \
  --port 8102 \
  --kv-transfer-config '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}' &

echo "Starting engine on GPU 7 (port 8103)..."
IMAGE=lmcache/vllm-openai:2025-05-17-v1 && \
docker run --runtime=nvidia --gpus all \
  --env "HF_TOKEN=$HF_TOKEN" \
  --env "LMCACHE_USE_EXPERIMENTAL=True" \
  --env "LMCACHE_CHUNK_SIZE=256" \
  --env "LMCACHE_LOCAL_CPU=True" \
  --env "LMCACHE_MAX_LOCAL_CPU_SIZE=200" \
  --env "CUDA_VISIBLE_DEVICES=7" \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --network host \
  $IMAGE \
  meta-llama/Llama-3.1-8B-Instruct \
  --max-model-len 32768 \
  --port 8103 \
  --kv-transfer-config '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}' &

echo "Waiting for engines to initialize..."

# Function to check if an endpoint is ready
check_endpoint() {
  local port=$1

  while true; do
    if curl -s http://localhost:$port/v1/models &>/dev/null; then
      echo "Engine on port $port is ready!"
      return 0
    fi

    sleep 10
  done
}

# Check all endpoints in parallel
check_endpoint 8100 &
check_endpoint 8101 &
check_endpoint 8102 &
check_endpoint 8103 &

# Wait for all health check processes to complete
wait

echo "All engines have been started and verified."
echo "To view logs for a specific container, use 'docker logs CONTAINER_ID'"


IMAGE=lmcache/fault_tolerance_router:latest
docker run $IMAGE vllm-router \
    --port 30080 \
    --service-discovery static \
    --static-backends "http://localhost:8100" \
    --static-models "meta-llama/Llama-3.1-70B-Instruct" \
    --engine-stats-interval 10 \
    --log-stats \
    --routing-logic roundrobin




IMAGE=lmcache/vllm-openai:2025-05-17-v1 && \
docker run --runtime=nvidia --gpus all \
  --env "HF_TOKEN=$HF_TOKEN" \
  --env "LMCACHE_USE_EXPERIMENTAL=True" \
  --env "LMCACHE_CHUNK_SIZE=256" \
  --env "LMCACHE_LOCAL_CPU=True" \
  --env "LMCACHE_MAX_LOCAL_CPU_SIZE=200" \
  --env "CUDA_VISIBLE_DEVICES=0" \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --network host \
  $IMAGE \
  meta-llama/Llama-3.1-8B-Instruct \
  --max-model-len 32768 \
  --port 8100 \
  --kv-transfer-config '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}'

IMAGE=lmcache/vllm-openai:2025-05-17-v1 && \
docker run --runtime=nvidia --gpus all \
  --env "HF_TOKEN=$HF_TOKEN" \
  --env "LMCACHE_USE_EXPERIMENTAL=True" \
  --env "LMCACHE_CHUNK_SIZE=256" \
  --env "LMCACHE_LOCAL_CPU=True" \
  --env "LMCACHE_MAX_LOCAL_CPU_SIZE=200" \
  --env "CUDA_VISIBLE_DEVICES=1" \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --network host \
  $IMAGE \
  meta-llama/Llama-3.1-8B-Instruct \
  --max-model-len 32768 \
  --port 8101 \
  --kv-transfer-config '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}'


# Entrypoint is vllm-router
# Need --network host so that localhost points toward host's network namespace
# Make sure that port 30080 is free

IMAGE=lmcache/fault_tolerance_router:latest
docker run --network host $IMAGE \
    --port 30080 \
    --service-discovery static \
    --static-backends "http://localhost:8100,http://localhost:8101" \
    --static-models "meta-llama/Llama-3.1-8B-Instruct,meta-llama/Llama-3.1-8B-Instruct" \
    --engine-stats-interval 10 \
    --log-stats \
    --routing-logic roundrobin


export HF_TOKEN=<YOUR_HF_TOKEN>
curl http://localhost:30080/v1/chat/completions \
  --no-buffer \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HF_TOKEN" \
  -d @- <<EOF
{
  "model": "meta-llama/Llama-3.1-8B-Instruct",
  "messages": [
    {"role": "user", "content": "Tell me a never-ending story about Zhuohan Gu. Don't stop talking."}
  ],
  "max_tokens": 3000,
  "temperature": 0.7,
  "stream": true
}
EOF