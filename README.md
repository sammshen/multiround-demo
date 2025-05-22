# Overview

Demonstrate the TTFT and ITL benefits of Production Stack + LMCache in Multi-Round Long Context QA Situations.

## Example 1: Production Stack + LMCache vs Ray Serve

Compare Production Stack with Ray Serve by Running them Side-by-Side

### 1a. Setting up Production Stack (Simple Helm Deployment)

See `production-stack/DEPLOY.md`

This will yield production stack set of serving engines on `localhost:30080/v1/chat/completions`.

### 1b. Setting up RayServe (Simple Deployment)

See `ray-serve/DEPLOY.md`

This will yield ray serve set of serving engines on `localhost:30081/v1/chat/completions`

### 2. Running the Comparison Benchmark on Multi-User RAG QA

`multi-round-qa.py` script queries both endpoints simultaneously and generates comparison metrics.

To run the comparison:

Long Input (30000 tok w/ 3000 System Prompt and 30000 User Conversation History) Short Output (200 tok) is a good approximation of RAG QA.

```bash
cd workload-generator
# the "benchmark-results" is embedded into the csv filename and the 1 and 1.5 are QPS
./long_input_short_output_run.sh meta-llama/Llama-3.1-8B-Instruct benchmark-results 1 1.5
```

This will:
1. Send identical requests to both endpoints
2. Capture real-time performance metrics in `real_time_stats_{qps}.txt` files
3. Generate summary CSV files for each endpoint
4. Provide a direct comparison of key metrics (TTFT, ITL) between the two endpoints

### Analyzing Results

For each QPS value, you'll find:
- `real_time_stats_{qps}.txt`: Contains request-by-request performance data and final comparison
- `ProductionStack_benchmark-results_{qps}.csv`: Raw data for Production Stack endpoint
- `RayServe_benchmark-results_{qps}.csv`: Raw data for Ray Serve endpoint

The real-time stats file shows the differences in Time to First Token (TTFT) and Inter-token Latency (ITL) between the two endpoints, both of which are critical metrics for perceived responsiveness in multi-round QA scenarios.


### 3. Real-Time Live Interactive Demo

See `live-querying/README.md`. This will spin up a streamlit Web UI that lets you test queries
with conversation history as a single user. You will see improvement but keep in mind that the multi-user case is where Production Stack and LMCache really shine.

### 4. Fault Tolerance of Production Stack

In this section we will demonstrate the fault tolerance of production stack.

First let's send a message with session-id 9999 (user 9999) to the production stack router at 30080 and see which serving engine it routed to.

We need to remember the serving engine port so we can prepare to kill it.

Let's prompt a long response from this router with the same session-id and immediately kill the router to see how production stack deployment responds.

Let's do the same thing with Ray Serve and see that our request gets lost into the void.

Let's do

## Example 2: Production Stack + LMCache vs XXXXX (COMING SOON)

