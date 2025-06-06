from openai import OpenAI
import threading
import sys
from io import StringIO
import time
import random
import os



class ChatSession:
    def __init__(self, name, port, context_separator="###"):
        openai_api_key = "EMPTY"
        openai_api_base = f"http://localhost:{port}/v1"
        self.name = name
        self.port = port

        # Create custom HTTP headers with x-user-id: 0
        custom_headers = {
            "x-user-id": "0"
        }
        print(f"[{name}] Setting custom header: x-user-id: 0")

        self.client = client = OpenAI(
            # defaults to os.environ.get("OPENAI_API_KEY")
            api_key=openai_api_key,
            base_url=openai_api_base,
            default_headers=custom_headers
        )

        try:
            models = client.models.list()
            self.model = models.data[0].id
        except Exception as e:
            print(f"Error fetching models from {openai_api_base}: {e}")
            self.model = "llama3"  # Fallback model name

        self.messages = []
        self.final_context = ""
        self.context_separator = context_separator

        # Performance metrics
        self.metrics = []

    def set_context(self, context_strings):
        contexts = []
        for context in context_strings:
            contexts.append(context)

        self.final_context = self.context_separator.join(contexts)
        self.on_user_message(self.final_context, display=False)
        self.on_server_message("Got it!", display=False)

    def get_context(self):
        return self.final_context

    def on_user_message(self, message, display=True):
        if display:
            print(f"[{self.name}] User message:", message)
        self.messages.append({"role": "user", "content": message})

    def on_server_message(self, message, display=True):
        if display:
            print(f"[{self.name}] Server message:", message)
        self.messages.append({"role": "assistant", "content": message})

    def chat(self, question):
        self.on_user_message(question)

        # Track performance metrics
        start_time = time.perf_counter()
        first_token_time = None
        last_token_time = None
        total_tokens = 0
        ttft_sent = False

        try:
            chat_completion = self.client.chat.completions.create(
                messages=self.messages,
                model=self.model,
                temperature=0.5,
                stream=True,
            )

            output_buffer = StringIO()
            server_message = []
            for chunk in chat_completion:
                chunk_message = chunk.choices[0].delta.content
                if chunk_message is not None:
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                        ttft = first_token_time - start_time
                        ttft_ms = ttft * 1000  # Convert to ms

                        # Send TTFT metric before any content
                        ttft_sent = True
                        yield f"<metric:ttft:{ttft_ms:.2f}>"
                        print(f"[{self.name}] Sent TTFT metric: {ttft_ms:.2f} ms")

                    last_token_time = time.perf_counter()
                    total_tokens += 1

                    yield chunk_message
                    server_message.append(chunk_message)

            complete_message = "".join(server_message)
            self.on_server_message(complete_message)

            # Calculate metrics
            ttft = first_token_time - start_time if first_token_time else 0
            total_time = last_token_time - start_time if last_token_time else 0

            # Store metrics
            self.metrics.append({
                "ttft": ttft * 1000,  # Convert to ms
                "total_time": total_time,
                "tokens": total_tokens
            })

            # If we never got a first token, send a default TTFT
            if not ttft_sent:
                yield "<metric:ttft:10000.00>"
                print(f"[{self.name}] No tokens received, sending default TTFT")

        except Exception as e:
            error_message = f"Error: {str(e)}"
            print(f"[{self.name}] {error_message}")

            # Send a default TTFT on error
            if not ttft_sent:
                yield "<metric:ttft:10000.00>"
                print(f"[{self.name}] Error occurred, sending default TTFT")

            yield error_message
            self.on_server_message(error_message)

    def get_last_metrics(self):
        if self.metrics:
            return self.metrics[-1]
        return None

    def get_avg_metrics(self, last_n=None):
        if not self.metrics:
            return None

        metrics_to_use = self.metrics[-last_n:] if last_n else self.metrics

        avg_ttft = sum(m["ttft"] for m in metrics_to_use) / len(metrics_to_use)

        return {
            "avg_ttft": avg_ttft
        }