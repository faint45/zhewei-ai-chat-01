"""
虛擬人物 MV 製作服務整合模組
整合 LivePortrait + Wav2Lip + ComfyUI + Jarvis 系統
"""

import os
import json
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

# 專案路徑
PROJECT_ROOT = Path(__file__).parent.parent
MV_PROJECTS_DIR = PROJECT_ROOT / "mv_projects"
LIVEPORTRAIT_DIR = PROJECT_ROOT / "LivePortrait"
WAV2LIP_DIR = PROJECT_ROOT / "Wav2Lip"
COMFYUI_DIR = PROJECT_ROOT / "ComfyUI"

@dataclass
class MVProject:
    """MV 專案資料結構"""
    name: str
    character_path: str
    audio_path: str
    driving_video_path: Optional[str] = None
    status: str = "pending"
    progress: int = 0
    output_path: Optional[str] = None
    created_at: Optional[str] = None

class MVService:
    """虛擬人物 MV 製作服務"""
    
    def __init__(self):
        self.projects = {}
        self.venv_path = PROJECT_ROOT / "Jarvis_Training" / ".venv312"
    
    def create_project(self, name: str, character_path: str, audio_path: str) -> Dict[str, Any]:
        """建立 MV 專案"""
        project_dir = MV_PROJECTS_DIR / name
        
        # 建立目錄結構
        for subdir in ["01_character", "02_backgrounds", "03_liveportrait", "04_wav2lip", "05_final"]:
            (project_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        # 複製角色圖片
        import shutil
        char_dest = project_dir / "01_character" / Path(character_path).name
        shutil.copy(character_path, char_dest)
        
        # 複製音樂
        audio_dest = project_dir / "05_final" / Path(audio_path).name
        shutil.copy(audio_path, audio_dest)
        
        # 建立專案資訊
        project_info = {
            "name": name,
            "character_path": str(char_dest),
            "audio_path": str(audio_dest),
            "status": "created",
            "progress": 0,
            "created_at": str(Path(__file__).stat().st_mtime) if os.path.exists(str(Path(__file__))) else None
        }
        
        # 儲存專案資訊
        info_file = project_dir / "project.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)
        
        self.projects[name] = project_info
        return project_info
    
    def generate_character(self, prompt: str, negative_prompt: str = None, width: int = 512, height: int = 512) -> Dict[str, Any]:
        """使用 ComfyUI 生成角色圖片"""
        # 這裡需要調用 ComfyUI API
        # 暫時返回指令讓用戶手動執行
        return {
            "status": "ready",
            "message": "請啟動 ComfyUI 並載入 workflows/mv_background.json",
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "settings": {
                "width": width,
                "height": height,
                "steps": 25,
                "cfg_scale": 7
            },
            "output_path": str(MV_PROJECTS_DIR / "demo_idol" / "01_character" / "character.png")
        }
    
    def run_liveportrait(self, project_name: str, driving_video: str = None, auto_run: bool = False) -> Dict[str, Any]:
        """執行 LivePortrait"""
        project = self.projects.get(project_name)
        if not project:
            return {"error": f"專案 {project_name} 不存在"}

        project_dir = MV_PROJECTS_DIR / project_name

        # 如果沒有指定驅動影片，使用預設路徑
        if driving_video is None:
            driving_video = project_dir / "03_liveportrait" / "driving.mp4"

        source = project["character_path"]
        output = str(project_dir / "03_liveportrait" / "character_animated.mp4")

        # 構建命令
        cmd = [
            str(self.venv_path / "Scripts" / "python.exe"),
            "-m", "LivePortrait",
            "--source", source,
            "--driving", str(driving_video),
            "--output", output
        ]

        if auto_run:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
                return {
                    "status": "completed",
                    "command": " ".join(cmd),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "output": output if os.path.exists(output) else None
                }
            except subprocess.TimeoutExpired:
                return {"status": "timeout", "error": "執行超時"}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        return {
            "status": "ready_to_run",
            "command": " ".join(cmd),
            "project": project_name,
            "input": {"character": source, "driving": str(driving_video)},
            "output": output
        }
    
    def run_wav2lip(self, project_name: str, auto_run: bool = False) -> Dict[str, Any]:
        """執行 Wav2Lip 對口型"""
        project = self.projects.get(project_name)
        if not project:
            return {"error": f"專案 {project_name} 不存在"}

        project_dir = MV_PROJECTS_DIR / project_name
        animated_video = project_dir / "03_liveportrait" / "character_animated.mp4"
        audio_wav = project_dir / "04_wav2lip" / "audio.wav"
        output = str(project_dir / "04_wav2lip" / "character_lipsync.mp4")

        # 構建命令
        cmd = [
            str(self.venv_path / "Scripts" / "python.exe"),
            "-m", "Wav2Lip",
            "--checkpoint_path", str(WAV2LIP_DIR / "checkpoints" / "wav2lip_gan.pth"),
            "--face", str(animated_video),
            "--audio", str(audio_wav),
            "--outfile", output
        ]

        if auto_run:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
                return {
                    "status": "completed",
                    "command": " ".join(cmd),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "output": output if os.path.exists(output) else None
                }
            except subprocess.TimeoutExpired:
                return {"status": "timeout", "error": "執行超時"}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        return {
            "status": "ready_to_run",
            "command": " ".join(cmd),
            "project": project_name,
            "input": {"video": str(animated_video), "audio": str(audio_wav)},
            "output": output
        }
    
    def run_ffmpeg_composite(self, project_name: str, auto_run: bool = False) -> Dict[str, Any]:
        """執行 FFmpeg 合成最終 MV"""
        project = self.projects.get(project_name)
        if not project:
            return {"error": f"專案 {project_name} 不存在"}

        project_dir = MV_PROJECTS_DIR / project_name
        background = project_dir / "02_backgrounds" / "background.mp4"
        character = project_dir / "04_wav2lip" / "character_lipsync.mp4"
        output = str(project_dir / "05_final" / "mv_final.mp4")

        # 構建 FFmpeg 命令
        cmd = [
            "ffmpeg", "-i", str(background), "-i", str(character),
            "-filter_complex", "[0:v][1:v]overlay=(W-w)/2:(H-h)/2:format=yuv420p",
            "-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-c:a", "copy", "-y", output
        ]

        if auto_run:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
                return {
                    "status": "completed",
                    "command": " ".join(cmd),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "output": output if os.path.exists(output) else None
                }
            except subprocess.TimeoutExpired:
                return {"status": "timeout", "error": "執行超時"}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        return {
            "status": "ready_to_run",
            "command": " ".join(cmd),
            "project": project_name,
            "input": {"background": str(background), "character": str(character)},
            "output": output
        }

    def run_full_pipeline(self, project_name: str) -> Dict[str, Any]:
        """執行完整 MV 製作流程"""
        project = self.projects.get(project_name)
        if not project:
            return {"error": f"專案 {project_name} 不存在"}

        results = {"project": project_name, "steps": []}

        # Step 1: LivePortrait
        lp_result = self.run_liveportrait(project_name, auto_run=True)
        results["steps"].append({"step": "liveportrait", **lp_result})
        if lp_result.get("status") != "completed":
            return {"status": "failed", "error": "LivePortrait 失敗", **results}

        # Step 2: Wav2Lip
        wl_result = self.run_wav2lip(project_name, auto_run=True)
        results["steps"].append({"step": "wav2lip", **wl_result})
        if wl_result.get("status") != "completed":
            return {"status": "failed", "error": "Wav2Lip 失敗", **results}

        # Step 3: Composite
        comp_result = self.run_ffmpeg_composite(project_name, auto_run=True)
        results["steps"].append({"step": "composite", **comp_result})
        if comp_result.get("status") != "completed":
            return {"status": "failed", "error": "合成失敗", **results}

        results["status"] = "completed"
        results["final_output"] = results["steps"][-1].get("output")
        return results
    
    def list_projects(self) -> Dict[str, Any]:
        """列出所有專案"""
        projects = {}
        if MV_PROJECTS_DIR.exists():
            for project_dir in MV_PROJECTS_DIR.iterdir():
                if project_dir.is_dir():
                    info_file = project_dir / "project.json"
                    if info_file.exists():
                        with open(info_file, 'r', encoding='utf-8') as f:
                            projects[project_dir.name] = json.load(f)
                    else:
                        projects[project_dir.name] = {"name": project_dir.name, "status": "incomplete"}
        return projects
    
    def get_project_status(self, project_name: str) -> Dict[str, Any]:
        """取得專案狀態"""
        project = self.projects.get(project_name)
        if not project:
            return {"error": f"專案 {project_name} 不存在"}
        
        project_dir = MV_PROJECTS_DIR / project_name
        
        # 檢查各階段檔案
        status = {
            "project": project_name,
            "character": (project_dir / "01_character").exists(),
            "backgrounds": len(list((project_dir / "02_backgrounds").glob("*.png"))) if (project_dir / "02_backgrounds").exists() else 0,
            "liveportrait": (project_dir / "03_liveportrait" / "character_animated.mp4").exists() if (project_dir / "03_liveportrait").exists() else False,
            "wav2lip": (project_dir / "04_wav2lip" / "character_lipsync.mp4").exists() if (project_dir / "04_wav2lip").exists() else False,
            "final": (project_dir / "05_final" / "mv_final.mp4").exists() if (project_dir / "05_final").exists() else False
        }
        
        return status

# 單例服務
mv_service = MVService()

# API 端點處理函數
def handle_create_project(data: Dict[str, Any]) -> Dict[str, Any]:
    """建立 MV 專案"""
    name = data.get("name")
    character_path = data.get("character_path")
    audio_path = data.get("audio_path")
    
    if not all([name, character_path, audio_path]):
        return {"error": "缺少必要參數: name, character_path, audio_path"}
    
    return mv_service.create_project(name, character_path, audio_path)

def handle_generate_character(data: Dict[str, Any]) -> Dict[str, Any]:
    """生成角色圖片"""
    prompt = data.get("prompt")
    negative_prompt = data.get("negative_prompt", "text, watermark, blurry, low quality")
    width = data.get("width", 512)
    height = data.get("height", 512)
    
    return mv_service.generate_character(prompt, negative_prompt, width, height)

def handle_run_liveportrait(data: Dict[str, Any]) -> Dict[str, Any]:
    """執行 LivePortrait"""
    project_name = data.get("project_name")
    driving_video = data.get("driving_video")
    
    return mv_service.run_liveportrait(project_name, driving_video)

def handle_run_wav2lip(data: Dict[str, Any]) -> Dict[str, Any]:
    """執行 Wav2Lip"""
    project_name = data.get("project_name")
    
    return mv_service.run_wav2lip(project_name)

def handle_run_composite(data: Dict[str, Any]) -> Dict[str, Any]:
    """執行 FFmpeg 合成"""
    project_name = data.get("project_name")
    
    return mv_service.run_ffmpeg_composite(project_name)

def handle_list_projects() -> Dict[str, Any]:
    """列出專案"""
    return {"projects": mv_service.list_projects()}

def handle_get_status(data: Dict[str, Any]) -> Dict[str, Any]:
    project_name = data.get("project_name")
    return mv_service.get_project_status(project_name)

def handle_run_full_pipeline(data: Dict[str, Any]) -> Dict[str, Any]:
    project_name = data.get("project_name")
    if not project_name:
        return {"error": "project_name required"}
    return mv_service.run_full_pipeline(project_name)
