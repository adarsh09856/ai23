from __future__ import annotations

import copy
from typing import Any

from loguru import logger

from api.db.global_settings_client import GlobalSettingsClient
from api.schemas.ai_model_configuration import EffectiveAIModelConfiguration
from api.services.configuration.registry import ServiceProviders


async def inject_admin_keys(
    config: EffectiveAIModelConfiguration,
) -> EffectiveAIModelConfiguration:
    """
    Inject admin-managed provider keys into configuration where the organization has none.
    This enables admin-key platform mode where admin enters all keys and users just pick models.
    """
    try:
        global_settings = GlobalSettingsClient()
        
        # Create a copy to avoid mutating the original
        injected_config = copy.deepcopy(config)
        
        # Inject keys for each service type
        if injected_config.llm and not _has_api_key(injected_config.llm):
            await _inject_admin_key_for_service(global_settings, injected_config.llm, "LLM")
        
        if injected_config.tts and not _has_api_key(injected_config.tts):
            await _inject_admin_key_for_service(global_settings, injected_config.tts, "TTS")
        
        if injected_config.stt and not _has_api_key(injected_config.stt):
            await _inject_admin_key_for_service(global_settings, injected_config.stt, "STT")
        
        if injected_config.embeddings and not _has_api_key(injected_config.embeddings):
            await _inject_admin_key_for_service(global_settings, injected_config.embeddings, "embeddings")
        
        if injected_config.realtime and not _has_api_key(injected_config.realtime):
            await _inject_admin_key_for_service(global_settings, injected_config.realtime, "realtime")
        
        return injected_config
        
    except Exception as e:
        logger.error(f"Failed to inject admin keys: {e}")
        # Return original config if injection fails
        return config


async def _inject_admin_key_for_service(
    global_settings: GlobalSettingsClient, 
    service: Any, 
    service_type: str
) -> None:
    """Inject admin key for a specific service if available."""
    provider = _get_provider(service)
    provider_config = await global_settings.get_provider_key_decrypted(f"provider_key:{provider}")
    
    if provider_config and provider_config.get("api_key"):
        api_key = provider_config["api_key"]
        # Handle both single keys and key arrays
        if isinstance(api_key, list) and api_key:
            api_key = api_key[0]  # Use first key if multiple
        
        if api_key:
            _inject_key_into_service(service, api_key)
            logger.debug(f"Injected admin key for {service_type} provider: {provider}")


def _has_api_key(service: Any) -> bool:
    """Check if a service already has an API key configured."""
    if hasattr(service, 'api_key') and service.api_key:
        return True
    if hasattr(service, 'get_all_api_keys'):
        keys = service.get_all_api_keys()
        return len(keys) > 0 and any(key for key in keys)
    return False


def _get_provider(service: Any) -> str:
    """Extract provider name from a service configuration."""
    if hasattr(service, 'provider'):
        provider = service.provider
        if isinstance(provider, str):
            return provider.lower()
        if hasattr(provider, 'value'):
            return provider.value.lower()
        return str(provider).lower()
    return 'unknown'


def _inject_key_into_service(service: Any, api_key: str) -> None:
    """Inject an API key into a service configuration."""
    if hasattr(service, 'api_key'):
        service.api_key = api_key
    elif hasattr(service, '__dict__'):
        # Fallback for dynamic attribute setting
        service.__dict__['api_key'] = api_key
