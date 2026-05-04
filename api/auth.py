import os
import time
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

_bearer = HTTPBearer()
_jwks_cache: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 3600


def get_user_id(credentials: HTTPAuthorizationCredentials = Security(_bearer)) -> str:
    token = credentials.credentials
    try:
        return _verify_and_extract_subject(token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"invalid token: {exc}")


def _verify_and_extract_subject(token: str) -> str:
    header = jwt.get_unverified_header(token)
    algorithm = header.get("alg", "RS256")
    if algorithm == "HS256":
        return _decode_hs256(token)
    return _decode_with_jwks(token, header.get("kid"))


def _decode_hs256(token: str) -> str:
    secret = os.environ["SUPABASE_JWT_SECRET"]
    payload = jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
    return payload["sub"]


def _decode_with_jwks(token: str, key_id: str | None) -> str:
    keys = _load_jwks()
    matching = next((k for k in keys if k["kid"] == key_id), keys[0])
    payload = jwt.decode(
        token, matching, algorithms=[matching["alg"]], audience="authenticated"
    )
    return payload["sub"]


def _load_jwks() -> list[dict[str, Any]]:
    if _jwks_cache["keys"] and time.time() - _jwks_cache["fetched_at"] < _JWKS_TTL_SECONDS:
        return _jwks_cache["keys"]
    project_url = os.environ["SUPABASE_URL"]
    response = httpx.get(f"{project_url}/auth/v1/.well-known/jwks.json", timeout=5.0)
    response.raise_for_status()
    _jwks_cache["keys"] = response.json()["keys"]
    _jwks_cache["fetched_at"] = time.time()
    return _jwks_cache["keys"]


UserId = Depends(get_user_id)
