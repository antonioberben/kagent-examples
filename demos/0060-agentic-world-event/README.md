# Agentic World Event - Kagent Enterprise Lab

This lab demonstrates enterprise-grade policy-based access control for AI agents using Solo's enterprise products. Two custom agents (team1, team2-not-allowed) have identical configuration, but team2 is blocked from accessing k8s-agent by an Istio AuthorizationPolicy enforced at the waypoint proxy.

## Demo Scenario

- **team1** agent -> calls k8s-agent -> **ALLOWED** (200 OK)
- **team2-not-allowed** agent -> calls k8s-agent -> **DENIED** (403 Forbidden - RBAC: access denied)

Both agents have the same tools, same system prompt structure, same model. The only difference is the `AGENT_IDENTITY` env var and the service account name. Policy enforcement is external to the agents.

## Architecture

```
                         User (UI)
                            |
                     kagent-controller
                            |
                   +--------+--------+
                   |                 |
                 team1         team2-not-allowed
                   |                 |
                   |    A2A (direct pod-to-pod)
                   |                 |
              kagent-waypoint (L7 proxy)
              [AuthorizationPolicy]
                   |                 |
                   v                 v
              k8s-agent         k8s-agent
              200 OK            403 Forbidden
```

**Enforcement chain:**
1. `istio-base` Helm chart -> provides AuthorizationPolicy CRD
2. `istio.io/dataplane-mode=ambient` on namespace -> enrolls pods in mesh with mTLS identity
3. `istio.io/use-waypoint=kagent-waypoint` on k8s-agent service -> routes traffic through L7 waypoint
4. `AuthorizationPolicy` targeting waypoint -> DENY rule matching team2's SPIFFE identity

## Components

| Component | Purpose |
|-----------|---------|
| Solo Enterprise for Istio (ambient) | Zero-trust mTLS, ztunnel, waypoint proxy for L7 policy |
| Solo Enterprise for Agentgateway | Gateway + HTTPRoute for A2A, EnterpriseAgentgatewayPolicy |
| Solo Enterprise for Kagent | Agent runtime, controller, 10 community agents |
| AgentRegistry | Centralized agent/skill/MCP discovery with pgvector |
| Management UI | Solo Enterprise UI with OIDC auto provider, ClickHouse telemetry |

### Community Agents (10)

k8s-agent, istio-agent, kgateway-agent, helm-agent, observability-agent, promql-agent, argo-rollouts-agent, cilium-policy-agent, cilium-manager-agent, cilium-debug-agent

### Custom Agents (2)

- **team1** - Authorized orchestrator with A2A tools to community agents
- **team2-not-allowed** - Identical config but blocked by policy

## Prerequisites

1. Kind cluster with context `agentic-world`
2. `kubectl`, `helm` (v3.12+), `openssl`
3. Environment variables in `.env`:

```bash
export KUBE_CONTEXT=agentic-world
export OPENAI_API_KEY=<your-openai-key>
export SOLO_ISTIO_LICENSE_KEY=<license>
export GLOO_GATEWAY_LICENSE_KEY=<license>
export AGENTGATEWAY_LICENSE_KEY=<license>
```

## Installation

### Step 1: Source Environment

```bash
source .env
```

### Step 2: Create Namespaces

```bash
kubectl create namespace istio-system --context $KUBE_CONTEXT
kubectl create namespace kagent --context $KUBE_CONTEXT
kubectl create namespace agentgateway-system --context $KUBE_CONTEXT
```

### Step 3: Create OpenAI Secret

Agents need an API key to connect to OpenAI.

```bash
kubectl create secret generic llm-api-keys \
  --namespace kagent \
  --context $KUBE_CONTEXT \
  --from-literal=OPENAI_API_KEY=$OPENAI_API_KEY
```

### Step 4: Install Gateway API CRDs

Required by both Istio waypoint gateways and enterprise-agentgateway.

```bash
GATEWAY_API_VERSION=$(curl -s https://api.github.com/repos/kubernetes-sigs/gateway-api/releases/latest | grep tag_name | cut -d '"' -f 4)
kubectl apply -f \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml \
  --context $KUBE_CONTEXT
```

### Step 5: Install Istio Ambient Mesh (Solo Distribution)

Istio ambient mesh provides mTLS identity (SPIFFE) for every pod, which is how the authorization policy identifies team1 vs team2.

```bash
export ISTIO_VERSION=1.29.1
export ISTIO_IMAGE=${ISTIO_VERSION}-solo
export REPO=us-docker.pkg.dev/soloio-img/istio
export HELM_REPO=us-docker.pkg.dev/soloio-img/istio-helm

cat > /tmp/istio-values.yaml <<EOF
global:
  hub: ${REPO}
  tag: ${ISTIO_IMAGE}
profile: ambient
EOF
```

**5a. Install Istio base CRDs** - This provides the `AuthorizationPolicy` CRD. Without this chart, the policy cannot be created.

```bash
helm install istio-base istio/base \
  --namespace istio-system \
  --version ${ISTIO_VERSION} \
  --kube-context $KUBE_CONTEXT
```

**5b. Install istiod (control plane)**

```bash
helm upgrade --install istiod-solo oci://${HELM_REPO}/istiod \
  --version ${ISTIO_VERSION} \
  --namespace istio-system \
  --kube-context $KUBE_CONTEXT \
  --values /tmp/istio-values.yaml
```

**5c. Install Istio CNI**

```bash
helm upgrade --install istio-cni oci://${HELM_REPO}/cni \
  --version ${ISTIO_VERSION} \
  --namespace istio-system \
  --kube-context $KUBE_CONTEXT \
  --values /tmp/istio-values.yaml
```

**5d. Install ztunnel** - The per-node proxy that encrypts all pod traffic with mTLS.

```bash
helm upgrade --install ztunnel oci://${HELM_REPO}/ztunnel \
  --version ${ISTIO_VERSION} \
  --namespace istio-system \
  --kube-context $KUBE_CONTEXT \
  --values /tmp/istio-values.yaml
```

**5e. Wait and enable ambient mode** - Labeling the namespace enrolls all pods in the mesh.

```bash
kubectl wait --for=condition=ready pod -l app=istiod -n istio-system --timeout=120s --context $KUBE_CONTEXT
kubectl wait --for=condition=ready pod -l app=ztunnel -n istio-system --timeout=120s --context $KUBE_CONTEXT

# Enroll kagent namespace in ambient mesh
kubectl label namespace kagent istio.io/dataplane-mode=ambient --context $KUBE_CONTEXT
```

### Step 6: Install Agentgateway Enterprise

Provides the `EnterpriseAgentgatewayPolicy` CRD and the gateway proxy for A2A traffic routing.

```bash
helm upgrade -i --create-namespace \
  --namespace agentgateway-system \
  --version v2.2.0 \
  enterprise-agentgateway-crds \
  oci://us-docker.pkg.dev/solo-public/enterprise-agentgateway/charts/enterprise-agentgateway-crds \
  --kube-context $KUBE_CONTEXT

helm upgrade -i -n agentgateway-system enterprise-agentgateway \
  oci://us-docker.pkg.dev/solo-public/enterprise-agentgateway/charts/enterprise-agentgateway \
  --version v2.2.0 \
  --kube-context $KUBE_CONTEXT \
  --set-string licensing.licenseKey=${AGENTGATEWAY_LICENSE_KEY}
```

### Step 7: Install Kagent Enterprise

Deploys the kagent controller, 10 community agents, and the UI.

- `manifests/kagent-enterprise-values.yaml` - Enables all 10 community agents with resource limits, OIDC auto provider, OTel tracing to telemetry-collector, and `controller.a2aBaseUrl` pointing to the gateway.

```bash
helm upgrade --install kagent-crds \
  oci://us-docker.pkg.dev/solo-public/kagent-enterprise-helm/charts/kagent-enterprise-crds \
  --namespace kagent \
  --kube-context $KUBE_CONTEXT \
  --version 0.3.14

helm upgrade --install kagent \
  oci://us-docker.pkg.dev/solo-public/kagent-enterprise-helm/charts/kagent-enterprise \
  --namespace kagent \
  --kube-context $KUBE_CONTEXT \
  --version 0.3.14 \
  --values manifests/kagent-enterprise-values.yaml \
  --set licensing.licenseKey=$GLOO_GATEWAY_LICENSE_KEY
```

### Step 8: Install Management UI

Provides the Solo Enterprise UI with OIDC auto provider and ClickHouse for telemetry storage.

- `manifests/management-values.yaml` - Registers `kagent-enterprise` as a static OIDC client for OBO token exchange.

```bash
helm upgrade -i kagent-mgmt \
  oci://us-docker.pkg.dev/solo-public/solo-enterprise-helm/charts/management \
  --namespace kagent \
  --kube-context $KUBE_CONTEXT \
  --version 0.3.14 \
  --values manifests/management-values.yaml \
  --set licensing.licenseKey=$GLOO_GATEWAY_LICENSE_KEY
```

```bash
KAGENT_URL=$(kubectl --context $KUBE_CONTEXT get svc solo-enterprise-ui -n kagent -o jsonpath="{.status.loadBalancer.ingress[0]['hostname','ip']}")
echo $KAGENT_URL
open http://$KAGENT_URL
```

### Step 9: Install AgentRegistry

Centralized discovery for agents, skills, and MCP servers. Uses PostgreSQL with pgvector for semantic search.

- `manifests/postgres-pgvector.yaml` - External PostgreSQL 16 with pgvector extension.
- `manifests/agentregistry-values.yaml` - AgentRegistry configuration with MCP servers and skill registrations.

```bash
export AGENT_REGISTRY_JWT=$(openssl rand -hex 32)

kubectl apply -f manifests/postgres-pgvector.yaml --context $KUBE_CONTEXT

helm upgrade --install agentregistry \
  oci://ghcr.io/agentregistry-dev/agentregistry/charts/agentregistry \
  --namespace agentregistry \
  --create-namespace \
  --kube-context $KUBE_CONTEXT \
  --version 0.3.3 \
  --set config.jwtPrivateKey="$AGENT_REGISTRY_JWT" \
  --set database.postgres.bundled.enabled=false \
  --set-string database.postgres.url="postgres://agentregistry:agentregistry@postgres-pgvector.agentregistry.svc.cluster.local:5432/agent-registry?sslmode=disable" \
  --set database.postgres.vectorEnabled=true \
  --set service.type=LoadBalancer \
  -f manifests/agentregistry-values.yaml \
  --set config.disableBuiltinSeed="false"
```

```bash
AGENT_REGISTRY_URL=$(kubectl --context $KUBE_CONTEXT get svc agentregistry -n agentregistry -o jsonpath="{.status.loadBalancer.ingress[0]['hostname','ip']}")
echo $AGENT_REGISTRY_URL
open http://$AGENT_REGISTRY_URL:12121
```

Create a new package in the registry for the everything server:

>Server Name: example.com/server-everything
>Display title: everything server
>Version: 0.0.1
>Description: Everything server catalog entry
>Click "Add Package"
>Package identifier: @modelcontextprotocol/server-everything
>Package version: 2025.9.25

Deploy the everything server MCP server (not strictly required for the demo, but shows how to register MCP servers in the registry):

```bash
arctl deployments create user/my-mcp-server \
 --type mcp \
 --provider-id kubernetes-default \
 --namespace default \
 --version 0.1.0
```

### Step 10: Deploy Istio Waypoint Gateway

The waypoint proxy is the L7 enforcement point. Traffic to services labeled with `istio.io/use-waypoint=kagent-waypoint` is routed through this proxy, where AuthorizationPolicy rules are evaluated.

- `manifests/kagent-waypoint.yaml` - Istio waypoint Gateway (HBONE protocol on port 15008).

```bash
kubectl apply -f manifests/kagent-waypoint.yaml --context $KUBE_CONTEXT
kubectl wait --for=condition=Programmed gateway kagent-waypoint -n kagent --timeout=120s --context $KUBE_CONTEXT
```

### Step 11: Deploy A2A Gateway and Enterprise Policies

- `manifests/a2a-gateway.yaml` - Gateway + HTTPRoute for A2A traffic (port 8083, path `/api/a2a/`).
- `manifests/a2a-authz-policy.yaml` - 5 EnterpriseAgentgatewayPolicy resources for gateway-routed A2A traffic.

```bash
kubectl apply -f manifests/a2a-gateway.yaml --context $KUBE_CONTEXT
kubectl apply -f manifests/a2a-authz-policy.yaml --context $KUBE_CONTEXT
```

### Step 12: Deploy Custom Agents

- `manifests/team1-agent.yaml` - Authorized agent (AGENT_IDENTITY=team1)
- `manifests/team2-not-allowed-agent.yaml` - Blocked agent (AGENT_IDENTITY=team2-not-allowed)

Both agents have identical tools (k8s-agent, istio-agent, kgateway-agent, helm-agent) and identical system prompt structure. The only difference is the service account name, which is what the policy uses to distinguish them.

```bash
kubectl apply -f manifests/team1-agent.yaml --context $KUBE_CONTEXT
kubectl apply -f manifests/team2-not-allowed-agent.yaml --context $KUBE_CONTEXT
```

### Step 13: Label Services for Waypoint Routing

This is the critical step that makes policy enforcement work. Labeling agent services with `istio.io/use-waypoint` causes all inbound traffic to route through the waypoint proxy, where the AuthorizationPolicy is enforced.

Without these labels, agents call each other directly (pod-to-pod) and bypass all policies.

```bash
kubectl label service k8s-agent istio-agent helm-agent kgateway-agent kagent-controller \
  -n kagent \
  --context $KUBE_CONTEXT \
  istio.io/use-waypoint=kagent-waypoint
```

### Step 14: Apply Istio AuthorizationPolicy

This is the actual enforcement mechanism. It targets the waypoint Gateway and denies any request from the `team2-not-allowed` service account to the k8s-agent service.

- `manifests/istio-authz-policy.yaml` - DENY rule matching team2's SPIFFE identity (`spiffe://cluster.local/ns/kagent/sa/team2-not-allowed`).

```bash
kubectl apply -f manifests/istio-authz-policy.yaml --context $KUBE_CONTEXT
```

Verify the policy is bound to the waypoint:

```bash
kubectl describe authorizationpolicy -n kagent deny-team2-to-k8s-agent | grep "Message:"
# Expected: "bound to kagent/kagent-waypoint"
```

## Verification

### Check All Pods

```bash
kubectl get pods -n kagent --context $KUBE_CONTEXT
# Should show ~21 pods (controller, 10 community agents, 2 custom agents, UI, postgres, clickhouse, waypoint, etc.)

kubectl get agents -n kagent --context $KUBE_CONTEXT
# Should show 12 agents (10 community + team1 + team2-not-allowed)
```

### Test Policy Enforcement (CLI)

```bash
# team2 should be DENIED
kubectl exec -n kagent deployment/team2-not-allowed -- \
  curl -s -w "\nHTTP_CODE: %{http_code}\n" http://k8s-agent.kagent:8080/.well-known/agent-card.json | tail -2
# Expected: RBAC: access denied
#           HTTP_CODE: 403

# team1 should be ALLOWED
kubectl exec -n kagent deployment/team1 -- \
  curl -s -w "\nHTTP_CODE: %{http_code}\n" http://k8s-agent.kagent:8080/.well-known/agent-card.json | tail -2
# Expected: ...agent card JSON...
#           HTTP_CODE: 200
```

### Test Policy Enforcement (UI)

```bash
kubectl port-forward -n kagent svc/kagent-ui 8080:8080 --context $KUBE_CONTEXT
# Open http://localhost:8080
```

1. Select **team1** -> Send "List all pods in the kagent namespace" -> Should succeed
2. Select **team2-not-allowed** -> Send "List all pods" -> Should fail with access denied

## Manifest Files

| File | Resources | Purpose |
|------|-----------|---------|
| `kagent-enterprise-values.yaml` | Helm values | 10 community agents, OIDC, OTel tracing, A2A gateway routing |
| `management-values.yaml` | Helm values | Solo Enterprise UI, OIDC static client for OBO tokens, ClickHouse |
| `agentregistry-values.yaml` | Helm values | AgentRegistry with MCP servers and skill definitions |
| `postgres-pgvector.yaml` | Namespace, PVC, Deployment, Service | PostgreSQL 16 + pgvector for AgentRegistry |
| `team1-agent.yaml` | Agent | Authorized orchestrator with A2A tools |
| `team2-not-allowed-agent.yaml` | Agent | Blocked orchestrator (identical config, different identity) |
| `kagent-waypoint.yaml` | Gateway (istio-waypoint) | L7 proxy for AuthorizationPolicy enforcement |
| `a2a-gateway.yaml` | Gateway, HTTPRoute | Enterprise agentgateway for `/api/a2a/` routing |
| `a2a-authz-policy.yaml` | 5x EnterpriseAgentgatewayPolicy | Gateway-level ALLOW/DENY rules (CEL + JWT) |
| `istio-authz-policy.yaml` | AuthorizationPolicy | **The actual enforcement** - DENY team2 at waypoint L7 |

## How Policy Enforcement Works

Agents discover each other via Kubernetes DNS and call services directly (pod-to-pod). This means EnterpriseAgentgatewayPolicy (which applies to HTTPRoute traffic) is not sufficient alone - it only covers calls routed through the gateway.

The actual enforcement uses **Istio AuthorizationPolicy** at the waypoint proxy:

1. **Ambient mesh** assigns each pod a SPIFFE identity based on its service account
2. **Waypoint label** on the k8s-agent service routes all inbound traffic through the waypoint proxy
3. **AuthorizationPolicy** at the waypoint inspects the source identity and denies `team2-not-allowed`

```yaml
# istio-authz-policy.yaml - the key resource
spec:
  targetRefs:
    - group: gateway.networking.k8s.io
      kind: Gateway
      name: kagent-waypoint      # Enforced at L7 waypoint
  action: DENY
  rules:
    - from:
        - source:
            principals:
              - "cluster.local/ns/kagent/sa/team2-not-allowed"  # SPIFFE identity
      to:
        - operation:
            hosts: ["k8s-agent*"]
            ports: ["8080"]
```

### Why Both Policy Layers Exist

| Layer | Scope | Mechanism |
|-------|-------|-----------|
| `a2a-authz-policy.yaml` | Gateway-routed A2A calls | EnterpriseAgentgatewayPolicy with CEL + JWT claims |
| `istio-authz-policy.yaml` | Direct pod-to-pod calls | Istio AuthorizationPolicy with SPIFFE identity |

The Istio policy is defense-in-depth: even if agents bypass the gateway, the waypoint proxy still blocks unauthorized access.

## Troubleshooting

### Policy Not Working

Check the full enforcement chain:

```bash
# 1. Is istio-base installed? (provides AuthorizationPolicy CRD)
kubectl get crd authorizationpolicies.security.istio.io
# If missing: helm install istio-base istio/base -n istio-system --version 1.29.1

# 2. Is namespace in ambient mode?
kubectl get namespace kagent -o jsonpath='{.metadata.labels.istio\.io/dataplane-mode}'
# Should return: ambient

# 3. Is k8s-agent service labeled for waypoint?
kubectl get svc k8s-agent -n kagent -o jsonpath='{.metadata.labels.istio\.io/use-waypoint}'
# Should return: kagent-waypoint

# 4. Is the AuthorizationPolicy bound to waypoint?
kubectl describe authorizationpolicy -n kagent deny-team2-to-k8s-agent | grep "Message:"
# Should say: "bound to kagent/kagent-waypoint"

# 5. Is waypoint pod running?
kubectl get pods -n kagent -l gateway.networking.k8s.io/gateway-name=kagent-waypoint
```

### Service Labels Lost After Helm Upgrade

The `istio.io/use-waypoint` labels are applied manually (Step 13) and may be removed if the kagent Helm chart recreates services. Re-apply after upgrades:

```bash
kubectl label service k8s-agent istio-agent helm-agent kgateway-agent kagent-controller \
  -n kagent istio.io/use-waypoint=kagent-waypoint
```

### Agent Pods in CreateContainerConfigError

The `llm-api-keys` secret is missing:

```bash
kubectl create secret generic llm-api-keys \
  --namespace kagent \
  --from-literal=OPENAI_API_KEY=$OPENAI_API_KEY
```

## Cleanup

```bash
kubectl delete namespace kagent agentregistry agentgateway-system --context $KUBE_CONTEXT
helm uninstall istio-base istiod-solo istio-cni ztunnel -n istio-system --kube-context $KUBE_CONTEXT
kubectl delete namespace istio-system --context $KUBE_CONTEXT
```

## References

- [Solo Enterprise for Kagent](https://docs.solo.io/kagent-enterprise/docs/latest/install/)
- [Solo Enterprise for Agentgateway](https://docs.solo.io/gateway/2.0.x/ai/about/)
- [Istio Ambient Mesh](https://istio.io/latest/docs/ops/ambient/)
- [Istio AuthorizationPolicy](https://istio.io/latest/docs/reference/config/security/authorization-policy/)
- [A2A Protocol](https://a2a-protocol.org/)
