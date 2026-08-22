"""Guardrail webhook for agentgateway: LLM-as-a-judge on the response path.

agentgateway calls POST /request before the model and POST /response after it.
This service only does real work on /response: it reads the answer, asks a
small local model to score it, and returns one `action` object.

What it scores is one thing: does the answer state specifics it cannot possibly
support? Figures, percentages, money amounts, dates or claims about named
organisations, given without a source. Not truth, and not quality: this service
never sees the user's question. Refusing or hedging scores well. Unsourced
precision does not.

The action is an untagged union on agentgateway's side, so the SHAPE of what
you return is the decision:

  pass    {"action": {"reason": "..."}}
  mask    {"action": {"body": {"choices": [...]}, "reason": "..."}}
  reject  {"action": {"body": "text", "status_code": 403, "reason": "..."}}

Non-streaming responses only. promptGuard.streaming defaults to disabled, so a client
that asks for `"stream": true` never reaches this service. See manifests/04.

Standard library only. No pip install at pod startup.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODE = os.environ.get("MODE", "observe").strip().lower()
THRESHOLD = int(os.environ.get("THRESHOLD", "3"))
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "qwen2.5:3b")
OLLAMA_URL = os.environ.get(
    "OLLAMA_URL",
    "http://ollama.agentgateway-system.svc.cluster.local:11434/v1/chat/completions",
)
# agentgateway caps the guardrail webhook call at 10s on its side, so anything at or
# above that means the gateway gives up before we answer and failureMode decides.
JUDGE_TIMEOUT = float(os.environ.get("JUDGE_TIMEOUT", "8"))
PORT = int(os.environ.get("PORT", "8000"))

# Note on scope: the response phase gives us the answer, NOT the original question,
# so anything of the form "does it answer what was asked" is not gradeable here.
#
# Note on shape: this asks ONE question, not three. A multi-criteria rubric reads
# well and scores badly on a small model: it returns confident numbers that do not
# discriminate. One sharply defined question with explicit anchors does.
RUBRIC = """You check one answer for fabrication. You do NOT have the original question.

One question only: does the answer state specifics it cannot possibly support?
Specifics means precise statistics, percentages, money amounts, dates, or claims
about named organisations, given without a source.

Score 1 to 5:
  1 = several unsourced specifics, stated as fact
  3 = one or two, or specifics that are common knowledge
  5 = no unsupported specifics, or all of them attributed to a named source

An answer that refuses, hedges, or says it does not know is GOOD: score 5.
Being vague is not a fault. Unsourced precision is.

Reply with JSON only, no prose, no fences:
{"score": <1-5>, "reason": "<one short sentence>"}
"""

def log(msg):
    print(f"[judge] {msg}", flush=True)


def extract_answer(payload):
    """Pull the assistant text out of the /response envelope.

    agentgateway sends {"body": {"choices": [{"message": {"role", "content"}}]}}
    """
    choices = payload.get("body", {}).get("choices", []) or []
    parts = []
    for choice in choices:
        content = (choice.get("message") or {}).get("content")
        if content:
            parts.append(content)
    return "\n".join(parts)


def parse_verdict(raw):
    """Small models wrap JSON in prose and fences. Be tolerant, not clever."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON object in judge output: {raw[:200]!r}")
    verdict = json.loads(match.group(0))
    score = verdict.get("score")
    if not isinstance(score, (int, float)):
        raise ValueError(f"missing or non-numeric 'score' in {verdict!r}")
    scores = {
        "score": max(1, min(5, int(round(score)))),
        "reason": str(verdict.get("reason", ""))[:300],
    }
    return scores


def ask_judge(answer):
    body = json.dumps(
        {
            "model": JUDGE_MODEL,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": RUBRIC},
                {"role": "user", "content": f"Answer to grade:\n\n{answer}"},
            ],
        }
    ).encode()
    request = urllib.request.Request(
        OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=JUDGE_TIMEOUT) as response:
        completion = json.loads(response.read())
    return parse_verdict(completion["choices"][0]["message"]["content"])


def annotate(payload, verdict):
    """Rewrite every choice, appending the verdict to the text the user sees."""
    note = (
        f"\n\n---\nUnsourced figures check ({JUDGE_MODEL}): {verdict['score']}/5. "
        f"{verdict['reason']}"
    )
    choices = []
    for choice in payload.get("body", {}).get("choices", []) or []:
        message = choice.get("message") or {}
        choices.append(
            {
                "message": {
                    "role": message.get("role", "assistant"),
                    "content": (message.get("content") or "") + note,
                }
            }
        )
    return {"action": {"body": {"choices": choices}, "reason": "verdict appended"}}


def decide(payload):
    answer = extract_answer(payload)
    if not answer.strip():
        return {"action": {"reason": "empty response, nothing to grade"}}

    try:
        verdict = ask_judge(answer)
    except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError) as err:
        # Fail open on purpose: a broken judge must not break the product.
        # If your risk appetite is the other way round, reject here instead
        # and say so out loud in your runbook.
        log(f"judge unavailable, passing through: {err}")
        return {"action": {"reason": "judge unavailable, not evaluated"}}

    log(f"score={verdict['score']}/5 mode={MODE} :: {verdict['reason']}")

    if MODE == "annotate":
        return annotate(payload, verdict)

    if MODE == "block" and verdict["score"] < THRESHOLD:
        return {
            "action": {
                "body": "This answer was withheld: it states figures without a source.",
                "status_code": 403,
                "reason": f"score {verdict['score']}/5 below threshold {THRESHOLD}",
            }
        }

    return {"action": {"reason": f"score {verdict['score']}/5"}}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, status, payload):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/healthz":
            self._send(200, {"status": "ok", "mode": MODE})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as err:
            log(f"bad request body: {err}")
            self._send(200, {"action": {"reason": "unparseable body, not evaluated"}})
            return

        if self.path.rstrip("/").endswith("/request"):
            # This lab guards responses only. Grade prompts here if you want
            # topic boundaries or injection detection on the way in.
            self._send(200, {"action": {"reason": "request phase not evaluated"}})
            return

        if self.path.rstrip("/").endswith("/response"):
            self._send(200, decide(payload))
            return

        self._send(404, {"error": "not found"})

    def log_message(self, *args):
        pass  # our own log() is enough


if __name__ == "__main__":
    if MODE not in ("observe", "annotate", "block"):
        sys.exit(f"MODE must be observe, annotate or block, got {MODE!r}")
    log(f"listening on :{PORT} mode={MODE} judge={JUDGE_MODEL} threshold={THRESHOLD}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
