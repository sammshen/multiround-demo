#!/usr/bin/env python3
"""
Fault Tolerance Demo - A more automated way to test Production Stack's fault tolerance
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

# Global variables
identified_pod = None
pod_identified_event = threading.Event()
request_in_progress = threading.Event()
response_queue = queue.Queue()

def signal_handler(sig, frame):
    print("\nInterrupted by user. Cleaning up...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def monitor_logs(pod_pattern, session_id):
    """Monitor logs from pods matching the pattern for the session ID."""
    print(f"\nStarting log monitor for pods matching '{pod_pattern}' and session ID '{session_id}'...")

    try:
        # Get pods matching the pattern
        result = subprocess.run(
            ["kubectl", "get", "pods", "--no-headers", "-o", "custom-columns=:metadata.name"],
            capture_output=True,
            text=True,
            check=True
        )

        pods = [pod for pod in result.stdout.strip().split('\n') if pod and pod_pattern in pod]

        if not pods:
            print(f"No pods found matching pattern '{pod_pattern}'")
            return None

        print(f"Monitoring logs for {len(pods)} pods: {', '.join(pods)}")

        # Start processes to monitor each pod's logs
        processes = []
        log_files = []

        for pod in pods:
            log_file = f"{pod}.log"
            log_files.append(log_file)

            with open(log_file, 'w') as f:
                process = subprocess.Popen(
                    ["kubectl", "logs", "-f", pod],
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True
                )
                processes.append(process)

        # Wait a moment for logs to start
        time.sleep(2)

        # Monitor the log files for session ID
        while not pod_identified_event.is_set():
            for i, log_file in enumerate(log_files):
                try:
                    with open(log_file, 'r') as f:
                        content = f.read()
                        if session_id in content and "session id" in content.lower():
                            global identified_pod
                            identified_pod = pods[i]
                            print(f"\n🔍 Session ID {session_id} detected in pod {identified_pod}!")
                            pod_identified_event.set()
                            break
                except Exception as e:
                    print(f"Error reading log file {log_file}: {e}")

            if not pod_identified_event.is_set():
                time.sleep(0.5)

        # Clean up the processes
        for process in processes:
            try:
                process.terminate()
            except:
                pass

        # Clean up the log files
        for log_file in log_files:
            try:
                os.remove(log_file)
            except:
                pass

        return identified_pod

    except Exception as e:
        print(f"Error monitoring logs: {e}")
        return None

def send_request(endpoint, session_id, prompt, stream=True):
    """Send a request to the specified endpoint with a session ID header."""
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

def test_fault_tolerance(endpoint, session_id, pod_pattern):
    """Test fault tolerance by identifying, killing during a request, and then testing again."""

    # Step 1: Start monitoring the logs for the session ID
    monitor_thread = threading.Thread(target=monitor_logs, args=(pod_pattern, session_id))
    monitor_thread.daemon = True
    monitor_thread.start()

    # Step 2: Send an initial request to identify which pod handles the session
    send_request(endpoint, session_id, "Hello, I'm testing the fault tolerance. Can you identify yourself?", stream=False)

    # Step 3: Wait for the pod to be identified
    pod_identified_timeout = 10  # seconds
    pod_identified_event.wait(pod_identified_timeout)

    if not pod_identified_event.is_set():
        print(f"\nFailed to identify which pod is handling session {session_id} within {pod_identified_timeout} seconds.")
        print("Let's try to identify it manually...")
        get_kubernetes_pods()
        target_pod = input("\nEnter the name of the pod you believe is handling your session: ")
    else:
        target_pod = identified_pod
        print(f"\nIdentified pod handling session {session_id}: {target_pod}")

    # Step 4: Send a long-running request that we'll interrupt by killing the pod
    request_thread = threading.Thread(
        target=send_request,
        args=(endpoint, session_id, "Please generate a detailed, long explanation about fault tolerance in distributed systems. Include specific examples of fault tolerance mechanisms and how they work in practice.")
    )
    request_thread.daemon = True
    request_thread.start()

    # Step 5: Wait for the request to start processing
    request_in_progress.wait(5)
    time.sleep(2)  # Give it a moment to get deep into processing

    # Step 6: Kill the pod while the request is being processed
    if kill_pod(target_pod):
        print("\nPod killed while request was being processed!")

        # Step 7: Wait to see what happens to the in-progress request
        try:
            status, message = response_queue.get(timeout=10)
            print(f"\nIn-progress request {status}: {message}")
        except queue.Empty:
            print("\nNo response received from the in-progress request within timeout.")

    # Step 8: Wait a moment for the system to recover
    print("\nWaiting for system to recover...")
    time.sleep(10)

    # Step 9: List the current pods to see what happened
    get_kubernetes_pods()

    # Step 10: Send another request with the same session ID
    print("\nSending another request with the same session ID to test fault tolerance...")
    send_request(endpoint, session_id, "If you receive this message, it means the fault tolerance mechanism is working! Can you confirm that you received my previous messages?")

def main():
    parser = argparse.ArgumentParser(description="Demonstrate fault tolerance of LLM serving deployments")
    parser.add_argument("--endpoint", type=str, default="http://localhost:30080/v1/chat/completions",
                      help="API endpoint URL (default: http://localhost:30080/v1/chat/completions)")
    parser.add_argument("--session-id", type=str, default="9999",
                      help="Session ID to use for testing (default: 9999)")
    parser.add_argument("--pod-pattern", type=str, default="vllm-deployment-router",
                      help="Pattern to identify pods to monitor (default: vllm-deployment-router)")
    args = parser.parse_args()

    # Ensure HF_TOKEN is set
    if not os.environ.get('HF_TOKEN'):
        print("Warning: HF_TOKEN environment variable is not set. Requests might fail.")

    # Test fault tolerance
    test_fault_tolerance(args.endpoint, args.session_id, args.pod_pattern)

if __name__ == "__main__":
    main()