"""Smoke tests for the unified data_pipelines pipeline."""
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from data_pipelines.attach_pdbs import main as attach_pdbs_cli
from data_pipelines.build_inputs import main as build_inputs_cli
from data_pipelines.fasta_to_sources import main as fasta_to_sources_cli
from data_pipelines.filter_pdbs import main as filter_pdbs_cli
from data_pipelines.pdb_utils import (
    count_residues,
    extract_chain_sequence,
    first_missing_ca,
)
from data_pipelines.sources import (
    SourceRow,
    filter_by_length,
    populate_residue_stats,
    read_sources,
    write_sources,
)


@pytest.fixture
def tiny_pdb(tmp_path: Path) -> Path:
    """Three-residue chain A: ALA-GLY-VAL, all with CA atoms."""
    path = tmp_path / "tiny.pdb"
    path.write_text(
        "ATOM      1  N   ALA A   1      27.340  24.430   2.614  1.00  9.67           N\n"
        "ATOM      2  CA  ALA A   1      26.266  25.413   2.842  1.00 10.38           C\n"
        "ATOM      3  C   ALA A   1      26.913  26.639   3.531  1.00  9.62           C\n"
        "ATOM      4  N   GLY A   2      26.336  27.770   3.875  1.00  9.30           N\n"
        "ATOM      5  CA  GLY A   2      26.880  29.012   4.470  1.00 10.99           C\n"
        "ATOM      6  C   GLY A   2      27.658  29.731   3.339  1.00  8.65           C\n"
        "ATOM      7  N   VAL A   3      28.928  29.985   3.626  1.00  6.59           N\n"
        "ATOM      8  CA  VAL A   3      29.808  30.690   2.692  1.00  9.24           C\n"
        "ATOM      9  C   VAL A   3      30.835  31.628   3.354  1.00 10.44           C\n"
    )
    return path


def test_pdb_utils_extract_chain_sequence(tiny_pdb: Path) -> None:
    assert extract_chain_sequence(tiny_pdb) == "AGV"


def test_pdb_utils_count_residues(tiny_pdb: Path) -> None:
    assert count_residues(tiny_pdb) == (3, 1)


def test_pdb_utils_first_missing_ca(tmp_path: Path) -> None:
    path = tmp_path / "no_ca.pdb"
    path.write_text(
        "ATOM      1  N   ALA A   1      27.340  24.430   2.614  1.00  9.67           N\n"
        "ATOM      2  C   ALA A   1      26.913  26.639   3.531  1.00  9.62           C\n"
    )
    reason = first_missing_ca(path)
    assert reason is not None and "ALA A1" in reason


def test_sources_roundtrip(tmp_path: Path) -> None:
    rows = [
        SourceRow(name="haz_1", label=1, sequence="MKL", n_residues=3),
        SourceRow(name="ben_1", label=0, structure_path=Path("/x/1abc.pdb"), n_residues=120, min_residue=1),
    ]
    out = tmp_path / "sources.csv"
    write_sources(out, rows)
    assert read_sources(out) == rows


def test_sources_filter_by_length() -> None:
    rows = [
        SourceRow(name="a", label=1, n_residues=10),
        SourceRow(name="b", label=1, n_residues=200),
        SourceRow(name="c", label=1, n_residues=500),
        SourceRow(name="d", label=1),
    ]
    kept = filter_by_length(rows, max_residues=300, min_residues=50)
    assert [r.name for r in kept] == ["b"]


def test_sources_populate_residue_stats(tiny_pdb: Path) -> None:
    rows = [SourceRow(name="x", label=1, structure_path=tiny_pdb)]
    enriched = populate_residue_stats(rows)
    assert enriched[0].n_residues == 3
    assert enriched[0].min_residue == 1


def test_fasta_to_sources_filters_length_and_noncanonical(tmp_path: Path) -> None:
    fasta = tmp_path / "tiny.fasta"
    fasta.write_text(
        ">acc1\nMKLAG\n"
        ">acc2\nMK\n"            # too short
        ">acc3\nMKLAGX\n"        # non-canonical X
        ">acc4(extra)\nAAGGCC\n"
    )
    out = tmp_path / "sources.csv"
    result = CliRunner().invoke(fasta_to_sources_cli, [
        "--fasta", str(fasta), "--out", str(out),
        "--label", "1", "--name-prefix", "haz",
        "--min-length", "5", "--max-length", "10",
    ])
    assert result.exit_code == 0, result.output

    rows = read_sources(out)
    assert [r.name for r in rows] == ["haz_acc1", "haz_acc4"]
    assert all(r.label == 1 and r.sequence and r.n_residues == len(r.sequence) for r in rows)


def test_filter_pdbs_pairs_classes_and_drops_neg_indexed(tmp_path: Path) -> None:
    rows = [
        SourceRow(name="haz_a", label=1, n_residues=80),
        SourceRow(name="haz_b", label=1, n_residues=90),
        SourceRow(name="haz_neg", label=1, n_residues=85, min_residue=-2),  # rejected
        SourceRow(name="ben_a", label=0, n_residues=85),
        SourceRow(name="ben_b", label=0, n_residues=95),
        SourceRow(name="ben_c", label=0, n_residues=99),
    ]
    sources = tmp_path / "in.csv"
    out = tmp_path / "filtered.csv"
    write_sources(sources, rows)
    result = CliRunner().invoke(filter_pdbs_cli, [
        "--sources", str(sources), "--out", str(out),
        "--bin-size", "50", "--seed", "0",
    ])
    assert result.exit_code == 0, result.output
    kept = read_sources(out)
    assert len(kept) == 4
    assert sum(r.label == 1 for r in kept) == 2
    assert sum(r.label == 0 for r in kept) == 2
    assert "haz_neg" not in {r.name for r in kept}


def test_build_inputs_emits_rfd3_dict_and_rf3_examples(tmp_path: Path, tiny_pdb: Path) -> None:
    sources = tmp_path / "sources.csv"
    write_sources(sources, [
        SourceRow(name="haz_1", label=1, sequence="MKL"),                       # rf3-only
        SourceRow(name="haz_2", label=1, structure_path=tiny_pdb),              # rfd3-eligible
    ])
    hooks = tmp_path / "hooks.yaml"
    hooks.write_text("hooks:\n  - name: block12\n    module_path: x\n")

    rfd3_out = tmp_path / "rfd3.json"
    result = CliRunner().invoke(build_inputs_cli, [
        "--sources", str(sources), "--out", str(rfd3_out),
        "--model", "rfd3", "--hooks-yaml", str(hooks), "--partial-t", "5.0",
    ])
    assert result.exit_code == 0, result.output
    rfd3_payload = json.loads(rfd3_out.read_text())
    assert "run_config" in rfd3_payload and "haz_2" in rfd3_payload
    assert rfd3_payload["haz_2"] == {"input": str(tiny_pdb.resolve()), "partial_t": 5.0}
    assert "haz_1" not in rfd3_payload    # skipped (no structure_path)

    rf3_out = tmp_path / "rf3.json"
    result = CliRunner().invoke(build_inputs_cli, [
        "--sources", str(sources), "--out", str(rf3_out),
        "--model", "rf3", "--hooks-yaml", str(hooks),
    ])
    assert result.exit_code == 0, result.output
    rf3_payload = json.loads(rf3_out.read_text())
    names = [ex["name"] for ex in rf3_payload["examples"]]
    assert names == ["haz_1", "haz_2"]    # haz_2's sequence comes from chain A of tiny_pdb
    assert rf3_payload["examples"][1]["components"][0]["seq"] == "AGV"


def test_attach_pdbs_matches_rf3_fold_layout(tmp_path: Path) -> None:
    """rf3 fold writes <out_dir>/<sample_idx>/<name>/<name>_model.cif. We should find it."""
    sources = tmp_path / "sources.csv"
    write_sources(sources, [
        SourceRow(name="haz_a", label=1, sequence="MK"),
        SourceRow(name="haz_b", label=1, sequence="MK"),     # no PDB
        SourceRow(name="haz_c", label=1, sequence="MK"),     # bare .pdb in flat dir
    ])
    pdb_dir = tmp_path / "pdbs"
    rf3_layout = pdb_dir / "0" / "haz_a"
    rf3_layout.mkdir(parents=True)
    (rf3_layout / "haz_a_model.cif").write_text("loop_\n")
    (pdb_dir / "haz_c.pdb").write_text("ATOM\n")

    out = tmp_path / "out.csv"
    result = CliRunner().invoke(attach_pdbs_cli, [
        "--sources", str(sources), "--out", str(out), "--pdb-dir", str(pdb_dir),
    ])
    assert result.exit_code == 0, result.output
    rows = {r.name: r for r in read_sources(out)}
    assert rows["haz_a"].structure_path == (rf3_layout / "haz_a_model.cif").resolve()
    assert rows["haz_b"].structure_path is None
    assert rows["haz_c"].structure_path == (pdb_dir / "haz_c.pdb").resolve()
