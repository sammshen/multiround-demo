# Multi-Round Chat Workload Generator

This workload generator simulates multi-round conversations between users and LLM systems, allowing for performance benchmarking under various configurations.

## Performance Monitoring

The script provides comprehensive performance monitoring through several output files:

1. **Real-time metrics**: All request metrics are written to `realtime_stats_qps_X.XX.txt` as they complete, giving you immediate visibility into performance trends.

2. **Periodic summaries**: During execution, aggregated performance summaries are saved to `performance_summary_qps_X.XX.txt` files at regular intervals.

3. **Final comprehensive summary**: At the end of the run, a `final_performance_summary_qps_X.XX.txt` file is generated containing:
   - Detailed run configuration (model, QPS, users, rounds, etc.)
   - Complete performance metrics with detailed latency statistics

## Usage Example

```bash
python multi-round-qa.py \
  --num-users 10 \
  --shared-system-prompt 100 \
  --user-history-prompt 100 \
  --answer-len 200 \
  --num-rounds 5 \
  --qps 2 \
  --model llama3 \
  --base-url http://localhost:8000 \
  --time 60 \
  --output summary.csv
```

## Parameters

- `--num-users`: Maximum number of concurrent users
- `--shared-system-prompt`: Length of shared system prompt (tokens)
- `--user-history-prompt`: Length of user-specific history prompt (tokens)
- `--answer-len`: Maximum length of model responses
- `--num-rounds`: Number of conversation rounds per user
- `--qps`: Target queries per second
- `--model`: Model to use for inference
- `--base-url`: Endpoint URL of the serving engine
- `--time`: Duration to run the simulation (seconds)
- `--output`: CSV file to save detailed results
- `--log-interval`: Time between intermediate performance summaries (seconds)
- `--sharegpt`: Use ShareGPT dataset for conversations (optional)

## Performance Metrics

The performance summary files include comprehensive metrics:

### Basic Statistics
- Number of successful requests
- Benchmark duration
- Total input and generated tokens
- Request throughput (requests/second)
- Token throughput (tokens/second)

### Latency Metrics
- **Time to First Token (TTFT)**: Mean, median, and P99 in milliseconds
- **Time per Output Token (TPOT)**: Mean, median, and P99 in milliseconds (excluding first token)
- **Inter-token Latency (ITL)**: Mean, median, and P99 in milliseconds

### Real-time Metrics
For each completed request, these metrics are recorded to the real-time stats file:
- Timestamp
- User ID and request ID
- Token counts (prompt and generation)
- TTFT, TPOT, and ITL values
- Generation speed (tokens/second)

These detailed metrics provide insights into both throughput performance and latency characteristics of the LLM serving system.