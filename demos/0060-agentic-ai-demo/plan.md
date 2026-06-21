# Plan / estado — Demo 0060 Agentic AI (kagent + AgentRegistry + AgentCore)

Documento de estado. Refleja lo que está hecho en el cluster `agentic-ai-demo` y lo que queda.

## Estado actual (arquitectura viva)

- **kagent-enterprise** (ns `kagent`): runtime + autorización. `team1`/`team2` Declarative,
  `AccessPolicy` (ALLOW team1 / DENY team2 → k8s-agent), harness OpenClaw. **Enforcement OK**
  (team1 200 / team2 403, verificado tras todos los cambios).
- **AgentRegistry**: migrado de OSS → **Solo Enterprise for agentregistry v2026.5.4**
  (ns `agentregistry-system`, OIDC obligatorio). El OSS fue eliminado.
- **Keycloak** (ns `keycloak`): IdP compartido. Realm `agentregistry`, issuer
  `http://172.18.3.7:8080/realms/agentregistry`, user `admin-user/password` (grupo `admins`).
  Clientes `ar-*` (agentregistry) y `kagent-*` (kagent). Secrets/issuer en `.certs/keycloak.env`.
- **kagent ↔ agentregistry conectados**: Runtime tipo Kagent en AR + OIDC Keycloak compartido en
  controller y UI de kagent. **El UI de kagent ahora pide login Keycloak** (antes "auto", sin login).
- **dice** (agente demo): corre en kagent como BYO (desplegado por AR vía el runtime kagent). La copia
  en **AWS Bedrock AgentCore fue ELIMINADA** (no era conectable a AR sin meter claves IAM de larga
  duración en el pod — ver sección D).

## Hecho

### A. AgentRegistry como capa de descubrimiento (catálogo)
- `manifests/agentregistry-catalog.yaml`: 9 registros `ar.dev/v1alpha1` (2 Agent team1/team2, 6 Skill,
  1 MCPServer). Ordenado **deps-first** (enterprise valida cross-refs). Solo metadatos; el runtime y la
  política siguen en kagent-enterprise.
- Verificado el límite del producto: AR solo despliega agentes **BYO** (no Declarative) y **no tiene
  política**; el antiguo `agentregistry-values.yaml` (claves registry/mcpServers/skills) era inerte.

### B. Migración OSS → Enterprise
- OSS borrado (`helm uninstall agentregistry -n agentregistry` + postgres + ns).
- Keycloak desplegado: `manifests/keycloak.yaml` (dev-mode, realm import).
- Enterprise instalado: chart
  `oci://us-docker.pkg.dev/solo-public/agentregistry-enterprise/helm/agentregistry-enterprise`
  v2026.5.4, ns `agentregistry-system`, OIDC Keycloak (`ar-backend`/`ar-ui`, roleClaim `Groups`,
  superuserRole `admins`), postgres bundled. Sin campo `licensing` en el chart (imagen en solo-public).
- Auth verificada: sin token → **401**; con token Keycloak → **200**. Catálogo re-sembrado autenticado.
- arctl: el cliente enterprise es `ARCTL_VERSION=v2026.5.4` + `arctl user login` (no instalado aún).

### C. Agente demo `dice` (build → push → publish → deploy)
- Proyecto `agents/dice/` (ADK, `openai/gpt-4o-mini`). Imagen `docker.io/antonioberben/dice:0.1.0`
  (ARM64, build+push OK).
- Publicado en el registry y **desplegado en kagent vía el runtime kagent** (Agent BYO `dice`,
  Ready=True). Modelo rutado por el LLM agentgateway (`OPENAI_API_BASE`, sin clave real en el pod).
- `manifests/dice-agent.yaml` = equivalente kubectl/BYO (fallback).
- Histórico: arctl 0.1.9 no soporta deploy a k8s; v0.3.3 sí (`--registry-url`/anónimo, OSS).

### D. dice en AWS Bedrock AgentCore — ELIMINADO
- Se desplegó y verificó (runtime `dice_agentcore-vZYY8KHY03`, HTTP 200), pero **estaba desconectado de
  agentregistry**. Conectarlo exige un Runtime AR tipo `BedrockAgentCore` (config roleArn+externalId+
  region) con **credenciales AWS inyectadas en el pod de AR vía Helm** (IAM user keys o EKS Pod
  Identity). En **kind** no hay Pod Identity → requeriría claves IAM de larga duración en el cluster
  (pesado + riesgo). Decisión (instrucción del usuario): **borrado de AgentCore** — runtime DELETING,
  ECR repo `dice-agentcore` y rol `AgentCoreRuntime-dice` eliminados.
- El proyecto `agents/dice-agentcore/` (código del wrapper) se conserva para referencia.

### E. Conexión kagent ↔ agentregistry (la integración de la doc)
- `manifests/agentregistry-kagent-runtime.yaml`: `Runtime` tipo Kagent → `kagent-controller.kagent:8083`.
- kagent movido de OIDC "auto" → **Keycloak** en controller (`kagent-enterprise`) y UI (`management`):
  clientes `kagent-backend`/`kagent-ui`, secrets `kagent-enterprise-oidc-secret`+`ui-backend-oidc-secret`,
  `oidc.issuer=$KEYCLOAK_ISSUER`. Sin esto, el deploy por el runtime fallaba ("authentication token
  expired"). Valores helm previos en `.certs/rollback/`.
- Verificado: AR despliega `dice` DENTRO de kagent por el runtime kagent (Ready); enforcement intacto.

## Pendiente (no ejecutado)

- **Sync de scripts/docs al flujo enterprise+Keycloak** para reproducibilidad end-to-end:
  `deploy.sh` (Keycloak + chart enterprise + ns `agentregistry-system` + OIDC + arctl enterprise),
  `cleanup.sh` (ns `keycloak`, `agentregistry-system`), `README.md`, `.env(.example)` (versión
  enterprise, sin license key específica). Hoy estos siguen describiendo el flujo OSS.
- **arctl enterprise** (`install.sh ARCTL_VERSION=v2026.5.4` + `arctl user login`) para operar el
  registry desde CLI (hoy uso REST con token de Keycloak).
- **Integración de UI** (pestaña de AR dentro del UI de kagent): **bloqueada por versión** — management
  `0.4.4` no tiene `products.agentregistry` (la doc usa el track 0.4.0 de AR). Requeriría alinear
  versiones. Hoy solo está la conexión data-plane (Runtime + OIDC compartido).

## Hechos / gotchas clave

- Issuer Keycloak = LB IP `172.18.3.7:8080` (en este cluster las IP de MetalLB SÍ son enrutables desde
  el host y desde pods). Si el cluster reinicia y cambia la IP, el OIDC se rompe → re-aplicar.
- Token para REST: `curl -d client_id=ar-cli-password -d username=admin-user -d password=password
  -d grant_type=password $KEYCLOAK_ISSUER/protocol/openid-connect/token | jq -r .access_token`.
- AR enterprise valida cross-refs en `POST /v0/apply` → catálogo deps-first.
- Entorno: Docker se ha caído varias veces; al reiniciar, el daemon local de arctl OSS se rompía
  (ya no aplica: enterprise no usa daemon local).

## Ficheros tocados / nuevos

- `manifests/keycloak.yaml` (nuevo), `manifests/agentregistry-kagent-runtime.yaml` (nuevo)
- `manifests/agentregistry-catalog.yaml` (reordenado deps-first)
- `manifests/agentregistry-values.yaml` (slim; del flujo OSS, hoy no usado por enterprise)
- `manifests/management-values.yaml`, `manifests/kagent-enterprise-values.yaml` (OIDC → Keycloak)
- `manifests/dice-agent.yaml` (nuevo, BYO fallback), `agents/dice/**`, `agents/dice-agentcore/**` (nuevos)
- `deploy.sh` (fase 16 catálogo, del flujo OSS — pendiente sync a enterprise)
- `README.md`, `CLAUDE.md`, memoria (actualizados)
- `.certs/keycloak.env`, `.certs/rollback/` (secrets/issuer y rollback helm values)
