import json
from pathlib import Path
from typing import Any

from supabase import Client


def build_inputs_json(work_dir: Path, config: dict[str, Any], motif_path: Path | None) -> Path:
    spec = _build_spec(config, motif_path)
    inputs_path = work_dir / "inputs.json"
    inputs_path.write_text(json.dumps({config["design_name"]: spec}))
    return inputs_path


def fetch_motif_pdb(db: Client, storage_path: str | None, work_dir: Path) -> Path | None:
    if not storage_path:
        return None
    motif_bytes = db.storage.from_("inputs").download(storage_path)
    motif_path = work_dir / "motif.pdb"
    motif_path.write_bytes(motif_bytes)
    return motif_path


def _build_spec(config: dict[str, Any], motif_path: Path | None) -> dict[str, Any]:
    spec: dict[str, Any] = {}
    if motif_path is not None:
        spec["input"] = str(motif_path)
        spec["select_fixed_atoms"] = True
        if config.get("partial_t", 0) > 0:
            spec["partial_t"] = config["partial_t"]
    if config.get("contig"):
        spec["contig"] = config["contig"]
    if config.get("length"):
        spec["length"] = config["length"]
    if motif_path is not None and config.get("hotspots"):
        spec["select_hotspots"] = config["hotspots"]
    strategy = config.get("infer_ori_strategy")
    if strategy and strategy != "none" and motif_path is not None and config.get("hotspots"):
        spec["infer_ori_strategy"] = strategy
    if config.get("is_non_loopy"):
        spec["is_non_loopy"] = config["is_non_loopy"]
    return spec
