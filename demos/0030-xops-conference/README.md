# X-Ops Conference Demo

## Prerequisites

- A Kubernetes cluster
- `kubectl` configured to access the cluster
- `helm` installed
- OpenAI API key (can be obtained from OpenAI)

## Kagent Installation

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


## Kgateway Installation

This guide walks you through installing KGateway with AgentGateway.

```bash
export KGATEWAY_VERSION=v2.1.1
```

```bash
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.0/standard-install.yaml
```

```bash
helm upgrade -i kgateway-crds oci://cr.kgateway.dev/kgateway-dev/charts/kgateway-crds \
    --create-namespace \
    --namespace kgateway-system \
    --version $KGATEWAY_VERSION \
    --set controller.image.pullPolicy=Always
```

Install kgateway with AgentGateway enabled

```bash
helm upgrade -i kgateway oci://cr.kgateway.dev/kgateway-dev/charts/kgateway \
    --namespace kgateway-system \
    --create-namespace \
    --version $KGATEWAY_VERSION \
    --set controller.image.pullPolicy=Always \
    --set agentGateway.enabled=true \
    --set agentGateway.enableAlphaAPIs=true
```

Deploy a gateway to access the kagent UI:

```bash
kubectl apply -f gateway.yaml
```

Get the gateway IP and register a domain:

```bash
export GW_IP=$(kubectl get gtw -n kagent kagent-gw-ui -ojsonpath='{.status.addresses[0].value}')
../../register-domain.sh my-kagent.example ${GW_IP}
```

Access the UI at http://my-kagent.example:8080


## Run the demo

## Manolo descubre qu'e es la IA

[N/A]

## Manolo usa la IA

[N/A]

## Manolo use RAG con la IA


## Manolo conecta a los servicios de su empresa con agentes de IA y servidores MCP

Manolo descubre kagent. Despliega un agente.

```bash
kubectl apply -f manolo-agent-v1.yaml
```

Manolo conecta su agente a su servidor MCP corporativo.

```bash
kubectl apply -f manolo-agent-v2.yaml
```

## Manolo aplica seguridad con agentgateway

Manolo aplica gardrails.

```bash
kubectl apply -f manolo-agent-v3.yaml
```

Manolo un gateway para aplicar AuthN y AuthZ

```bash
kubectl apply -f manolo-agentgateway.yaml
```

## Manolo aplica Agentic AI (multi-agent, A2A)

```bash
kubectl apply -f manolo-agent-v4.yaml
```

## Manolo crea un agente para publicar articulos en Linkedin

