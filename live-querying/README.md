# LLM Performance Comparison Demo

This demo shows the performance difference between Production Stack and Ray Serve LLM serving platforms in real-time. It allows you to compare Time to First Token (TTFT) and Inter-Token Latency (ITL) metrics side-by-side with a focus on long context scenarios.

## Prerequisites

1. Ensure both serving endpoints are running:
   - Production Stack on `localhost:30080`
   - Ray Serve on `localhost:30081`

2. Python dependencies:
   - streamlit
   - pandas
   - altair
   - openai
   - transformers

## Running the Demo

Simply run the provided script:

```bash
chmod +x run_demo.sh
./run_demo.sh
```

Or manually:

```bash
streamlit run frontend.py
```

## Features

- Side-by-side comparison of responses from both serving platforms
- Real-time streaming responses with visual cursor indicating generation progress
- Pre-loaded conversation history with real technical documentation
- Documentation previews available in the UI
- Metrics visualization:
  - Time to First Token (TTFT) - How quickly the first token appears
  - Inter-Token Latency (ITL) - Average time between tokens during generation
- Metrics difference charts to visualize performance trends over time

## How It Works

1. The demo loads complete documentation files into each LLM's context window
2. A substantial 5-round conversation about the documentation is pre-loaded to both endpoints
3. This initial conversation allows Production Stack to benefit from its context caching capabilities
4. When you ask a new question, it's sent simultaneously to both endpoints
5. Responses are streamed in real-time to show the difference in responsiveness
6. Performance metrics are captured and displayed for comparison

## Technical Documentation

The demo uses real technical documentation from man pages to create context-rich conversations:
- man-unix.txt
- man-python.txt
- man-sed.txt
- man-grep.txt
- man-bash.txt
- man-ffmpeg.txt

Each document is loaded in full, creating a substantial context window that demonstrates the performance advantages of Production Stack's caching mechanisms.

## Components

- `frontend.py`: Streamlit web interface with side-by-side comparison
- `dual_chat_session.py`: Manages dual endpoint communication
- `chat_session.py`: Single endpoint chat session with performance metrics
- `conversation_generator.py`: Generates realistic conversations based on documentation
- `run_demo.sh`: Script to run the demo

## Tips

- The "Show/Hide Documentation Previews" button lets you see the actual content being used
- Watch the blinking cursor to see which endpoint responds first (TTFT)
- Notice the smoothness of text generation on each endpoint (related to ITL)
- Reset the conversation to generate a new conversation about different documentation files
- Look at the performance trend charts to see how the difference evolves over multiple queries