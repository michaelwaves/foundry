#!/usr/bin/env bash
# Download benign proteins from UniProt: reviewed (Swiss-Prot), NOT toxin,
# NOT virulence, NOT viral. Cursor-paginated FASTA download.
#
# Defaults match SafeBench-Seq's negative-set recipe (NOT KW-0800, non-viral),
# plus a stricter NOT virulence (KW-0843) filter. Resumable: re-running tops
# up an existing benigns.fasta instead of re-fetching from scratch.
#
# Usage:
#   ./download_uniprot_benigns.sh                            # default 10000 records
#   ./download_uniprot_benigns.sh 5000                       # custom count
#   ./download_uniprot_benigns.sh 5000 50 500                # length range 50-500 aa
#   ./download_uniprot_benigns.sh 5000 50 500 /custom/dest

set -euo pipefail

TARGET_COUNT="${1:-10000}"
LEN_MIN="${2:-1}"
LEN_MAX="${3:-2000}"
DEST="${4:-$(dirname "$0")/uniprot_benigns}"
PAGE_SIZE=500

mkdir -p "$DEST"
FASTA_TARGET="$DEST/benigns.fasta"
touch "$FASTA_TARGET"

QUERY="reviewed:true+NOT+keyword:KW-0800+NOT+keyword:KW-0843+NOT+taxonomy_id:10239+AND+length:%5B${LEN_MIN}%20TO%20${LEN_MAX}%5D"
URL="https://rest.uniprot.org/uniprotkb/search?query=${QUERY}&format=fasta&size=${PAGE_SIZE}"

echo "fetch  UniProt benigns (target=${TARGET_COUNT}, length=${LEN_MIN}-${LEN_MAX})"

python3 - "$URL" "$TARGET_COUNT" "$FASTA_TARGET" <<'PY'
import re, sys, urllib.error, urllib.request

start_url, target_count, fasta_target = sys.argv[1:]
target_count = int(target_count)

# Resume: skip accessions already present in the fasta.
already_fetched = set()
header_pattern = re.compile(r"^>\S+\|([^|]+)\|")
with open(fasta_target) as f:
    for line in f:
        if line.startswith(">"):
            match = header_pattern.match(line)
            if match:
                already_fetched.add(match.group(1))
total = len(already_fetched)
next_url = start_url
print(f"  starting at {total} (already-fetched accessions skipped)")

with open(fasta_target, "a") as out:
    while next_url and total < target_count:
        request = urllib.request.Request(next_url, headers={"Accept": "text/plain"})
        with urllib.request.urlopen(request) as response:
            link_header = response.headers.get("Link", "")
            body = response.read().decode("utf-8")

        # Split FASTA body into per-entry records, write only those whose accession
        # isn't already in the set.
        records = re.split(r"(?=^>)", body, flags=re.MULTILINE)
        added_this_page = 0
        for record in records:
            if total >= target_count:
                break
            if not record.startswith(">"):
                continue
            match = header_pattern.match(record)
            if not match:
                continue
            accession = match.group(1)
            if accession in already_fetched:
                continue
            out.write(record if record.endswith("\n") else record + "\n")
            already_fetched.add(accession)
            total += 1
            added_this_page += 1
        print(f"  fetched {added_this_page} records (total={total})")

        # Robust Link header next-cursor extraction (URLs may contain commas).
        link_match = re.search(r'<(https?://[^>]+)>;\s*rel="next"', link_header)
        next_url = link_match.group(1) if link_match else None

print(f"done: {total} benign protein sequences")
PY

echo
echo "UniProt benigns downloaded to $DEST"
echo "  $(grep -c '^>' "$FASTA_TARGET") benign protein sequences"
