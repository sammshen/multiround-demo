#! /bin/bash

helm uninstall vllm
helm repo add vllm https://vllm-project.github.io/production-stack
helm install vllm vllm/vllm-stack -f multi-vllm-lmcache.yaml

sleep 5

echo "Waiting for all vLLM pods to be ready..."
TIMEOUT=1200
START_TIME=$(date +%s)
while true; do
  CURRENT_TIME=$(date +%s)
  ELAPSED_TIME=$((CURRENT_TIME - START_TIME))
  if [ $ELAPSED_TIME -gt $TIMEOUT ]; then
    echo "❌ Timeout reached! Pods not ready after 20 minutes."
    kubectl get pods
    kubectl delete all --all
    exit 1
  fi

  PODS=$(kubectl get pods 2>/dev/null)

  TOTAL=$(echo "$PODS" | tail -n +2 | wc -l)
  READY=$(echo "$PODS" | grep '1/1' | wc -l)

#   if echo "$PODS" | grep -E 'CrashLoopBackOff|Error|ImagePullBackOff' > /dev/null; then
#     echo "❌ Detected pod in CrashLoopBackOff / Error / ImagePullBackOff state!"
#     kubectl get pods
#     kubectl get pods --no-headers -o custom-columns=":metadata.name" | grep '^vllm-' | xargs kubectl describe pod
#     kubectl delete all --all
#     exit 1
#   fi

#   kubectl get pods -o name | grep deployment-vllm | while read pod; do
#     echo "Checking logs for $pod for CUDA OOM"
#     if kubectl logs $pod --tail=50 | grep "CUDA out of memory" >/dev/null; then
#       echo "❗ CUDA OOM detected in $pod"
#       kubectl get pods
#       kubectl get pods --no-headers -o custom-columns=":metadata.name" | grep '^vllm-' | xargs kubectl describe pod
#       kubectl delete all --all
#       exit 1
#     fi
#   done

  if [ "$READY" -eq "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
    echo "✅ All $TOTAL pods are running and ready."
    kubectl get pods
    break
  else
    echo "⏳ $READY/$TOTAL pods ready... (${ELAPSED_TIME}s elapsed out of ${TIMEOUT}s timeout)"
    kubectl get pods
    sleep 15
  fi
done


# Kill any existing processes on port 30080
echo "Checking for existing processes on port 30080..."
PIDS=$(ps aux | grep "port-forward.*30080" | grep -v grep | awk '{print $2}')
if [ ! -z "$PIDS" ]; then
    echo "Found processes on port 30080, killing them..."
    echo "$PIDS" | xargs sudo kill -9
    echo "✅ Processes killed"
else
    echo "No processes found on port 30080"
fi


# Start port forwarding as a daemon
echo "Starting port forwarding as daemon on port 30080..."
nohup kubectl port-forward svc/vllm-router-service 30080:80 > /tmp/vllm-portforward.log 2>&1 &
PORTFORWARD_PID=$!
echo "✅ Port forwarding started as daemon with PID: $PORTFORWARD_PID"
echo "📝 Port forwarding logs available at: /tmp/vllm-portforward.log"