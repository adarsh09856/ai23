"""
Admin Provider Keys Routes
Admin (admin@admin.com) manages platform AI provider credentials.
Users never see these keys — they only pick a model in the UI.
"""
import random
from typing import Any, Optional, List, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.db import db_client
from api.db.global_settings_client import GlobalSettingsClient, _mask_value, _decrypt_value, _encrypt_value
from api.db.models import UserModel
from api.services.auth.depends import get_superuser

router = APIRouter(prefix="/superuser/providers", tags=["admin-providers"])

global_settings = GlobalSettingsClient()

# All providers supported by Dograh registry, grouped by service type
PROVIDER_CATALOG = {
    "llm": [
        {"id": "openai", "name": "OpenAI", "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "o1", "o1-mini", "o3-mini"]},
        {"id": "google", "name": "Google Gemini", "models": ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"]},
        {"id": "xai", "name": "Grok (xAI)", "models": ["grok-2", "grok-2-mini", "grok-beta"]},
        {"id": "groq", "name": "Groq", "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]},
        {"id": "openrouter", "name": "OpenRouter", "models": ["meta-llama/llama-3.3-70b-instruct", "anthropic/claude-3.5-sonnet", "google/gemini-2.0-flash-001"]},
        {"id": "azure", "name": "Azure OpenAI", "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]},
        {"id": "aws_bedrock", "name": "AWS Bedrock", "models": ["anthropic.claude-3-5-sonnet-20241022-v2:0", "anthropic.claude-3-haiku-20240307-v1:0", "amazon.nova-pro-v1:0"]},
        {"id": "huggingface", "name": "HuggingFace", "models": ["meta-llama/Llama-3.1-70B-Instruct", "Qwen/Qwen2.5-72B-Instruct"]},
    ],
    "tts": [
        {"id": "elevenlabs", "name": "ElevenLabs", "models": ["eleven_turbo_v2_5", "eleven_multilingual_v2", "eleven_flash_v2_5"]},
        {"id": "deepgram", "name": "Deepgram", "models": ["aura-2-thalia-en", "aura-2-luna-en", "aura-2-stella-en", "aura-2-athena-en"]},
        {"id": "cartesia", "name": "Cartesia", "models": ["sonic-2", "sonic-turbo", "sonic-english"]},
        {"id": "rime", "name": "Rime", "models": ["mistv2", "arcana"]},
        {"id": "lmnt", "name": "LMNT", "models": ["blizzard", "lily", "ryan"]},
        {"id": "sarvam", "name": "Sarvam AI (India)", "models": ["bulbul:v2", "bulbul:v1"]},
        {"id": "smallest", "name": "Smallest.ai (India)", "models": ["lightning", "lightning-large"]},
        {"id": "google", "name": "Google TTS", "models": ["en-US-Neural2-A", "en-US-Wavenet-A", "hi-IN-Neural2-A"]},
        {"id": "azure_speech", "name": "Azure Speech", "models": ["en-US-JennyNeural", "en-US-GuyNeural", "hi-IN-SwaraNeural"]},
    ],
    "stt": [
        {"id": "deepgram", "name": "Deepgram", "models": ["nova-3", "nova-2", "nova-2-general", "nova-2-meeting"]},
        {"id": "assemblyai", "name": "AssemblyAI", "models": ["nano", "best"]},
        {"id": "gladia", "name": "Gladia", "models": ["solaria-1", "fast"]},
        {"id": "google", "name": "Google STT", "models": ["latest_long", "latest_short", "chirp_2"]},
        {"id": "sarvam", "name": "Sarvam AI (India)", "models": ["saarika:v2", "saarika:v1"]},
        {"id": "speaches", "name": "Speaches (Self-hosted)", "models": ["Systran/faster-whisper-large-v3", "Systran/faster-whisper-medium"]},
    ],
    "embeddings": [
        {"id": "openai", "name": "OpenAI", "models": ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"]},
        {"id": "google", "name": "Google", "models": ["text-embedding-004", "textembedding-gecko@003"]},
        {"id": "azure", "name": "Azure OpenAI", "models": ["text-embedding-3-small", "text-embedding-3-large"]},
    ],
    "realtime": [
        {"id": "openai_realtime", "name": "OpenAI Realtime", "models": ["gpt-4o-realtime-preview", "gpt-4o-mini-realtime-preview"]},
        {"id": "google_realtime", "name": "Google Realtime (Multimodal Live)", "models": ["gemini-2.0-flash-exp"]},
    ],
}


class ProviderKeyRequest(BaseModel):
    """Request to save a provider API key."""
    api_key: str | list[str]
    enabled: bool = True
    # Optional extra fields for specific providers
    extra: dict[str, Any] = {}


class ProviderKeyResponse(BaseModel):
    provider_id: str
    provider_name: str
    enabled: bool
    has_key: bool
    api_key_masked: str | list[str] | None = None
    api_key_count: int = 0
    extra: dict[str, Any] = {}


class ProviderPolicyRequest(BaseModel):
    enabled_models: list[str]
    default_model: Optional[str] = None
    hidden: bool = False
    premium_only: bool = False


class ProviderPolicyResponse(BaseModel):
    provider_id: str
    service_type: str
    enabled_models: list[str]
    default_model: Optional[str] = None
    hidden: bool = False
    premium_only: bool = False


class ProviderCatalogEntry(BaseModel):
    id: str
    name: str
    models: list[str]
    has_key: bool = False
    enabled: bool = False
    api_key_count: int = 0
    policy: Optional[ProviderPolicyResponse] = None


class ProviderCatalogResponse(BaseModel):
    llm: list[ProviderCatalogEntry]
    tts: list[ProviderCatalogEntry]
    stt: list[ProviderCatalogEntry]
    embeddings: list[ProviderCatalogEntry]
    realtime: list[ProviderCatalogEntry]


@router.get("/catalog", response_model=ProviderCatalogResponse)
async def get_provider_catalog(user: UserModel = Depends(get_superuser)):
    """Get all providers with their current key/policy status."""
    all_keys = await global_settings.get_all_provider_keys_masked()
    all_policies = await global_settings.get_all_provider_policies()

    def build_entries(service_type: str) -> list[ProviderCatalogEntry]:
        entries = []
        for p in PROVIDER_CATALOG.get(service_type, []):
            key_data = all_keys.get(p["id"], {})
            policy_data = all_policies.get(f"{service_type}:{p['id']}", {})
            has_key = bool(key_data.get("api_key"))
            enabled = key_data.get("enabled", False) if has_key else False
            api_key_count = key_data.get("api_key_count", 1 if has_key else 0)

            policy = None
            if policy_data:
                policy = ProviderPolicyResponse(
                    provider_id=p["id"],
                    service_type=service_type,
                    enabled_models=policy_data.get("enabled_models", p["models"]),
                    default_model=policy_data.get("default_model"),
                    hidden=policy_data.get("hidden", False),
                    premium_only=policy_data.get("premium_only", False),
                )

            entries.append(ProviderCatalogEntry(
                id=p["id"],
                name=p["name"],
                models=p["models"],
                has_key=has_key,
                enabled=enabled,
                api_key_count=api_key_count,
                policy=policy,
            ))
        return entries

    return ProviderCatalogResponse(
        llm=build_entries("llm"),
        tts=build_entries("tts"),
        stt=build_entries("stt"),
        embeddings=build_entries("embeddings"),
        realtime=build_entries("realtime"),
    )


@router.put("/{provider_id}/key")
async def save_provider_key(
    provider_id: str,
    request: ProviderKeyRequest,
    user: UserModel = Depends(get_superuser),
):
    """
    Save API key(s) for a provider. Admin only.
    Keys are encrypted at rest. Never returned in plain text.
    Multiple keys enable automatic rotation (random.choice per call).
    """
    # Normalize api_key to list
    keys = request.api_key if isinstance(request.api_key, list) else [request.api_key]
    keys = [k.strip() for k in keys if k.strip()]
    if not keys:
        raise HTTPException(status_code=400, detail="At least one API key is required")

    value = {
        "api_key": keys if len(keys) > 1 else keys[0],
        "enabled": request.enabled,
        **request.extra,
    }

    await global_settings.set_provider_key(
        f"provider_key:{provider_id}",
        value,
        updated_by=user.id,
    )
    return {"message": f"Provider key for {provider_id} saved successfully"}


@router.delete("/{provider_id}/key")
async def delete_provider_key(
    provider_id: str,
    user: UserModel = Depends(get_superuser),
):
    """Remove API key for a provider."""
    deleted = await global_settings.delete(f"provider_key:{provider_id}")
    if not deleted:
        raise HTTPException(status_code=404, detail="Provider key not found")
    return {"message": f"Provider key for {provider_id} deleted"}


@router.patch("/{provider_id}/toggle")
async def toggle_provider(
    provider_id: str,
    enabled: bool,
    user: UserModel = Depends(get_superuser),
):
    """Enable or disable a provider without changing its key."""
    existing = await global_settings.get_provider_key_decrypted(f"provider_key:{provider_id}")
    if not existing:
        raise HTTPException(status_code=404, detail="Provider not configured. Add a key first.")
    existing["enabled"] = enabled
    await global_settings.set_provider_key(f"provider_key:{provider_id}", existing, updated_by=user.id)
    return {"message": f"Provider {provider_id} {'enabled' if enabled else 'disabled'}"}


@router.put("/{service_type}/{provider_id}/policy")
async def save_provider_policy(
    service_type: str,
    provider_id: str,
    request: ProviderPolicyRequest,
    user: UserModel = Depends(get_superuser),
):
    """Set model visibility policy for a provider."""
    if service_type not in PROVIDER_CATALOG:
        raise HTTPException(status_code=400, detail=f"Unknown service type: {service_type}")
    await global_settings.set(
        f"provider_policy:{service_type}:{provider_id}",
        {
            "enabled_models": request.enabled_models,
            "default_model": request.default_model,
            "hidden": request.hidden,
            "premium_only": request.premium_only,
        },
        updated_by=user.id,
    )
    return {"message": "Policy saved"}


@router.get("/defaults")
async def get_platform_defaults(user: UserModel = Depends(get_superuser)):
    """Get current platform default provider selections."""
    llm = await global_settings.get_value("platform:default_llm", None)
    tts = await global_settings.get_value("platform:default_tts", None)
    stt = await global_settings.get_value("platform:default_stt", None)
    return {"default_llm": llm, "default_tts": tts, "default_stt": stt}


@router.put("/defaults")
async def set_platform_defaults(
    default_llm: Optional[str] = None,
    default_tts: Optional[str] = None,
    default_stt: Optional[str] = None,
    user: UserModel = Depends(get_superuser),
):
    """Set platform default providers."""
    if default_llm:
        await global_settings.set("platform:default_llm", default_llm, updated_by=user.id)
    if default_tts:
        await global_settings.set("platform:default_tts", default_tts, updated_by=user.id)
    if default_stt:
        await global_settings.set("platform:default_stt", default_stt, updated_by=user.id)
    return {"message": "Defaults updated"}
