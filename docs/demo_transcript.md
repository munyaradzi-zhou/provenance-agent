# Live demo transcript

Real responses captured from the deployed AWS endpoint
(`https://79075o8z5f.execute-api.eu-central-1.amazonaws.com`) before teardown.
Kept as evidence and as a fallback for the README/demo if the live stack is down.

## 1. Auth enforced — no API key → 401

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST "$EP/v1/query" \
    -H "Content-Type: application/json" -d '{"question":"test"}'
HTTP 401
```

## 2. Vector route — single semantic lookup

**Q:** *What nationality is the director of the film Nemesis 2: Nebula?*

```json
{
  "answer": "The director of the film Nemesis 2: Nebula, Albert Pyun, is American [Nemesis 2: Nebula].",
  "route": "vector",
  "grounded": true,
  "citations": ["Nemesis 2: Nebula"],
  "trace": [
    "redacted input",
    "supervisor: route=vector (The question is a single semantic lookup about the director's nationality.)",
    "vector agent ran",
    "synthesis complete (1 citations)",
    "grader: grounded=True (The answer correctly identifies Albert Pyun as the director and states his nationality as American, both of which are supported by the context.)"
  ],
  "request_id": "461b2ca81ea1422aa6f31c41e827ae8f",
  "latency_ms": 15102.0
}
```

## 3. Both routes — compositional multi-hop (the flagship behaviour)

**Q:** *Who is the director of Nemesis 2: Nebula and what is that person known for?*

```json
{
  "answer": "The director of Nemesis 2: Nebula is Albert Pyun, who is known for making many low-budget B-movies and direct-to-video action films, including titles like \"Cyborg\" and \"Captain America\" [Nemesis 2: Nebula].",
  "route": "both",
  "grounded": true,
  "citations": ["Nemesis 2: Nebula"],
  "trace": [
    "redacted input",
    "supervisor: route=both (The question requires identifying the director (a relational query) and also understanding their notable works (a semantic lookup).)",
    "graph agent ran",
    "vector agent ran",
    "synthesis complete (1 citations)",
    "grader: grounded=True (Every claim in the answer about Albert Pyun and his work is supported by the context.)"
  ],
  "request_id": "cffd4f25356b4e0294dcea7129e40162",
  "latency_ms": 4811.0
}
```

The supervisor recognises this needs *both* a relational hop (who directed) and a
semantic hop (what they're known for), runs both agents, synthesises one cited
answer, and the grader confirms every claim is supported — the whole multi-agent
loop in one response.
