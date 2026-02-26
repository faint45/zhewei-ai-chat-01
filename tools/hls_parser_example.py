"""
HLS m3u8 標籤解析範例
僅示範解析格式，不包含解密或下載邏輯
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExtXKey:
    method: str
    uri: Optional[str]
    iv: Optional[str]
    key_format: Optional[str]
    key_format_versions: Optional[str]


@dataclass
class ExtXMap:
    uri: str
    byterange: Optional[str]


@dataclass
class ExtInf:
    duration: float
    title: Optional[str]
    uri: Optional[str]


def parse_ext_x_key(line: str) -> Optional[ExtXKey]:
    if not line.startswith("#EXT-X-KEY:"):
        return None
    attr = _parse_attributes(line[len("#EXT-X-KEY:"):])
    return ExtXKey(
        method=attr.get("METHOD", "NONE"),
        uri=attr.get("URI", "").strip('"') or None,
        iv=attr.get("IV"),
        key_format=attr.get("KEYFORMAT"),
        key_format_versions=attr.get("KEYFORMATVERSIONS"),
    )


def parse_ext_x_map(line: str) -> Optional[ExtXMap]:
    if not line.startswith("#EXT-X-MAP:"):
        return None
    attr = _parse_attributes(line[len("#EXT-X-MAP:"):])
    return ExtXMap(
        uri=attr.get("URI", "").strip('"'),
        byterange=attr.get("BYTERANGE"),
    )


def parse_ext_inf(line: str) -> Optional[ExtInf]:
    m = re.match(r"#EXTINF:([\d.]+)(?:,(.+))?", line)
    if not m:
        return None
    return ExtInf(
        duration=float(m.group(1)),
        title=m.group(2).strip() if m.group(2) else None,
        uri=None,
    )


def _parse_attributes(text: str) -> dict:
    result = {}
    for part in re.findall(r'([A-Z-]+)=(?:"([^"]*)"|([^,]+))', text):
        key, qval, val = part
        result[key] = qval if qval else val.strip()
    return result


def parse_m3u8(content: str, base_uri: str = "") -> dict:
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    playlist = {
        "ext_x_key": None,
        "ext_x_map": None,
        "segments": [],
        "is_master": False,
    }
    next_extinf = None

    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-KEY:"):
            playlist["ext_x_key"] = parse_ext_x_key(line)
        elif line.startswith("#EXT-X-MAP:"):
            playlist["ext_x_map"] = parse_ext_x_map(line)
        elif line.startswith("#EXT-X-STREAM-INF:"):
            playlist["is_master"] = True
        elif line.startswith("#EXTINF:"):
            next_extinf = parse_ext_inf(line)
        elif next_extinf and not line.startswith("#"):
            next_extinf.uri = line if not line.startswith("http") else line
            playlist["segments"].append(next_extinf)
            next_extinf = None

    return playlist


if __name__ == "__main__":
    sample = """
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-KEY:METHOD=AES-128,URI="https://cdn.example.com/key.bin",IV=0x00000000000000000000000000000001
#EXTINF:10.0,
segment0.ts
#EXTINF:10.0,
segment1.ts
#EXT-X-ENDLIST
"""
    result = parse_m3u8(sample)
    print("解析結果:")
    print(f"  加密: {result['ext_x_key']}")
    print(f"  片段數: {len(result['segments'])}")
    for s in result["segments"]:
        print(f"    - {s.duration}s: {s.uri}")
