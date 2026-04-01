# AgentGateway Installation

This guide walks you through installing AgentGateway.

## Prerequisites

- A Kubernetes cluster
- `kubectl` configured to access the cluster
- `helm` installed
- Gateway API CRDs installed (see [kgateway-installation](kgateway-installation.md))

## Installation

```bash
export AGENTGATEWAY_VERSION=v1.0.1
```

```bash
helm upgrade -i agentgateway-crds oci://cr.agentgateway.dev/charts/agentgateway-crds \
    --create-namespace \
    --namespace agentgateway-system \
    --version $AGENTGATEWAY_VERSION \
    --set controller.image.pullPolicy=Always
```

```bash
helm upgrade -i agentgateway oci://cr.agentgateway.dev/charts/agentgateway \
    --namespace agentgateway-system \
    --version $AGENTGATEWAY_VERSION \
    --set controller.image.pullPolicy=Always \
    --wait
```
