#!/usr/bin/env bash
# Download VaxiJen registry proteins from Swiss-Prot:
#   - FASTAs from UniProt          -> positives.fasta / negatives.fasta
#   - AlphaFold-DB structures      -> pdbs/{accession}.pdb
# Source: vaxijen/registry.xls (sheets: bacterial, viral, tumour). Viral
# negatives use VOGdb IDs (no Swiss-Prot mapping) and are skipped. Resumable.
#
# Usage: ./download_vaxijen.sh [dest_dir]

set -euo pipefail

REGISTRY="$(dirname "$0")/vaxijen/registry.xls"
DEST="${1:-$(dirname "$0")/vaxijen}"

mkdir -p "$DEST/pdbs"
touch "$DEST/positives.fasta" "$DEST/negatives.fasta"

echo "fetch  VaxiJen Swiss-Prot proteins (registry=${REGISTRY})"

uv run --with pandas --with xlrd --quiet python3 - "$REGISTRY" "$DEST" <<'PY'
import json, re, sys, time, urllib.error, urllib.request
from pathlib import Path
import pandas as pd

REGISTRY, DEST = sys.argv[1], Path(sys.argv[2])
SWISSPROT_RE = re.compile(r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$")
FASTA_HEADER_RE = re.compile(r"^>\S+\|([^|]+)\|")
UNIPROT_BATCH = 100


def main():
    accessions = parse_registry()
    write_labels(accessions)
    download_fastas(accessions)
    download_alphafold_pdbs([acc for acc, _, _ in accessions])


def parse_registry():
    sheets = pd.read_excel(REGISTRY, sheet_name=None)
    rows = []
    for sheet_name in ("bacterial", "viral"):
        for _, row in sheets[sheet_name].iterrows():
            accession = str(row["swiss-prot"]).strip()
            label = str(row["protection"]).strip().lower()
            if SWISSPROT_RE.match(accession) and label in ("yes", "no"):
                rows.append((accession, label, sheet_name))
    for _, row in sheets["tumour"].iterrows():
        accession = str(row["Unnamed: 1"]).strip()
        if SWISSPROT_RE.match(accession):
            rows.append((accession, "yes", "tumour"))
    by_accession = {}
    for accession, label, category in rows:
        by_accession.setdefault(accession, []).append((label, category))
    deduped, conflicts = [], []
    for accession, entries in by_accession.items():
        labels = {label for label, _ in entries}
        if len(labels) > 1:
            conflicts.append(accession)
            continue
        deduped.append((accession, entries[0][0], entries[0][1]))
    n_pos = sum(1 for _, l, _ in deduped if l == "yes")
    print(f"  registry: {len(deduped)} accessions ({n_pos} positive, {len(deduped) - n_pos} negative)")
    if conflicts:
        print(f"  skipped {len(conflicts)} accessions with conflicting yes/no labels: {','.join(conflicts)}")
    return deduped


def write_labels(accessions):
    with open(DEST / "labels.tsv", "w") as out:
        out.write("accession\tlabel\tcategory\n")
        for accession, label, category in accessions:
            out.write(f"{accession}\t{label}\t{category}\n")


def download_fastas(accessions):
    targets = {"yes": DEST / "positives.fasta", "no": DEST / "negatives.fasta"}
    for label, path in targets.items():
        already = existing_accessions(path)
        pending = [acc for acc, lbl, _ in accessions if lbl == label and acc not in already]
        print(f"  FASTA[{label}]: {len(pending)} to fetch ({len(already)} cached)")
        with open(path, "a") as out:
            for batch in chunks(pending, UNIPROT_BATCH):
                body = http_get(uniprot_batch_url(batch))
                for record in re.split(r"(?=^>)", body, flags=re.MULTILINE):
                    if record.startswith(">"):
                        out.write(record if record.endswith("\n") else record + "\n")
                print(f"    fetched batch of {len(batch)}")


def download_alphafold_pdbs(accessions):
    pdb_dir = DEST / "pdbs"
    misses_path = DEST / "alphafold_missing.txt"
    misses = set(misses_path.read_text().split()) if misses_path.exists() else set()
    pending = [a for a in accessions if not (pdb_dir / f"{a}.pdb").exists() and a not in misses]
    print(f"  PDB: {len(pending)} accessions to query AlphaFold-DB")
    fetched = 0
    for accession in pending:
        pdb_url = alphafold_pdb_url(accession)
        if pdb_url is None:
            misses.add(accession)
            continue
        (pdb_dir / f"{accession}.pdb").write_text(http_get(pdb_url))
        fetched += 1
        time.sleep(0.05)
    misses_path.write_text("\n".join(sorted(misses)) + "\n")
    print(f"  fetched {fetched} PDBs ({len(misses)} accessions have no AlphaFold model)")


def alphafold_pdb_url(accession):
    try:
        payload = json.loads(http_get(f"https://alphafold.ebi.ac.uk/api/prediction/{accession}"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    return payload[0].get("pdbUrl") if payload else None


def uniprot_batch_url(batch):
    return f"https://rest.uniprot.org/uniprotkb/accessions?accessions={','.join(batch)}&format=fasta&size=500"


def existing_accessions(fasta_path):
    with open(fasta_path) as f:
        return {m.group(1) for line in f if line.startswith(">") for m in [FASTA_HEADER_RE.match(line)] if m}


def http_get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "*/*"})) as response:
        return response.read().decode("utf-8")


def chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


main()
PY

echo
echo "VaxiJen download complete in $DEST"
echo "  positives:  $(grep -c '^>' "$DEST/positives.fasta") sequences"
echo "  negatives:  $(grep -c '^>' "$DEST/negatives.fasta") sequences"
echo "  AF PDBs:    $(find "$DEST/pdbs" -name '*.pdb' | wc -l)"
