# Ollama Installation

This guide walks you through installing Ollama.

## Prerequisites

- A Kubernetes cluster
- `kubectl` configured to access the cluster
- `helm` installed  

```bash
helm repo add ollama-helm https://otwld.github.io/ollama-helm/
helm repo update
```

```bash
helm upgrade --install ollama ollama-helm/ollama --namespace ollama --create-namespace -f ollama-values.yaml
```
