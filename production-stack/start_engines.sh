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
