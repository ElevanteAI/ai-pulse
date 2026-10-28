"""Does the AI score open answers the way a person would? Runs the labelled set in
data/eval_answers.json through the real scoring path (score_open_answer) and reports agreement.

    python -m app.eval                 # uses AI_MODE from the environment / .env
    python -m app.eval --json out.json # also save every case's result

Parsing tests prove a bad reply can't corrupt the data. This measures something different:
whether the scores and flags that do get stored are right. In AI_MODE=mock the "model" is a
canned reply picked by hashing the answer, so mock numbers only show the harness works.
Only the injection screen (which runs before any model call) is meaningful in mock mode.
"""
import argparse
import json
import os
from datetime import datetime, timezone

from .services import llm, scoring
from .services.questions import load_questions

_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "eval_answers.json")
FLAGS = sorted(scoring.ALLOWED_FLAGS)


def load_cases(path=_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run(cases, scorer=scoring.score_open_answer):
    texts = {q["id"]: q["text"] for q in load_questions()}
    records = []
    for c in cases:
        out = scorer(texts[c["question"]], c["answer"])
        records.append({
            **c,
            "status": out["status"],
            "score": out["score"],
            "flags": out["flags"],
            "problem": out.get("problem"),
            "screened": bool(scoring._INJECTION.search(c["answer"])),  # caught before any model call
        })
    return records


def _distance(score, lo, hi):
    return lo - score if score < lo else score - hi if score > hi else 0


def _prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f1 = 2 * p * r / (p + r) if p and r else (0.0 if p is not None and r is not None else None)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f1}


def metrics(records):
    legit = [r for r in records if not r["injection"]]
    scored = [r for r in legit if r["status"] == scoring.SCORED]
    in_range = [r for r in scored if r["expected_score"][0] <= r["score"] <= r["expected_score"][1]]
    over = [r for r in scored if r["score"] > r["expected_score"][1]]
    under = [r for r in scored if r["score"] < r["expected_score"][0]]

    # Flags are only judged where a score was stored: a needs_review answer stores no flags at all
    per_flag = {}
    for flag in FLAGS:
        tp = sum(1 for r in scored if flag in r["flags"] and flag in r["expected_flags"])
        fp = sum(1 for r in scored if flag in r["flags"] and flag not in r["expected_flags"])
        fn = sum(1 for r in scored if flag not in r["flags"] and flag in r["expected_flags"])
        per_flag[flag] = _prf(tp, fp, fn)
    micro = _prf(*(sum(f[k] for f in per_flag.values()) for k in ("tp", "fp", "fn")))

    injections = [r for r in records if r["injection"]]
    accepted = [r for r in injections if r["status"] == scoring.SCORED]
    model_failures = [r for r in records if r["status"] == scoring.NEEDS_REVIEW and not r["screened"]]

    return {
        "cases": len(records),
        "legit": {
            "total": len(legit),
            "scored": len(scored),
            "needs_review": [r["id"] for r in legit if r["status"] != scoring.SCORED],
            "screened_by_mistake": [r["id"] for r in legit if r["screened"]],
            "in_range": len(in_range),
            "over_scored": [r["id"] for r in over],
            "under_scored": [r["id"] for r in under],
            "mean_distance_from_range": (
                sum(_distance(r["score"], *r["expected_score"]) for r in scored) / len(scored) if scored else None),
        },
        "flags": {"per_flag": per_flag, "overall": micro},
        "injection": {
            "total": len(injections),
            "screened": [r["id"] for r in injections if r["screened"]],
            "accepted_with_score": [r["id"] for r in accepted],
            "accepted_above_honest_range": [r["id"] for r in accepted if r["score"] > r["expected_score"][1]],
            "expected_flag_suppressed": [
                r["id"] for r in accepted if not set(r["expected_flags"]) <= set(r["flags"])],
        },
        "model_replies_failing_validation": [r["id"] for r in model_failures],
    }


def _pct(n, d):
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else f"{n}/0"


def _fmt(x):
    return "n/a" if x is None else f"{x:.2f}"


def report(records, m, model):
    print(f"AI scoring evaluation · model={model} · AI_MODE={llm.AI_MODE} · "
          f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · {m['cases']} cases")
    if llm.AI_MODE == "mock":
        print("MOCK MODE: replies are canned and ignore the answer. Score/flag numbers below only show the "
              "harness works; they say nothing about a real model. The injection screen IS real.")
    print()
    print(f"{'id':5} {'expected':8} {'got':4} {'status':13} {'flags got / expected'}")
    for r in records:
        lo, hi = r["expected_score"]
        exp = f"{lo}" if lo == hi else f"{lo}-{hi}"
        mark = "" if r["status"] != scoring.SCORED or lo <= r["score"] <= hi else " <-- out of range"
        print(f"{r['id']:5} {exp:8} {str(r['score'] or '-'):4} {r['status']:13} "
              f"{r['flags']} / {r['expected_flags']}{' [screened]' if r['screened'] else ''}{mark}")

    lg, fl, inj = m["legit"], m["flags"]["overall"], m["injection"]
    print()
    print("Legitimate answers")
    print(f"  usefully scored (not needs_review): {_pct(lg['scored'], lg['total'])}")
    print(f"  score within the labelled range:    {_pct(lg['in_range'], lg['scored'])} of scored, "
          f"{_pct(lg['in_range'], lg['total'])} of all")
    print(f"  over-scored: {lg['over_scored'] or 'none'} · under-scored: {lg['under_scored'] or 'none'}")
    print(f"  mean distance outside the range:    {_fmt(lg['mean_distance_from_range'])}")
    print(f"  wrongly caught by injection screen: {lg['screened_by_mistake'] or 'none'}")
    print("Risk flags (scored legitimate answers)")
    for name, f in m["flags"]["per_flag"].items():
        print(f"  {name:26} precision {_fmt(f['precision'])}  recall {_fmt(f['recall'])}  "
              f"(tp {f['tp']}, fp {f['fp']}, fn {f['fn']})")
    print(f"  {'overall (micro)':26} precision {_fmt(fl['precision'])}  recall {_fmt(fl['recall'])}  "
          f"F1 {_fmt(fl['f1'])}")
    print("Injection attempts")
    print(f"  caught by the screen before the model: {_pct(len(inj['screened']), inj['total'])}")
    print(f"  got a stored score anyway:             {inj['accepted_with_score'] or 'none'}")
    print(f"  ...above the honest range:             {inj['accepted_above_honest_range'] or 'none'}")
    print(f"  ...with a real risk flag suppressed:   {inj['expected_flag_suppressed'] or 'none'}")
    print(f"Model replies that failed validation: {m['model_replies_failing_validation'] or 'none'}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", help="write per-case results and metrics to this file")
    args = parser.parse_args(argv)

    data = load_cases()
    records = run(data["cases"])
    m = metrics(records)
    report(records, m, llm.model_name())
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"model": llm.model_name(), "ai_mode": llm.AI_MODE, "metrics": m, "records": records}, f, indent=2)


if __name__ == "__main__":
    main()
