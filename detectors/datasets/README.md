# Dataset pipeline

Single path:

```
download → fasta_to_sources → [rf3 fold → attach_pdbs] → [filter_pdbs] → build_inputs → saffron collect
```

Every step reads / writes the same `SourceRow` schema
(`name, label, sequence, structure_path, n_residues, min_residue`)
defined at `detectors/src/detectors/datasets/sources.py`. Square-bracketed
steps are optional and only needed for RFD3 (which requires PDB inputs).

## 1. Download (FASTA only)

| Script                          | Source       | Output                       |
|---------------------------------|--------------|------------------------------|
| `download_safeprotein.sh`       | SafeProtein  | 429 hazard FASTA + JSON      |
| `download_vfdb.sh`              | VFDB         | bacterial-VF FASTA           |
| `download_toxinpred3.sh`        | ToxinPred 3  | 5,518 peptide CSVs           |
| `download_toxinpred2.sh`        | ToxinPred 2  | toxin / non-toxin FASTAs     |
| `download_uniprot_benigns.sh`   | Swiss-Prot   | benign FASTA (no toxin/VF/viral) |
| `download_ncbi_viral.sh`        | NCBI viral   | viral RefSeq FASTA           |
| `download_uniprot_pdb_benigns.sh` | Swiss-Prot + RCSB | benign FASTA + matched PDBs |

## 2. FASTA → sources.csv

```bash
python -m detectors.datasets.fasta_to_sources \
    --fasta detectors/datasets/vfdb/VFDB_setA_pro.fas \
    --label 1 --name-prefix vf \
    --out detectors/datasets/vfdb/sources.csv \
    --min-length 50 --max-length 300
```

Filters by length, drops non-canonical residues, sets `n_residues = len(sequence)`.
This is the **RF3-ready** form — RF3 takes `sequence` directly, no folding needed.

## 3. (RFD3 only) fold sequences with `rf3 fold`, then attach paths

RFD3 needs PDBs. The project already ships its own batch folder, `rf3 fold`,
which consumes the same JSON shape as `saffron collect` so we can build the
inputs once and reuse them.

```bash
# build the rf3-fold inputs JSON
python -m detectors.datasets.build_inputs \
    --sources detectors/datasets/safeprotein/sources.csv \
    --out detectors/datasets/safeprotein/rf3_inputs.json \
    --model rf3 \
    --hooks-yaml detectors/datasets/hooks/rf3.yaml

# fold (project's own CLI; supports skip_existing for resumability)
rf3 fold \
    inputs=detectors/datasets/safeprotein/rf3_inputs.json \
    out_dir=detectors/datasets/safeprotein/pdbs \
    skip_existing=True

# pair sources.csv rows with the predicted CIFs
python -m detectors.datasets.attach_pdbs \
    --sources detectors/datasets/safeprotein/sources.csv \
    --pdb-dir detectors/datasets/safeprotein/pdbs \
    --out detectors/datasets/safeprotein/sources_with_pdbs.csv
```

`attach_pdbs` recursively walks `--pdb-dir` and matches each row's `name` to a
file with one of: `<name>_model.cif` (rf3 fold output), `<name>.pdb`,
`<name>.cif`, `<name>.cif.gz`. Rows with no match pass through.

`download_uniprot_pdb_benigns.sh` already writes a sources.csv with
`structure_path` populated from RCSB experimental structures, so it can skip
this whole step.

## 4. (Optional) RFD3-compatibility filter + class balance

```bash
cat hazards.csv <(tail -n +2 benigns.csv) > combined.csv

python -m detectors.datasets.filter_pdbs \
    --sources combined.csv \
    --out filtered.csv \
    --bin-size 50
```

Drops PDBs with non-positive residue indices (RFD3's contig parser rejects
`A0`/`A-1`) and pairs `min(#hazard, #benign)` per length bucket so length
isn't a probe shortcut feature.

## 5. Build saffron inputs JSON

```bash
python -m detectors.datasets.build_inputs \
    --sources detectors/datasets/safeprotein/sources_filtered.csv \
    --out tutorials/sae_data_rfd3_partial/train_inputs.json \
    --model rfd3 \
    --hooks-yaml detectors/datasets/hooks/rfd3_partial.yaml \
    --partial-t 5.0
```

For RF3, swap `--model rf3 --hooks-yaml detectors/datasets/hooks/rf3.yaml`.
RF3 takes `sequence` directly; if a row has `structure_path` but no `sequence`,
the chain-A sequence is extracted from the PDB.

## 6. Run `saffron collect` (original interface)

```bash
saffron collect \
    model=rfd3 \
    inputs=tutorials/sae_data_rfd3_partial/train_inputs.json \
    out_dir=tutorials/sae_data_rfd3_partial/train_activations
```

Output: `<out_dir>/activations/activations.h5`.

## Adding a new dataset

1. Write `download_<name>.sh` (FASTA → disk).
2. Run `fasta_to_sources` to produce `sources.csv` (RF3-ready).
3. (For RFD3) `build_inputs --model rf3` → `rf3 fold` → `attach_pdbs`.
4. (Optional) merge per-class CSVs and run `filter_pdbs`.
5. Run `build_inputs --model rfd3` to produce a saffron inputs JSON.
6. Run `saffron collect` against that JSON.
