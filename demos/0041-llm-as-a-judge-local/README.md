# Lab: LLM-as-a-judge as a response guardrail with agentgateway

Runnable companion to the write-up *How to catch the numbers your provider's model makes
up, with a second model in your cluster*, which has the narrative and every command in
order. This file is just the map.

What it catches, precisely: **answers that state specifics they cannot possibly support**.
Figures, percentages, money amounts, dates or claims about named organisations, given
without a source. Not truth, and not quality: the checker never sees the question. Refusing
or hedging scores well. Unsourced precision does not.

Everything here is open source agentgateway (`agentgateway.dev` API group). No image
build: the webhook is standard-library Python in a ConfigMap. You need one provider API
key for the generator; the judge needs nothing.

Want the cloud-judge variant instead, with the agent deployed through kagent and Gemini
doing the grading? That one lives in
[antonioberben/kagent-examples, demo 0040](https://github.com/antonioberben/kagent-examples/tree/main/demos/0040-llm-as-a-judge).
Same `promptGuard` policy shape, different judge, and it needs OpenAI and Google keys.

## Layout

The generator stays with your provider. Only the grading happens in the cluster.

| Path | What it is |
| --- | --- |
| `manifests/01-ollama.yaml` | The **judge model**, in-cluster: Ollama Deployment + ClusterIP Service. Only the webhook talks to it. |
| `manifests/02-backend-route.yaml` | `AgentgatewayBackend` for your **provider** (the one hop that leaves), plus the `HTTPRoute`. |
| `manifests/03-judge-webhook.yaml` | The webhook Deployment + Service. Reads the code from the `judge-code` ConfigMap. |
| `manifests/04-guardrail-policy.yaml` | The `AgentgatewayPolicy` with `promptGuard.response.webhook`. |
| `manifests/05-judge-via-gateway.yaml` | **Optional.** Routes the judge through agentgateway so its tokens show up in the metric too. |
| `judge/judge.py` | The judge webhook. Python standard library only, ~200 lines. |
| `test.sh` | Asserts the whole thing behaves as documented. Run it after any change. |
| `.env.example` | Every knob the lab uses, including the pinned versions. Copy to `.env`, which is gitignored. |

## Prerequisites

A cluster (`kind` works), `kubectl`, `helm`, `jq`, an API key for your provider, and
enough memory on a node to keep a 3b model resident.

## Configuration

**`.env` is the source of truth for versions.** Nothing in this lab installs a rolling
tag: the Gateway API release, the agentgateway chart and both container images are pinned
there, and `test.sh` fails if a manifest drifts from what `.env` declares. That check
exists because the failure it prevents is silent — you bump one and forget the other, and
the lab keeps working until the day it doesn't.

To move to newer releases, change the value in `.env`, change the matching `image:` line
in `manifests/01` or `manifests/03`, and re-run `./test.sh`. The current stable releases
are listed in the comments in `.env.example`, along with the `gh release list` commands
that tell you what is newer.

```bash
cp .env.example .env
$EDITOR .env            # OPENAI_API_KEY is the only value you have to fill in
set -a && source .env && set +a
```

`.env` is gitignored, `.env.example` is not, and `OPENAI_API_KEY` is the only secret in
either. The article types that key at a prompt instead, which is the better move when you
are following along in a terminal and do not want a file holding it at all. If you do
that, leave the `.env` line empty and export the key in your shell: `test.sh` keeps an
exported key rather than letting an empty `.env` line overwrite it.

## Order

```bash
# 0. cluster, Gateway API CRDs, agentgateway control plane, Gateway. See the article.

# 1. the judge model, then pull it (a real 1.9 GB download)
kubectl apply -f manifests/01-ollama.yaml
kubectl -n agentgateway-system rollout status deploy/ollama
kubectl -n agentgateway-system exec deploy/ollama -- ollama pull "$JUDGE_MODEL"

# 2. your provider, and the route the policy will target
kubectl -n agentgateway-system create secret generic openai-secret \
  --from-literal=Authorization="$OPENAI_API_KEY"
kubectl apply -f manifests/02-backend-route.yaml

# 3. the judge webhook: code first, then workload
kubectl -n agentgateway-system create configmap judge-code \
  --from-file=judge.py=judge/judge.py \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f manifests/03-judge-webhook.yaml
kubectl -n agentgateway-system rollout status deploy/judge-webhook

# 4. wire it in
kubectl apply -f manifests/04-guardrail-policy.yaml

# 5. check the whole thing
./test.sh
```

`manifests/` is numbered but **not** safe to `kubectl apply -f manifests/` in one go: the
`judge-code` ConfigMap has to exist before step 3, and it is created from `judge/judge.py`
rather than checked in, so the code has exactly one source of truth.

## Verifying it

`./test.sh` is the answer to "did I break something". It reads `.env`, pins every kubectl
call to `KUBE_CONTEXT`, walks all three modes, and puts the webhook back the way it found
it. It is safe to re-run and it exits non-zero on the first real failure.

What it asserts, in order: that the pinned versions in `.env` match both the manifests and
what is actually running; that the control plane, the Gateway, the policy attachment and
the route are all healthy; that the provider route is not a catch-all and an unmatched path
404s rather than reaching the provider; that the webhook honours its contract on every
path, including the malformed ones; that observe leaves the answer alone, annotate appends
the verdict and block returns a 403; that both failure boundaries behave; and that the
token metric names the models you expect.

The prompts and the canned answers are deliberately dateless: they ask about "next year"
and "last quarter" rather than a year somebody typed, so the impossibility stays relative
to whenever you run this. A prompt with a fixed year in it quietly stops testing
hallucination once that year becomes history.

On the scores, it asserts **direction, not values**: that a fabricated answer lands below
`THRESHOLD`, that an honest one lands at or above it, and that the honest one outscores
the fabricated one. A 3b judge is noisy at the margin, so a test demanding exactly 1/5
would be a test that starts lying the first time you change the model or the rubric.

Everything from "end to end through the gateway" onwards needs `OPENAI_API_KEY`: about a
dozen assertions, including all three modes, both failure boundaries and the token metric.
Without the key that whole block is skipped rather than failed, and what still runs is the
webhook contract against the local judge, which is the half that does not cost money.

It also refuses to start if `JUDGE_TIMEOUT` is 10 or higher, for the reason in the next
section, and it does not stop at the first failure: every assertion runs, then it exits
non-zero if any of them failed.

## The route match is not cosmetic

`manifests/02` gives the provider `HTTPRoute` an explicit `matches` on the `/v1` prefix.
Without it the route is a catch-all, and a catch-all in front of a metered provider turns
a typo into a bill: if `OLLAMA_URL` is ever wrong, the judge's own calls stop 404ing and
match the provider route instead, so every answer gets graded by `gpt-4o-mini` out on the
internet, with correct-looking scores in the logs and nothing to tell you.

Measured while re-running the lab: three graded answers on a broken `OLLAMA_URL` added
~15k input tokens to the provider counter and zero to Ollama's. With the path match in
place the same typo returns 404, `judge.py` logs `judge unavailable`, and the provider
counter does not move. `test.sh` asserts both the match and the 404.

## Two timeouts, and only one of them is yours

`JUDGE_TIMEOUT` is how long `judge.py` waits for the judge model. agentgateway has its own
budget for the whole webhook call and it is **10 seconds, hard-coded in the proxy** and not
configurable from the policy. So a value at or above 10 buys the judge nothing: the gateway
gives up first, applies `failureMode`, and your verdict arrives in the log after the answer
already reached the user. The symptom is nasty precisely because it looks fine, an ungraded
answer plus a healthy-looking score a moment later.

The lab ships `JUDGE_TIMEOUT=8` and `test.sh` refuses to run at 10 or above.

The case where ten seconds is genuinely not enough is a **cold model**, and it is worth knowing
before it bites you. Measured here: a warm call is 0.6s, the first call after Ollama has unloaded
the model is 11.6s. Over the gateway's cap, so the guardrail times out and the answer goes out
ungraded. That is why `manifests/01` sets `OLLAMA_KEEP_ALIVE=-1` instead of a timeout you cannot
raise anyway. On a shared node where you do not want the model resident forever, warm it on a
timer instead.

## Non-streaming only

`promptGuard` has a third field next to `request` and `response`, called `streaming`, and it
is **disabled by default** to keep streaming throughput intact. A client that sends
`"stream": true` therefore bypasses the judge completely: no verdict, no log line, no 403.
Every call in this lab is non-streaming, which is why all three modes behave.

`streaming: Enabled` brings the response guards back for streamed answers, and changes the
job: the webhook is called per window of text as tokens go by, so it grades fragments rather
than a finished answer, and masking is not supported there at all. Annotate has no streaming
equivalent; observe and block do. Worth settling before you promise a product team a quality
gate on a streaming endpoint.

## Two failure boundaries, not one

Worth understanding before you rely on any of this, because they are configured in
different places and can disagree with each other.

If the **judge model** is unreachable, `judge.py` catches it and returns a pass action.
That is a decision in the code, on the `except` branch in `decide()`.

If the **webhook itself** is unreachable, `judge.py` never runs and agentgateway decides,
via `failureMode` on the webhook guard. **The default is `FailClosed`**, which means a
dead webhook rejects live traffic. This lab sets `FailOpen` explicitly in `manifests/04`
so both boundaries agree with the fail-open posture the article argues for.

For a quality signal, fail open on both. For a guardrail that is legally load-bearing,
fail closed on both. What you do not want is the two disagreeing because one of them was
a default you never looked at.

## Switching modes

The policy never changes. Only the webhook does.

```bash
kubectl -n agentgateway-system set env deploy/judge-webhook MODE=observe    # log only
kubectl -n agentgateway-system set env deploy/judge-webhook MODE=annotate   # append the verdict
kubectl -n agentgateway-system set env deploy/judge-webhook MODE=block THRESHOLD=3
```

Editing `judge/judge.py` means recreating the ConfigMap and bumping the
`judge/code-revision` annotation in `03-judge-webhook.yaml`, otherwise the pod keeps
running the old code.

## Watching it

```bash
kubectl -n agentgateway-system logs -l app=judge-webhook -f

kubectl -n agentgateway-system port-forward deploy/agentgateway-proxy 15020:15020
curl -s localhost:15020/metrics | grep agentgateway_gen_ai_client_token_usage_sum
```

The metric only counts what crosses the gateway. Until you apply `manifests/05` and point
`OLLAMA_URL` at the gateway, the judge is invisible there and you are looking at your
billed spend only.

## Testing the webhook without a cluster

`judge.py` is importable and has no cluster dependencies, so the contract can be
exercised against any OpenAI-compatible endpoint:

```bash
MODE=observe OLLAMA_URL=http://localhost:11434/v1/chat/completions python3 judge/judge.py

curl -s localhost:8000/response -H 'content-type: application/json' -d '{
  "body": {"choices": [{"message": {"role": "assistant", "content":
    "Last quarter the top five European banks prevented 61.4% of fraud attempts."}}]}
}' | jq
```

## A note on the judge model

`qwen2.5:1.5b` was not good enough. It scored a fabricated answer and an honest one
identically, and marked a correct answer *down* for not containing enough numbers. The
lab settled on `qwen2.5:3b`, which discriminates reliably on the obvious cases and stays
noisy on the marginal ones. If you shrink the model or swap the family, re-run `./test.sh`
before trusting anything: the discrimination assertion is exactly the one that catches it.

## Cleanup

```bash
kind delete cluster --name "$CLUSTER_NAME"
```
