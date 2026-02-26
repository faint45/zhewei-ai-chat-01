import urllib.request
import urllib.error

urls = [
    "https://jarvis.zhe-wei.net/health",
    "https://jarvis.zhe-wei.net/jarvis-login",
    "https://vision.zhe-wei.net/",
    "https://brain.zhe-wei.net/health",
    "https://cms.zhe-wei.net/",
    "https://dify.zhe-wei.net/",
    "https://codesim.zhe-wei.net/",
]

for url in urls:
    print(f"=== {url} ===")
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        r = urllib.request.urlopen(req, timeout=10)
        print("OK", r.status)
    except urllib.error.HTTPError as e:
        print("ERR", e.code)
    except Exception as e:
        print("FAIL", e)
    print()
