"""
築未科技大腦 - 影片學習（免費本地）
影片 → 抽出音軌 → 語音轉文字 → 存入知識庫
需：ffmpeg + 二擇一：faster-whisper 或 vosk
"""
import json
import subprocess
import tempfile
import wave
from pathlib import Path

BASE = Path(__file__).parent
VOSK_MODEL_DIR = BASE / "vosk-model-small-cn"  # 需下載：https://alphacephei.com/vosk/models


def _extract_audio(video_path: str) -> str | None:
    """用 ffmpeg 抽出音軌為 wav（16kHz 單聲道）"""
    try:
        kw = {"suffix": ".wav", "delete": False}
        try:
            from brain_data_config import TEMP_DIR
            kw["dir"] = str(TEMP_DIR)
        except ImportError:
            pass
        out = tempfile.NamedTemporaryFile(**kw)
        out.close()
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", out.name],
            capture_output=True,
            timeout=600,
            check=True,
        )
        return out.name
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _transcribe_faster_whisper(audio_path: str) -> str:
    """用 faster-whisper 轉文字（需 pip install faster-whisper）"""
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, language="zh", beam_size=1)
    return " ".join(s.text.strip() for s in segments if s.text.strip())


def _transcribe_vosk(audio_path: str) -> str:
    """用 Vosk 轉文字（需 pip install vosk + 下載中文模型）"""
    from vosk import Model, KaldiRecognizer
    if not VOSK_MODEL_DIR.exists():
        raise RuntimeError(
            "請下載 Vosk 中文模型：\n"
            "1. 前往 https://alphacephei.com/vosk/models\n"
            "2. 下載 model-small-cn-0.22，解壓到專案資料夾\n"
            "3. 資料夾名稱改為 vosk-model-small-cn"
        )
    model = Model(str(VOSK_MODEL_DIR))
    rec = KaldiRecognizer(model, 16000)
    rec.SetWords(True)
    with wave.open(audio_path, "rb") as wf:
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            rec.AcceptWaveform(data)
    result = json.loads(rec.FinalResult())
    return (result.get("text") or "").strip()


def _transcribe(audio_path: str) -> str:
    """依序嘗試 faster-whisper → vosk"""
    try:
        return _transcribe_faster_whisper(audio_path)
    except ImportError:
        pass
    try:
        return _transcribe_vosk(audio_path)
    except ImportError:
        raise RuntimeError(
            "請安裝任一套件：\n"
            "• pip install vosk（較易安裝，另需下載模型）\n"
            "• 或 pip install faster-whisper（需 Rust + 編譯 av）"
        )


def ingest_video(video_path: str) -> tuple[bool, str]:
    """
    將影片轉成文字並存入知識庫。
    回傳 (成功, 訊息)
    """
    from brain_knowledge import add_transcript

    path = Path(video_path)
    if not path.exists():
        return False, f"找不到檔案: {video_path}"

    # 檢查 ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
    except FileNotFoundError:
        return False, "請先安裝 ffmpeg 並加入 PATH。下載: https://ffmpeg.org"

    # 抽出音軌
    audio_path = _extract_audio(str(path))
    if not audio_path:
        return False, "無法抽出音軌，請確認 ffmpeg 已正確安裝"

    try:
        text = _transcribe(audio_path)
        Path(audio_path).unlink(missing_ok=True)
    except RuntimeError as e:
        Path(audio_path).unlink(missing_ok=True)
        return False, str(e)

    if not text.strip():
        return False, "未辨識到語音內容"

    add_transcript(text, source_name=path.name)
    return True, f"已學習影片「{path.name}」，約 {len(text)} 字"


def can_learn_video() -> tuple[bool, str]:
    """檢查是否能進行影片學習"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=3)
    except FileNotFoundError:
        return False, "需安裝 ffmpeg"
    try:
        from faster_whisper import WhisperModel
        return True, "就緒 (faster-whisper)"
    except ImportError:
        pass
    try:
        from vosk import Model
        if VOSK_MODEL_DIR.exists():
            return True, "就緒 (vosk)"
        return False, "需下載 Vosk 中文模型（見說明）"
    except ImportError:
        return False, "需安裝: pip install vosk"
