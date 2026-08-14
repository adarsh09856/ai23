"""
User-facing provider catalog endpoint.
Returns which providers/models are available (configured by admin).
Users use this to populate the model picker — no API keys involved.
"""
import random
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.db.global_settings_client import GlobalSettingsClient, _decrypt_value
from api.db.models import UserModel
from api.services.auth.depends import get_user

router = APIRouter(prefix="/user/providers", tags=["user-providers"])

global_settings = GlobalSettingsClient()


class AvailableModel(BaseModel):
    id: str
    name: str
    is_default: bool = False


class AvailableProvider(BaseModel):
    id: str
    name: str
    service_type: str
    models: list[AvailableModel]
    is_default: bool = False


class AvailableProvidersResponse(BaseModel):
    llm: list[AvailableProvider]
    tts: list[AvailableProvider]
    stt: list[AvailableProvider]
    embeddings: list[AvailableProvider]
    realtime: list[AvailableProvider]
    default_llm: Optional[str] = None
    default_tts: Optional[str] = None
    default_stt: Optional[str] = None


# Provider name lookup (same as PROVIDER_CATALOG in admin providers route)
PROVIDER_NAMES = {
    "openai": "OpenAI", "google": "Google Gemini", "xai": "Grok (xAI)",
    "groq": "Groq", "openrouter": "OpenRouter", "azure": "Azure OpenAI",
    "aws_bedrock": "AWS Bedrock", "huggingface": "HuggingFace",
    "elevenlabs": "ElevenLabs", "deepgram": "Deepgram", "cartesia": "Cartesia",
    "rime": "Rime", "lmnt": "LMNT", "sarvam": "Sarvam AI (India)",
    "smallest": "Smallest.ai (India)", "azure_speech": "Azure Speech",
    "assemblyai": "AssemblyAI", "gladia": "Gladia", "speaches": "Speaches",
    "openai_realtime": "OpenAI Realtime", "google_realtime": "Google Realtime",
    "google_vertex": "Google Vertex AI", "google_vertex_realtime": "Google Vertex Realtime",
    "azure_realtime": "Azure Realtime",
}

SERVICE_TYPES = ["llm", "tts", "stt", "embeddings", "realtime"]


@router.get("/available", response_model=AvailableProvidersResponse)
async def get_available_providers(user: UserModel = Depends(get_user)):
    """
    Get all providers/models available to users.
    Only returns providers that admin has configured with a valid key and enabled.
    """
    default_llm = await global_settings.get_value("platform:default_llm")
    default_tts = await global_settings.get_value("platform:default_tts")
    default_stt = await global_settings.get_value("platform:default_stt")

    result = {st: [] for st in SERVICE_TYPES}

    for st in SERVICE_TYPES:
        # Get all provider_key entries
        key_rows = await global_settings.get_all_by_prefix("provider_key:")
        policy_rows = await global_settings.get_all_by_prefix(f"provider_policy:{st}:")

        policies = {}
        for row in policy_rows:
            pid = row.key.removeprefix(f"provider_policy:{st}:")
            policies[pid] = row.value

        for row in key_rows:
            provider_id = row.key.removeprefix("provider_key:")
            config = row.value

            # Only show enabled providers
            if not config.get("enabled", False):
                continue

            policy = policies.get(provider_id, {})
            # If hidden for this service type, skip
            if policy.get("hidden", False):
                continue

            # Get models list from policy, or empty (provider needs policy set)
            enabled_models = policy.get("enabled_models", [])
            if not enabled_models:
                continue  # Provider key exists but no models configured for this service type

            default_model = policy.get("default_model")
            models = [
                AvailableModel(
                    id=m,
                    name=m,
                    is_default=(m == default_model),
                )
                for m in enabled_models
            ]

            if not models:
                continue

            result[st].append(AvailableProvider(
                id=provider_id,
                name=PROVIDER_NAMES.get(provider_id, provider_id.replace("_", " ").title()),
                service_type=st,
                models=models,
                is_default=(
                    (st == "llm" and provider_id == default_llm) or
                    (st == "tts" and provider_id == default_tts) or
                    (st == "stt" and provider_id == default_stt)
                ),
            ))

    return AvailableProvidersResponse(
        llm=result["llm"],
        tts=result["tts"],
        stt=result["stt"],
        embeddings=result["embeddings"],
        realtime=result["realtime"],
        default_llm=default_llm,
        default_tts=default_tts,
        default_stt=default_stt,
    )
