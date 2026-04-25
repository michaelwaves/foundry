import re
from pathlib import Path
from typing import Iterator

import h5py
import pandas as pd


def run_labels(config: dict) -> pd.DataFrame:
    """Build labels.csv (and sources.csv) from labelled FASTAs and an activations.h5.

    config:
        positives: [path1, path2, ...]   # FASTAs (or per-line CSVs) labelled 1
        negatives: [path1, ...]           # labelled 0
        activations_path: /path/to/h5     # optional; if omitted, only sources.csv is written
    """
    out_dir = Path(config["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = _build_sources(config.get("positives", []), config.get("negatives", []))
    sources.to_csv(out_dir / "sources.csv", index=False)

    if config.get("activations_path") is None:
        return sources

    design_ids = _read_design_ids(config["activations_path"])
    labels = _align_to_designs(sources, design_ids)
    labels.to_csv(out_dir / "labels.csv", index=False)
    _print_alignment_summary(design_ids, labels)
    return labels


def _build_sources(positive_paths: list[str], negative_paths: list[str]) -> pd.DataFrame:
    rows = []
    for path in positive_paths:
        rows.extend((source_id, 1, str(path)) for source_id in _iter_source_ids(Path(path)))
    for path in negative_paths:
        rows.extend((source_id, 0, str(path)) for source_id in _iter_source_ids(Path(path)))
    return pd.DataFrame(rows, columns=["source_id", "label", "source_file"])


def _iter_source_ids(path: Path) -> Iterator[str]:
    text = path.read_text()
    if text.lstrip().startswith(">"):
        yield from _parse_fasta_ids(text)
    else:
        yield from _parse_line_ids(text, path.stem)


def _parse_fasta_ids(text: str) -> Iterator[str]:
    for line in text.splitlines():
        if line.startswith(">"):
            header = line[1:].split()[0] if line[1:].strip() else ""
            yield _sanitize(header)


def _parse_line_ids(text: str, stem: str) -> Iterator[str]:
    counter = 0
    for line in text.splitlines():
        if line.strip():
            counter += 1
            yield f"{stem}_{counter}"


def _sanitize(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", raw)


def _read_design_ids(activations_path: str) -> list[str]:
    with h5py.File(activations_path, "r") as f:
        first_hook = next(iter(f.keys()))
        return list(f[first_hook].keys())


def _align_to_designs(sources: pd.DataFrame, design_ids: list[str]) -> pd.DataFrame:
    source_label = dict(zip(sources["source_id"], sources["label"]))
    matched = []
    for design_id in design_ids:
        source_id = _match_source(design_id, source_label)
        if source_id is not None:
            matched.append((design_id, source_label[source_id], source_id))
    return pd.DataFrame(matched, columns=["design_id", "label", "source_id"])


def _match_source(design_id: str, source_label: dict) -> str | None:
    if design_id in source_label:
        return design_id
    stripped = re.sub(r"_\d+$", "", design_id)
    if stripped in source_label:
        return stripped
    return None


def _print_alignment_summary(design_ids: list[str], labels: pd.DataFrame) -> None:
    n_total, n_matched = len(design_ids), len(labels)
    print(f"aligned {n_matched}/{n_total} design_ids to a source")
    if n_matched > 0:
        counts = labels["label"].value_counts().to_dict()
        print(f"  positives={counts.get(1, 0)}  negatives={counts.get(0, 0)}")
