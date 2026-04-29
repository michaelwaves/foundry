"""Build a combined collect input JSON and labels CSV for steering.

Merges rf3_inputs_positives.json + rf3_inputs_negatives.json into a single
collect input (all examples in one run), and writes a labels CSV with
design_id,label matching the example names.

Usage:
    python data_pipelines/vaxijen/build_steering_inputs.py
"""
import json
from pathlib import Path

_HERE = Path(__file__).parent
_OUT_COLLECT = _HERE / "rf3_inputs_all.json"
_OUT_LABELS = _HERE / "labels_for_steering.csv"


def build() -> None:
    pos = json.loads((_HERE / "rf3_inputs_positives.json").read_text())
    neg = json.loads((_HERE / "rf3_inputs_negatives.json").read_text())

    combined = {
        "run_config": pos["run_config"],
        "examples": pos["examples"] + neg["examples"],
    }
    _OUT_COLLECT.write_text(json.dumps(combined, indent=2))
    print(f"Wrote {len(combined['examples'])} examples → {_OUT_COLLECT}")

    rows = ["design_id,label"]
    for ex in pos["examples"]:
        rows.append(f"{ex['name']},1")
    for ex in neg["examples"]:
        rows.append(f"{ex['name']},0")
    _OUT_LABELS.write_text("\n".join(rows) + "\n")
    print(f"Wrote {len(rows)-1} label rows → {_OUT_LABELS}")


if __name__ == "__main__":
    build()
