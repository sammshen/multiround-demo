# Scripts Inside the Folder

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

