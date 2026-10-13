"""语音服务：基于 Vosk 的本地离线语音识别（STT）

Vosk 是开源语音识别工具包，完全离线运行，无需 API Key。
支持中文，需要下载中文语言模型。

TTS（文字转语音）在前端使用浏览器 speechSynthesis 实现，无需后端。
"""

import os
import sys
import json
import wave
import tempfile
import struct
from typing import Optional

# 添加 vosk 库路径
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOSK_LIB_PATH = os.path.join(BACKEND_ROOT, "libs")
if VOSK_LIB_PATH not in sys.path:
    sys.path.insert(0, VOSK_LIB_PATH)

# Vosk 模型路径（必须使用纯 ASCII 路径，Vosk C 库不支持中文路径）
# 默认指向本 backend 自带的 vosk_models 副本（随模块一起拷贝），可用环境变量 VOSK_MODEL_PATH 覆盖
VOSK_MODEL_PATH = os.environ.get(
    "VOSK_MODEL_PATH",
    os.path.join(BACKEND_ROOT, "vosk_models", "vosk-model-small-cn-0.22")
)


class VoiceService:
    """Vosk 本地语音识别服务（完全离线，无需 Key）"""

    _model = None  # 单例模型

    def __init__(self, api_key: str = "", secret_key: str = ""):
        self._model_loaded = False

    def _get_model(self):
        """获取 Vosk 模型（单例）"""
        if VoiceService._model is not None:
            return VoiceService._model

        if not os.path.exists(VOSK_MODEL_PATH):
            print(f"[语音] Vosk 模型未找到: {VOSK_MODEL_PATH}")
            print("[语音] 请运行 backend/download_vosk_model.py 下载模型")
            return None

        try:
            from vosk import Model
            VoiceService._model = Model(VOSK_MODEL_PATH)
            self._model_loaded = True
            print("[语音] Vosk 模型加载成功")
            return VoiceService._model
        except ImportError:
            print("[语音] Vosk 库未安装，请运行: pip install vosk")
            return None
        except Exception as e:
            print(f"[语音] Vosk 模型加载失败: {e}")
            return None

    @staticmethod
    def _resample_pcm(pcm_data: bytes, input_rate: int, output_rate: int) -> bytes:
        """纯 Python PCM 重采样（线性插值，int16 单声道）"""
        if input_rate == output_rate:
            return pcm_data

        import math
        src_samples = len(pcm_data) // 2
        ratio = output_rate / input_rate
        dst_samples = int(src_samples * ratio)

        src = [struct.unpack_from("<h", pcm_data, i * 2)[0] for i in range(src_samples)]
        dst = bytearray(dst_samples * 2)

        for i in range(dst_samples):
            src_idx = i / ratio
            idx0 = int(src_idx)
            idx1 = min(idx0 + 1, src_samples - 1)
            frac = src_idx - idx0
            val = src[idx0] * (1 - frac) + src[idx1] * frac
            val = max(-32768, min(32767, int(round(val))))
            struct.pack_into("<h", dst, i * 2, val)

        return bytes(dst)

    def stt(self, audio_data: bytes, format: str = "wav", rate: int = 16000, channel: int = 1) -> Optional[str]:
        """语音转文字（支持 WAV 格式）

        Args:
            audio_data: WAV 音频数据
            format: 音频格式（目前仅支持 wav）
            rate: 采样率（默认 16000）
            channel: 声道数（默认 1）

        Returns:
            识别出的文字，失败返回 None
        """
        model = self._get_model()
        if model is None:
            print("[语音] 模型未加载，无法识别")
            return None

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name

            wf = wave.open(tmp_path, "rb")
            nchannels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            duration = nframes / framerate if framerate > 0 else 0

            print(f"[语音] 收到音频: channels={nchannels}, width={sampwidth}, rate={framerate}, frames={nframes}, duration={duration:.2f}s, size={len(audio_data)}B")

            if nframes == 0 or duration < 0.3:
                print("[语音] 音频太短或为空，无法识别")
                wf.close()
                return None

            audio_frames = wf.readframes(nframes)
            wf.close()

            if nchannels != 1 or sampwidth != 2:
                print(f"[语音] 音频格式不匹配: channels={nchannels}, width={sampwidth}，需要单声道 16bit PCM")
                return None

            # 重采样到 16000Hz（如果需要）
            if framerate != 16000:
                print(f"[语音] 重采样: {framerate}Hz -> 16000Hz")
                audio_frames = self._resample_pcm(audio_frames, framerate, 16000)
                framerate = 16000

            from vosk import KaldiRecognizer
            rec = KaldiRecognizer(model, framerate)

            chunk_size = 4000
            offset = 0
            while offset < len(audio_frames):
                end = min(offset + chunk_size, len(audio_frames))
                data = audio_frames[offset:end]
                rec.AcceptWaveform(data)
                offset = end

            final_result = json.loads(rec.FinalResult())
            text = final_result.get("text", "")

            if text:
                print(f"[语音] 识别结果: {text}")
            else:
                print("[语音] 识别结果为空")

            return text if text else None

        except Exception as e:
            print(f"[语音] STT 错误: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def stt_from_file(self, file_path: str) -> Optional[str]:
        """从 WAV 文件识别语音"""
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "rb") as f:
                audio_data = f.read()
            return self.stt(audio_data)
        except Exception as e:
            print(f"[语音] 文件识别错误: {e}")
            return None

    def is_available(self) -> bool:
        """检查 Vosk 语音服务是否可用"""
        model = self._get_model()
        return model is not None

    def tts(self, text: str, per: int = 0, spd: int = 5, pit: int = 5, vol: int = 5) -> Optional[bytes]:
        """文字转语音（占位，实际在前端用浏览器 speechSynthesis 实现）"""
        return None
