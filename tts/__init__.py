"""TTS Provider 抽象层

提供可插拔的 TTS 接口，支持不同 TTS 后端实现。

使用方式:
    from tts import create_tts_provider
    provider = create_tts_provider()
    audio_b64 = provider.synthesize("你好", language="zh")
"""

from tts.base import TTSProvider
from tts.mimo import MiMoTTS

# 已注册的 TTS 提供者
_PROVIDERS = {
    "mimo": MiMoTTS,
}


def create_tts_provider(name: str = None) -> TTSProvider:
    """创建 TTS 提供者实例

    Args:
        name: 提供者名称，为 None 时从配置读取

    Returns:
        TTSProvider 实例
    """
    import api_config

    if name is None:
        name = api_config.TTS_PROVIDER

    provider_cls = _PROVIDERS.get(name)
    if provider_cls is None:
        raise ValueError(f"未知的 TTS 提供者: {name}，可用: {list(_PROVIDERS.keys())}")

    return provider_cls()


def register_tts_provider(name: str, cls: type):
    """注册自定义 TTS 提供者"""
    _PROVIDERS[name] = cls


__all__ = ["TTSProvider", "MiMoTTS", "create_tts_provider", "register_tts_provider"]
