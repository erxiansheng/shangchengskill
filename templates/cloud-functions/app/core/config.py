import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve cloud-functions/app/core/_secrets.py — agent writes this file at
# deploy time (see SKILL.md step 4.3) so Cloud Function and Edge Function
# both pick up the secrets without touching the EdgeOne console env panel.
# Never commit _secrets.py (already in .gitignore).
_SECRETS_MODULE = Path(__file__).resolve().parent / "_secrets.py"

if _SECRETS_MODULE.exists():
    import importlib.util
    _spec = importlib.util.spec_from_file_location("app.core._secrets", _SECRETS_MODULE)
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        for _k in (
            "JWT_SECRET", "INTERNAL_KEY",
            "KV_NAMESPACE", "STORAGE_MODE",
            "S3_ENDPOINT", "S3_BUCKET", "S3_ACCESS_KEY", "S3_SECRET_KEY",
        ):
            _v = getattr(_mod, _k, None)
            if _v is not None and _k not in os.environ:
                os.environ[_k] = str(_v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
        extra="allow",
    )

    PROJECT_NAME: str = "EdgeOneMall API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # 从 Pages 环境变量 `JWT_SECRET` 读取（与 Edge Function 一致）。
    # 错误填入 "SECRET_KEY" 同名环境变量也能被 pydantic 默认读到作为 fallback。
    SECRET_KEY: str = Field(
        default="",
        validation_alias="JWT_SECRET",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # EdgeOne KV Storage (accessed via Edge Function KV proxy)

    # S3-compatible Object Storage (defaults; overridden at runtime from KV settings)
    S3_ENDPOINT: str = ""
    S3_BUCKET: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "us-east-1"
    S3_PUBLIC_URL: str = ""

    # File upload limits (defaults; overridden at runtime from KV settings)
    MAX_IMAGE_SIZE: int = 5 * 1024 * 1024       # 5MB
    MAX_SKILL_PACKAGE_SIZE: int = 5 * 1024 * 1024  # 5MB

    PLATFORM_FEE_RATE: float = 0.3  # 30% default commission

    # API Token
    API_TOKEN_PREFIX: str = "oc_"


settings = Settings()
