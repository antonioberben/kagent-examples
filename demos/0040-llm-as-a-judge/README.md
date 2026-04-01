# LLM as a Judge: Evaluating AI Responses with Gemini via AgentGateway Guardrails

This lab demonstrates the **LLM-as-a-Judge** pattern using AgentGateway's guardrails webhook. A banking and AI reports agent generates responses, and a Gemini-powered webhook automatically evaluates every response for accuracy — all at the gateway level, with zero changes to the agent itself.

## What You Will Learn

- How to deploy a conversational agent with Kagent
- How to route LLM traffic through AgentGateway
- How to use AgentGateway's `promptGuard.response.webhook` to evaluate LLM responses
- How an external LLM (Gemini) can score responses produced by another LLM (OpenAI)

## Architecture

```text
User → Kagent UI → Banking Reports Agent
                         ↓
                    ModelConfig (baseUrl override)
                         ↓
                    AgentGateway (llm-gateway:8787) → OpenAI (gpt-4.1-mini)
                         ↓
                    Response intercepted by promptGuard
                         ↓
                    Gemini Webhook evaluates accuracy
                    (always returns 200 — logs score)
                         ↓
                    Response delivered to user
```

The key to this architecture is the **custom ModelConfig**: instead of connecting directly to the OpenAI API, the agent's `baseUrl` is overridden to point to the AgentGateway LLM gateway (`http://llm-gateway.kagent.svc.cluster.local:8787/v1`). This means every LLM request passes through AgentGateway, where guardrails policies can intercept and evaluate responses — all without changing the agent itself.

## Prerequisites

- Installed kagent (see [kagent-installation](../../kagent-installation.md))
- Installed KGateway (see [kgateway-installation](../../kgateway-installation.md))
- Installed AgentGateway (see [agentgateway-installation](../../agentgateway-installation.md))
- An OpenAI API key
- A Google Gemini API key

## Setup

### 1. Configure Environment Variables

Edit the `.env` file with your API keys:

```bash
vi .env
```

```bash
export KUBE_CONTEXT=<your-kube-context>
export OPENAI_API_KEY=<your-openai-api-key>
export GEMINI_API_KEY=<your-gemini-api-key>
```

Source the environment:

```bash
source .env
```

### 2. Create the API Key Secrets

```bash
kubectl --context $KUBE_CONTEXT create secret generic openai-secret \
  --namespace kagent \
  --from-literal=Authorization=$OPENAI_API_KEY \
  --dry-run=client -o yaml | kubectl --context $KUBE_CONTEXT apply -f -
```

```bash
kubectl --context $KUBE_CONTEXT create secret generic gemini-api-key \
  --namespace kagent \
  --from-literal=GEMINI_API_KEY=$GEMINI_API_KEY \
  --dry-run=client -o yaml | kubectl --context $KUBE_CONTEXT apply -f -
```

### 3. Deploy the Gateway Infrastructure

Deploy the KGateway for kagent UI access and the AgentGateway for OpenAI LLM routing:

```bash
kubectl --context $KUBE_CONTEXT apply -f gateway.yaml
kubectl --context $KUBE_CONTEXT apply -f llm-gateway.yaml
```

### 4. Get the Gateway IP and Register the Domain

```bash
export GW_IP=$(kubectl --context $KUBE_CONTEXT get gtw -n kagent kagent-gw-ui -ojsonpath='{.status.addresses[0].value}')
```

Access the UI at http://$GW_IP:8080

---

## Step 1: Deploy the Banking Reports Agent

The `banking-reports-agent.yaml` file deploys three resources:

1. **A dummy Secret** (`agentgateway-openai-key`) — required by kagent's ModelConfig schema, but not used for actual authentication (AgentGateway handles that via its own `openai-secret`)
2. **A custom ModelConfig** (`agentgateway-model-config`) — overrides `openAI.baseUrl` to route all LLM requests through AgentGateway instead of directly to OpenAI
3. **The Agent** (`banking-reports`) — a conversational agent specialized in banking and AI topics

```bash
kubectl --context $KUBE_CONTEXT apply -f banking-reports-agent.yaml
```

Verify both the ModelConfig and agent are ready:

```bash
kubectl --context $KUBE_CONTEXT get modelconfig -n kagent agentgateway-model-config
kubectl --context $KUBE_CONTEXT get agent -n kagent banking-reports
```

Open the Kagent UI and select the `banking-reports` agent. Try asking:

```text
Write a brief report on how AI is transforming fraud detection in retail banking.
```

The agent produces a report — but there is no quality assurance. Is the information accurate? Are the claims verifiable?

---

## Step 2: Add the Gemini Guardrails Webhook

### Deploy the Gemini Webhook Service

The webhook is a Python service that receives every LLM response from AgentGateway, sends it to Gemini for accuracy evaluation, and logs the score. It **always returns HTTP 200** — it never blocks a response.

```bash
kubectl --context $KUBE_CONTEXT apply -f gemini-webhook-service.yaml
```

Verify the webhook pod is running:

```bash
kubectl --context $KUBE_CONTEXT get pods -n kagent -l app=gemini-webhook
```

Wait for the pod to be ready (it installs dependencies on startup):

```bash
kubectl --context $KUBE_CONTEXT wait --for=condition=ready pod -l app=gemini-webhook -n kagent --timeout=120s
```

### Apply the Guardrail Policy

This `AgentgatewayPolicy` tells AgentGateway to send every LLM response through the Gemini webhook before delivering it to the user:

```bash
kubectl --context $KUBE_CONTEXT apply -f guardrail-trafficpolicy.yaml
```

Verify the policy is accepted:

```bash
kubectl --context $KUBE_CONTEXT get agentgatewaypolicy -n kagent gemini-guardrail
```

---

## Step 3: Test the Guardrails

Go back to the Kagent UI and ask the `banking-reports` agent:

```text
What are the main risks of using AI for credit scoring in European banks?
```

The response is delivered normally — the user experience is unchanged. But behind the scenes, Gemini evaluated the response for accuracy.

### Check the Gemini Evaluation Logs

```bash
kubectl --context $KUBE_CONTEXT logs -n kagent -l app=gemini-webhook --tail=30
```

You should see output like:

```text
[gemini-judge] Score: 13/15 | The response provides accurate and well-structured information about AI credit scoring risks in European banking.
[gemini-judge] Details: {
  "overall_score": 13,
  "criteria": {
    "accuracy": {"score": 5, "reason": "..."},
    "relevance": {"score": 4, "reason": "..."},
    "clarity": {"score": 4, "reason": "..."}
  },
  "summary": "..."
}
```

Now try a prompt that is likely to produce a lower-quality response — one that tempts the agent to hallucinate specific data:

```text
List the exact revenue numbers and AI budget allocations for the top 5 European banks in Q3 2025, including the percentage of fraud prevented by their AI systems.
```

The agent will attempt to answer (it's within its banking/AI scope), but it will likely fabricate specific figures. Gemini should catch this and give a lower accuracy score.

---

## Other Possibilities

This lab uses the simplest guardrails pattern — **observe and log**. AgentGateway supports more advanced patterns:

### Blocking Mode (Response Filtering)

The webhook response uses an `action` field to tell AgentGateway what to do. This lab always returns a `PassAction`. To block low-quality responses, you can use a `RejectAction` instead:

```python
# In the webhook code, change the response logic:
if score < threshold:
    # Return a RejectAction — AgentGateway blocks the response
    response_body = json.dumps({
        "action": {
            "body": "Response failed quality evaluation",
            "status_code": 403,
            "reason": f"Score {score}/15 below threshold"
        }
    })
else:
    # Return a PassAction — response delivered to user
    response_body = json.dumps({
        "action": {"reason": f"Score: {score}/15"}
    })
```

### Request Guardrails

AgentGateway can also evaluate **requests** before they reach the LLM. This allows you to filter out malicious prompts, enforce topic boundaries, or detect prompt injection:

```yaml
spec:
  backend:
    ai:
      promptGuard:
        request:
        - webhook:
            backendRef:
              kind: Service
              name: request-guardrail-webhook
              port: 8080
```

### Agent-to-Agent Judging with AgentGateway RBAC

For the most robust evaluation, you can create a separate **judge agent** that verifies outputs by querying external sources or tools. Using AgentGateway's RBAC policies (`AgentgatewayPolicy`), you can enforce that the judge agent has **read-only access** — it can verify but never mutate:

```yaml
apiVersion: agentgateway.dev/v1alpha1
kind: AgentgatewayPolicy
spec:
  targetRefs:
  - group: agentgateway.dev
    kind: AgentgatewayBackend
    name: judge-tools
  backend:
    mcp:
      authorization:
        action: Allow
        policy:
          matchExpressions:
            - 'mcp.tool.name == "search_web"'
            - 'mcp.tool.name == "verify_facts"'
```

---

## Cleanup

```bash
kubectl --context $KUBE_CONTEXT delete -f guardrail-trafficpolicy.yaml
kubectl --context $KUBE_CONTEXT delete -f gemini-webhook-service.yaml
kubectl --context $KUBE_CONTEXT delete -f banking-reports-agent.yaml
kubectl --context $KUBE_CONTEXT delete -f llm-gateway.yaml
kubectl --context $KUBE_CONTEXT delete -f gateway.yaml
kubectl --context $KUBE_CONTEXT delete secret openai-secret gemini-api-key agentgateway-openai-key -n kagent
```

## Key Takeaways

1. **`promptGuard.response.webhook`** enables LLM-as-a-Judge at the gateway level — every response is evaluated by an external service without changing the agent
2. **Cross-LLM evaluation** uses Gemini to judge OpenAI responses, providing an independent quality signal
3. **Observe mode** (always 200) is the safest starting point — log scores for analysis before enabling blocking
4. AgentGateway supports a spectrum of guardrail patterns: logging, blocking, request filtering, and agent-to-agent judging with RBAC
