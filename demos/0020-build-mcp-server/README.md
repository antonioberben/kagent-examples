# Building a MCP Server with kMCP and kagent

This demo shows how to build a MCP Server with kMCP and kagent, and how to use it with an agent.

## Prerequisites

- Installed a kmcp server (see [kmcp guide](../../mcp-servers/kmcp/README.md))
- Installed kagent (see [kagent-installation](../../kagent-installation.md))
- Installed Kgateway (see [kgateway-agentgateway](../../kgateway-installation.md))
- (Optional) Installed Gloo Mesh for communication encryption and observability (see [gloo-mesh-installation](../../gloo-mesh-installation.md))


## Run

Let's make istio apply encryption to all the communications in the kagent namespace. Now all the services in the kagent namespace will be able to communicate securely (mtls) and observable.

```bash
kubectl label namespace kagent istio.io/dataplane-mode=ambient
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

After creating an echo mcp server following the [kmcp guide](../../mcp-servers/kmcp/README.md), create an agent to use that mcp server.

```bash
kubectl apply -f my-agent-with-mcp.yaml
```

Now type in the UI, and you should see the message from the mcp server:

```
call echo
```