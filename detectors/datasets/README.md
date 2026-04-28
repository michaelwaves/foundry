# Dataset pipeline

Single path:

```
download → fasta_to_sources → [fetch_pdbs] → [filter_pdbs] → build_inputs → saffron collect
```

Every step reads / writes the same `SourceRow` schema
(`name, label, sequence, structure_path, n_residues, min_residue`)
defined at `detectors/src/detectors/datasets/sources.py`. Square-bracketed
steps are optional: `fetch_pdbs` is RFD3-only, and `filter_pdbs` is only
needed if you care about RFD3-compatibility filtering and cross-class
length-stratification.

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

## 3. (RFD3 only) attach `structure_path`

RFD3 needs PDBs. Two paths:

**(a) RCSB cross-references**, when the source dataset already maps accessions
to PDB IDs (SafeProtein ships these in its JSON):

```bash
python -m detectors.datasets.fetch_pdbs \
    --sources detectors/datasets/safeprotein/sources.csv \
    --safeprotein-json detectors/datasets/safeprotein/SafeProtein_Bench.json \
    --strip-prefix hazard_ \
    --pdb-dir detectors/datasets/safeprotein/pdbs \
    --out detectors/datasets/safeprotein/sources_with_pdbs.csv
```

For arbitrary mappings (any dataset), pass `--pdb-map mapping.json` instead,
where `mapping.json` is `{row_name: pdb_id, ...}`.

**(b) Fold from sequence** when no experimental structure exists (e.g. VFDB).
No bundled folder — install ESMFold separately, run it on the FASTA, write
`structure_path` into the sources CSV with whatever script you prefer.

`download_uniprot_pdb_benigns.sh` writes a sources.csv with `structure_path`
already populated, so it can skip this step.

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
3. (For RFD3) run `fetch_pdbs` or fold separately to attach `structure_path`.
4. (Optional) merge per-class CSVs and run `filter_pdbs`.
5. Run `build_inputs` to produce a saffron inputs JSON.
6. Run `saffron collect` against that JSON.
