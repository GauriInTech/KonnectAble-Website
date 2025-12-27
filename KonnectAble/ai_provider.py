from typing import Dict, Optional
import os
from django.conf import settings


def is_claude_haiku_enabled() -> bool:
    return getattr(settings, 'ENABLE_CLAUDE_HAIKU_4_5', False)


def get_claude_model_name() -> Optional[str]:
    return "claude-haiku-4.5" if is_claude_haiku_enabled() else None


def get_anthropic_api_key() -> str:
    return getattr(settings, 'ANTHROPIC_API_KEY', os.getenv('ANTHROPIC_API_KEY', ''))


def describe_enablement() -> Dict[str, object]:
    return {
        "enabled": is_claude_haiku_enabled(),
        "model": get_claude_model_name(),
        "note": "Set ENABLE_CLAUDE_HAIKU_4_5=true and provide ANTHROPIC_API_KEY to enable."
    }
