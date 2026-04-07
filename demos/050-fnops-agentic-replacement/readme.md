# FinOps Kagent Lab

Build a FinOps agent platform on Kubernetes using **kagent** (OSS), **agentgateway** (OSS), and a Grafana observability stack. All agents use Anthropic Claude as the LLM provider.

## Architecture

See [architecture.md](architecture.md) for the full Mermaid diagram of agents, MCPs, skills, and observability.

## Prerequisites

- Kubernetes cluster with context `finops-kagent`
- `kubectl`, `helm`, `envsubst` installed
- An Anthropic API key

---

## Step 0: Configure environment

Edit `.env` and set your `ANTHROPIC_API_KEY`, then source it.

```bash
# Edit the API key
vi .env

# Load all variables and the k alias
source .env
```

Every `kubectl` command below uses the alias `k` which includes `--context=${KUBE_CONTEXT}`.

---

## Step 1: Create namespaces

```bash
k create namespace ${KAGENT_NS} --dry-run=client -o yaml | k apply -f -
k create namespace ${TELEMETRY_NS} --dry-run=client -o yaml | k apply -f -
k create namespace ${FINOPS_NS} --dry-run=client -o yaml | k apply -f -
```

---

## Step 2: Install the observability stack

### 2.1 Loki (logs backend)

```bash
helm upgrade --install loki loki \
  --repo https://grafana.github.io/helm-charts \
  --version ${LOKI_VERSION} \
  --namespace ${TELEMETRY_NS} \
  --values manifests/loki-values.yaml \
  --kube-context ${KUBE_CONTEXT}
```

### 2.2 Tempo (traces backend)

```bash
helm upgrade --install tempo tempo \
  --repo https://grafana.github.io/helm-charts \
  --version ${TEMPO_VERSION} \
  --namespace ${TELEMETRY_NS} \
  --values manifests/tempo-values.yaml \
  --kube-context ${KUBE_CONTEXT}
```

### 2.3 OpenTelemetry Collector

```bash
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

helm upgrade --install opentelemetry-collector-audit open-telemetry/opentelemetry-collector \
  --namespace ${TELEMETRY_NS} \
  --values manifests/otel-collector-values.yaml \
  --kube-context ${KUBE_CONTEXT}
```

### 2.4 Grafana

```bash
helm upgrade --install grafana grafana \
  --repo https://grafana.github.io/helm-charts \
  --version ${GRAFANA_VERSION} \
  --namespace ${TELEMETRY_NS} \
  --values manifests/grafana-values.yaml \
  --kube-context ${KUBE_CONTEXT}
```

### 2.5 Verify observability pods

```bash
k get pods -n ${TELEMETRY_NS}
```

---

## Step 3: Install agentgateway (OSS)

agentgateway provides MCP/A2A/LLM routing on Kubernetes via the Gateway API.

### 3.1 Gateway API CRDs

```bash
k apply --server-side \
  -f https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml
```

### 3.2 agentgateway CRDs

```bash
helm upgrade -i --create-namespace \
  --namespace ${AGENTGATEWAY_NS} \
  --version ${AGENTGATEWAY_VERSION} \
  agentgateway-crds oci://cr.agentgateway.dev/charts/agentgateway-crds \
  --kube-context ${KUBE_CONTEXT}
```

### 3.3 agentgateway control plane

```bash
helm upgrade -i agentgateway oci://cr.agentgateway.dev/charts/agentgateway \
  --namespace ${AGENTGATEWAY_NS} \
  --version ${AGENTGATEWAY_VERSION} \
  --kube-context ${KUBE_CONTEXT}
```

### 3.4 Verify agentgateway

```bash
k get pods -n ${AGENTGATEWAY_NS}
```

---

## Step 4: Install kagent (OSS)

### 4.1 kagent CRDs

```bash
helm install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds \
  --namespace ${KAGENT_NS} \
  --kube-context ${KUBE_CONTEXT}
```

### 4.2 Create the Anthropic API key secret (idempotent)

```bash
k create secret generic kagent-anthropic \
  -n ${KAGENT_NS} \
  --from-literal=ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
  --dry-run=client -o yaml | k apply -f -
```

### 4.3 Install kagent with OTel + Anthropic

The values file references the OTel collector endpoints. Use `envsubst` to interpolate the API key at install time.

```bash
envsubst < manifests/kagent-values.yaml | \
  helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent \
    --namespace ${KAGENT_NS} \
    --version ${KAGENT_VERSION} \
    --values - \
    --kube-context ${KUBE_CONTEXT}
```

### 4.4 Verify kagent

```bash
k get pods -n ${KAGENT_NS}
```

---

## Step 5: Deploy the Anthropic ModelConfig

```bash
k apply -f manifests/model-config.yaml --context ${KUBE_CONTEXT}
```

Verify:

```bash
k get modelconfig -n ${KAGENT_NS} --context ${KUBE_CONTEXT}
```

---

## Step 6: Deploy the MCP tool server

This deploys a sample `fetch` MCP server that agents can use to retrieve web content.

```bash
k apply -f manifests/mcp-server-fetch.yaml --context ${KUBE_CONTEXT}
```

Verify:

```bash
k get mcpserver -n ${KAGENT_NS} --context ${KUBE_CONTEXT}
```

---

## Step 7: Deploy FinOps agents

```bash
k apply -f manifests/cost-visibility-agent.yaml --context ${KUBE_CONTEXT}
k apply -f manifests/anomaly-detection-agent.yaml --context ${KUBE_CONTEXT}
k apply -f manifests/optimization-agent.yaml --context ${KUBE_CONTEXT}
k apply -f manifests/orchestrator-agent.yaml --context ${KUBE_CONTEXT}
```

Verify all agents are accepted and ready:

```bash
k get agents -n ${KAGENT_NS} --context ${KUBE_CONTEXT}
```

---

## Step 8: Access the UIs

### kagent UI

```bash
k port-forward -n ${KAGENT_NS} svc/kagent-ui 8080:8080 --context ${KUBE_CONTEXT}
```

Open http://localhost:8080

### Grafana

```bash
k port-forward -n ${TELEMETRY_NS} svc/grafana 3000:80 --context ${KUBE_CONTEXT}
```

Open http://localhost:3000 (admin / finops)

---

## Step 9: Test an agent

In the kagent UI, select the **cost-visibility-agent** and ask:

> What Kubernetes resources are running in the kagent namespace?

Or use the CLI:

```bash
k port-forward -n ${KAGENT_NS} svc/kagent-controller 8083:8083 --context ${KUBE_CONTEXT}
```

---

## Cleanup

To tear everything down and re-run from scratch:

```bash
# Agents and CRDs
k delete -f manifests/orchestrator-agent.yaml --context ${KUBE_CONTEXT} --ignore-not-found
k delete -f manifests/optimization-agent.yaml --context ${KUBE_CONTEXT} --ignore-not-found
k delete -f manifests/anomaly-detection-agent.yaml --context ${KUBE_CONTEXT} --ignore-not-found
k delete -f manifests/cost-visibility-agent.yaml --context ${KUBE_CONTEXT} --ignore-not-found
k delete -f manifests/mcp-server-fetch.yaml --context ${KUBE_CONTEXT} --ignore-not-found
k delete -f manifests/model-config.yaml --context ${KUBE_CONTEXT} --ignore-not-found

# kagent
helm uninstall kagent -n ${KAGENT_NS} --kube-context ${KUBE_CONTEXT}
helm uninstall kagent-crds -n ${KAGENT_NS} --kube-context ${KUBE_CONTEXT}

# agentgateway
helm uninstall agentgateway -n ${AGENTGATEWAY_NS} --kube-context ${KUBE_CONTEXT}
helm uninstall agentgateway-crds -n ${AGENTGATEWAY_NS} --kube-context ${KUBE_CONTEXT}
k delete -f https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml --ignore-not-found

# Observability
helm uninstall opentelemetry-collector-audit -n ${TELEMETRY_NS} --kube-context ${KUBE_CONTEXT}
helm uninstall grafana -n ${TELEMETRY_NS} --kube-context ${KUBE_CONTEXT}
helm uninstall tempo -n ${TELEMETRY_NS} --kube-context ${KUBE_CONTEXT}
helm uninstall loki -n ${TELEMETRY_NS} --kube-context ${KUBE_CONTEXT}

# Namespaces
k delete namespace ${KAGENT_NS} --context ${KUBE_CONTEXT} --ignore-not-found
k delete namespace ${TELEMETRY_NS} --context ${KUBE_CONTEXT} --ignore-not-found
k delete namespace ${AGENTGATEWAY_NS} --context ${KUBE_CONTEXT} --ignore-not-found
k delete namespace ${FINOPS_NS} --context ${KUBE_CONTEXT} --ignore-not-found
```

---

## File structure

```
.
├── .env                                    # Environment variables (source before running)
├── readme.md                               # This lab guide
├── plan.md                                 # Full FinOps replacement plan
└── manifests/
    ├── kagent-values.yaml                  # Helm values: kagent + Anthropic + OTel
    ├── loki-values.yaml                    # Helm values: Grafana Loki
    ├── tempo-values.yaml                   # Helm values: Grafana Tempo
    ├── grafana-values.yaml                 # Helm values: Grafana dashboards
    ├── otel-collector-values.yaml          # Helm values: OTel Collector
    ├── model-config.yaml                   # kagent ModelConfig CRD (Anthropic Claude)
    ├── mcp-server-fetch.yaml               # Sample MCP server (web fetch)
    ├── cost-visibility-agent.yaml          # Agent: cost queries and breakdowns
    ├── anomaly-detection-agent.yaml        # Agent: cost spike/drop detection
    ├── optimization-agent.yaml             # Agent: idle/orphaned resource detection
    └── orchestrator-agent.yaml             # Agent: routes to domain agents
```

## References

- [kagent docs](https://kagent.dev/docs/kagent/introduction/installation)
- [agentgateway on Kubernetes](https://agentgateway.dev/docs/kubernetes/main/install/helm/)
- [kagent observability](https://kagent.dev/docs/kagent/observability/audit-prompts)
- [kagent Anthropic provider](https://kagent.dev/docs/kagent/supported-providers/anthropic)
