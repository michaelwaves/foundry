import h5py
import pandas as pd

from detectors.pipelines.labels import run_labels


def test_labels_align_design_ids_with_batch_suffixes(tmp_path):
    pos_fasta = tmp_path / "pos.fasta"
    pos_fasta.write_text(">A0A096YGU7\nMKVLI\n>P0DTC2\nMFVFLVLLPLVS\n")
    neg_fasta = tmp_path / "neg.fasta"
    neg_fasta.write_text(">sp|P12345|HUMAN\nMASTER\n>sp|Q67890|MOUSE\nMOUSEPROT\n")

    h5_path = tmp_path / "activations.h5"
    with h5py.File(h5_path, "w") as f:
        block = f.create_group("block8")
        for design_id in ["A0A096YGU7_0", "A0A096YGU7_1", "P0DTC2_0",
                          "sp_P12345_HUMAN_0", "sp_Q67890_MOUSE_0", "unmatched_xyz_0"]:
            block.create_group(design_id).create_dataset("0", data=[[[0.0]]])

    out_dir = tmp_path / "labels_out"
    run_labels({
        "positives": [str(pos_fasta)],
        "negatives": [str(neg_fasta)],
        "activations_path": str(h5_path),
        "out_dir": str(out_dir),
    })

    labels = pd.read_csv(out_dir / "labels.csv").set_index("design_id")
    assert set(labels.index) == {
        "A0A096YGU7_0", "A0A096YGU7_1", "P0DTC2_0",
        "sp_P12345_HUMAN_0", "sp_Q67890_MOUSE_0",
    }
    assert labels.loc["A0A096YGU7_0", "label"] == 1
    assert labels.loc["sp_P12345_HUMAN_0", "label"] == 0


def test_labels_handles_lineformat_csv(tmp_path):
    # ToxinPred 3 style: one peptide per line, no '>' header
    pos = tmp_path / "train_pos.csv"
    pos.write_text("IWKS\nGCPWMPWC\nSVDMVMKGLKIWPL\n")
    out_dir = tmp_path / "out"
    sources = run_labels({"positives": [str(pos)], "negatives": [], "out_dir": str(out_dir)})
    assert list(sources["source_id"]) == ["train_pos_1", "train_pos_2", "train_pos_3"]
    assert (sources["label"] == 1).all()
