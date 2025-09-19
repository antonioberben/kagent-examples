# Gloo Mesh Installation

This guide walks you through installing Gloo Mesh multi-cluster setup.

## Prerequisites

- 1 (single cluster) or 3 Kubernetes clusters (multi-cluster). 1 management cluster, 2 workload clusters
- `kubectl` configured to access all clusters
- `helm` installed
- `meshctl` CLI tool
- Gloo Mesh license key (can be obtained from Solo.io)

## Installation

Load environment variables and install `meshctl`:

Copy .env-template to .env and fill in the variables.

```bash
source .env
```

```bash
curl -sL https://run.solo.io/meshctl/install | GLOO_MESH_VERSION=v2.10.0 sh -
export PATH=$HOME/.gloo-mesh/bin:$PATH
```

```bash
export MGMT_CLUSTER=
export REMOTE_CLUSTER1=
export REMOTE_CLUSTER2=

export MGMT_CONTEXT=
export REMOTE_CONTEXT1=
export REMOTE_CONTEXT2=
```

```bash
export GLOO_MESH_LICENSE_KEY=
```

Install Gloo Mesh management plane in the management cluster:

1. Single cluster:

  ```bash
  meshctl install --profiles mgmt-server \
  --register \
  --kubecontext ${MGMT_CONTEXT} \
  --set common.cluster=${MGMT_CLUSTER} \
  --set glooUi.enabled=true \
  --set glooUi.serviceType=LoadBalancer \
  --set licensing.glooMeshLicenseKey=${GLOO_MESH_LICENSE_KEY}
  ```

  ```bash
  kubectl get pods -n gloo-mesh --context $MGMT_CONTEXT
  ```

2. Multi-cluster:

  ```bash
  meshctl install --profiles mgmt-server \
  --kubecontext ${MGMT_CONTEXT} \
  --set common.cluster=${MGMT_CLUSTER} \
  --set glooUi.enabled=true \
  --set glooUi.serviceType=LoadBalancer \
  --set licensing.glooMeshLicenseKey=${GLOO_MESH_LICENSE_KEY}
  ```

  ```bash
  kubectl get pods -n gloo-mesh --context $MGMT_CONTEXT
  ```

  Get Telemetry Gateway address to be used when registering remote clusters:

  Depends on your kuberentes flavour:
  ```bash
  export TELEMETRY_GATEWAY_IP=$(kubectl get svc -n gloo-mesh gloo-telemetry-gateway --context $MGMT_CONTEXT -o jsonpath="{.status.loadBalancer.ingress[0]['hostname','ip']}")
  export TELEMETRY_GATEWAY_PORT=$(kubectl get svc -n gloo-mesh gloo-telemetry-gateway --context $MGMT_CONTEXT -o jsonpath='{.spec.ports[?(@.name=="otlp")].port}')
  export TELEMETRY_GATEWAY_ADDRESS=${TELEMETRY_GATEWAY_IP}:${TELEMETRY_GATEWAY_PORT}
  echo $TELEMETRY_GATEWAY_ADDRESS
  ```

  ```bash
  meshctl cluster register $REMOTE_CLUSTER1 \
  --kubecontext $MGMT_CONTEXT \
  --remote-context $REMOTE_CONTEXT1 \
  --profiles agent,ratelimit,extauth \
  --telemetry-server-address $TELEMETRY_GATEWAY_ADDRESS

  meshctl cluster register $REMOTE_CLUSTER2 \
  --kubecontext $MGMT_CONTEXT \
  --remote-context $REMOTE_CONTEXT2 \
  --profiles agent,ratelimit,extauth \
  --telemetry-server-address $TELEMETRY_GATEWAY_ADDRESS
  ```

  ```bash
  kubectl get pods -n gloo-mesh --context $REMOTE_CONTEXT1
  kubectl get pods -n gloo-mesh --context $REMOTE_CONTEXT2
  ```

Install Istio in the workload clusters using Gloo Mesh Service Mesh Controller (SMC):

1. Single cluster:

  ```bash
  helm upgrade --install gloo-operator oci://us-docker.pkg.dev/solo-public/gloo-operator-helm/gloo-operator \
  --version 0.3.1 \
  -n gloo-mesh \
  --create-namespace \
  --kube-context ${MGMT_CONTEXT} \
  --set manager.env.SOLO_ISTIO_LICENSE_KEY=${GLOO_MESH_LICENSE_KEY}
  ```

  Check the operator is running:

  ```bash
  kubectl get pods -n gloo-mesh --context ${MGMT_CONTEXT} -l app.kubernetes.io/name=gloo-operator
  ```

2. Multi-cluster:

  ```bash
  for context in ${REMOTE_CONTEXT1} ${REMOTE_CONTEXT2}; do
    helm upgrade --install gloo-operator oci://us-docker.pkg.dev/solo-public/gloo-operator-helm/gloo-operator \
    --version 0.3.1 \
    -n gloo-mesh \
    --create-namespace \
    --kube-context ${context} \
    --set manager.env.SOLO_ISTIO_LICENSE_KEY=${GLOO_MESH_LICENSE_KEY}
  done
  ```

  Check the operator is running:

  ```bash
  for context in ${REMOTE_CONTEXT1} ${REMOTE_CONTEXT2}; do
    kubectl get pods -n gloo-mesh --context ${context} -l app.kubernetes.io/name=gloo-operator
  done
  ```

Deploy Istio using SMC:

1. Single cluster:

  ```bash
  kubectl apply -n gloo-mesh --context ${MGMT_CONTEXT} -f - <<EOF
  apiVersion: operator.gloo.solo.io/v1
  kind: ServiceMeshController
  metadata:
    name: managed-istio
    labels:
      app.kubernetes.io/name: managed-istio
  spec:
    # required for multicluster setups
    cluster: mgmt
    dataplaneMode: Ambient
    installNamespace: istio-system
    version: 1.27.0
  EOF
  ```

2. Multi-cluster:

  ```bash
  function apply_smc() {
  context=${1:?context}
  cluster=${2:?cluster}

  kubectl apply -n gloo-mesh --context ${context} -f - <<EOF
  apiVersion: operator.gloo.solo.io/v1
  kind: ServiceMeshController
  metadata:
    name: managed-istio
    labels:
      app.kubernetes.io/name: managed-istio
  spec:
    # required for multicluster setups
    cluster: ${cluster}
    dataplaneMode: Ambient
    installNamespace: istio-system
    version: 1.27.0
  EOF
  }

  apply_smc ${REMOTE_CONTEXT1} ${REMOTE_CLUSTER1}
  apply_smc ${REMOTE_CONTEXT2} ${REMOTE_CLUSTER2}
  ```

Check Istio pods are running.