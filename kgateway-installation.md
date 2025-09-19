# KGateway Installation

This guide walks you through installing KGateway with AgentGateway.

## Prerequisites

- A Kubernetes cluster
- `kubectl` configured to access the cluster
- `helm` installed  

```bash
helm upgrade -i kgateway-crds oci://cr.kgateway.dev/kgateway-dev/charts/kgateway-crds \
    --create-namespace \
    --namespace kgateway-system \
    --version v2.1.0-main \
    --set controller.image.pullPolicy=Always
```

Install kgateway with AgentGateway enabled

```bash
helm upgrade -i kgateway oci://cr.kgateway.dev/kgateway-dev/charts/kgateway \
    --namespace kgateway-system \
    --create-namespace \
    --version v2.1.0-main \
    --set controller.image.pullPolicy=Always \
    --set agentGateway.enabled=true \
    --set agentGateway.enableAlphaAPIs=true
```