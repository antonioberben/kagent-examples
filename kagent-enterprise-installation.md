# Kagent Enterprise Installation

```bash
istioctl install -y --set profile=ambient --set meshConfig.accessLogFile=/dev/stdout
```

```bash
helm upgrade -i kgateway-crds oci://cr.kgateway.dev/kgateway-dev/charts/kgateway-crds \
--namespace kgateway-system --create-namespace \
--version v2.1.0-main \
--set controller.image.pullPolicy=Always \
--set controller.image.registry=docker.io \
--set controller.image.repository=howardjohn/kgateway \
--set controller.image.tag=1756156487

helm upgrade -i kgateway oci://cr.kgateway.dev/kgateway-dev/charts/kgateway \
--namespace kgateway-system \
--version v2.1.0-main \
--set agentGateway.enabled=true \
--set agentGateway.enableAlphaAPIs=true \
--set controller.image.registry=docker.io \
--set controller.image.repository=howardjohn/kgateway \
--set controller.image.tag=1756156487
```

```bash
helm upgrade -i kagent-enterprise \
oci://us-docker.pkg.dev/solo-public/kagent-enterprise-helm/charts/management \
-n kagent --create-namespace \
--version 0.0.9 \
--set cluster=cluster2 \
--values - <<EOF
ui:
  backend:
    metricsBackendHost: http://a6515dfd5f1f44b0dbb16ede232cc9fb-1597895675.eu-central-1.elb.amazonaws.com:8080
    oidcIssuer: http://afc88102283e34966a4814da3ece69c8-1807421306.eu-central-1.elb.amazonaws.com:8080/realms/kagent-dev
  frontend:
    uiBackendHost: http://a6515dfd5f1f44b0dbb16ede232cc9fb-1597895675.eu-central-1.elb.amazonaws.com:8090
    includeAuth: true
    authEndpoint: http://afc88102283e34966a4814da3ece69c8-1807421306.eu-central-1.elb.amazonaws.com:8080/realms/kagent-dev/protocol/openid-connect/auth
    tokenEndpoint: http://afc88102283e34966a4814da3ece69c8-1807421306.eu-central-1.elb.amazonaws.com:8080/realms/kagent-dev/protocol/openid-connect/token
    logoutEndpoint: http://afc88102283e34966a4814da3ece69c8-1807421306.eu-central-1.elb.amazonaws.com:8080/realms/kagent-dev/protocol/openid-connect/logout

EOF
```


```bash
helm upgrade -i kagent-crds \
oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds \
-n kagent \
--version 0.6.8

helm upgrade -i kagent \
oci://ghcr.io/kagent-dev/kagent/helm/kagent \
-n kagent \
--version 0.6.8 \
--values - <<EOF
service:
  type: LoadBalancer
providers:
  openAI:
    apiKey: ${OPENAI_API_KEY}
otel:
  tracing:
    enabled: true
    exporter:
      otlp:
        endpoint: kagent-enterprise-ui.kagent.svc.cluster.local:4317
        insecure: true
kagent-tools:
  openAI:
    apiKey: ${OPENAI_API_KEY}
  otel:
    tracing:
      enabled: true
      exporter:
        otlp:
          endpoint: kagent-enterprise-ui.kagent.svc.cluster.local:4317
          insecure: true
EOF
```



```bash
export GW_IP=$(kubectl get svc -n kagent kagent-enterprise-ui -ojsonpath='{.status.loadBalancer.ingress[0].ip}{.status.loadBalancer.ingress[0].hostname}')
open -na "Google Chrome" --args --user-data-dir="/tmp/kagent-dev" --unsafely-treat-insecure-origin-as-secure="http://${GW_IP}/" "http://${GW_IP}/"
```