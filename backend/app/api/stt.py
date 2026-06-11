"""语音转文字（STT）端点——本地 Whisper 离线识别"""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stt", tags=["stt"])


class STTResponse(BaseModel):
    success: bool
    text: str = ""
    engine: str = ""
    message: str = ""


# ---------- 识别引擎 ----------

def _whisper_py_available() -> bool:
    """检测 openai-whisper Python 包是否安装"""
    try:
        import whisper
        return True
    except ImportError:
        return False


def _whisper_cpp_available() -> bool:
    """检测 whisper.cpp 命令行工具是否可用"""
    try:
        result = subprocess.run(
            ["whisper", "--help"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # 检查常见路径
    for path in ["/usr/local/bin/whisper", "/usr/bin/whisper",
                 os.path.expanduser("~/whisper.cpp/main")]:
        if os.path.isfile(path):
            return True
    return False


async def transcribe_with_whisper_py(audio_path: str) -> Optional[str]:
    """使用 openai-whisper Python 包识别"""
    try:
        import whisper
        model = whisper.load_model("tiny")  # tiny 最快，约 1GB
        result = model.transcribe(audio_path, language="zh")
        return result["text"].strip()
    except Exception as e:
        logger.error(f"Whisper Python 识别失败: {e}")
        return None


async def transcribe_with_whisper_cpp(audio_path: str) -> Optional[str]:
    """使用 whisper.cpp 命令行工具识别"""
    try:
        result = subprocess.run(
            ["whisper", audio_path, "--language", "zh",
             "--output-txt", "--output-dir", tempfile.gettempdir()],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            txt_path = Path(audio_path).with_suffix(".txt")
            if txt_path.exists():
                return txt_path.read_text(encoding="utf-8").strip()
            # 也可能输出到 stdout
            return result.stdout.strip()
        return None
    except Exception as e:
        logger.error(f"Whisper.cpp 识别失败: {e}")
        return None


# ---------- 音频预处理 ----------

def _ensure_wav(input_path: str) -> str:
    """确保音频格式为 WAV 16kHz 16bit mono（Whisper 最佳输入）"""
    output_path = input_path + "_converted.wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_path,
             "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
             output_path],
            capture_output=True, text=True, timeout=30,
        )
        return output_path if os.path.isfile(output_path) else input_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.warning("ffmpeg 不可用，使用原始音频格式")
        return input_path


# ---------- 路由 ----------

@router.post("/", response_model=STTResponse)
async def speech_to_text(file: UploadFile = File(...)):
    """语音转文字

    接受音频文件（WAV/MP3/Opus/WebM），返回识别文本。
    优先使用 openai-whisper Python 包，其次 whisper.cpp。
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供音频文件")

    # 保存上传的音频到临时文件
    suffix = Path(file.filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 1. 尝试 Whisper Python 包
        if _whisper_py_available():
            logger.info(f"使用 Whisper Python 识别: {file.filename}")
            text = await transcribe_with_whisper_py(tmp_path)
            if text:
                return STTResponse(
                    success=True, text=text,
                    engine="whisper-py", message="识别成功",
                )

        # 2. 尝试 Whisper.cpp
        if _whisper_cpp_available():
            logger.info(f"使用 Whisper.cpp 识别: {file.filename}")
            # 先转成 WAV
            wav_path = _ensure_wav(tmp_path)
            text = await transcribe_with_whisper_cpp(wav_path)
            if text:
                return STTResponse(
                    success=True, text=text,
                    engine="whisper-cpp", message="识别成功",
                )
            if wav_path != tmp_path and os.path.isfile(wav_path):
                os.unlink(wav_path)

        # 3. 没有可用引擎
        engines = []
        if not _whisper_py_available():
            engines.append("openai-whisper (pip install openai-whisper)")
        if not _whisper_cpp_available():
            engines.append("whisper.cpp")
        return STTResponse(
            success=False,
            text="",
            engine="none",
            message="没有可用的语音识别引擎。请安装: " + " 或 ".join(engines),
        )

    finally:
        os.unlink(tmp_path)
