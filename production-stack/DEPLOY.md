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