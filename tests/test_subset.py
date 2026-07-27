"""Subsetting logic — pure functions over in-memory examples (no corpus file)."""

from app.ingest.subset import build_artifacts, select_examples


def _example(_id, typ, title="T", subj="S", rel="director", obj="O"):
    return {
        "_id": _id,
        "type": typ,
        "question": f"q-{_id}",
        "answer": f"a-{_id}",
        "context": [[title, ["sentence one.", "sentence two."]]],
        "evidences": [[subj, rel, obj]],
        "supporting_facts": [[title, 0]],
    }


def test_select_is_balanced_and_deterministic():
    data = (
        [_example(f"c{i}", "compositional") for i in range(10)]
        + [_example(f"m{i}", "comparison") for i in range(10)]
        + [_example(f"b{i}", "bridge_comparison") for i in range(10)]
        + [_example(f"i{i}", "inference") for i in range(10)]
    )
    a = select_examples(data, per_type=3)
    b = select_examples(data, per_type=3)
    assert len(a) == 12  # 3 per type * 4 types
    assert [e["_id"] for e in a] == [e["_id"] for e in b]  # deterministic (seeded)


def test_build_artifacts_dedupes():
    # two examples sharing the same passage title and the same triple
    data = [
        _example("1", "comparison", title="Shared", subj="A", obj="B"),
        _example("2", "inference", title="Shared", subj="A", obj="B"),
    ]
    passages, triples, eval_rows = build_artifacts(data)
    assert len(passages) == 1  # deduped by title
    assert len(triples) == 1  # deduped by (s,r,o)
    assert len(eval_rows) == 2
    assert eval_rows[0]["supporting_titles"] == ["Shared"]
