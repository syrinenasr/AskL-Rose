"""Evaluation: ask the model every question in questions.yaml and score its answers.

Run from the project root:  uv run --env-file .env python -m eval.run
Options: --limit 3, --only q01,q27, --no-semantic, --rescore eval/results/<file>.json.
Set OLLAMA_MODEL to try another model.
"""
import argparse
import json
import time
from collections import defaultdict
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import yaml

from ask import answer_question, run_query
from llm import MODEL
from schema import get_schema, get_schema_text
from semantic import format_semantic_layer, load_semantic_layer

QUESTIONS_FILE = "eval/questions.yaml"
RESULTS_DIR = Path("eval/results")
DECIMALS = Decimal("0.01")  # numbers are compared rounded to 2 decimals
TOLERANCE = Decimal("0.001")  # and may differ by 0.1% (money division loses precision)


def normalize(value):
    """Make equal answers compare equal: round numbers, dates as text, trim strings."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value)).quantize(DECIMALS, rounding=ROUND_HALF_UP)
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == datetime.min.time() else value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def close(a, b):
    """Equal, but numbers may differ by TOLERANCE of b (at least 0.01). Rows are compared value by value."""
    if isinstance(a, tuple):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, Decimal) and isinstance(b, Decimal):
        return abs(a - b) <= max(DECIMALS, abs(b) * TOLERANCE)
    return a == b


def all_close(model_values, ref_values):
    return len(model_values) == len(ref_values) and all(close(m, r) for m, r in zip(model_values, ref_values))


def sort_key(value):
    """Numbers by size, everything else as text, so mixed types still sort."""
    return (0, value, "") if isinstance(value, Decimal) else (1, 0, repr(value))


def row_key(row):
    return tuple(sort_key(v) for v in row)


def column_values(rows, i):
    """The values of column i, sorted."""
    return sorted((row[i] for row in rows), key=sort_key)


def match_columns(ref_rows, model_rows):
    """Match each reference column to a free model column with the same values, ignoring row order.

    Returns (the matched model column for each reference column, "") or (None, reason).
    """
    free = list(range(len(model_rows[0])))
    picked = []
    for i in range(len(ref_rows[0])):
        wanted = column_values(ref_rows, i)
        match = next((j for j in free if all_close(column_values(model_rows, j), wanted)), None)
        if match is None:
            return None, f"no column matches reference column {i + 1}"
        free.remove(match)
        picked.append(match)
    return picked, ""


def same_result(ref_rows, model_rows, ordered):
    """Compare results, ignoring column names and order, and allowing extra columns in the model's answer.

    First the values, ignoring row order; then, only for ordered questions, the row order.
    """
    ref_rows = [tuple(normalize(v) for v in row) for row in ref_rows]
    model_rows = [tuple(normalize(v) for v in row) for row in model_rows]
    if len(ref_rows) != len(model_rows):
        return False, f"{len(model_rows)} rows instead of {len(ref_rows)}"
    if not ref_rows:
        return True, ""

    picked, reason = match_columns(ref_rows, model_rows)
    if picked is None:
        return False, reason

    # The columns match one by one; now check they belong together row by row.
    projected = [tuple(row[j] for j in picked) for row in model_rows]
    if not all_close(sorted(projected, key=row_key), sorted(ref_rows, key=row_key)):
        return False, "values combined differently across rows"
    if ordered and not all_close(projected, ref_rows):
        return False, "rows in a different order"
    return True, ""


def score(question, answer, error):
    """Return (passed, reason) for one question."""
    if question["sql"] is None:  # not a data question: no SQL may run
        if error is not None:
            if "unsafe" in question["tags"] and isinstance(error, ValueError):
                return True, "blocked by check_sql"
            return False, f"tried SQL: {error}"
        if answer["sql"]:
            return False, "ran SQL for a message that isn't a data question"
        return True, ""

    if error is not None:
        return False, f"error: {error}"
    if not answer["sql"]:
        return False, "treated as not a data question"
    _, ref_rows, _ = run_query(question["sql"])
    passed, reason = same_result(ref_rows, answer["rows"], question["ordered"])
    return passed, "" if passed else reason


def print_summary(records):
    """Print accuracy overall and per tag, repairs and timing."""
    passed = sum(r["passed"] for r in records)
    print(f"\nAccuracy: {passed}/{len(records)} ({100 * passed / len(records):.0f}%)")

    by_tag = defaultdict(list)
    for r in records:
        for tag in r["tags"]:
            by_tag[tag].append(r["passed"])
    for tag, results in sorted(by_tag.items(), key=lambda item: -len(item[1])):
        print(f"  {tag:<12} {sum(results):>2}/{len(results):<2} ({100 * sum(results) / len(results):.0f}%)")

    repaired = [r for r in records if r["repaired"]]
    print(f"Repaired: {len(repaired)} (passed after repair: {sum(r['passed'] for r in repaired)})")
    seconds = [r["seconds"] for r in records]
    print(f"Time: {sum(seconds):.0f} s in total, {sum(seconds) / len(seconds):.1f} s per question")


def print_result(id, passed, seconds, repaired, reason):
    print(f"{id}  {'PASS' if passed else 'FAIL'}  {seconds:5.1f} s{'  repaired' if repaired else ''}  {reason}")


def ask_model(questions, no_semantic):
    """Ask the model every question and score its answers. Returns the records."""
    schema_text = get_schema_text(*get_schema())
    semantic_text = "" if no_semantic else format_semantic_layer(load_semantic_layer())
    print(f"Model {MODEL}, semantic layer {'off' if no_semantic else 'on'}, {len(questions)} questions\n")

    records = []
    for question in questions:
        start = time.perf_counter()
        answer, error = None, None
        try:
            answer = answer_question(question["question"], schema_text, semantic_text)
        except Exception as e:  # a failed repair or a timeout: score it, keep going
            error = e
        seconds = time.perf_counter() - start

        passed, reason = score(question, answer, error)
        repaired = bool(answer and answer["repaired"])
        print_result(question["id"], passed, seconds, repaired, reason)
        records.append({
            "id": question["id"],
            "question": question["question"],
            "tags": question["tags"],
            "passed": passed,
            "reason": reason,
            "sql": answer["sql"] if answer else None,
            "error": str(error) if error else None,
            "repaired": repaired,
            "seconds": round(seconds, 1),
        })
    return records


def rescore(run, questions):
    """Score the SQL saved in an earlier run again, without asking the model. Returns the records."""
    by_id = {q["id"]: q for q in questions}
    print(f"Rescoring: model {run['model']}, semantic layer {'on' if run['semantic_layer'] else 'off'}\n")

    records = []
    for old in run["records"]:
        question = by_id.get(old["id"])
        if question is None:  # left out by --only or --limit
            continue
        if old["question"] != question["question"]:
            print(f"{old['id']}  warning: the question was reworded since this run; ask the model again")

        if old["sql"] is None:  # the model's call raised an error: no SQL to run again, keep the old result
            passed, reason = old["passed"], old["reason"]
        else:
            answer, error = {"sql": old["sql"], "rows": []}, None
            if old["sql"]:
                try:
                    _, answer["rows"], _ = run_query(old["sql"])
                except Exception as e:
                    error = e
            passed, reason = score(question, answer, error)

        print_result(old["id"], passed, old["seconds"], old["repaired"], reason)
        records.append({**old, "tags": question["tags"], "passed": passed, "reason": reason})
    return records


def main():
    parser = argparse.ArgumentParser(description="Evaluate AskL-Rose on the questions in questions.yaml.")
    parser.add_argument("--limit", type=int, help="only the first N questions")
    parser.add_argument("--only", help="comma-separated ids, e.g. q01,q27")
    parser.add_argument("--no-semantic", action="store_true", help="run without the semantic layer")
    parser.add_argument("--rescore", metavar="FILE", help="score the SQL saved in a results file again, without the model")
    args = parser.parse_args()

    with open(QUESTIONS_FILE) as f:
        questions = yaml.safe_load(f)["questions"]
    if args.only:
        questions = [q for q in questions if q["id"] in args.only.split(",")]
    if args.limit:
        questions = questions[: args.limit]

    if args.rescore:
        with open(args.rescore) as f:
            run = json.load(f)
        records = rescore(run, questions)
        model, semantic_layer = run["model"], run["semantic_layer"]
        name = f"{Path(args.rescore).stem}_rescored.json"
    else:
        records = ask_model(questions, args.no_semantic)
        model, semantic_layer = MODEL, not args.no_semantic
        name = f"{datetime.now():%Y-%m-%d_%H%M}_{MODEL.replace(':', '-')}{'_no-semantic' if args.no_semantic else ''}.json"

    print_summary(records)

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(RESULTS_DIR / name, "w") as f:
        json.dump({"model": model, "semantic_layer": semantic_layer, "records": records}, f, indent=2)
    print(f"Saved {RESULTS_DIR / name}")


if __name__ == "__main__":
    main()
