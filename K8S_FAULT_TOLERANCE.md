# Kubernetes Fault Tolerance Explained

## What is Fault Tolerance?

Fault tolerance is the ability of a system to continue functioning correctly even when some of its components fail. In a Kubernetes-based deployment, this means the system should continue to serve requests even if individual pods crash or are terminated.

## How Production Stack Achieves Fault Tolerance

The Production Stack deployment uses several Kubernetes and application-level features to achieve fault tolerance:

1. **Pod Replication**: Multiple serving engine pods are deployed, allowing the system to continue operating even if some pods fail.

2. **Session-Based Routing**: Client sessions are tracked and properly redirected when a serving pod fails.

3. **Fast Recovery**: When a pod fails, Kubernetes automatically schedules a replacement, minimizing downtime.

4. **Health Checks**: Kubernetes monitors the health of pods and restarts them if they become unresponsive.

## What the Demo Tests

Our fault tolerance demo script tests how well the system handles a pod failure during an active request:

1. It identifies which serving engine pod is handling requests for a specific user ID (9999)
2. It sends a long-running request to that pod
3. It forcibly terminates the pod while the request is being processed
4. It monitors whether the request completes successfully, which would indicate successful failover

## Expected Behavior

In a properly configured Production Stack:

1. The request should continue processing even after the pod is terminated
2. The router should automatically route subsequent requests for the same session to another available pod
3. The client should experience minimal or no interruption

## Common Issues

If the fault tolerance test fails, common causes include:

1. **Insufficient Replicas**: Having only one serving engine pod means there's nowhere to fail over to
2. **Misconfigured Routing**: The router service must be configured to properly handle session persistence
3. **Networking Issues**: Problems with network connectivity can interfere with proper failover
4. **Resource Constraints**: If the cluster is under heavy load, failover may be slow or unsuccessful