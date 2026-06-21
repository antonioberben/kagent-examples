# 0060 Agentic AI — kagent-enterprise demo

Enterprise policy-based access control for AI agents on Solo products. Two custom agents
(`team1`, `team2-not-allowed`) are identical except for SPIFFE identity; an `AccessPolicy`
ALLOWs team1 and DENYs team2 to `k8s-agent`, enforced at the agent's agentgateway waypoint.
Scripted end to end: `./deploy.sh`, `./test.sh` (team1 200 / team2 403), `./cleanup.sh`.

## Versions / env
Pinned in `.env` (copy from `.env.example`). Key: Istio `1.30.0-solo`, enterprise-agentgateway
`v2026.5.2`, kagent-enterprise `0.4.4` (OSS 0.9.1), agentregistry `0.3.3`, Gateway API `v1.2.1`,
OpenShell `0.0.55`, agent-sandbox `v0.4.6`. Kube context: `agentic-ai-demo` (kind on macOS/arm64).
Needs `OPENAI_API_KEY` + Solo license keys. Run scripts from this directory.

## Architecture & product boundaries (verified — do not re-litigate)
- **Runtime + authz = kagent-enterprise.** `team1`/`team2` are `Declarative` Agents
  (modelConfig + systemMessage + native A2A `tools:[Agent]`). The `AccessPolicy`
  (`policy.kagent-enterprise.solo.io/v1alpha1`) is translated by the controller into an
  `EnterpriseAgentgatewayPolicy` on the target agent's waypoint. Target needs label
  `kagent.solo.io/waypoint=true`; ns `kagent` is in ambient mesh for SPIFFE identity.
- **Discovery = AgentRegistry, nothing else.** AgentRegistry only deploys **containerized BYO**
  agents and only has kinds `Agent`/`MCPServer`. It does NOT deploy the Declarative agents, the
  `AccessPolicy`, or the `AgentHarness`. In this demo it is the catalog/discovery layer only.
- **LLM gateway fronting.** Agents never hold the real OpenAI key. `default-model-config`
  points at `http://llm-agentgateway.agentgateway-system.svc.cluster.local:8080/openai/v1`
  (manifests/llm-gateway.yaml). Real key lives only in `agentgateway-system/openai-secret`;
  kagent-side `llm-api-keys` is a placeholder. Model: `gpt-4o-mini`.
- **OpenClaw harness.** `AgentHarness` backend must be `openclaw` (0.4.4 CRD enum; no `hermes`).
  Needs OpenShell gateway + upstream agent-sandbox CRD installed before OpenShell, and controller
  env `OPENSHELL_GATEWAY_URL` + `OPENSHELL_INSECURE=true`. Deployed in parallel, own track.

## AgentRegistry specifics

**Now running Solo Enterprise for agentregistry v2026.5.4** (chart
`oci://us-docker.pkg.dev/solo-public/agentregistry-enterprise/helm/agentregistry-enterprise`,
ns `agentregistry-system`, svc `agentregistry-enterprise-server` :12121 LB). No `licensing` field
in the chart (image is in solo-public). The OSS build (`ghcr.io/agentregistry-dev/...`, ns
`agentregistry`) was removed.

- **Auth = OIDC (required), via Keycloak** (`manifests/keycloak.yaml`, ns `keycloak`, realm
  `agentregistry`). Anonymous is OFF: no token → 401. Get a bearer token from Keycloak and send it.
  Issuer + client secrets cached in `.certs/keycloak.env` (issuer = `http://<keycloak-LB-IP>:8080/realms/agentregistry`).
  Token for scripts: `curl -d client_id=ar-cli-password -d username=admin-user -d password=password
  -d grant_type=password $KEYCLOAK_ISSUER/protocol/openid-connect/token | jq -r .access_token`.
  Enterprise chart OIDC values: `oidc.issuer`, `oidc.clientId=ar-backend`, `oidc.clientSecret`,
  `oidc.publicClientId=ar-ui`, `oidc.roleClaim=Groups` (realm maps the `Groups` claim),
  `oidc.superuserRole=admins`. arctl enterprise (`ARCTL_VERSION=v2026.5.4`, `arctl user login`).
- Seed the catalog via REST: `POST /v0/apply` (Content-Type `application/yaml`, `Authorization:
  Bearer <token>`), `DELETE /v0/apply` to remove. Enterprise **validates cross-refs**, so
  `manifests/agentregistry-catalog.yaml` is ordered deps-first (MCPServer + Skills before Agents).
- BYO agent deploy flow (image build is unchanged from OSS; only the registry/auth differs):
  build+push ARM64 to a registry, `arctl agent publish .`, then `arctl deployments create <name>
  --type agent --provider-id kubernetes-default --namespace kagent --env ...` → reconciles into a
  kagent BYO Agent `<name>-<version>-<deployment-id>` (label `aregistry.ai/managed=true`). ADK agents
  use LiteLLM → route the model via `OPENAI_API_BASE` (no real key in pod). The `dice` agent
  (`agents/dice/`, image `docker.io/antonioberben/dice:0.1.0`) still runs as a kagent BYO Agent
  (orphaned after the OSS removal but Ready). `manifests/dice-agent.yaml` = kubectl/BYO fallback.
  `agents/dice-agentcore/` is the AWS Bedrock AgentCore variant (see its memory).
- Runtimes/providers: `GET /v0/runtimes` → `kubernetes-default`, `local`, `virtual-default`, and
  `kagent` (the kagent connection, see below).
- **kagent ↔ agentregistry connection (the documented integration).** A `Runtime` of `type: Kagent`
  (`manifests/agentregistry-kagent-runtime.yaml`, `spec.config.kagentUrl=http://kagent-controller.kagent:8083`)
  points agentregistry at the kagent controller. To deploy INTO kagent through it: a Deployment with
  `runtimeRef:{kind:Runtime,name:kagent}` (verified with `dice` → kagent BYO Agent `dice`, Ready).
  **This requires kagent and agentregistry to share the SAME Keycloak realm.** So kagent was moved
  OFF the "auto" OIDC: both the controller (`kagent-enterprise` chart) and the UI (`management` chart)
  now use Keycloak (`oidc.clientId=kagent-backend`/`kagent-ui`, secrets `kagent-enterprise-oidc-secret`
  + `ui-backend-oidc-secret` = the Keycloak `kagent-backend` secret, `oidc.issuer=$KEYCLOAK_ISSUER`).
  Consequence: **the kagent UI now requires Keycloak login** (`admin-user`/`password`). Policy
  enforcement is unaffected (team1 200 / team2 403 verified after the change). Rollback values are in
  `.certs/rollback/`. Version skew: management `0.4.4` has NO `products.agentregistry` (the UI-level
  product integration the AR docs show needs the AR-docs management track), so only the data-plane
  connection (Runtime + shared OIDC) is wired, not a kagent-UI tab for AR.
- Historical: arctl 0.1.9 couldn't target a remote registry; v0.3.3 added `--registry-url`. The old
  `agentregistry-values.yaml` keys `registry:`/`mcpServers:`/`skills:` were INERT. The OSS registry
  allowed anonymous access — enterprise does NOT.

## Gotchas
- kind + MetalLB on macOS: LB IPs aren't routable from the host. Use `kubectl port-forward`
  (UI: `svc/solo-enterprise-ui 8080:80`; registry: `svc/agentregistry-enterprise-server 12121:12121`,
  ns `agentregistry-system`). Note: in this cluster the MetalLB LB IPs (172.18.x) ARE reachable from
  the host, so the Keycloak/registry LB IPs work directly too.
- Controller can be briefly down on first boot (depends on solo-enterprise-ui OIDC); waypoint
  Gateway is created asynchronously — poll before `kubectl wait`.
- `kagent-enterprise-oidc-secret` and the `jwt` (OBO RSA) secret must exist or the controller
  crashes; deploy.sh creates them (cached in `.certs/`).

## Conventions
- Manifests live in `manifests/`. `istio-values-AUTOGENERATED.yaml` is generated by deploy.sh.
- Match existing script style (LOG/OK/WARN printf, `kubectl --context="$KUBE_CONTEXT"`, bounded
  waits, idempotent applies). Keep local files in sync with the cluster.
- `plan.md` tracks current task progress; this file is durable project context.
