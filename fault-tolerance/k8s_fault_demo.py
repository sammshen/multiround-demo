import os
import sys
import threading
import time
import json
import subprocess
from io import StringIO
import re

from openai import OpenAI

# Constants
PORT = 30080  # The port-forwarded router service from production-stack deployment
USER_ID = "9999"  # Fixed user ID for demonstration
API_TYPE = "chat"  # Use "chat" for chat completions API or "completion" for completions API
DEBUG = True  # Enable verbose debug output

def debug_print(message):
    if DEBUG:
        print(f"DEBUG: {message}")

class Printer:
    def __init__(self):
        self._thread = None
        self._stop_event = threading.Event()

    def _print(self):
        idx = 0
        while not self._stop_event.is_set():
            arrows = ">" * (idx % 6)
            string = "{:6s}".format(arrows)
            print("\033[31m\r" + string + "\033[0m", end="", flush=True)
            idx += 1
            time.sleep(0.2)

    def start(self):
        if self._thread is None:
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._print)
            self._thread.start()

    def stop(self):
        if self._thread is not None:
            self._stop_event.set()
            self._thread.join()
            self._thread = None
            print("\033[31m\r>>>>> \033[0m", end="", flush=True)

def get_model_name():
    """Get the model name from the available pods"""
    try:
        # First check if we can get the model name from the deployment
        model_name = "meta-llama/Llama-3.1-8B-Instruct"  # Default fallback model name

        # Try to determine model name from the pods
        pods_output = subprocess.check_output(
            "kubectl get pods | grep 'vllm-.*engine.*'",
            shell=True
        ).decode().strip()

        print(f"Found serving engine pods: {pods_output}")

        # Check if we can get model name from deployment
        try:
            yaml_output = subprocess.check_output(
                "kubectl get deployment -o yaml | grep -A 10 modelURL",
                shell=True, stderr=subprocess.PIPE
            ).decode().strip()
            debug_print(f"Deployment YAML info: {yaml_output}")

            # Look for modelURL
            model_match = re.search(r"modelURL:\s*(.+)", yaml_output)
            if model_match:
                model_name = model_match.group(1).strip()
                print(f"Found model name from deployment: {model_name}")
        except Exception as e:
            debug_print(f"Could not get model name from deployment: {e}")

        return model_name
    except Exception as e:
        print(f"Warning: Could not get model name: {e}")
        return "meta-llama/Llama-3.1-8B-Instruct"  # Default fallback

def get_router_logs():
    """Get logs from the router pod"""
    try:
        # Find the router pod
        router_pod = subprocess.check_output(
            "kubectl get pods | grep router | awk '{print $1}'",
            shell=True
        ).decode().strip()

        if not router_pod:
            print("Could not find router pod")
            return None, None

        print(f"Found router pod: {router_pod}")

        # Get the most recent logs
        logs = subprocess.check_output(
            f"kubectl logs {router_pod} --tail=500",
            shell=True
        ).decode()

        return router_pod, logs
    except Exception as e:
        print(f"Error getting router logs: {e}")
        return None, None

def find_serving_engine_pod():
    """Find which pod is handling requests for user 9999"""
    print("Sending test request to identify which pod handles user ID 9999...")

    model_name = get_model_name()
    print(f"Using model name: {model_name}")

    client = OpenAI(
        api_key="EMPTY",
        base_url=f"http://localhost:{PORT}/v1",
        default_headers={"x-user-id": USER_ID}
    )

    # Send a simple request to identify which pod handles it
    try:
        print(f"Sending request with user ID {USER_ID}...")
        if API_TYPE == "chat":
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, this is a test message to identify which pod you are."}
                ],
                max_tokens=10
            )
            debug_print(f"Response received: {response}")
        else:
            response = client.completions.create(
                model=model_name,
                prompt="Hello, this is a test message to identify which pod you are.",
                max_tokens=10
            )
            debug_print(f"Response received: {response}")
    except Exception as e:
        print(f"Error sending initial request: {e}")
        print("Check that the model name is correct and the service is running.")
        return None

    # Wait a moment for logs to be written
    print("Waiting for logs to be updated...")
    time.sleep(3)  # Increased wait time to ensure logs are captured

    # Get router logs to see which pod handled the request
    print("Checking router logs to identify serving engine pod...")
    router_pod, logs = get_router_logs()

    if not logs:
        print("No router logs available")
        return select_fallback_pod()

    # Print a sample of the logs to help debug
    print("\nSample of router logs:")
    log_lines = logs.splitlines()
    for i in range(min(10, len(log_lines))):
        print(f"  {log_lines[i]}")

    # First, try to find router logs that specifically mention routing decisions
    print("\nLooking for routing information in logs...")
    routing_lines = []
    for line in logs.splitlines():
        if "rout" in line.lower() and "session" in line.lower():
            routing_lines.append(line)
            print(f"Found routing log: {line}")

    # Then look for entries with our user ID
    print(f"\nLooking for entries with user ID {USER_ID} in logs...")
    user_id_lines = []
    for line in logs.splitlines():
        if USER_ID in line:
            user_id_lines.append(line)
            print(f"Found log entry with user ID {USER_ID}: {line}")

    # Combine both sets of lines, prioritizing routing lines
    all_lines = routing_lines + user_id_lines

    if not all_lines:
        print(f"No relevant log entries found")

        # Try one more approach - check if there's a session cache entry
        session_cache_lines = []
        for line in logs.splitlines():
            if "session cache" in line.lower() or "session_id" in line.lower():
                session_cache_lines.append(line)
                print(f"Found session cache log: {line}")

        if session_cache_lines:
            all_lines = session_cache_lines
        else:
            return select_fallback_pod()

    # Try to extract pod name from the lines using various patterns
    patterns = [
        r"routing to\s+(\S+)",            # "routing to pod-name"
        r"routed to\s+(\S+)",             # "routed to pod-name"
        r"session.+?pod\s+(\S+)",         # "session XX using pod pod-name"
        rf"{USER_ID}.+?pod\s+(\S+)",      # "user 9999 ... pod pod-name"
        r"using pod\s+(\S+)",             # "using pod pod-name"
        r"to pod\s+(\S+)",                # "to pod pod-name"
        r"pod:\s*(\S+)",                  # "pod: pod-name"
        r"pod=(\S+)",                     # "pod=pod-name"
        r"engine:\s*(\S+)",               # "engine: pod-name"
        r"engine=(\S+)",                  # "engine=pod-name"
        r"serving engine\s+(\S+)",        # "serving engine pod-name"
    ]

    for line in all_lines:
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                pod_name = match.group(1).strip()
                # Remove any trailing commas, quotes, etc.
                pod_name = re.sub(r'[,."\':;]$', '', pod_name)
                print(f"Extracted pod name using pattern '{pattern}': {pod_name}")

                # Verify this is actually a pod
                try:
                    pod_check = subprocess.run(
                        f"kubectl get pod {pod_name}",
                        shell=True,
                        capture_output=True
                    )
                    if pod_check.returncode == 0:
                        print(f"Verified pod exists: {pod_name}")
                        return pod_name
                    else:
                        print(f"Extracted name {pod_name} is not a valid pod, continuing search...")
                except Exception as e:
                    print(f"Error checking pod {pod_name}: {e}")

    # If we still couldn't find a pod from logs, try to find pods by querying k8s
    return select_fallback_pod()

def select_fallback_pod():
    """Select a fallback pod if we can't identify the right one"""
    print("Could not extract pod name from logs, listing available pods...")
    try:
        pods = subprocess.check_output(
            "kubectl get pods | grep 'vllm-.*engine.*' | awk '{print $1}'",
            shell=True
        ).decode().strip().split('\n')

        if pods and pods[0]:
            pod_name = pods[0]
            print(f"Using first available serving engine pod as fallback: {pod_name}")
            return pod_name

        print("No serving engine pods found")
        return None
    except Exception as e:
        print(f"Error getting pods: {e}")
        return None

def kill_pod(pod_name):
    """Kill the specified pod"""
    print(f"Killing pod {pod_name}...")
    try:
        subprocess.run(f"kubectl delete pod {pod_name} --grace-period=0 --force", shell=True, check=True)
        print(f"Pod {pod_name} deleted")
    except subprocess.CalledProcessError as e:
        print(f"Error deleting pod: {e}")
        return False
    return True

def demo_fault_tolerance():
    # Step 1: Find which pod is handling our user ID
    serving_pod = find_serving_engine_pod()
    if not serving_pod:
        print("Could not identify the serving engine pod. Exiting.")
        return

    print(f"\nIdentified serving pod: {serving_pod}")

    # Step 2: Create a client with our fixed user ID
    client = OpenAI(
        api_key="EMPTY",
        base_url=f"http://localhost:{PORT}/v1",
        default_headers={"x-user-id": USER_ID}
    )

    # Step 3: Start a long request
    print("\nSending long-running request...")
    printer = Printer()
    printer.start()

    # Track request state
    start_time = time.perf_counter()
    first_token_time = None
    request_completed = False
    pod_killed = False
    stream_stopped_after_kill = False
    response_continued_after_kill = False
    tokens_after_kill_count = 0
    tokens_before_kill_count = 0
    expected_min_tokens = 200  # We expect at least this many tokens in a complete response
    pod_kill_time = None

    # Set up pod kill detection
    def mark_pod_killed():
        nonlocal pod_killed, pod_kill_time
        pod_killed = True
        pod_kill_time = time.perf_counter()

    # Create a thread to kill the pod after a delay
    kill_thread = threading.Thread(
        target=lambda: (time.sleep(5), kill_pod(serving_pod), mark_pod_killed())
    )
    kill_thread.start()

    try:
        # Get the model name
        model_name = get_model_name()

        if API_TYPE == "chat":
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Write a detailed 500-word essay about the history of artificial intelligence, including key milestones and influential researchers."}
                ],
                max_tokens=1000,
                stream=True
            )

            # Process the streaming response
            full_response = ""
            last_token_time = start_time

            for chunk in response:
                current_time = time.perf_counter()

                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    if first_token_time is None:
                        first_token_time = current_time
                        printer.stop()

                    # Track tokens before/after pod kill
                    if pod_killed:
                        tokens_after_kill_count += 1
                        response_continued_after_kill = True
                    else:
                        tokens_before_kill_count += 1

                    # Check for long pauses after pod kill
                    if pod_killed and (current_time - last_token_time) > 2.0:
                        stream_stopped_after_kill = True

                    print(token, end="", flush=True)
                    full_response += token
                    last_token_time = current_time

            # If we get here without exception, the stream completed
            request_completed = True

        else:
            response = client.completions.create(
                model=model_name,
                prompt="Write a detailed 500-word essay about the history of artificial intelligence, including key milestones and influential researchers.",
                max_tokens=1000,
                stream=True
            )

            # Process the streaming response
            full_response = ""
            last_token_time = start_time

            for chunk in response:
                current_time = time.perf_counter()

                if chunk.choices and chunk.choices[0].text:
                    token = chunk.choices[0].text
                    if first_token_time is None:
                        first_token_time = current_time
                        printer.stop()

                    # Track tokens before/after pod kill
                    if pod_killed:
                        tokens_after_kill_count += 1
                        response_continued_after_kill = True
                    else:
                        tokens_before_kill_count += 1

                    # Check for long pauses after pod kill
                    if pod_killed and (current_time - last_token_time) > 2.0:
                        stream_stopped_after_kill = True

                    print(token, end="", flush=True)
                    full_response += token
                    last_token_time = current_time

            # If we get here without exception, the stream completed
            request_completed = True

        print("\n\n------------------- RESULT -------------------")

        # Proper fault tolerance detection logic
        if request_completed and len(full_response) > expected_min_tokens and tokens_after_kill_count > 50:
            print("✅ FAULT TOLERANCE SUCCESS: Response completed successfully despite pod failure!")
            print(f"    - {tokens_before_kill_count} tokens received before pod killed")
            print(f"    - {tokens_after_kill_count} tokens received after pod killed")
        else:
            print("❌ FAULT TOLERANCE FAILED: Response was likely cut off after pod failure")
            print(f"    - {tokens_before_kill_count} tokens received before pod killed")
            print(f"    - Only {tokens_after_kill_count} tokens received after pod killed")

            if tokens_after_kill_count < 10:
                print("    - Very few tokens after pod killed - clear indication of failure")

            if stream_stopped_after_kill:
                print("    - Stream had unexplained pauses after pod killed")

            if len(full_response) < expected_min_tokens:
                print(f"    - Response too short ({len(full_response)} chars) - likely incomplete")

        if first_token_time:
            print(f"TTFT: {first_token_time - start_time:.2f}s")
        else:
            print("No tokens received before the script ended.")

        print(f"Total time: {time.perf_counter() - start_time:.2f}s")
        print(f"Response length: {len(full_response)} characters")
        print(f"Response ends with: \"...{full_response[-50:]}\"")
        print("-------------------------------------------------")

    except Exception as e:
        printer.stop()
        print(f"\n\n------------------- RESULT -------------------")
        print(f"❌ FAULT TOLERANCE FAILED: Error during request: {e}")
        print("Request failed to recover from pod failure.")
        print(f"Total time before failure: {time.perf_counter() - start_time:.2f}s")
        print("-------------------------------------------------")

    # Wait for kill thread to complete
    kill_thread.join()

if __name__ == "__main__":
    print("Starting fault tolerance demonstration...")
    print(f"Using port {PORT}, user ID {USER_ID}, and API type {API_TYPE}")

    # Process command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ["chat", "completion"]:
            API_TYPE = sys.argv[1]
            print(f"API type set to {API_TYPE}")

    # Check if port forwarding is active
    try:
        result = subprocess.run(f"lsof -i :{PORT}", shell=True, capture_output=True)
        if result.returncode != 0:
            print(f"Port {PORT} doesn't appear to be forwarded. Make sure you've run:")
            print(f"kubectl port-forward svc/vllm-router-service {PORT}:80")
            sys.exit(1)
    except Exception as e:
        print(f"Error checking port forwarding: {e}")
        print(f"Please ensure port {PORT} is forwarded manually")

    demo_fault_tolerance()