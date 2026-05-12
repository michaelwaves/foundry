from pathlib import Path

from supabase import Client

_SIGNED_URL_TTL_SECONDS = 60 * 60


def upload_output(db: Client, user_id: str, job_id: str, output_path: Path) -> str:
    storage_path = f"{user_id}/{job_id}.cif.gz"
    db.storage.from_("outputs").upload(
        storage_path,
        output_path.read_bytes(),
        {"content-type": "application/gzip", "upsert": "true"},
    )
    return storage_path


def make_fresh_signed_url(db: Client, storage_path: str) -> str:
    response = db.storage.from_("outputs").create_signed_url(storage_path, _SIGNED_URL_TTL_SECONDS)
    return response["signedURL"]
