# KAgent Installation

This guide walks you through installing KAgent

## Prerequisites

- A Kubernetes cluster
- `kubectl` configured to access the cluster
- `helm` installed
- OpenAI API key (can be obtained from OpenAI)

## Installation

Load environment variables and install `meshctl`:

Copy .env-template to .env and fill in the variables.

```bash
source .env
```

If using OpenAI:

```bash
export OPENAI_API_KEY=
```

```bash
export KAGENT_VERSION=0.7.4
```

```bash
helm upgrade --install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds \
    --namespace kagent \
    --version $KAGENT_VERSION \
    --create-namespace
```

```bash
helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent \
    --namespace kagent \
    --create-namespace \
    --version $KAGENT_VERSION \
    --set providers.openAI.apiKey=$OPENAI_API_KEY \
    --set service.type=LoadBalancer
```