import asyncio
import time
import chat_session
import conversation_generator
from typing import Dict, List, Tuple, Optional, Any, Generator
import threading

class DualChatSession:
    """Manages chat sessions with two different endpoints simultaneously"""

    def __init__(self):
        # Initialize both chat sessions
        self.ps_session = chat_session.ChatSession("ProductionStack", 30080)
        self.rs_session = chat_session.ChatSession("RayServe", 30081)

        # Initialize history
        self.history = []

        # Dictionary to store document contents
        self.docs = {
            "doc1": None,
            "doc2": None,
            "doc3": None,
            "doc4": None,
            "doc5": None,
            "doc6": None,
            "doc7": None
        }
        self.doc_contents = {}

        # Initialize metrics comparison
        self.ttft_diff_history = []

    def initialize_with_conversation(self, num_rounds=5):
        """Initialize both sessions with the same conversation history"""
        # Generate a conversation and get doc names
        conversation, doc1, doc2, doc3, doc4, doc5, doc6, doc7 = conversation_generator.generate_conversation(num_rounds)

        # Store document names
        self.docs["doc1"] = doc1
        self.docs["doc2"] = doc2
        self.docs["doc3"] = doc3
        self.docs["doc4"] = doc4
        self.docs["doc5"] = doc5
        self.docs["doc6"] = doc6
        self.docs["doc7"] = doc7

        # Load document contents
        self.load_doc_contents("doc1")
        self.load_doc_contents("doc2")
        self.load_doc_contents("doc3")
        self.load_doc_contents("doc4")
        self.load_doc_contents("doc5")
        self.load_doc_contents("doc6")
        self.load_doc_contents("doc7")

        # Add a system message that we track in our history
        system_msg = {
            "role": "system",
            "content": f"""You are a helpful assistant that answers questions about Unix command line tools and programming.
You have access to the following documentation:
1. {doc1}
2. {doc2}
3. {doc3}
4. {doc4}
5. {doc5}
6. {doc6}
7. {doc7}

Please provide accurate and helpful responses based on this documentation."""
        }
        self.history.append(system_msg)

        # Set the context for both sessions (load the documentation)
        combined_docs = []
        for doc_key in ["doc1", "doc2", "doc3", "doc4", "doc5", "doc6", "doc7"]:
            if self.doc_contents.get(doc_key):
                combined_docs.append(f"# {self.docs[doc_key]} Documentation\n{self.doc_contents[doc_key]}")

        # Set the context in both sessions
        print("Setting context with documentation in both sessions...")
        if combined_docs:
            self.ps_session.set_context(combined_docs)
            self.rs_session.set_context(combined_docs)
            print(f"Loaded {len(combined_docs)} documentation files ({sum(len(doc) for doc in combined_docs)} bytes)")

        # First, make sure both sessions have a clean slate
        self.ps_session.messages = []
        self.rs_session.messages = []

        # Start by adding system message
        self.ps_session.messages.append({"role": "system", "content": system_msg["content"]})
        self.rs_session.messages.append({"role": "system", "content": system_msg["content"]})

        # Add conversation to our history and to both sessions
        print("Adding conversation history to both sessions...")
        for msg in conversation:
            if msg["role"] == "system":
                continue  # Skip system message as we've already added our own

            self.history.append(msg)

            if msg["role"] == "user":
                self.ps_session.messages.append({"role": "user", "content": msg["content"]})
                self.rs_session.messages.append({"role": "user", "content": msg["content"]})
                print(f"Added user message: {msg['content'][:30]}...")
            elif msg["role"] == "assistant":
                self.ps_session.messages.append({"role": "assistant", "content": msg["content"]})
                self.rs_session.messages.append({"role": "assistant", "content": msg["content"]})
                print(f"Added assistant message: {msg['content'][:30]}...")

        # Verify the conversation was loaded properly
        print(f"Initialized with {len(self.ps_session.messages)} messages in ProductionStack")
        print(f"Initialized with {len(self.rs_session.messages)} messages in RayServe")

        return self.history, self.docs

    def send_message(self, message: str) -> Tuple[Generator, Generator, Dict, Dict]:
        """Send a message to both sessions and return the streaming generators"""
        # Add message to history
        self.history.append({"role": "user", "content": message})

        # Create empty assistant responses in history first
        ps_entry = {
            "role": "assistant",
            "endpoint": "ProductionStack",
            "content": "",
            "metrics": {"ttft": None}
        }
        rs_entry = {
            "role": "assistant",
            "endpoint": "RayServe",
            "content": "",
            "metrics": {"ttft": None}
        }

        # Add these entries to history right away
        self.history.append(ps_entry)
        self.history.append(rs_entry)

        # Print debug info
        print(f"Added placeholder entries to history: PS={id(ps_entry)}, RS={id(rs_entry)}")

        # Store metrics for comparison
        ps_metrics = {"ttft": None, "complete": False, "history_entry": ps_entry}
        rs_metrics = {"ttft": None, "complete": False, "history_entry": rs_entry}

        # Get the streaming generators from both sessions
        ps_stream = self._wrap_stream(self.ps_session.chat(message), "ProductionStack", ps_metrics)
        rs_stream = self._wrap_stream(self.rs_session.chat(message), "RayServe", rs_metrics)

        return ps_stream, rs_stream, ps_metrics, rs_metrics

    def _wrap_stream(self, stream, endpoint_name, metrics_dict):
        """Wrap a streaming generator to extract metrics"""
        content_chunks = []
        history_entry = metrics_dict["history_entry"]

        # Print debug info
        print(f"Starting stream for {endpoint_name}, entry id={id(history_entry)}")

        for chunk in stream:
            # Check for metric markers
            if chunk.startswith("<metric:ttft:"):
                try:
                    ttft_value = chunk.split(":")[2].rstrip(">")
                    ttft = float(ttft_value)
                    metrics_dict["ttft"] = ttft

                    # Update the metrics in our history entry directly
                    history_entry["metrics"]["ttft"] = ttft

                    # Print debug information
                    print(f"Found TTFT metric for {endpoint_name}: {ttft} ms, updated entry id={id(history_entry)}")
                except Exception as e:
                    print(f"Error parsing TTFT metric: {e}, chunk: {chunk}")

                # Skip adding metric chunks to content
                continue
            elif chunk.startswith("<metric:"):
                # Skip other metric markers
                continue

            # Regular content
            content_chunks.append(chunk)
            yield chunk

        # After stream completes, update the complete response in history
        complete_content = "".join(content_chunks)
        history_entry["content"] = complete_content

        # Print debug
        print(f"Completed stream for {endpoint_name}, updated content for entry id={id(history_entry)}")

        # Mark this stream as complete
        metrics_dict["complete"] = True

        # Calculate metrics diff if both streams are complete
        latest_ps_metrics = None
        latest_rs_metrics = None

        # Find the latest metrics for each endpoint
        for msg in reversed(self.history):
            if msg.get("role") == "assistant":
                if msg.get("endpoint") == "ProductionStack" and not latest_ps_metrics and msg.get("metrics"):
                    latest_ps_metrics = msg["metrics"]
                elif msg.get("endpoint") == "RayServe" and not latest_rs_metrics and msg.get("metrics"):
                    latest_rs_metrics = msg["metrics"]

            if latest_ps_metrics and latest_rs_metrics:
                break

        # Calculate differences if we have both metrics
        if latest_ps_metrics and latest_rs_metrics:
            ps_ttft = latest_ps_metrics.get("ttft")
            rs_ttft = latest_rs_metrics.get("ttft")

            # Calculate differences
            if ps_ttft is not None and rs_ttft is not None:
                ttft_diff = ps_ttft - rs_ttft
                self.ttft_diff_history.append(ttft_diff)

    def get_metrics_comparison(self):
        """Get the comparison of metrics between the two endpoints"""
        if not self.ttft_diff_history:
            return None

        avg_ttft_diff = sum(self.ttft_diff_history) / len(self.ttft_diff_history)

        return {
            "avg_ttft_diff": avg_ttft_diff,
            "ttft_diff_history": self.ttft_diff_history
        }

    def get_doc_preview(self, doc_key, max_chars=1000):
        """Get a preview of the documentation for display in UI"""
        if doc_key in self.doc_contents:
            content = self.doc_contents[doc_key]
            if len(content) > max_chars:
                return content[:max_chars] + "..."
            return content
        return "Documentation not available"

    def load_doc_contents(self, doc_key):
        """Load the contents of a document into the doc_contents dictionary"""
        if doc_key in self.docs and self.docs[doc_key]:
            self.doc_contents[doc_key] = conversation_generator.load_man_file(self.docs[doc_key])