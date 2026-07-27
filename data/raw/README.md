# Corpus — 2WikiMultihopQA

ProvenanceAgent uses **2WikiMultihopQA** (COLING 2020, Apache-2.0). It is the
rare multi-hop QA benchmark that ships each example with **both** a graph form and
a text form, which is exactly what lets us prove graph-vs-vector routing.

## Why this corpus

Each example contains:

| Field | Feeds | Purpose |
|-------|-------|---------|
| `evidences` (subject–relation–object triples) | **Neo4j** | graph agent traverses multi-hop reasoning paths |
| `context` (Wikipedia paragraphs) | **Qdrant** | vector agent does semantic retrieval |
| `supporting_facts` (title, sentence-idx) | reasoning trace | sentence-level provenance |
| `answer` | RAGAS eval | ground truth |
| `type` | eval slices | comparison / inference / compositional / bridge_comparison |

Example (a 2-hop compositional question flat RAG struggles with):

> **Q:** Who is the mother of the director of film Polish-Russian War (Film)?
> **Triples:** (Polish-Russian War, director, Xawery Żuławski), (Xawery Żuławski, mother, Małgorzata Braunek)
> **A:** Małgorzata Braunek

## Splits (fixed "april7" release)

| File | Examples | Notes |
|------|----------|-------|
| `train.json` | ~167k | training pool (unused for the demo) |
| `dev.json` | 12,576 | ingestion + eval source |
| `test.json` | ~12.5k | no answers (held out) |
| `id_aliases.json` | — | Wikidata entity alias map |

Ingestion (Phase 2) subsets `dev.json` to a demo-sized corpus.

## How to fetch (files are gitignored — not committed)

```bash
mkdir -p data/raw && cd data/raw
curl -L -o data.zip "https://www.dropbox.com/s/ms2m13252h6xubs/data_ids_april7.zip?dl=1"
unzip -o data.zip
```

Source: https://github.com/Alab-NII/2wikimultihop
Paper: "Constructing A Multi-hop QA Dataset for Comprehensive Evaluation of Reasoning Steps" (COLING 2020)
License: Apache-2.0
