"""TTS Provider 基类"""

from abc import ABC, abstractmethod
from typing import Optional


class TTSProvider(ABC):
    """TTS 提供者抽象基类

    所有 TTS 后端实现都需要继承此类并实现 synthesize 方法。

    返回值约定:
        - 成功: 返回 base64 编码的 WAV 音频字符串
        - 失败: 返回 None
    """

    @abstractmethod
    def synthesize(self, text: str, language: str = "zh") -> Optional[str]:
        """将文本合成为语音

        Args:
            text: 要合成的文本
            language: 语言代码，"zh" 或 "en"

        Returns:
            base64 编码的 WAV 音频数据，失败返回 None
        """
        pass

    @property
    def name(self) -> str:
        """提供者名称"""
        return self.__class__.__name__
