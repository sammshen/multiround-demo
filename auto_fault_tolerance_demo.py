#!/usr/bin/env python3
"""
Automated Fault Tolerance Demo - Properly identifies and targets serving engine pods
"""

import requests
import json
import time
import argparse
import subprocess
import sys
import os
import threading
import signal
import queue
import re

# Global variables
identified_router = None
identified_serving_engine = None
serving_engine_ip = None
pod_identified_event = threading.Event()
request_in_progress = threading.Event()
response_queue = queue.Queue()

def signal_handler(sig, frame):
    print("\nInterrupted by user. Cleaning up...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def print_section(title):
    """Print a section header with clear delimiters."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")
    # Sleep a moment to make the UI more readable
    time.sleep(1)

def get_pod_ip_mapping():
    """Get a mapping of pod names to IP addresses."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-o", "wide"],
            capture_output=True,
            text=True,
            check=True
        )

        pod_ip_map = {}
        lines = result.stdout.strip().split('\n')

        # Skip the header line
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 6:  # Ensure there are enough parts for name and IP
                pod_name = parts[0]
                pod_ip = parts[5]
                pod_ip_map[pod_ip] = pod_name
                pod_ip_map[pod_name] = pod_ip

        return pod_ip_map
    except Exception as e:
        print(f"Error getting pod IP mapping: {e}")
        return {}

def monitor_router_logs(router_pattern, session_id, timeout=30):
    """Monitor router logs to identify which serving engine is handling the session."""
    global identified_router, identified_serving_engine, serving_engine_ip

    print(f"\nMonitoring router logs to identify which serving engine handles session {session_id}...")

    try:
        # Get pods matching the router pattern
        result = subprocess.run(
            ["kubectl", "get", "pods", "--no-headers", "-o", "custom-columns=:metadata.name"],
            capture_output=True,
            text=True,
            check=True
        )

        router_pods = [pod for pod in result.stdout.strip().split('\n') if pod and router_pattern in pod]

        if not router_pods:
            print(f"No router pods found matching pattern '{router_pattern}'")
            return None, None

        print(f"Found router pod: {router_pods[0]}")
        router_pod = router_pods[0]
        identified_router = router_pod

        # Get the pod to IP mapping
        pod_ip_map = get_pod_ip_mapping()
        print("Pod to IP mapping:")
        for name, ip in pod_ip_map.items():
            if not name.startswith('10.') and 'vllm' in name:
                print(f"  {name}: {ip}")

        # Start monitoring router logs
        start_time = time.time()
        found_serving_engine = False

        while time.time() - start_time < timeout and not found_serving_engine:
            # Get recent logs from the router pod
            log_result = subprocess.run(
                ["kubectl", "logs", "--tail=50", router_pod],
                capture_output=True,
                text=True
            )

            logs = log_result.stdout

            # Look for session ID and routing information
            session_pattern = f"Got session id: {session_id}"
            routing_pattern = r"Routing request .+ to (http://[\d\.]+:\d+)"

            session_match = session_id in logs and session_pattern in logs
            if session_match:
                print(f"\n🔍 Session ID {session_id} detected in router logs!")

                # Find the most recent routing destination after the session ID
                routing_matches = re.findall(routing_pattern, logs)
                if routing_matches:
                    target_url = routing_matches[-1]  # Get the most recent match
                    current_serving_engine_ip = target_url.split('//')[1].split(':')[0]
                    print(f"Request routed to serving engine at IP: {current_serving_engine_ip}")

                    # Look up the pod name using the IP
                    if current_serving_engine_ip in pod_ip_map:
                        serving_engine_pod = pod_ip_map[current_serving_engine_ip]
                        print(f"Identified serving engine pod: {serving_engine_pod}")
                        identified_serving_engine = serving_engine_pod
                        serving_engine_ip = current_serving_engine_ip
                        found_serving_engine = True
                        pod_identified_event.set()
                        break
                    else:
                        print(f"Warning: Could not find pod name for IP {current_serving_engine_ip}")

            if not found_serving_engine:
                time.sleep(1)

        if not found_serving_engine:
            print(f"Could not identify serving engine within {timeout} seconds")
            return None, None

        return identified_router, identified_serving_engine

    except Exception as e:
        print(f"Error monitoring router logs: {e}")
        return None, None

def send_request(endpoint, session_id, prompt, stream=True, kill_pod_callback=None):
    """
    Send a request to the specified endpoint with a session ID header.
    If kill_pod_callback is provided, it will be called during streaming to kill the pod.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('HF_TOKEN', '')}",
        "x-user-id": str(session_id)  # Session ID header as specified in the YAML
    }

    data = {
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500 if stream else 100,  # Longer output for streamed response to give time to kill the pod
        "temperature": 0.7,
        "stream": stream
    }

    print(f"\nSending request to {endpoint} with session ID {session_id}")
    print(f"Prompt: \"{prompt}\"")

    try:
        if stream:
            request_in_progress.set()
            response = requests.post(endpoint, headers=headers, json=data, stream=True)

            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")

            # Extract and print the streamed content
            print("\nResponse content:")

            # These variables track the state for killing the pod
            token_count = 0
            pod_killed = False
            kill_after_tokens = 20  # Kill the pod after receiving this many tokens

            try:
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            line = line[6:]  # Remove 'data: ' prefix
                            if line.strip() == '[DONE]':
                                print("[DONE]")
                                break
                            try:
                                data = json.loads(line)
                                if 'choices' in data and len(data['choices']) > 0:
                                    content = data['choices'][0].get('delta', {}).get('content', '')
                                    if content:
                                        print(content, end='', flush=True)
                                        token_count += 1

                                        # Check if we should kill the pod
                                        if kill_pod_callback and token_count >= kill_after_tokens and not pod_killed:
                                            print("\n\n" + "-" * 50)
                                            print("  🔥 KILLING POD DURING ACTIVE STREAMING 🔥")
                                            print("-" * 50 + "\n")

                                            # Call the kill_pod function
                                            pod_killed = True
                                            threading.Thread(target=kill_pod_callback).start()

                                            # Give a moment for the kill to take effect
                                            time.sleep(1)
                                            print("\nContinuing to read response after pod kill...\n")
                            except json.JSONDecodeError:
                                print(f"Failed to parse JSON: {line}")
            except Exception as e:
                print(f"\nStream interrupted: {e}")
                response_queue.put(("interrupted", str(e)))
            else:
                print("\nStream completed successfully")
                response_queue.put(("completed", ""))
            finally:
                request_in_progress.clear()

            return response
        else:
            response = requests.post(endpoint, headers=headers, json=data)
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            response_content = response.json() if response.content else 'No content'
            print(f"Response content: {response_content}")
            return response
    except Exception as e:
        print(f"Request error: {e}")
        return None

def kill_pod(pod_name):
    """Kill a specific Kubernetes pod by name."""
    print(f"\nKilling pod {pod_name}...")
    result = subprocess.run(
        ["kubectl", "delete", "pod", pod_name, "--now"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Failed to kill pod: {result.stderr}")
        return False

    print(f"Pod {pod_name} kill command issued successfully")
    return True

def get_kubernetes_pods():
    """Get all running Kubernetes pods and their details."""
    result = subprocess.run(
        ["kubectl", "get", "pods", "-o", "wide"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Failed to get Kubernetes pods: {result.stderr}")
        return None

    print("\nRunning Kubernetes pods:")
    print(result.stdout)
    return result.stdout

def test_fault_tolerance(endpoint, session_id, router_pattern, serving_engine_pattern):
    """Test fault tolerance by identifying the serving engine, killing it during a request, and then testing again."""

    print_section("INITIAL SETUP")
    print("This test will demonstrate the fault tolerance capabilities of the Production Stack router.")
    print("The router should automatically redirect requests to a healthy serving engine")
    print("when the original serving engine fails - EVEN DURING ACTIVE STREAMING.")
    print("\nStep 1: First, let's see what pods are running...")
    time.sleep(1)

    # Step 1: Get initial list of pods
    get_kubernetes_pods()
    time.sleep(2)

    print_section("IDENTIFYING SERVING ENGINE")
    print("Step 2: Sending an initial request to identify which serving engine handles the session...")
    print("The router will use session ID to consistently route requests to the same serving engine.")
    time.sleep(1)

    # Step 2: Send an initial request to identify which serving engine handles the session
    send_request(endpoint, session_id, "Hello, I'm testing the fault tolerance. Can you identify yourself?", stream=False)
    time.sleep(2)

    # Step 3: Monitor router logs to identify which serving engine is handling the session
    router_pod, serving_engine_pod = monitor_router_logs(router_pattern, session_id)

    if not serving_engine_pod:
        print("\nCould not automatically identify the serving engine pod.")
        print("Let's try to identify it manually...")
        get_kubernetes_pods()
        serving_engine_pod = input("\nEnter the name of the serving engine pod you believe is handling your session: ")
    else:
        print(f"\nAutomatically identified serving engine pod handling session {session_id}: {serving_engine_pod}")

    time.sleep(2)

    print_section("TESTING FAULT TOLERANCE DURING STREAMING")
    print("Step 3: Now we'll send a long-running request and kill the serving engine WHILE it's processing")
    print("If the fault tolerance is working properly, the router should:")
    print("  1. Detect that the serving engine has failed")
    print("  2. Automatically redirect the request to another serving engine")
    print("  3. Continue streaming the response without interruption")
    print("\nWatching this in action demonstrates true fault tolerance, not just Kubernetes recovery!")
    time.sleep(3)

    # Step 4: Send a long-running request and set up a callback to kill the pod during streaming
    kill_callback = lambda: kill_pod(serving_engine_pod)

    print("\nSending a long-running request. The pod will be killed during streaming...")
    send_request(
        endpoint,
        session_id,
        "Please provide a detailed, comprehensive explanation of fault tolerance in distributed systems. " +
        "Include examples of different fault tolerance mechanisms and how they work in practice. " +
        "Explain the difference between replication, redundancy, and failover strategies.",
        stream=True,
        kill_pod_callback=kill_callback
    )

    # Step 5: Wait a moment for the system to recover
    print_section("CHECKING SYSTEM STATE AFTER POD KILL")
    print("Step 4: Let's check what happened to our pods after killing the serving engine...")
    time.sleep(3)

    # Get the updated pod list
    get_kubernetes_pods()
    time.sleep(2)

    print_section("TESTING CONTINUED SESSION CONSISTENCY")
    print("Step 5: Now let's send another request with the same session ID")
    print("The router should route this request to a different serving engine,")
    print("while maintaining the same session consistency.")
    time.sleep(2)

    # Step 6: Send another request with the same session ID
    final_response = send_request(
        endpoint,
        session_id,
        "If you're receiving this message, it means the fault tolerance worked! " +
        "The first serving engine was killed, but the router redirected to another one. " +
        "Can you confirm you're a different serving engine than the one I was talking to before?"
    )

    # Step 7: Check if we can identify which pod handled the new request
    print_section("VERIFYING ROUTING BEHAVIOR")
    print("Step 6: Let's verify which serving engine handled our follow-up request...")
    time.sleep(1)

    new_router_pod, new_serving_engine_pod = monitor_router_logs(router_pattern, session_id)

    if new_serving_engine_pod:
        print(f"\nFollow-up request was handled by serving engine pod: {new_serving_engine_pod}")
        if serving_engine_pod != new_serving_engine_pod:
            print("\n✅ SUCCESS! The router correctly redirected the request to a different serving engine.")
            print(f"  Original serving engine: {serving_engine_pod}")
            print(f"  New serving engine:      {new_serving_engine_pod}")
        else:
            print("\n❌ UNEXPECTED: The router redirected to the same serving engine pod that was killed.")
    else:
        print("\nCould not automatically identify which serving engine handled the follow-up request.")

    print_section("TEST COMPLETE")
    print("The fault tolerance test is complete.")
    print("This demonstrates how the Production Stack router provides fault tolerance")
    print("by redirecting requests to healthy serving engines when failures occur,")
    print("EVEN DURING ACTIVE STREAMING.")
    print("\nThis is a key advantage over traditional serving systems that would lose the entire request.")

def main():
    parser = argparse.ArgumentParser(description="Demonstrate fault tolerance of LLM serving deployments")
    parser.add_argument("--endpoint", type=str, default="http://localhost:30080/v1/chat/completions",
                      help="API endpoint URL (default: http://localhost:30080/v1/chat/completions)")
    parser.add_argument("--session-id", type=str, default="9999",
                      help="Session ID to use for testing (default: 9999)")
    parser.add_argument("--router-pattern", type=str, default="vllm-deployment-router",
                      help="Pattern to identify router pods (default: vllm-deployment-router)")
    parser.add_argument("--serving-engine-pattern", type=str, default="vllm-llama3-deployment-vllm",
                      help="Pattern to identify serving engine pods (default: vllm-llama3-deployment-vllm)")
    args = parser.parse_args()

    # Ensure HF_TOKEN is set
    if not os.environ.get('HF_TOKEN'):
        print("Warning: HF_TOKEN environment variable is not set. Requests might fail.")

    # Test fault tolerance
    test_fault_tolerance(
        args.endpoint,
        args.session_id,
        args.router_pattern,
        args.serving_engine_pattern
    )

if __name__ == "__main__":
    main()