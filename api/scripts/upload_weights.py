"""One-time Modal volume population.

Run from your laptop (uploads SAE + steering vectors), then triggers an
in-volume RFD3 download (avoids routing 2GB through your home connection).

    modal run api/scripts/upload_weights.py
"""

import subprocess
from pathlib import Path

import modal

REPO_ROOT = Path(__file__).resolve().parents[2]
SAE_LOCAL = REPO_ROOT / "outputs/sae/2026-04-26_15-38-55"
STEERING_LOCAL = REPO_ROOT / "outputs/steering/vectors"
RFD3_URL = "https://files.ipd.uw.edu/pub/rfd3/rfd3_foundry_2025_12_01_remapped.ckpt"
VOLUME_PATH = "/weights"

volume = modal.Volume.from_name("foundry-weights", create_if_missing=True)
download_image = modal.Image.debian_slim().apt_install("curl")
download_app = modal.App("foundry-weights-download", image=download_image)


@download_app.function(volumes={VOLUME_PATH: volume}, timeout=1800)
def download_rfd3() -> str:
    target = Path(VOLUME_PATH) / "checkpoints" / "rfd3_latest.ckpt"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return f"already present: {target} ({target.stat().st_size:,} bytes)"
    subprocess.run(["curl", "-fL", "-o", str(target), RFD3_URL], check=True)
    volume.commit()
    return f"downloaded: {target} ({target.stat().st_size:,} bytes)"


@download_app.local_entrypoint()
def main() -> None:
    _upload_local_tree(SAE_LOCAL, "outputs/sae/2026-04-26_15-38-55", patterns=["**/final.pt"])
    _upload_local_tree(STEERING_LOCAL, "outputs/steering/vectors", patterns=["**/*.pt", "**/*.json"])
    print(download_rfd3.remote())


def _upload_local_tree(local_root: Path, remote_prefix: str, patterns: list[str]) -> None:
    if not local_root.exists():
        raise FileNotFoundError(f"missing local source: {local_root}")
    files = sorted({p for pattern in patterns for p in local_root.glob(pattern)})
    print(f"uploading {len(files)} files from {local_root} → {remote_prefix}/")
    with volume.batch_upload(force=True) as batch:
        for source in files:
            destination = f"{remote_prefix}/{source.relative_to(local_root)}"
            batch.put_file(str(source), destination)
