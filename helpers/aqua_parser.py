# parse_aqua_to_json.py

import json
import argparse
from json import JSONDecoder
from pathlib import Path


def parse_concatenated_json(blob: str):
    """
    Parse a file containing multiple JSON objects one after another:
    {...}
    {...}
    {...}
    """
    decoder = JSONDecoder()
    pos = 0
    objects = []

    while pos < len(blob):
        while pos < len(blob) and blob[pos].isspace():
            pos += 1

        if pos >= len(blob):
            break

        obj, pos = decoder.raw_decode(blob, pos)
        objects.append(obj)

    return objects


def convert_aqua_examples(objects):
    simplified = []
    question_id = 1

    for i, obj in enumerate(objects):
        dataset = (
            obj.get("dataset") or
            obj.get("base", {}).get("dataset") or
            obj.get("meta", {}).get("dataset")
        )
        if dataset and (dataset.lower() in {"trivia_qa", "truthful_qa"}
                       or dataset.lower().startswith("trivia_qa")
                       or dataset.lower().startswith("truthful_qa")):
            continue

        base = obj["base"]
        question = base["question"].strip()
        answers = base["answers"].strip()
        correct_letter = base["correct_letter"].strip()

        simplified.append({
            "question_id": question_id,
            "dataset": dataset,
            "question": f"{question}\n\n{answers}",
            "correct_response": correct_letter
        })
        question_id += 1

    return simplified


def main():
    parser = argparse.ArgumentParser(
        description="Convert AQUA-style examples into a JSON list of simple question dicts."
    )

    parser.add_argument(
        "input_file",
        help="Path to input file containing concatenated AQUA-style JSON examples."
    )

    parser.add_argument(
        "output_file",
        help="Path to output JSON file."
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    blob = input_path.read_text(encoding="utf-8")

    objects = parse_concatenated_json(blob)
    simplified = convert_aqua_examples(objects)

    output_path.write_text(
        json.dumps(simplified, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Parsed {len(simplified)} examples.")
    print(f"Wrote JSON output to: {output_path}")


if __name__ == "__main__":
    main()