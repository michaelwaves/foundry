#!/usr/bin/env bash
# Fetch benign Swiss-Prot proteins that have PDB cross-references, download the
# associated PDBs from RCSB, and emit a sources.csv row per entry. Pairs with
# SafeProtein hazards for the RFD3 partial-diffusion pipeline.
#
# UniProt query (matches the SafeBench-Seq benign recipe + stricter NOT virulence,
# and requires a PDB cross-reference):
#   reviewed:true
#   NOT keyword:KW-0800 (Toxin)
#   NOT keyword:KW-0843 (Virulence)
#   NOT taxonomy_id:10239 (Viruses)
#   AND database:PDB
#   AND length:[LEN_MIN TO LEN_MAX]
#
# Usage:
#   ./download_uniprot_pdb_benigns.sh                          # default 200 records, length 100-400
#   ./download_uniprot_pdb_benigns.sh 500 80 600
#   ./download_uniprot_pdb_benigns.sh 500 80 600 /custom/dest

set -euo pipefail

TARGET_COUNT="${1:-200}"
LEN_MIN="${2:-100}"
LEN_MAX="${3:-400}"
DEST="${4:-$(dirname "$0")/uniprot_pdb_benigns}"
PAGE_SIZE=500

PDB_DIR="$DEST/pdbs"
SOURCES_CSV="$DEST/sources.csv"
mkdir -p "$PDB_DIR"
[[ -s "$SOURCES_CSV" ]] || echo "name,label,structure_path" > "$SOURCES_CSV"

QUERY="reviewed:true+NOT+keyword:KW-0800+NOT+keyword:KW-0843+NOT+taxonomy_id:10239+AND+database:PDB+AND+length:%5B${LEN_MIN}%20TO%20${LEN_MAX}%5D"
URL="https://rest.uniprot.org/uniprotkb/search?query=${QUERY}&format=tsv&fields=accession,length,xref_pdb&size=${PAGE_SIZE}"

echo "fetch  UniProt benigns w/ PDB (target=${TARGET_COUNT}, length=${LEN_MIN}-${LEN_MAX})"

python3 - "$URL" "$TARGET_COUNT" "$PDB_DIR" "$SOURCES_CSV" <<'PY'
import csv, os, re, sys, urllib.error, urllib.request


def _fetch_structure(pdb_id: str, pdb_dir: str) -> str | None:
    """Try .pdb first; fall back to .cif.gz for structures too large for legacy PDB."""
    pid = pdb_id.lower()
    for filename in (f"{pid}.pdb", f"{pid}.cif.gz"):
        target = os.path.join(pdb_dir, filename)
        if os.path.exists(target) and os.path.getsize(target) > 0:
            return target
        try:
            urllib.request.urlretrieve(f"https://files.rcsb.org/download/{filename}", target)
            return target
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            try: os.remove(target)
            except FileNotFoundError: pass
    return None


start_url, target_count, pdb_dir, sources_csv = sys.argv[1:]
target_count = int(target_count)

# Resume: skip accessions already in sources.csv (lets you re-run after a crash).
already_fetched = set()
if os.path.exists(sources_csv):
    with open(sources_csv) as f:
        for row in csv.reader(f):
            if row and row[0].startswith("benign_"):
                already_fetched.add(row[0][len("benign_"):])
total = len(already_fetched)
next_url = start_url
print(f"  starting at {total} (already-fetched accessions skipped)")

with open(sources_csv, "a", newline="") as out:
    writer = csv.writer(out)
    while next_url and total < target_count:
        request = urllib.request.Request(next_url, headers={"Accept": "text/tab-separated-values"})
        with urllib.request.urlopen(request) as response:
            link_header = response.headers.get("Link", "")
            body = response.read().decode("utf-8")

        rows = body.strip().splitlines()
        if rows and rows[0].lower().startswith("entry"):
            rows = rows[1:]
        for row in rows:
            if total >= target_count:
                break
            cols = row.split("\t")
            if len(cols) < 3:
                continue
            accession, length, pdb_field = cols[0], cols[1], cols[2]
            if accession in already_fetched:
                continue
            pdb_id = next((p.strip() for p in pdb_field.split(";") if p.strip()), None)
            if not pdb_id:
                continue
            target_path = _fetch_structure(pdb_id, pdb_dir)
            if target_path is None:
                print(f"  fail {accession} ({pdb_id}): no .pdb or .cif.gz at RCSB")
                continue
            writer.writerow([f"benign_{accession}", 0, os.path.abspath(target_path)])
            total += 1
            if total % 25 == 0:
                print(f"  {total} fetched...")

        # Link header URLs contain commas (fields=accession,length,xref_pdb), so
        # naive split(",") shreds them. Match <URL>; rel="next" with regex.
        match = re.search(r'<(https?://[^>]+)>;\s*rel="next"', link_header)
        next_url = match.group(1) if match else None

print(f"done: {total} benign PDBs fetched")
PY

echo "wrote sources.csv -> $SOURCES_CSV"
echo "  $(($(wc -l < "$SOURCES_CSV") - 1)) benign rows"
