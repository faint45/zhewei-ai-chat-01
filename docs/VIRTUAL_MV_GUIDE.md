# 虛擬人物 AI 音樂 MV 製作完整指南

## 系統組成

本方案結合三大 AI 工具：
1. **LivePortrait** - 讓靜態角色圖動起來（表情、頭部動作）
2. **Wav2Lip** - 讓角色跟著音樂自動對口型
3. **ComfyUI** - 生成背景畫面

---

## 安裝步驟

### 第一步：安裝 LivePortrait

```batch
scripts\install_liveportrait.bat
```

**注意事項：**
- 需要下載約 1.2GB 模型檔案
- 安裝完成後會自動加入 ComfyUI 節點

### 第二步：安裝 Wav2Lip

```batch
scripts\install_wav2lip.bat
```

**注意事項：**
- 需要下載約 300MB 模型檔案
- 支援 CUDA 加速

### 第三步：確認 ComfyUI

你的 ComfyUI 已安裝在 `D:\zhe-wei-tech\ComfyUI`，
Workflow 檔案已放入 `ComfyUI\workflows\` 目錄

---

## 製作流程

### 1. 準備素材

| 素材 | 說明 | 建議規格 |
|------|------|---------|
| **角色圖片** | 虛擬人物正面照 | 512x512 或 1024x1024，PNG |
| **音樂檔** | Suno 生成的歌曲 | MP3 或 WAV，5 分鐘 |
| **驅動影片** | 動作參考（可選）| 30-60 秒 MP4 |

### 2. 設計虛擬角色

**方法 A：使用 Midjourney/Leonardo（線上）**
```
Prompt: portrait of virtual idol, anime style, blue hair, cyberpunk outfit, 
front facing, neutral expression, clean background, professional lighting, 4k
```

**方法 B：使用本地 ComfyUI（免費）**
- 載入 `workflows/mv_background.json`
- 提示詞加上 `front facing character, portrait, clean background`

### 3. 生成 MV 分鏡背景

開啟 `workflows/mv_background.json`，建議分鏡：

| 段落 | 時間 | 背景風格提示詞 |
|------|------|---------------|
| 前奏 | 0:00-0:15 | cyberpunk city skyline, night, neon lights |
| 主歌1 | 0:15-1:00 | futuristic concert stage, holographic displays |
| 副歌1 | 1:00-1:30 | energy explosion, dynamic lights, crowd |
| 間奏 | 1:30-1:45 | calm space, stars, peaceful |
| 主歌2 | 1:45-2:30 | city streets, rain, reflections |
| 副歌2 | 2:30-3:00 | climax, maximum energy, light show |
| 尾奏 | 3:00-3:30 | sunrise, hope, new beginning |

輸出設定：
- 尺寸：1280x720（16:9）
- 批次：生成 60-90 張圖片（每秒 2-3 張）

### 4. 角色動畫（LivePortrait）

**命令行方式：**
```bash
cd D:\zhe-wei-tech\LivePortrait
python inference.py \
    --source character.png \
    --driving driving_video.mp4 \
    --output character_animated.mp4
```

**ComfyUI 方式：**
- 開啟 `workflows/liveportrait_character.json`
- 載入角色圖片和驅動影片
- 調整參數後執行

### 5. 對口型（Wav2Lip）

```bash
cd D:\zhe-wei-tech\Wav2Lip

# 先將音樂轉為 16kHz WAV
ffmpeg -i song.mp3 -ar 16000 -ac 1 audio.wav

# 執行 Wav2Lip
python inference.py \
    --checkpoint_path checkpoints/wav2lip_gan.pth \
    --face character_animated.mp4 \
    --audio audio.wav \
    --outfile character_lipsync.mp4
```

**參數說明：**
- `--face`: 角色動畫影片
- `--audio`: 音樂檔案
- `--outfile`: 輸出檔案

### 6. 合成最終 MV

```bash
cd D:\zhe-wei-tech\mv_projects\[專案名稱]

# 方法 1：簡單疊加（角色在背景中央）
ffmpeg -i background.mp4 -i character_lipsync.mp4 \
    -filter_complex "[0:v][1:v]overlay=(W-w)/2:(H-h)/2:format=auto" \
    -c:v libx264 -crf 18 -preset slow \
    -c:a copy \
    -y final_mv.mp4

# 方法 2：帶縮放動畫（角色從小變大）
ffmpeg -i background.mp4 -i character_lipsync.mp4 \
    -filter_complex "
        [1:v]scale=iw*0.8:ih*0.8[character];
        [0:v][character]overlay=(W-w)/2:(H-h)/2:format=auto
    " \
    -c:v libx264 -crf 18 -preset slow \
    -c:a copy \
    -y final_mv.mp4

# 方法 3：多背景切換
ffmpeg -f concat -i scenes.txt -i character_lipsync.mp4 \
    -filter_complex "[0:v][1:v]overlay=(W-w)/2:(H-h)/2" \
    -c:v libx264 -crf 18 -y final_mv.mp4
```

---

## 快捷腳本

已為你準備自動化腳本：

```batch
scripts\make_virtual_mv.bat [專案名] [角色圖] [音樂檔]
```

範例：
```batch
scripts\make_virtual_mv.bat cyberpunk_idol character.png song.mp3
```

---

## 進階技巧

### 1. 角色一致性

使用相同種子（Seed）生成多個表情：
```
--seed 12345
```

### 2. 更自然的口型

Wav2Lip GAN 版本比標準版本更自然：
```
--checkpoint_path checkpoints/wav2lip_gan.pth
```

### 3. 去背合成

如果角色影片有背景，先用去除背景：
```
# 使用 Rembg 或其他去背工具
python -m rembg -i character.png -o character_rmbg.png
```

### 4. 添加特效

```bash
# 發光效果
ffmpeg -i character_lipsync.mp4 -vf \
    "glow=radius=20:intensity=1.5" \
    character_glow.mp4

# 邊緣光
ffmpeg -i character_lipsync.mp4 -vf \
    "edgedetect=mode=colormix" \
    character_edge.mp4
```

---

## 常見問題

**Q: LivePortrait 輸出臉部扭曲？**
A: 確保輸入圖片是正面，解析度 512x512 以上

**Q: Wav2Lip 口型不同步？**
A: 確認音訊是 16kHz 單聲道 WAV 格式

**Q: 合成後影片模糊？**
A: 使用 `-crf 18` 而非預設的 23，數字越小品質越高

**Q: 角色和背景顏色不搭？**
A: 用 FFmpeg 調色：`-vf "hue=s=0.5"` 降低飽和度

---

## 完整範例

```bash
# 1. 建立專案
mkdir D:\zhe-wei-tech\mv_projects\demo
cd D:\zhe-wei-tech\mv_projects\demo

# 2. 生成 30 張背景（在 ComfyUI 中批次生成）
# 將圖片放入 backgrounds/ 目錄

# 3. 圖片序列轉影片
ffmpeg -framerate 2 -i backgrounds/frame_%03d.png \
    -c:v libx264 -pix_fmt yuv420p \
    -y background.mp4

# 4. LivePortrait 動畫
cd D:\zhe-wei-tech\LivePortrait
python inference.py \
    --source ../demo/character.png \
    --driving ../resources/driving_talking.mp4 \
    --output ../demo/character_anim.mp4

# 5. Wav2Lip 對口型
cd D:\zhe-wei-tech\Wav2Lip
ffmpeg -i ../demo/song.mp3 -ar 16000 -ac 1 ../demo/audio.wav
python inference.py \
    --checkpoint_path checkpoints/wav2lip_gan.pth \
    --face ../demo/character_anim.mp4 \
    --audio ../demo/audio.wav \
    --outfile ../demo/character_final.mp4

# 6. 合成
ffmpeg -i ../demo/background.mp4 -i ../demo/character_final.mp4 \
    -filter_complex "[0:v][1:v]overlay=(W-w)/2:(H-h)/2:format=auto" \
    -c:v libx264 -crf 18 -preset slow \
    -y ../demo/mv_final.mp4

echo "完成！輸出：mv_final.mp4"
```

---

## 硬體需求

| 項目 | 最低 | 建議 |
|------|------|------|
| GPU | RTX 3060 12GB | RTX 4060 Ti 16GB |
| RAM | 16GB | 32GB |
| 儲存 | 10GB 空間 | 50GB 空間 |
| 時間 | 5分鐘影片約 30 分鐘 | 約 10 分鐘 |

---

## 相關連結

- LivePortrait: https://github.com/KwaiVGI/LivePortrait
- Wav2Lip: https://github.com/Rudrabha/Wav2Lip
- ComfyUI: https://github.com/comfyanonymous/ComfyUI
