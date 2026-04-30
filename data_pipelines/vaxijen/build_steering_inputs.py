"""Build RFD3 partial-noising collect input and labels CSV for steering.

Matches positives/negatives to available PDB files by UniProt accession,
then writes:
  - rfd3_inputs_all.json  : flat dict {design_key: {input, partial_t}} for
                            saffron collect model=rfd3
  - labels_for_steering.csv : design_key,label for compute_steering_vector

Usage:
    python data_pipelines/vaxijen/build_steering_inputs.py
"""
import json
from pathlib import Path

_HERE = Path(__file__).parent
_PDB_DIR = _HERE / "pdbs"
_PARTIAL_T = 5.0
_OUT_COLLECT = _HERE / "rfd3_inputs_all.json"
_OUT_LABELS = _HERE / "labels_for_steering.csv"

_RUN_CONFIG = {
    "activation_collection": {
        "hooks": [
            {"name": "token_initializer_outputs",
             "module_path": "token_initializer.process_s_init",
             "hook_type": "static"},
            {"name": "block6",
             "module_path": "diffusion_module.diffusion_transformer.blocks.6.transition_block",
             "hook_type": "dynamic", "collect_every_n_steps": 5},
            {"name": "block8",
             "module_path": "diffusion_module.diffusion_transformer.blocks.8.transition_block",
             "hook_type": "dynamic", "collect_every_n_steps": 5},
            {"name": "block12",
             "module_path": "diffusion_module.diffusion_transformer.blocks.12.transition_block",
             "hook_type": "dynamic", "collect_every_n_steps": 5},
        ]
    }
}


def build() -> None:
    pos = json.loads((_HERE / "rf3_inputs_positives.json").read_text())
    neg = json.loads((_HERE / "rf3_inputs_negatives.json").read_text())

    pdb_accessions = {p.stem for p in _PDB_DIR.glob("*.pdb")}

    collect_inputs: dict = {"run_config": _RUN_CONFIG}
    label_rows = ["design_id,label"]

    for examples, label in [(pos, 1), (neg, 0)]:
        for ex in examples:
            acc = _accession(ex["name"])
            if acc not in pdb_accessions:
                continue
            key = f"vax_{'pos' if label == 1 else 'neg'}_{acc}"
            collect_inputs[key] = {
                "input": str(_PDB_DIR / f"{acc}.pdb"),
                "partial_t": _PARTIAL_T,
            }
            full_id = f"{_OUT_COLLECT.stem}_{key}_0"
            label_rows.append(f"{full_id},{label}")

    _OUT_COLLECT.write_text(json.dumps(collect_inputs, indent=2))
    n_pos = sum(1 for r in label_rows[1:] if r.endswith(",1"))
    n_neg = sum(1 for r in label_rows[1:] if r.endswith(",0"))
    print(f"Wrote {n_pos} pos + {n_neg} neg = {n_pos+n_neg} examples → {_OUT_COLLECT}")

    _OUT_LABELS.write_text("\n".join(label_rows) + "\n")
    print(f"Wrote labels → {_OUT_LABELS}")


def _accession(name: str) -> str:
    parts = name.split("|")
    return parts[1] if len(parts) >= 2 else name


if __name__ == "__main__":
    build()
