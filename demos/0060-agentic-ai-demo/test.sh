#!/usr/bin/env bash
# test.sh — verify AccessPolicy enforcement at the agent's agentgateway waypoint.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INVOKED_DIR="$(pwd)"
if [[ "$SCRIPT_DIR" != "$INVOKED_DIR" ]]; then
  echo "ERROR: this script must be run from its own directory."
  echo "       cd $SCRIPT_DIR && ./test.sh"
  exit 1
fi
REPO_ROOT="$SCRIPT_DIR"

if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a; source "${REPO_ROOT}/.env"; set +a
fi

REQUIRED_VARS=(KUBE_CONTEXT)
for v in "${REQUIRED_VARS[@]}"; do
  [[ -n "${!v:-}" ]] || { echo "missing $v" >&2; exit 1; }
done

LOG=$'\033[0;36m[ test ]\033[0m'
OK=$'\033[0;32m[ ok  ]\033[0m'
FAIL=$'\033[0;31m[fail ]\033[0m'

K8S_AGENT_URL="http://k8s-agent.kagent:8080/.well-known/agent-card.json"

probe() {
  local deploy="$1"
  kubectl --context="$KUBE_CONTEXT" -n kagent exec "deploy/${deploy}" -- \
    curl -s -o /dev/null -w "%{http_code}" "$K8S_AGENT_URL"
}

printf '%s == phase 1/4 — wait for team agents ==\n' "$LOG"
kubectl --context="$KUBE_CONTEXT" -n kagent rollout status \
  deploy/team1 --timeout=180s
kubectl --context="$KUBE_CONTEXT" -n kagent rollout status \
  deploy/team2-not-allowed --timeout=180s
printf '%s team1 and team2-not-allowed are ready\n' "$OK"

printf '%s == phase 2/4 — positive check: team1 -> k8s-agent (expect 200) ==\n' "$LOG"
code=$(probe team1 || true)
if [[ "$code" == "200" ]]; then
  printf '%s team1 -> k8s-agent: HTTP %s (ALLOWED)\n' "$OK" "$code"
else
  printf '%s team1 -> k8s-agent: HTTP %s (expected 200)\n' "$FAIL" "$code"
  exit 1
fi

printf '%s == phase 3/4 — negative check: team2 -> k8s-agent (expect 403) ==\n' "$LOG"
code=$(probe team2-not-allowed || true)
if [[ "$code" == "403" ]]; then
  printf '%s team2-not-allowed -> k8s-agent: HTTP %s (DENIED as expected)\n' "$OK" "$code"
else
  printf '%s team2-not-allowed -> k8s-agent: HTTP %s (expected 403)\n' "$FAIL" "$code"
  exit 1
fi

printf '%s == phase 4/4 — confirm AccessPolicy translated to a waypoint policy ==\n' "$LOG"
state=$(kubectl --context="$KUBE_CONTEXT" -n kagent get accesspolicy \
  deny-team2-to-k8s-agent -o jsonpath='{.status.state}' 2>/dev/null || true)
printf '%s AccessPolicy deny-team2-to-k8s-agent: state=%s\n' "$OK" "${state:-unknown}"
kubectl --context="$KUBE_CONTEXT" -n kagent get enterpriseagentgatewaypolicy \
  accesspolicy-deny-team2-to-k8s-agent-waypoint 2>/dev/null || true

echo "To inspect the demo UI:"
echo "  kubectl --context=${KUBE_CONTEXT} -n kagent port-forward svc/solo-enterprise-ui 8080:80"
echo "  open http://localhost:8080"
