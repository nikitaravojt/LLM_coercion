"""
helpers/moralchoice_parser.py
Convert moralchoice CSV files to the project's JSON dataset format.

Output schema per question:
  {
    "question_id":      "H_001",
    "dataset":          "moralchoice_high" | "moralchoice_low",
    "generation_rule":  "Do not kill",
    "question":         "{context}\n\n(A) {action1}\n(B) {action2}",
    "correct_response": null | "A" | "B"
  }

For high-ambiguity scenarios, correct_response is always null (no ground truth).
For low-ambiguity scenarios, correct_response is inferred from rule violation counts:
  the action with fewer "Yes" violations is taken as the preferred (correct) answer.
  If violations are equal, correct_response is null.

Run:
  python helpers/moralchoice_parser.py --ambiguity high
  python helpers/moralchoice_parser.py --ambiguity low
  python helpers/moralchoice_parser.py --ambiguity both
"""

import csv
import json
import argparse
from pathlib import Path

RAW_DATA_DIR = Path("data/raw_data")
DATA_DIR     = Path("data")

RULE_COLS = [
    "death", "pain", "disable", "freedom", "pleasure",
    "deceive", "cheat", "break_promise", "break_law", "duty",
]


def _count_violations(row: dict, prefix: str) -> int:
    return sum(
        1 for col in RULE_COLS
        if row.get(f"{prefix}_{col}", "").strip().lower() == "yes"
    )


def _infer_correct(row: dict) -> str | None:
    """Return 'A' or 'B' for the less-violating action, or None if tied."""
    a1 = _count_violations(row, "a1")
    a2 = _count_violations(row, "a2")
    if a1 < a2:
        return "A"
    if a2 < a1:
        return "B"
    return None


def parse_moralchoice(ambiguity: str) -> list[dict]:
    """
    Parse one or both moralchoice CSV files.
    ambiguity: "high", "low", or "both"
    """
    targets = []
    if ambiguity in ("high", "both"):
        targets.append(("high", RAW_DATA_DIR / "moralchoice_high_ambiguity.csv"))
    if ambiguity in ("low", "both"):
        targets.append(("low",  RAW_DATA_DIR / "moralchoice_low_ambiguity.csv"))

    questions = []
    for amb, path in targets:
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                context = row["context"].strip()
                action1 = row["action1"].strip()
                action2 = row["action2"].strip()

                questions.append({
                    "question_id":      row["scenario_id"].strip(),
                    "dataset":          f"moralchoice_{amb}",
                    "generation_rule":  row["generation_rule"].strip(),
                    "question":         f"{context}\n\n(A) {action1}\n(B) {action2}",
                    "correct_response": None if amb == "high" else _infer_correct(row),
                })

    return questions


def main():
    parser = argparse.ArgumentParser(
        description="Convert moralchoice CSV(s) to JSON dataset."
    )
    parser.add_argument(
        "--ambiguity", choices=["high", "low", "both"], default="high",
        help="Which ambiguity level to parse (default: high)",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output path (default: data/moralchoice_{ambiguity}.json)",
    )
    args = parser.parse_args()

    questions = parse_moralchoice(args.ambiguity)

    out_path = args.output or str(DATA_DIR / f"moralchoice_{args.ambiguity}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print(f"Parsed {len(questions)} scenarios -> {out_path}")
    if args.ambiguity in ("low", "both"):
        low_qs = [q for q in questions if q["dataset"] == "moralchoice_low"]
        inferred = sum(1 for q in low_qs if q["correct_response"] is not None)
        print(f"  low-ambiguity: {inferred}/{len(low_qs)} with inferred correct_response")


if __name__ == "__main__":
    main()
