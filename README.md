# kagent-examples

This repo is set of examples for kagent.

## Ecosystem Installation

### Ollama

```bash
helm repo add ollama-helm https://otwld.github.io/ollama-helm/
helm repo update
```

```bash
helm upgrade --install ollama ollama-helm/ollama --namespace ollama --create-namespace -f ollama-values.yaml
```

### MCP Server Kubernetes

It is based on Flux159's MCP Server Kubernetes and Strowk's MCP K8s Go.

https://github.com/Flux159/mcp-server-kubernetes


deploy kuberbnetes mcp server2 (https://github.com/Flux159/mcp-server-kubernetes)

```bash
kubectl apply -f mcp-servers/k8smcpserver.yaml
```

### DevPod

Since kagent uses devcontainers, to help on development, you can use DevPod[https://devpod.sh/] to run the examples in a containerized environment.


```bash

```

### API Key for OpenAI

You need to set the `OPENAI_API_KEY` environment variable with your OpenAI API key.

```bash
kubectl apply -f- <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: openai-secret
  namespace: kgateway-system
  labels:
    app: ai-kgateway
type: Opaque
stringData:
  Authorization: $OPENAI_API_KEY
EOF
```

### Kagent

Install Kagent

```bash
helm upgrade --install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds \
    --namespace kagent \
    --create-namespace \

```

```bash
helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent \
    --namespace kagent \
    --create-namespace \
    --set providers.openAI.apiKey=$OPENAI_API_KEY \
    --set service.type=LoadBalancer \
    -f kagent-values.yaml

```

```bash
kubectl apply -f kagent/my-agent.yaml
kubectl apply -f kagent/my-agent.yaml
```

Add kuberentes mcp server to my-agent

```bash
kubectl apply -f kagent/kubectl-toolserver.yaml
```