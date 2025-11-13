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


Using AI to ask for help. This is a simple agent that uses OpenAI to get help with tasks.

```bash
kubectl apply -f my-agent-v1.yaml
```

Access the UI at http://my-kagent.example:8080 and and ask to the agent:

```text
Create a deployment named 'nginx-deployment' using the nginx image in the existing 'kagent' namespace with 1 replica
```

```text
What is the capital of France?
```


But you don't want that your agent does everything. You want to give it some boundaries, guardrails. You can do that with system prompts:

```no-copy
    systemMessage: |-
      You are an expert Kubernetes assistant designed to help users manage, troubleshoot, and automate Kubernetes environments. Always provide clear, concise, and actionable guidance. When using tools, explain your reasoning and the steps you take. Proactively suggest best practices, security improvements, and optimizations. If a user request is unclear, ask clarifying questions before proceeding. Remain friendly, professional, and focused on helping users achieve their goals efficiently and safely.
      Do not answer anything different than Kubernetes related topics.
```

```bash
kubectl apply -f my-agent-v2.yaml
```

Access the UI and ask the same questions again. The agent will refuse to answer non-kubernetes related questions.

```text
What is the capital of France?
```

## Stage 2: Walk

The agent helps, but you want that you agent is able to run a task by its own. To do so, you need to give it access to `tools` (also called functions).

These actions can be anything, from calling an API, to running a script, to querying a database.

In this case, you want to connect to the kubernetes cluster and run kubectl commands. Kagent comes with an MCP Server with those tools:

```bash
kubectl get remotemcpserver kagent-tool-server -n kagent -oyaml
```

Let's use it with our agent:

```bash
kubectl apply -f my-agent-v3.yaml
```

Access the UI and ask the same questions again. The agent will be able to create the deployment in kubernetes.

```text
Create a deployment named 'nginx-deployment' using the nginx image in the existing 'kagent' namespace with 1 replica
```

## Stage 3: Fly

Now you want your agent to connect to other agents. This is useful for enterprise where different teams have different agents with different permissions.

Check the existing k8s-agent:

```bash
kubectl get agent k8s-agent -n kagent -oyaml
```

Deploy your own agent `my-agent-v4`:

```bash
kubectl apply -f my-agent-v4.yaml
```

Access the UI and try to perform a taks thorug the exisiting k8s-agent. You have entered the multi-agent world!

```text
Create a deployment named 'nginx-deployment2' using the nginx image in the existing 'kagent' namespace with 1 replica
```

> **Note:** If you try to delete, the k8s-agent will refuse because of the system prompt expects that the user confirms destructive actions. However, the default k8s-agent is not well configured, so it will fail. This is an example of the importance of fine-tuning the system prompt to your needs.


### 360 Observability with Ambient Mesh (Optional)

But this is useless if we cannot see anything. How can you ensure that the communication between agents is secure or even hapenning?

Service Mesh already gave us security by defaul. Now let's test observability.

Let's access the Gloo Mesh dashboard (in the mgmt cluster):

```bash
kubectl port-forward --context $MGMT_CONTEXT -n gloo-mesh svc/gloo-mesh-ui 8090
```

Go to the Graph tab and see the communication between agents similar to this:
![Gloo Mesh Graph](gloo-mesh-graph.png)