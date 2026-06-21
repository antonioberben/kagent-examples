# Agentic AI Kagent - Kagent Enterprise Lab

This lab demonstrates enterprise-grade policy-based access control for AI agents using Solo's enterprise products. Two custom agents (team1, team2-not-allowed) have identical configuration, but team2 is blocked from accessing k8s-agent by an **AccessPolicy**, the native kagent-enterprise authorization resource, enforced at the agent's agentgateway waypoint.

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
                   |   A2A call to k8s-agent
                   |                 |
                   v                 v
          agent-k8s-agent-waypoint (agentgateway, L7)
          [AccessPolicy -> EnterpriseAgentgatewayPolicy]
                   |                 |
                 ALLOW             DENY
                   |                 |
                   v                 v
               k8s-agent           403 Forbidden
               200 OK
```

**Enforcement chain:**
1. `kagent-enterprise` -> provides the `AccessPolicy` CRD and the controller that translates it.
2. `istio.io/dataplane-mode=ambient` on the namespace -> enrolls pods in the mesh with mTLS (SPIFFE) identity.
3. `kagent.solo.io/waypoint=true` on the target Agent (`k8s-agent`) -> the controller provisions an agentgateway waypoint in front of it (`agent-k8s-agent-waypoint`) and repoints the service's `istio.io/use-waypoint` label automatically.
4. `AccessPolicy` (subject = Agent, target = Agent, action ALLOW/DENY) -> the controller generates an `EnterpriseAgentgatewayPolicy` on the agent's HTTPRoute. The waypoint enforces it by matching the caller's SPIFFE identity.

## Components

| Component | Purpose |
|-----------|---------|
| Solo Enterprise for Istio (ambient) | Zero-trust mTLS, ztunnel, SPIFFE identity per pod |
| Solo Enterprise for Agentgateway | Per-agent agentgateway waypoint that enforces AccessPolicy, plus the A2A data-path gateway |
| Solo Enterprise for Kagent | Agent runtime, controller (AccessPolicy translation), community agents, UI |
| AgentRegistry | Centralized agent/skill/MCP **discovery/catalog** with pgvector (not runtime or policy) |
| Management UI | Solo Enterprise UI with OIDC auto provider, ClickHouse telemetry |

### Community Agents

k8s-agent, istio-agent, kgateway-agent, helm-agent, promql-agent, argo-rollouts-agent, cilium-policy-agent, cilium-manager-agent, cilium-debug-agent (observability-agent is disabled in this lab).

### Custom Agents (2)

- **team1** - Authorized orchestrator with A2A tools to community agents
- **team2-not-allowed** - Identical config but blocked by policy

## Prerequisites

1. Kind cluster with context `$KUBE_CONTEXT` and kubectl configured
2. `kubectl`, `helm` (v3.12+), `openssl`
3. Environment variables in `.env`:

```bash
export KUBE_CONTEXT=<your-kube-context>
export OPENAI_API_KEY=<your-openai-key>
export SOLO_ISTIO_LICENSE_KEY=<license>
export GLOO_GATEWAY_LICENSE_KEY=<license>
export AGENTGATEWAY_LICENSE_KEY=<license>
```

## Quick start

The whole lab is scripted. From this directory:

```bash
./deploy.sh    # install everything end-to-end
./test.sh      # verify policy enforcement (team1 200, team2 403)
./cleanup.sh   # tear down in reverse order
```

The sections below document the same flow step by step for reference. Pinned versions live in `.env` (Istio `1.30.0-solo`, enterprise-agentgateway `v2026.5.2`, kagent-enterprise `0.4.4`, agentregistry `0.3.3`, Gateway API `v1.2.1`).

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
kubectl apply -f \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml \
  --context $KUBE_CONTEXT
```

### Step 5: Install Istio Ambient Mesh (Solo Distribution)

Istio ambient mesh provides mTLS identity (SPIFFE) for every pod, which is how the AccessPolicy identifies team1 vs team2.

```bash
cat > /tmp/istio-values.yaml <<EOF
global:
  hub: ${ISTIO_REPO}
  tag: ${ISTIO_IMAGE_TAG}
profile: ambient
EOF
```

**5a. Install Istio base CRDs**

```bash
helm upgrade --install istio-base oci://${ISTIO_HELM_REPO}/base \
  --namespace istio-system \
  --version ${ISTIO_VERSION} \
  --kube-context $KUBE_CONTEXT
```

**5b. Install istiod (control plane)**

```bash
helm upgrade --install istiod-solo oci://${ISTIO_HELM_REPO}/istiod \
  --version ${ISTIO_VERSION} \
  --namespace istio-system \
  --kube-context $KUBE_CONTEXT \
  --values /tmp/istio-values.yaml
```

**5c. Install Istio CNI**

```bash
helm upgrade --install istio-cni oci://${ISTIO_HELM_REPO}/cni \
  --version ${ISTIO_VERSION} \
  --namespace istio-system \
  --kube-context $KUBE_CONTEXT \
  --values /tmp/istio-values.yaml
```

**5d. Install ztunnel** - The per-node proxy that encrypts all pod traffic with mTLS.

```bash
helm upgrade --install ztunnel oci://${ISTIO_HELM_REPO}/ztunnel \
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

Provides the agentgateway waypoint that fronts each policy-protected agent and enforces the generated `EnterpriseAgentgatewayPolicy`.

```bash
helm upgrade -i --create-namespace \
  --namespace agentgateway-system \
  --version ${AGENTGATEWAY_VERSION} \
  enterprise-agentgateway-crds \
  oci://us-docker.pkg.dev/solo-public/enterprise-agentgateway/charts/enterprise-agentgateway-crds \
  --kube-context $KUBE_CONTEXT

helm upgrade -i -n agentgateway-system enterprise-agentgateway \
  oci://us-docker.pkg.dev/solo-public/enterprise-agentgateway/charts/enterprise-agentgateway \
  --version ${AGENTGATEWAY_VERSION} \
  --kube-context $KUBE_CONTEXT \
  --set-string licensing.licenseKey=${AGENTGATEWAY_LICENSE_KEY}
```

### Step 7: Install Kagent Enterprise

Deploys the kagent controller, the community agents, and the UI.

- `manifests/kagent-enterprise-values.yaml` - Enables the community agents with resource limits, OIDC auto provider, OTel tracing to telemetry-collector, and `controller.a2aBaseUrl` pointing to the A2A gateway.

```bash
helm upgrade --install kagent-crds \
  oci://us-docker.pkg.dev/solo-public/kagent-enterprise-helm/charts/kagent-enterprise-crds \
  --namespace kagent \
  --kube-context $KUBE_CONTEXT \
  --version ${KAGENT_ENT_VERSION}

helm upgrade --install kagent \
  oci://us-docker.pkg.dev/solo-public/kagent-enterprise-helm/charts/kagent-enterprise \
  --namespace kagent \
  --kube-context $KUBE_CONTEXT \
  --version ${KAGENT_ENT_VERSION} \
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
  --version ${KAGENT_ENT_VERSION} \
  --values manifests/management-values.yaml \
  --set licensing.licenseKey=$GLOO_GATEWAY_LICENSE_KEY
```

```bash
KAGENT_URL=$(kubectl --context $KUBE_CONTEXT get svc solo-enterprise-ui -n kagent -o jsonpath="{.status.loadBalancer.ingress[0]['hostname','ip']}")
echo $KAGENT_URL
open http://$KAGENT_URL
```

### Step 9: Install AgentRegistry

Centralized **discovery/catalog** for agents, skills, and MCP servers, with PostgreSQL + pgvector for semantic search. AgentRegistry is the discovery layer only — it does **not** deploy the Declarative `team1`/`team2` agents, the `AccessPolicy`, or the OpenClaw harness. Those are owned by kagent-enterprise (Steps 11–13). See [How AgentRegistry fits](#how-agentregistry-fits) below.

- `manifests/postgres-pgvector.yaml` - External PostgreSQL 16 with pgvector extension.
- `manifests/agentregistry-values.yaml` - Minimal chart values (runtime config is passed via `--set` below; the catalog is seeded separately, see Step 9b).

```bash
export AGENT_REGISTRY_JWT=$(openssl rand -hex 32)

kubectl apply -f manifests/postgres-pgvector.yaml --context $KUBE_CONTEXT

helm upgrade --install agentregistry \
  oci://ghcr.io/agentregistry-dev/agentregistry/charts/agentregistry \
  --namespace agentregistry \
  --create-namespace \
  --kube-context $KUBE_CONTEXT \
  --version ${AGENTREGISTRY_VERSION} \
  --set config.jwtPrivateKey="$AGENT_REGISTRY_JWT" \
  --set database.postgres.bundled.enabled=false \
  --set-string database.postgres.url="postgres://agentregistry:agentregistry@postgres-pgvector.agentregistry.svc.cluster.local:5432/agent-registry?sslmode=disable" \
  --set database.postgres.vectorEnabled=true \
  --set service.type=LoadBalancer \
  -f manifests/agentregistry-values.yaml
```

```bash
AGENT_REGISTRY_URL=$(kubectl --context $KUBE_CONTEXT get svc agentregistry -n agentregistry -o jsonpath="{.status.loadBalancer.ingress[0]['hostname','ip']}")
echo $AGENT_REGISTRY_URL
open http://$AGENT_REGISTRY_URL:12121
```

### Step 9b: Register the catalog (discovery)

Seed the registry with catalog entries for the agents, skills, and MCP server this lab runs, so the registry is the single pane to discover them.

- `manifests/agentregistry-catalog.yaml` - `ar.dev/v1alpha1` records: 2 Agents (`team1`, `team2-not-allowed`), 6 Skills, 1 MCPServer (`kagent-tool-server`). Metadata only.

> Note on `arctl`: the bundled `arctl` 0.1.9 cannot target a remote registry — it starts its own local Docker daemon and has no `--registry-url` flag. So registration uses the registry's batch apply REST endpoint (`POST /v0/apply`), which is exactly what `arctl apply` wraps. `deploy.sh` does this automatically (phase 16).

```bash
# port-forward the in-cluster registry, then apply the catalog
kubectl --context $KUBE_CONTEXT -n agentregistry port-forward svc/agentregistry 12121:12121 &

curl -fsS -X POST http://localhost:12121/v0/apply \
  -H "Content-Type: application/yaml" \
  -H "Authorization: Bearer $(cat .certs/agent-registry-jwt)" \
  --data-binary @manifests/agentregistry-catalog.yaml

# verify
curl -fsS http://localhost:12121/v0/agents
open http://localhost:12121   # the registered agents/skills/MCP appear in the UI
```

### How AgentRegistry fits

AgentRegistry and kagent-enterprise own different layers — keep them straight:

| Concern | Owned by | Why |
|---------|----------|-----|
| Run the Declarative `team1`/`team2` agents | kagent-enterprise (`Agent` CRD) | AgentRegistry only deploys **containerized BYO** agents (`arctl agent init/build/publish/deploy`), not Declarative ones. |
| Authorization (`AccessPolicy` ALLOW/DENY) | kagent-enterprise | AgentRegistry has no policy kind; its only deployable kinds are `Agent` and `MCPServer`. |
| OpenClaw harness (`AgentHarness`) | kagent-enterprise | Not an AgentRegistry kind; deployed in parallel on its own track. |
| Discover/catalog agents, skills, MCP servers | **AgentRegistry** | Central registry with pgvector semantic search; what this Step adds. |

### Step 10: Deploy the A2A Gateway

The A2A gateway is the data path the controller uses to proxy agent-to-agent calls (`controller.a2aBaseUrl` in the kagent values points to it). It does not enforce policy; enforcement happens at the per-agent waypoint provisioned in Step 12.

- `manifests/a2a-gateway.yaml` - enterprise-agentgateway Gateway + HTTPRoute for A2A traffic (port 8083, path `/api/a2a/`).

```bash
kubectl apply -f manifests/a2a-gateway.yaml --context $KUBE_CONTEXT
```

### Step 11: Deploy Custom Agents

- `manifests/team1-agent.yaml` - Authorized agent (AGENT_IDENTITY=team1)
- `manifests/team2-not-allowed-agent.yaml` - Blocked agent (AGENT_IDENTITY=team2-not-allowed)

Both agents have identical tools (k8s-agent, istio-agent, kgateway-agent, helm-agent) and identical system prompt structure. The only difference is the service account name, which is the SPIFFE identity the AccessPolicy uses to distinguish them.

```bash
kubectl apply -f manifests/team1-agent.yaml --context $KUBE_CONTEXT
kubectl apply -f manifests/team2-not-allowed-agent.yaml --context $KUBE_CONTEXT
```

### Step 12: Put the Target Agent Behind an Agentgateway Waypoint

AccessPolicy is enforced by an agentgateway waypoint in front of the target Agent. Labeling the Agent with `kagent.solo.io/waypoint=true` makes the controller provision that waypoint (`Gateway/agent-k8s-agent-waypoint`), generate the agent's HTTPRoute, and set the service's `istio.io/use-waypoint` label automatically. No manual service labeling is required.

```bash
kubectl label agent k8s-agent -n kagent --context $KUBE_CONTEXT \
  kagent.solo.io/waypoint=true --overwrite

kubectl wait --for=condition=Programmed gateway/agent-k8s-agent-waypoint \
  -n kagent --timeout=120s --context $KUBE_CONTEXT
```

### Step 13: Apply the AccessPolicy

This is the enforcement mechanism. The controller translates each `AccessPolicy` into an `EnterpriseAgentgatewayPolicy` on the target agent's HTTPRoute, enforced by the waypoint.

- `manifests/access-policy.yaml` - `ALLOW team1 -> k8s-agent` and `DENY team2-not-allowed -> k8s-agent`, matching the caller's `Agent` identity.

```bash
kubectl apply -f manifests/access-policy.yaml --context $KUBE_CONTEXT
```

Verify the policy translated and attached:

```bash
kubectl get accesspolicy deny-team2-to-k8s-agent -n kagent \
  -o jsonpath='{.status.state}' --context $KUBE_CONTEXT
# Expected: Applied

kubectl get enterpriseagentgatewaypolicy accesspolicy-deny-team2-to-k8s-agent-waypoint \
  -n kagent --context $KUBE_CONTEXT
# Expected: ACCEPTED=True  ATTACHED=True
```

## Verification

### Check All Pods

```bash
kubectl get pods -n kagent --context $KUBE_CONTEXT
# controller, community agents, 2 custom agents, UI, postgres, clickhouse,
# and the agent-k8s-agent-waypoint pod

kubectl get agents -n kagent --context $KUBE_CONTEXT
# community agents + team1 + team2-not-allowed
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

Or just run `./test.sh`.

### Test Policy Enforcement (UI)

```bash
kubectl port-forward -n kagent svc/solo-enterprise-ui 8080:80 --context $KUBE_CONTEXT
# Open http://localhost:8080
```

1. Select **team1** -> Send "List all pods in the kagent namespace" -> Should succeed
2. Select **team2-not-allowed** -> Send "List all pods" -> Should fail with access denied

## Manifest Files

| File | Resources | Purpose |
|------|-----------|---------|
| `kagent-enterprise-values.yaml` | Helm values | Community agents, OIDC, OTel tracing, A2A gateway routing |
| `management-values.yaml` | Helm values | Solo Enterprise UI, OIDC static client for OBO tokens, ClickHouse |
| `agentregistry-values.yaml` | Helm values | Minimal AgentRegistry chart values (runtime config via `--set`) |
| `agentregistry-catalog.yaml` | 2 Agent, 6 Skill, 1 MCPServer (`ar.dev/v1alpha1`) | Catalog entries seeded into the registry via `POST /v0/apply` — discovery metadata only |
| `postgres-pgvector.yaml` | Namespace, PVC, Deployment, Service | PostgreSQL 16 + pgvector for AgentRegistry |
| `team1-agent.yaml` | Agent | Authorized orchestrator with A2A tools |
| `team2-not-allowed-agent.yaml` | Agent | Blocked orchestrator (identical config, different identity) |
| `a2a-gateway.yaml` | Gateway, HTTPRoute | Enterprise agentgateway for `/api/a2a/` A2A data path |
| `access-policy.yaml` | 2x AccessPolicy | ALLOW team1, DENY team2 to k8s-agent — **the enforcement** |

## How Policy Enforcement Works

`AccessPolicy` (`policy.kagent-enterprise.solo.io/v1alpha1`) is the native kagent-enterprise authorization resource. You declare *who* (subjects) may or may not reach *what* (targets), and the controller compiles it into the low-level enforcement resources:

1. **Ambient mesh** assigns each pod a SPIFFE identity based on its service account.
2. **Waypoint label** (`kagent.solo.io/waypoint=true`) on the target Agent makes the controller provision an agentgateway waypoint in front of it and route the service's traffic through it.
3. **AccessPolicy** is translated by the controller into an `EnterpriseAgentgatewayPolicy` (`accesspolicy-<name>-waypoint`) on the agent's HTTPRoute. The waypoint evaluates the caller's identity and allows or denies the request.

```yaml
# access-policy.yaml - the DENY rule
apiVersion: policy.kagent-enterprise.solo.io/v1alpha1
kind: AccessPolicy
metadata:
  name: deny-team2-to-k8s-agent
  namespace: kagent
spec:
  from:
    subjects:
    - kind: Agent
      name: team2-not-allowed
      namespace: kagent
  targetRef:
    kind: Agent
    name: k8s-agent
  action: DENY
```

Default behavior is allow: without a deny-all baseline (a wildcard target with an empty `subjects` list), any caller not matched by a DENY is allowed. That is why team1 reaches k8s-agent with only the DENY for team2 in place; the explicit ALLOW for team1 documents intent.

> Why not a hand-written Istio `AuthorizationPolicy`? That resource is one of the artifacts the controller *generates* (the optional L4 layer, off by default via `controller.istioAuthzTranslation.enabled`). Authoring it by hand bypasses the AccessPolicy abstraction and duplicates what the controller already produces. This lab uses the L7 AccessPolicy path, which is the primary enforcement layer in Solo Enterprise for kagent.

## Troubleshooting

### Policy Not Working

```bash
# 1. Is the AccessPolicy CRD installed?
kubectl get crd accesspolicies.policy.kagent-enterprise.solo.io

# 2. Is the namespace in ambient mode?
kubectl get namespace kagent -o jsonpath='{.metadata.labels.istio\.io/dataplane-mode}'
# Should return: ambient

# 3. Is the target Agent labeled for an agentgateway waypoint?
kubectl get agent k8s-agent -n kagent -o jsonpath='{.metadata.labels.kagent\.solo\.io/waypoint}'
# Should return: true

# 4. Did the controller provision the waypoint?
kubectl get gateway agent-k8s-agent-waypoint -n kagent
# CLASS should be enterprise-agentgateway-waypoint, PROGRAMMED=True

# 5. Did the AccessPolicy translate?
kubectl get accesspolicy -n kagent -o custom-columns=NAME:.metadata.name,STATE:.status.state
# state should be Applied (a Failed state usually means the target Agent
# is missing the kagent.solo.io/waypoint label)

# 6. Is the generated policy attached?
kubectl get enterpriseagentgatewaypolicy -n kagent
# accesspolicy-*-waypoint entries should show ACCEPTED=True ATTACHED=True
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
./cleanup.sh
```

Or manually:

```bash
kubectl delete namespace kagent agentregistry agentgateway-system --context $KUBE_CONTEXT
helm uninstall istio-base istiod-solo istio-cni ztunnel -n istio-system --kube-context $KUBE_CONTEXT
kubectl delete namespace istio-system --context $KUBE_CONTEXT
```

## References

- [Solo Enterprise for Kagent](https://docs.solo.io/kagent-enterprise/docs/latest/install/)
- [AccessPolicies for AuthZ](https://docs.solo.io/kagent-enterprise/docs/main/security/access-policies/)
- [Enforce AccessPolicies at the waypoint (L7)](https://docs.solo.io/kagent-enterprise/docs/main/security/access-policies/l7/)
- [Solo Enterprise for Agentgateway](https://docs.solo.io/gateway/2.0.x/ai/about/)
- [Istio Ambient Mesh](https://istio.io/latest/docs/ops/ambient/)
- [A2A Protocol](https://a2a-protocol.org/)
