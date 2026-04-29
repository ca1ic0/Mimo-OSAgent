"""MiMo TTS 实现

基于小米 MiMo API 的 TTS 提供者。
"""

from typing import Optional

import requests

import api_config
from tts.base import TTSProvider


class MiMoTTS(TTSProvider):
    """小米 MiMo TTS 提供者"""

    # 不同语言的风格提示词
    STYLE_PROMPTS = {
        "zh": "用自然、亲切、略带情绪的语气说话，像一个靠谱的AI助手",
        "en": "Speak naturally, warmly, and with a friendly tone, like a reliable AI assistant.",
    }

    def synthesize(self, text: str, language: str = "zh") -> Optional[str]:
        style_prompt = self.STYLE_PROMPTS.get(language, self.STYLE_PROMPTS["zh"])

        payload = {
            "model": api_config.TTS_MODEL,
            "messages": [
                {"role": "user", "content": style_prompt},
                {"role": "assistant", "content": text},
            ],
            "audio": {"format": "wav", "voice": api_config.TTS_VOICE},
        }

        try:
            resp = requests.post(
                api_config.TTS_ENDPOINT,
                headers=api_config.get_headers(),
                json=payload,
                timeout=15,
            )
            if resp.status_code != 200:
                return None
            audio_data = resp.json().get("choices", [{}])[0].get("message", {}).get("audio", {})
            return audio_data.get("data") if audio_data else None
        except Exception:
            return None
