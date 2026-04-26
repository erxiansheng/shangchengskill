"""
S3-compatible object storage client for file uploads.

Uses stdlib HTTP requests with AWS Signature V4 to avoid boto3/botocore
dependency issues on EdgeOne Pages (botocore.docs is stripped).

When S3_ENDPOINT is empty (local dev), falls back to local filesystem storage
under ./uploads/ so the app can run without cloud credentials.
"""

from __future__ import annotations

import os
import uuid
import hashlib
import hmac
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signature_key(secret_key: str, date_stamp: str, region: str, service: str) -> bytes:
    k_date = _sign(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "aws4_request")
    return k_signing


def _aws_v4_headers(
    method: str,
    endpoint: str,
    bucket: str,
    key: str,
    content: bytes,
    content_type: str,
    access_key: str,
    secret_key: str,
    region: str,
) -> dict:
    """Generate AWS Signature V4 headers for a request."""
    from urllib.parse import urlparse, quote

    parsed = urlparse(endpoint)
    host = parsed.hostname
    if parsed.port and parsed.port not in (80, 443):
        host = f"{parsed.hostname}:{parsed.port}"

    # Path-style addressing: /{bucket}/{key}
    canonical_uri = f"/{bucket}/{quote(key, safe='/')}"

    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    payload_hash = hashlib.sha256(content).hexdigest()

    canonical_headers = (
        f"content-type:{content_type}\n"
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "content-type;host;x-amz-content-sha256;x-amz-date"

    canonical_request = (
        f"{method}\n"
        f"{canonical_uri}\n"
        f"\n"  # empty query string
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{payload_hash}"
    )

    credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
    string_to_sign = (
        f"AWS4-HMAC-SHA256\n"
        f"{amz_date}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    signing_key = _get_signature_key(secret_key, date_stamp, region, "s3")
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization = (
        f"AWS4-HMAC-SHA256 "
        f"Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    return {
        "Content-Type": content_type,
        "Host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
        "Authorization": authorization,
    }


class S3Storage:
    """Handles file uploads to S3-compatible object storage.
    
    Config can be updated at runtime from KV settings via update_config().
    """

    def __init__(self):
        self._cfg = {
            "endpoint": settings.S3_ENDPOINT,
            "bucket": settings.S3_BUCKET,
            "access_key": settings.S3_ACCESS_KEY,
            "secret_key": settings.S3_SECRET_KEY,
            "region": settings.S3_REGION,
            "public_url": settings.S3_PUBLIC_URL,
        }
        self._use_remote = bool(self._cfg["endpoint"])
        if not self._use_remote:
            self._upload_dir = "./uploads"
            try:
                os.makedirs(f"{self._upload_dir}/images", exist_ok=True)
                os.makedirs(f"{self._upload_dir}/skills", exist_ok=True)
            except OSError:
                pass  # Read-only filesystem (cloud environment)

    def update_config(self, kv_settings: dict):
        """Override S3 config from KV site:settings. Empty values are ignored."""
        mapping = {
            "s3Endpoint": "endpoint",
            "s3Bucket": "bucket",
            "s3AccessKey": "access_key",
            "s3SecretKey": "secret_key",
            "s3Region": "region",
            "s3PublicUrl": "public_url",
        }
        for kv_key, cfg_key in mapping.items():
            val = kv_settings.get(kv_key)
            if val:
                self._cfg[cfg_key] = val
        self._use_remote = bool(self._cfg["endpoint"])

    def _put_object(self, key: str, content: bytes, content_type: str) -> bool:
        """Upload an object to S3 using the current instance config."""
        from urllib.parse import quote

        endpoint = self._cfg["endpoint"].rstrip("/")
        canonical_uri = f"/{self._cfg['bucket']}/{quote(key, safe='/')}"
        url = f"{endpoint}{canonical_uri}"

        headers = _aws_v4_headers(
            method="PUT",
            endpoint=endpoint,
            bucket=self._cfg["bucket"],
            key=key,
            content=content,
            content_type=content_type,
            access_key=self._cfg["access_key"],
            secret_key=self._cfg["secret_key"],
            region=self._cfg["region"],
        )

        req = urllib.request.Request(url, data=content, method="PUT", headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status in (200, 201, 204)
        except urllib.error.HTTPError as e:
            print(f"[S3] PUT failed ({e.code}): {e.read().decode('utf-8', errors='replace')}")
            return False
        except Exception as e:
            print(f"[S3] PUT error: {e}")
            return False

    def _delete_object(self, key: str) -> bool:
        """Delete an object from S3 using the current instance config."""
        from urllib.parse import quote

        endpoint = self._cfg["endpoint"].rstrip("/")
        canonical_uri = f"/{self._cfg['bucket']}/{quote(key, safe='/')}"
        url = f"{endpoint}{canonical_uri}"

        empty = b""
        headers = _aws_v4_headers(
            method="DELETE",
            endpoint=endpoint,
            bucket=self._cfg["bucket"],
            key=key,
            content=empty,
            content_type="application/octet-stream",
            access_key=self._cfg["access_key"],
            secret_key=self._cfg["secret_key"],
            region=self._cfg["region"],
        )

        req = urllib.request.Request(url, data=empty, method="DELETE", headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status in (200, 204)
        except urllib.error.HTTPError as e:
            print(f"[S3] DELETE failed ({e.code}): {e.read().decode('utf-8', errors='replace')}")
            return False
        except Exception as e:
            print(f"[S3] DELETE error: {e}")
            return False

    def upload_image(self, content: bytes, filename: str, content_type: str = "image/jpeg") -> str:
        """Upload an image and return its public URL."""
        ext = os.path.splitext(filename)[1] or ".jpg"
        key = f"images/{uuid.uuid4().hex}{ext}"

        if self._use_remote:
            if self._put_object(key, content, content_type):
                return self._public_url(key)
            raise RuntimeError("S3 上传图片失败，请检查 S3 存储配置")

        self._ensure_local_dirs()
        path = f"{self._upload_dir}/{key}"
        with open(path, "wb") as f:
            f.write(content)
        return f"/uploads/{key}"

    def upload_skill_package(self, content: bytes, filename: str) -> dict:
        """Upload a skill zip package. Returns {url, file_size, file_hash}."""
        ext = os.path.splitext(filename)[1] or ".zip"
        key = f"skills/{uuid.uuid4().hex}{ext}"
        file_hash = hashlib.sha256(content).hexdigest()

        if self._use_remote:
            if self._put_object(key, content, "application/zip"):
                return {
                    "url": key,
                    "file_size": len(content),
                    "file_hash": file_hash,
                }
            raise RuntimeError("S3 上传技能包失败，请检查 S3 存储配置")

        self._ensure_local_dirs()
        path = f"{self._upload_dir}/{key}"
        with open(path, "wb") as f:
            f.write(content)
        return {
            "url": f"/uploads/{key}",
            "file_size": len(content),
            "file_hash": file_hash,
        }

    def get_public_download_url(self, key: str) -> Optional[str]:
        """Return a direct public URL for downloading (no signature needed).
        Returns None if no public URL is configured."""
        if self._use_remote and self._cfg["public_url"]:
            return f"{self._cfg['public_url'].rstrip('/')}/{self._cfg['bucket']}/{key}"
        return None

    def get_presigned_url(self, key: str, expires: int = 3600) -> str:
        if self._use_remote:
            return self._generate_presigned_url(key, expires)
        return f"/uploads/{key}" if not key.startswith("/") else key

    def _generate_presigned_url(self, key: str, expires: int = 3600) -> str:
        """Generate an actual AWS Signature V4 presigned URL for GET."""
        from urllib.parse import urlparse, quote, urlencode

        endpoint = self._cfg["endpoint"].rstrip("/")
        parsed = urlparse(endpoint)
        host = parsed.hostname
        if parsed.port and parsed.port not in (80, 443):
            host = f"{parsed.hostname}:{parsed.port}"

        canonical_uri = f"/{self._cfg['bucket']}/{quote(key, safe='/')}"

        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        region = self._cfg["region"]
        access_key = self._cfg["access_key"]
        secret_key = self._cfg["secret_key"]

        credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
        credential = f"{access_key}/{credential_scope}"

        query_params = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": credential,
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(expires),
            "X-Amz-SignedHeaders": "host",
        }
        canonical_querystring = "&".join(
            f"{quote(k, safe='')}={quote(v, safe='')}"
            for k, v in sorted(query_params.items())
        )

        canonical_headers = f"host:{host}\n"
        canonical_request = (
            f"GET\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"host\n"
            f"UNSIGNED-PAYLOAD"
        )

        string_to_sign = (
            f"AWS4-HMAC-SHA256\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        signing_key = _get_signature_key(secret_key, date_stamp, region, "s3")
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        presigned_url = f"{endpoint}{canonical_uri}?{canonical_querystring}&X-Amz-Signature={signature}"
        return presigned_url

    def get_file_bytes(self, key: str) -> Optional[bytes]:
        """Read file content. Returns bytes or None if not found."""
        if self._use_remote:
            return self._get_object(key)
        # local
        path = key if key.startswith("/") else f"{self._upload_dir}/{key}"
        if key.startswith("/uploads/"):
            path = f".{key}"
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
        return None

    def _get_object(self, key: str) -> Optional[bytes]:
        """Fetch an object from S3 using header-based AWS V4 auth."""
        from urllib.parse import quote

        endpoint = self._cfg["endpoint"].rstrip("/")
        canonical_uri = f"/{self._cfg['bucket']}/{quote(key, safe='/')}"
        url = f"{endpoint}{canonical_uri}"

        # Use empty body for GET
        empty = b""
        headers = _aws_v4_headers(
            method="GET",
            endpoint=endpoint,
            bucket=self._cfg["bucket"],
            key=key,
            content=empty,
            content_type="application/octet-stream",
            access_key=self._cfg["access_key"],
            secret_key=self._cfg["secret_key"],
            region=self._cfg["region"],
        )

        req = urllib.request.Request(url, method="GET", headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            print(f"[S3] GET failed ({e.code}): {e.read().decode('utf-8', errors='replace')}")
            return None
        except Exception as e:
            print(f"[S3] GET error: {e}")
            return None

    def delete_file(self, key: str) -> None:
        """Delete a file from storage."""
        if self._use_remote:
            self._delete_object(key)
        else:
            path = f"{self._upload_dir}/{key}"
            if os.path.exists(path):
                os.remove(path)

    def _public_url(self, key: str) -> str:
        if self._cfg["public_url"]:
            return f"{self._cfg['public_url'].rstrip('/')}/{self._cfg['bucket']}/{key}"
        return f"{self._cfg['endpoint'].rstrip('/')}/{self._cfg['bucket']}/{key}"

    def _ensure_local_dirs(self):
        if not hasattr(self, '_upload_dir'):
            self._upload_dir = "./uploads"
        os.makedirs(f"{self._upload_dir}/images", exist_ok=True)
        os.makedirs(f"{self._upload_dir}/skills", exist_ok=True)
