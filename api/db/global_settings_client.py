"""
Global Settings DB Client
Platform-wide key-value store for admin configuration.
Used for provider API keys, platform settings, and policy.
"""
import json
from typing import Any, Optional

from cryptography.fernet import Fernet
from loguru import logger
from sqlalchemy.future import select

from api.db.base_client import BaseDBClient
from api.db.models import GlobalSettingsModel
from api.constants import OSS_JWT_SECRET


def _get_fernet() -> Fernet:
    """Derive a Fernet key from OSS_JWT_SECRET for encrypting provider API keys."""
    import base64
    import hashlib
    key_bytes = hashlib.sha256(OSS_JWT_SECRET.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def _encrypt_value(value: Any) -> Any:
    """Encrypt api_key fields inside a provider config dict."""
    if not isinstance(value, dict):
        return value
    result = dict(value)
    if "api_key" in result and result["api_key"]:
        f = _get_fernet()
        raw = result["api_key"]
        if isinstance(raw, list):
            result["api_key"] = [
                f.encrypt(k.encode()).decode() if not k.startswith("gAAAA") else k
                for k in raw
            ]
        elif isinstance(raw, str) and not raw.startswith("gAAAA"):
            result["api_key"] = f.encrypt(raw.encode()).decode()
    return result


def _decrypt_value(value: Any) -> Any:
    """Decrypt api_key fields inside a provider config dict."""
    if not isinstance(value, dict):
        return value
    result = dict(value)
    if "api_key" in result and result["api_key"]:
        f = _get_fernet()
        raw = result["api_key"]
        try:
            if isinstance(raw, list):
                result["api_key"] = [
                    f.decrypt(k.encode()).decode() if k.startswith("gAAAA") else k
                    for k in raw
                ]
            elif isinstance(raw, str) and raw.startswith("gAAAA"):
                result["api_key"] = f.decrypt(raw.encode()).decode()
        except Exception:
            pass  # If decryption fails, return as-is
    return result


def _mask_value(value: Any) -> Any:
    """Mask api_key fields for safe API responses."""
    if not isinstance(value, dict):
        return value
    result = dict(value)
    if "api_key" in result and result["api_key"]:
        raw = result["api_key"]
        if isinstance(raw, list):
            result["api_key"] = ["***MASKED***" for _ in raw]
            result["api_key_count"] = len(raw)
        elif isinstance(raw, str):
            result["api_key"] = "***MASKED***"
            result["api_key_count"] = 1
    return result


class GlobalSettingsClient(BaseDBClient):

    async def get(self, key: str) -> Optional[GlobalSettingsModel]:
        async with self.async_session() as session:
            result = await session.execute(
                select(GlobalSettingsModel).where(GlobalSettingsModel.key == key)
            )
            return result.scalars().first()

    async def get_value(self, key: str, default: Any = None) -> Any:
        row = await self.get(key)
        if row is None:
            return default
        return row.value

    async def get_provider_key_decrypted(self, key: str) -> Optional[dict]:
        """Get a provider config with decrypted api_key."""
        row = await self.get(key)
        if row is None:
            return None
        return _decrypt_value(row.value)

    async def set(self, key: str, value: Any, updated_by: Optional[int] = None) -> GlobalSettingsModel:
        async with self.async_session() as session:
            result = await session.execute(
                select(GlobalSettingsModel).where(GlobalSettingsModel.key == key)
            )
            row = result.scalars().first()
            if row:
                row.value = value
                row.updated_by = updated_by
            else:
                row = GlobalSettingsModel(key=key, value=value, updated_by=updated_by)
                session.add(row)
            try:
                await session.commit()
                await session.refresh(row)
            except Exception as e:
                await session.rollback()
                raise e
            return row

    async def set_provider_key(self, key: str, value: dict, updated_by: Optional[int] = None) -> GlobalSettingsModel:
        """Save a provider config with encrypted api_key."""
        encrypted = _encrypt_value(value)
        return await self.set(key, encrypted, updated_by)

    async def delete(self, key: str) -> bool:
        async with self.async_session() as session:
            result = await session.execute(
                select(GlobalSettingsModel).where(GlobalSettingsModel.key == key)
            )
            row = result.scalars().first()
            if not row:
                return False
            await session.delete(row)
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e
            return True

    async def get_all_by_prefix(self, prefix: str) -> list[GlobalSettingsModel]:
        async with self.async_session() as session:
            result = await session.execute(
                select(GlobalSettingsModel).where(
                    GlobalSettingsModel.key.like(f"{prefix}%")
                )
            )
            return result.scalars().all()

    async def get_all_provider_keys_masked(self) -> dict[str, dict]:
        """
        Return all provider_key:* entries with api_key masked.
        Used by admin list endpoint.
        """
        rows = await self.get_all_by_prefix("provider_key:")
        result = {}
        for row in rows:
            provider = row.key.removeprefix("provider_key:")
            result[provider] = _mask_value(row.value)
        return result

    async def get_all_provider_policies(self) -> dict[str, dict]:
        """Return all provider_policy:* entries."""
        rows = await self.get_all_by_prefix("provider_policy:")
        result = {}
        for row in rows:
            provider = row.key.removeprefix("provider_policy:")
            result[provider] = row.value
        return result
