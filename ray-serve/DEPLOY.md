# Deployment

Install `requirements.txt`

Change which GPUs you want to use with the CUDA_VISIBLE_DEVICES at the top.

Change your replicas, accelerator_type, model_id, and model_source and HF_TOKEN in `ray-deploy.py`

Do not change the 30081 port for multi-round-qa.py compatibility.

Check (you can substitute "model" for what model_id you set):
```bash
curl -X POST http://localhost:30081/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer fake-key" \
     -d '{
           "model": "meta-llama/Llama-3.1-8B-Instruct",
           "messages": [{"role": "user", "content": "Hello!"}]
         }'
```