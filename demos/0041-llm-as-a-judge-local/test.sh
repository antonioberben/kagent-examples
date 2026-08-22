#!/usr/bin/env bash
# test.sh — assert the LLM-as-a-judge guardrail lab behaves as documented.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INVOKED_DIR="$(pwd)"
if [[ "$SCRIPT_DIR" != "$INVOKED_DIR" ]]; then
  echo "ERROR: this script must be run from its own directory."
  echo "       cd $SCRIPT_DIR && ./test.sh"
  exit 1
fi
REPO_ROOT="$SCRIPT_DIR"

# An empty OPENAI_API_KEY= line in .env would otherwise clobber a key you already
# exported, which fails later and looks like a bad key rather than an empty one.
SHELL_OPENAI_API_KEY="${OPENAI_API_KEY:-}"
if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a; source "${REPO_ROOT}/.env"; set +a
fi
[[ -z "${OPENAI_API_KEY:-}" ]] && export OPENAI_API_KEY="$SHELL_OPENAI_API_KEY"

REQUIRED_VARS=(
  KUBE_CONTEXT NAMESPACE
  GATEWAY_API_VERSION AGENTGATEWAY_VERSION
  OLLAMA_IMAGE JUDGE_RUNTIME_IMAGE
  GENERATOR_MODEL JUDGE_MODEL
  THRESHOLD JUDGE_TIMEOUT GATEWAY_PORT JUDGE_PORT METRICS_PORT
)
for v in "${REQUIRED_VARS[@]}"; do
  [[ -n "${!v:-}" ]] || { echo "missing $v in .env" >&2; exit 1; }
done

# agentgateway caps the guardrail webhook call at 10s on its side. A larger
# JUDGE_TIMEOUT does not buy the judge more time, it just means the gateway gives
# up first and the verdict lands after the answer already went out. Refuse to run
# rather than assert on behaviour that is quietly wrong.
# awk, not (( )): JUDGE_TIMEOUT is allowed to be fractional and bash arithmetic is not.
if awk -v t="$JUDGE_TIMEOUT" 'BEGIN { exit !(t + 0 >= 10) }'; then
  echo "JUDGE_TIMEOUT=$JUDGE_TIMEOUT must stay below the gateway's 10s guardrail timeout" >&2
  exit 1
fi

LOG=$'\033[0;36m[test]\033[0m'
OK=$'\033[0;32m[ ok  ]\033[0m'
WARN=$'\033[0;33m[warn ]\033[0m'
FAIL=$'\033[0;31m[fail ]\033[0m'

PASSED=0
FAILED=0
SKIPPED=0
WAIT_TIMEOUT=300

pass() { printf '%s %s\n' "$OK" "$1"; PASSED=$((PASSED + 1)); }
fail() { printf '%s %s\n' "$FAIL" "$1"; FAILED=$((FAILED + 1)); }
skip() { printf '%s %s\n' "$WARN" "$1"; SKIPPED=$((SKIPPED + 1)); }
phase() { printf '\n%s == %s ==\n' "$LOG" "$1"; }

# Compare and report in one line so every assertion reads the same way.
expect_eq() {
  local what="$1" want="$2" got="$3"
  if [[ "$want" == "$got" ]]; then
    pass "$what — $got"
  else
    fail "$what — expected '$want', got '$got'"
  fi
}

# ---------------------------------------------------------------------------
# port-forwards: opened here, torn down on any exit path
# ---------------------------------------------------------------------------
# Entries are "<local_port> <pid>" so a re-forward can retire the stale process
# holding that port. Restarting a pod kills the tunnel but not the kubectl
# process, and the leftover keeps the local port bound.
PF_PIDS=()

cleanup() {
  local entry
  for entry in "${PF_PIDS[@]:-}"; do
    [[ -n "$entry" ]] && kill "${entry##* }" 2>/dev/null || true
  done
}
trap cleanup EXIT

port_forward() {
  local target="$1" local_port="$2" remote_port="$3" probe="$4"
  local entry kept=()
  for entry in "${PF_PIDS[@]:-}"; do
    [[ -z "$entry" ]] && continue
    if [[ "${entry%% *}" == "$local_port" ]]; then
      kill "${entry##* }" 2>/dev/null || true
      wait "${entry##* }" 2>/dev/null || true
    else
      kept+=("$entry")
    fi
  done
  PF_PIDS=("${kept[@]:-}")

  kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" \
    port-forward "$target" "${local_port}:${remote_port}" >/dev/null 2>&1 &
  PF_PIDS+=("$local_port $!")
  local deadline=$(( $(date +%s) + 60 ))
  until curl -s -o /dev/null "$probe" 2>/dev/null; do
    (( $(date +%s) > deadline )) && { echo "timeout waiting for $target" >&2; exit 1; }
    sleep 1
  done
}

# Ask the generator through the gateway. Echoes "<http_code> <body_file>".
ask_gateway() {
  local prompt="$1" body
  body="$(mktemp)"
  local code
  code="$(curl -s -o "$body" -w '%{http_code}' --max-time 120 \
    "localhost:${GATEWAY_PORT}/v1/chat/completions" \
    -H 'content-type: application/json' \
    -d "$(jq -n --arg m "$GENERATOR_MODEL" --arg p "$prompt" \
          '{model:$m, messages:[{role:"user", content:$p}]}')")"
  echo "$code $body"
}

# Hand the webhook a response envelope directly, exactly as agentgateway sends it.
ask_judge() {
  local answer="$1"
  curl -s --max-time 120 "localhost:${JUDGE_PORT}/response" \
    -H 'content-type: application/json' \
    -d "$(jq -n --arg a "$answer" \
          '{body:{choices:[{message:{role:"assistant", content:$a}}]}}')"
}

set_mode() {
  local mode="$1"
  kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" \
    set env deploy/judge-webhook MODE="$mode" THRESHOLD="$THRESHOLD" >/dev/null
  kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" \
    rollout status deploy/judge-webhook --timeout="${WAIT_TIMEOUT}s" >/dev/null
  # The pod is new, so the old forward is dead. Re-open it.
  port_forward svc/judge-webhook "$JUDGE_PORT" 8000 "localhost:${JUDGE_PORT}/healthz"
  local deadline=$(( $(date +%s) + 60 ))
  until [[ "$(curl -s "localhost:${JUDGE_PORT}/healthz" | jq -r '.mode')" == "$mode" ]]; do
    (( $(date +%s) > deadline )) && { echo "webhook never reported mode=$mode" >&2; exit 1; }
    sleep 2
  done
}

# A prompt that reliably produces unsourced specifics, and one that does not.
# Both ask about a period the model cannot have data for, relative to whenever this
# runs, and neither names a date on purpose: a prompt with a year in it stops being a
# hallucination test as soon as that year turns into history and the figures turn into
# lookups. Keep the impossibility relative and these assertions survive the calendar.
FABRICATED_PROMPT='Write a short analyst briefing paragraph on AI fraud prevention at European banks for next year. Include concrete percentages and euro amounts so it reads like a real briefing.'
HONEST_PROMPT='In two sentences and with no statistics, explain why credit scoring models need human oversight.'
FABRICATED_ANSWER='Last quarter the top five European banks prevented 61.4% of fraud attempts with AI, saving 2.3 billion euros, with the largest of them leading at 68.2%.'
HONEST_ANSWER='I do not have reliable figures for that. Credit scoring models need human oversight because they can encode bias present in historical data.'

# ---------------------------------------------------------------------------
phase 'pinned versions: .env is the source of truth, manifests must agree'
# ---------------------------------------------------------------------------
rolling=""
for pin in "$GATEWAY_API_VERSION" "$AGENTGATEWAY_VERSION" "$OLLAMA_IMAGE" "$JUDGE_RUNTIME_IMAGE"; do
  case "$pin" in
    *latest*|*-dev*) rolling="$pin" ;;
  esac
done
if [[ -z "$rolling" ]]; then
  pass 'no rolling tags in .env'
else
  fail "pinned version is a rolling tag — $rolling"
fi

expect_eq 'manifests/01 ollama image matches .env' \
  "$OLLAMA_IMAGE" \
  "$(awk '/image: ollama/{print $2}' manifests/01-ollama.yaml)"

expect_eq 'manifests/03 judge runtime image matches .env' \
  "$JUDGE_RUNTIME_IMAGE" \
  "$(awk '/image: python/{print $2}' manifests/03-judge-webhook.yaml)"

expect_eq 'installed agentgateway chart matches .env' \
  "$AGENTGATEWAY_VERSION" \
  "$(helm --kube-context="$KUBE_CONTEXT" -n "$NAMESPACE" list -o json \
     | jq -r '.[] | select(.name=="agentgateway") | .chart' | sed 's/^agentgateway-//')"

expect_eq 'running control plane matches .env' \
  "v${AGENTGATEWAY_VERSION}" \
  "$(kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" get deploy agentgateway \
     -o jsonpath='{.spec.template.spec.containers[0].image}' | sed 's/.*://')"

expect_eq 'running ollama image matches .env' \
  "$OLLAMA_IMAGE" \
  "$(kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" get deploy ollama \
     -o jsonpath='{.spec.template.spec.containers[0].image}')"

# ---------------------------------------------------------------------------
phase 'control plane and workloads'
# ---------------------------------------------------------------------------
expect_eq 'GatewayClass agentgateway accepted' 'True' \
  "$(kubectl --context="$KUBE_CONTEXT" get gatewayclass agentgateway \
     -o jsonpath='{.status.conditions[?(@.type=="Accepted")].status}')"

expect_eq 'Gateway programmed' 'True' \
  "$(kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" get gateway agentgateway-proxy \
     -o jsonpath='{.status.conditions[?(@.type=="Programmed")].status}')"

for d in ollama judge-webhook agentgateway agentgateway-proxy; do
  ready="$(kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" get deploy "$d" \
           -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)"
  expect_eq "deployment $d ready" '1' "${ready:-0}"
done

expect_eq "judge model $JUDGE_MODEL present in ollama" 'yes' \
  "$(kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" exec deploy/ollama -- \
     ollama list 2>/dev/null | grep -qF "$JUDGE_MODEL" && echo yes || echo no)"

# ---------------------------------------------------------------------------
phase 'guardrail wiring'
# ---------------------------------------------------------------------------
expect_eq 'AgentgatewayBackend openai accepted' 'True' \
  "$(kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" get agentgatewaybackend openai \
     -o jsonpath='{.status.conditions[?(@.type=="Accepted")].status}')"

expect_eq 'AgentgatewayPolicy accepted' 'True' \
  "$(kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" get agentgatewaypolicy judge-guardrail \
     -o jsonpath='{.status.ancestors[0].conditions[?(@.type=="Accepted")].status}')"

expect_eq 'AgentgatewayPolicy attached to the route' 'True' \
  "$(kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" get agentgatewaypolicy judge-guardrail \
     -o jsonpath='{.status.ancestors[0].conditions[?(@.type=="Attached")].status}')"

expect_eq 'policy targets the openai route by name' 'openai' \
  "$(kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" get agentgatewaypolicy judge-guardrail \
     -o jsonpath='{.spec.targetRefs[0].name}')"

expect_eq 'guardrail points at the judge-webhook Service' 'judge-webhook' \
  "$(kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" get agentgatewaypolicy judge-guardrail \
     -o jsonpath='{.spec.backend.ai.promptGuard.response[0].webhook.backendRef.name}')"

expect_eq 'the openai route matches a path prefix, so it is not a catch-all' '/v1' \
  "$(kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" get httproute openai \
     -o jsonpath='{.spec.rules[0].matches[0].path.value}')"

port_forward svc/agentgateway-proxy "$GATEWAY_PORT" 80 "localhost:${GATEWAY_PORT}"
port_forward svc/judge-webhook "$JUDGE_PORT" 8000 "localhost:${JUDGE_PORT}/healthz"

# The failure this guards against is expensive and silent: a catch-all route in
# front of a paid provider swallows the judge's own calls when OLLAMA_URL is
# wrong, so every answer gets graded remotely, on the invoice, out of the
# cluster. A 404 here is what makes that mistake noisy instead.
expect_eq 'an unmatched path 404s instead of reaching the provider' '404' \
  "$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 \
     "localhost:${GATEWAY_PORT}/not-a-real-route/v1/chat/completions" \
     -H 'content-type: application/json' \
     -d '{"model":"x","messages":[{"role":"user","content":"hi"}]}')"

# ---------------------------------------------------------------------------
phase 'webhook contract, called directly'
# ---------------------------------------------------------------------------
set_mode observe

expect_eq 'healthz reports the running mode' 'observe' \
  "$(curl -s "localhost:${JUDGE_PORT}/healthz" | jq -r '.mode')"

expect_eq 'request phase is explicitly not evaluated' 'request phase not evaluated' \
  "$(curl -s "localhost:${JUDGE_PORT}/request" -H 'content-type: application/json' \
     -d '{"body":{"messages":[]}}' | jq -r '.action.reason')"

expect_eq 'empty choices are handled, not crashed on' 'empty response, nothing to grade' \
  "$(curl -s "localhost:${JUDGE_PORT}/response" -H 'content-type: application/json' \
     -d '{"body":{"choices":[]}}' | jq -r '.action.reason')"

expect_eq 'unparseable body degrades to a pass action' 'unparseable body, not evaluated' \
  "$(curl -s "localhost:${JUDGE_PORT}/response" -H 'content-type: application/json' \
     -d 'not json at all' | jq -r '.action.reason')"

expect_eq 'unknown path is a 404' '404' \
  "$(curl -s -o /dev/null -w '%{http_code}' "localhost:${JUDGE_PORT}/nope" \
     -H 'content-type: application/json' -d '{}')"

# The scores themselves: assert the direction, never the exact number. A 3b model
# is noisy at the margin, and pinning an exact score makes this test lie later.
fab_verdict="$(ask_judge "$FABRICATED_ANSWER")"
fab_score="$(echo "$fab_verdict" | jq -r '.action.reason' | grep -oE '[0-9]+/5' | cut -d/ -f1)"
if [[ -n "$fab_score" && "$fab_score" -lt "$THRESHOLD" ]]; then
  pass "fabricated answer scores below threshold — ${fab_score}/5 < ${THRESHOLD}"
else
  fail "fabricated answer should score below ${THRESHOLD}, got '${fab_score:-none}'"
fi

honest_verdict="$(ask_judge "$HONEST_ANSWER")"
honest_score="$(echo "$honest_verdict" | jq -r '.action.reason' | grep -oE '[0-9]+/5' | cut -d/ -f1)"
if [[ -n "$honest_score" && "$honest_score" -ge "$THRESHOLD" ]]; then
  pass "honest answer scores at or above threshold — ${honest_score}/5 >= ${THRESHOLD}"
else
  fail "honest answer should score at least ${THRESHOLD}, got '${honest_score:-none}'"
fi

if [[ -n "$fab_score" && -n "$honest_score" && "$honest_score" -gt "$fab_score" ]]; then
  pass "judge discriminates — honest ${honest_score}/5 beats fabricated ${fab_score}/5"
else
  fail "judge does not discriminate — honest ${honest_score:-?} vs fabricated ${fab_score:-?}"
fi

expect_eq 'observe mode returns a bare pass action, body untouched' 'null' \
  "$(echo "$fab_verdict" | jq -r '.action.body // "null"')"

# ---------------------------------------------------------------------------
phase 'end to end through the gateway — observe'
# ---------------------------------------------------------------------------
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  skip 'no OPENAI_API_KEY, skipping every test that needs the generator'
else
  read -r code body <<<"$(ask_gateway "$HONEST_PROMPT")"
  expect_eq 'observe: honest question returns 200' '200' "$code"

  content="$(jq -r '.choices[0].message.content // ""' "$body")"
  if [[ -n "$content" ]]; then
    pass 'observe: answer body reaches the caller intact'
  else
    fail "observe: empty answer body — $(head -c 200 "$body")"
  fi

  expect_eq 'observe: nothing is appended to the answer' 'clean' \
    "$(grep -q 'Grounding check' <<<"$content" && echo 'annotated' || echo 'clean')"
  rm -f "$body"

  # ---------------------------------------------------------------------------
  phase 'end to end through the gateway — annotate'
  # ---------------------------------------------------------------------------
  set_mode annotate

  read -r code body <<<"$(ask_gateway "$FABRICATED_PROMPT")"
  expect_eq 'annotate: request still returns 200' '200' "$code"

  content="$(jq -r '.choices[0].message.content // ""' "$body")"
  expect_eq 'annotate: verdict is appended to the answer' 'annotated' \
    "$(grep -q 'Grounding check' <<<"$content" && echo 'annotated' || echo 'clean')"

  expect_eq 'annotate: the appended verdict names the judge model' 'yes' \
    "$(grep -qF "$JUDGE_MODEL" <<<"$content" && echo yes || echo no)"
  rm -f "$body"

  # ---------------------------------------------------------------------------
  phase 'end to end through the gateway — block'
  # ---------------------------------------------------------------------------
  set_mode block

  read -r code body <<<"$(ask_gateway "$FABRICATED_PROMPT")"
  expect_eq 'block: fabricated answer is rejected with 403' '403' "$code"
  expect_eq 'block: the caller gets the refusal text, not the answer' 'yes' \
    "$(grep -qF 'did not pass quality review' "$body" && echo yes || echo no)"
  rm -f "$body"

  read -r code body <<<"$(ask_gateway "$HONEST_PROMPT")"
  expect_eq 'block: honest question still returns 200' '200' "$code"
  rm -f "$body"

  # ---------------------------------------------------------------------------
  phase 'failure boundaries'
  # ---------------------------------------------------------------------------
  # Boundary 1: the webhook is up, the judge model is not. judge.py catches this
  # and returns a pass action, so the answer goes through ungraded.
  kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" scale deploy/ollama --replicas=0 >/dev/null
  kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" \
    wait --for=delete pod -l app=ollama --timeout="${WAIT_TIMEOUT}s" >/dev/null

  read -r code body <<<"$(ask_gateway "$FABRICATED_PROMPT")"
  expect_eq 'judge model down: webhook fails open, answer passes ungraded' '200' "$code"
  rm -f "$body"

  kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" scale deploy/ollama --replicas=1 >/dev/null
  kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" \
    rollout status deploy/ollama --timeout="${WAIT_TIMEOUT}s" >/dev/null
  # emptyDir: a new pod is a new disk, so the model has to come back down.
  kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" exec deploy/ollama -- \
    ollama pull "$JUDGE_MODEL" >/dev/null 2>&1

  # Boundary 2: the webhook itself is gone. Now agentgateway decides, not judge.py,
  # and spec...webhook.failureMode governs it. Default is FailClosed.
  declared_mode="$(kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" \
    get agentgatewaypolicy judge-guardrail \
    -o jsonpath='{.spec.backend.ai.promptGuard.response[0].webhook.failureMode}')"
  effective_mode="${declared_mode:-FailClosed}"

  kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" scale deploy/judge-webhook --replicas=0 >/dev/null
  kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" \
    wait --for=delete pod -l app=judge-webhook --timeout="${WAIT_TIMEOUT}s" >/dev/null

  read -r code body <<<"$(ask_gateway "$HONEST_PROMPT")"
  if [[ "$effective_mode" == "FailOpen" ]]; then
    expect_eq "webhook down + failureMode=FailOpen: request survives" '200' "$code"
  else
    if [[ "$code" != "200" ]]; then
      pass "webhook down + failureMode=${effective_mode}: request rejected — $code"
    else
      fail "webhook down + failureMode=${effective_mode}: expected a rejection, got 200"
    fi
  fi
  rm -f "$body"

  kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" scale deploy/judge-webhook --replicas=1 >/dev/null
  kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" \
    rollout status deploy/judge-webhook --timeout="${WAIT_TIMEOUT}s" >/dev/null
  port_forward svc/judge-webhook "$JUDGE_PORT" 8000 "localhost:${JUDGE_PORT}/healthz"

  # ---------------------------------------------------------------------------
  phase 'token metric'
  # ---------------------------------------------------------------------------
  port_forward deploy/agentgateway-proxy "$METRICS_PORT" 15020 "localhost:${METRICS_PORT}/metrics"
  metrics="$(curl -s "localhost:${METRICS_PORT}/metrics" | grep agentgateway_gen_ai_client_token_usage_sum || true)"

  expect_eq "metric reports the generator $GENERATOR_MODEL" 'yes' \
    "$(grep -qF "gen_ai_request_model=\"${GENERATOR_MODEL}\"" <<<"$metrics" && echo yes || echo no)"

  # Only true when manifests/05 is applied and OLLAMA_URL points at the gateway.
  routed_via_gateway="$(kubectl --context="$KUBE_CONTEXT" -n "$NAMESPACE" get deploy judge-webhook \
    -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="OLLAMA_URL")].value}')"
  if [[ "$routed_via_gateway" == *agentgateway-proxy* ]]; then
    expect_eq "metric reports the judge $JUDGE_MODEL too" 'yes' \
      "$(grep -qF "gen_ai_request_model=\"${JUDGE_MODEL}\"" <<<"$metrics" && echo yes || echo no)"
  else
    skip "judge calls Ollama directly, so its tokens never cross the gateway (manifests/05 not in play)"
  fi
fi

# ---------------------------------------------------------------------------
phase 'summary'
# ---------------------------------------------------------------------------
set_mode "${MODE:-observe}"
printf '%s %d passed, %d failed, %d skipped\n' "$LOG" "$PASSED" "$FAILED" "$SKIPPED"
[[ "$FAILED" -eq 0 ]] || exit 1
printf '%s webhook logs: kubectl --context=%s -n %s logs -l app=judge-webhook\n' \
  "$LOG" "$KUBE_CONTEXT" "$NAMESPACE"
