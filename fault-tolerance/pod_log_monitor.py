#!/usr/bin/env python3
"""
Pod Log Monitor - A tool to help identify which pod is handling a specific session ID.
Run this script before sending your test request, and it will monitor all pods for activity.
"""

import subprocess
import threading
import time
import argparse
import re
import signal
import sys

class PodLogMonitor:
    def __init__(self, pod_pattern="vllm-", session_id=None):
        self.pod_pattern = pod_pattern
        self.session_id = session_id
        self.processes = []
        self.threads = []
        self.running = True
        self.lock = threading.Lock()
        self.active_pods = set()

        # Setup signal handler for clean exit
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, sig, frame):
        print("\nShutting down log monitor...")
        self.stop()
        sys.exit(0)

    def get_pods(self):
        """Get all pods matching the pattern."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "pods", "--no-headers", "-o", "custom-columns=:metadata.name"],
                capture_output=True,
                text=True,
                check=True
            )

            pods = [pod for pod in result.stdout.strip().split('\n') if pod and self.pod_pattern in pod]
            return pods
        except subprocess.CalledProcessError as e:
            print(f"Error getting pods: {e}")
            return []

    def monitor_pod_logs(self, pod_name):
        """Monitor logs for a specific pod."""
        try:
            # Use kubectl logs with follow option to stream logs
            process = subprocess.Popen(
                ["kubectl", "logs", "-f", pod_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )

            self.processes.append(process)

            # Read the output line by line
            for line in process.stdout:
                if not self.running:
                    break

                # Look for session ID if provided
                if self.session_id and self.session_id in line:
                    with self.lock:
                        self.active_pods.add(pod_name)
                        print(f"\n🔍 Session ID {self.session_id} detected in pod {pod_name}!")
                        print(f"Log line: {line.strip()}")

                # Look for any request processing indicators
                if "request" in line.lower() or "processing" in line.lower():
                    print(f"\n[{pod_name}] {line.strip()}")

            process.wait()

        except Exception as e:
            print(f"Error monitoring {pod_name}: {e}")

    def start(self):
        """Start monitoring all matching pods."""
        pods = self.get_pods()

        if not pods:
            print(f"No pods found matching pattern '{self.pod_pattern}'")
            return False

        print(f"Starting to monitor logs for {len(pods)} pods: {', '.join(pods)}")
        print(f"Looking for session ID: {self.session_id if self.session_id else 'Not specified'}")
        print("Press Ctrl+C to stop monitoring")

        # Start a thread for each pod
        for pod in pods:
            thread = threading.Thread(target=self.monitor_pod_logs, args=(pod,))
            thread.daemon = True
            thread.start()
            self.threads.append(thread)

        return True

    def stop(self):
        """Stop all monitoring."""
        self.running = False

        # Terminate all processes
        for process in self.processes:
            try:
                process.terminate()
            except:
                pass

        # Wait for all threads to finish
        for thread in self.threads:
            thread.join(timeout=1.0)

        print("Log monitoring stopped")

    def get_active_pods(self):
        """Get the set of pods that processed requests with the session ID."""
        with self.lock:
            return self.active_pods.copy()

def main():
    parser = argparse.ArgumentParser(description="Monitor Kubernetes pod logs for specific session IDs")
    parser.add_argument("--pod-pattern", type=str, default="vllm-",
                       help="Pattern to match pod names (default: 'vllm-')")
    parser.add_argument("--session-id", type=str, default="9999",
                       help="Session ID to look for in logs (default: '9999')")
    parser.add_argument("--duration", type=int, default=0,
                       help="Duration to monitor in seconds. 0 means indefinitely (default: 0)")
    args = parser.parse_args()

    # Create and start the monitor
    monitor = PodLogMonitor(args.pod_pattern, args.session_id)
    if not monitor.start():
        return

    try:
        # If duration specified, monitor for that duration
        if args.duration > 0:
            time.sleep(args.duration)
            monitor.stop()

            active_pods = monitor.get_active_pods()
            if active_pods:
                print(f"\nPods that processed requests with session ID {args.session_id}:")
                for pod in active_pods:
                    print(f"- {pod}")
            else:
                print(f"\nNo pods detected processing requests with session ID {args.session_id}")
        else:
            # Otherwise, keep running until interrupted
            while monitor.running:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        monitor.stop()

        active_pods = monitor.get_active_pods()
        if active_pods:
            print(f"\nPods that processed requests with session ID {args.session_id}:")
            for pod in active_pods:
                print(f"- {pod}")
        else:
            print(f"\nNo pods detected processing requests with session ID {args.session_id}")

if __name__ == "__main__":
    main()