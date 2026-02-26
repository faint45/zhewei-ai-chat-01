"""
URL 樹狀結構 - 自動分類歸檔，多執行緒安全
"""
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse
import re


@dataclass
class URLNode:
    name: str
    full_path: str
    children: Dict[str, "URLNode"] = field(default_factory=dict)
    urls: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.full_path,
            "urls": self.urls.copy(),
            "children": {k: v.to_dict() for k, v in self.children.items()},
        }


class URLTree:
    """
    依 domain -> path segments 自動建樹，thread-safe 寫入
    """

    def __init__(self):
        self._root = URLNode("", "")
        self._lock = threading.RLock()

    def _parse_url(self, url: str) -> tuple:
        try:
            p = urlparse(url)
            domain = p.netloc or "unknown"
            path = p.path.strip("/") or "/"
            segments = [s for s in path.split("/") if s]
            return domain, segments, url
        except Exception:
            return "unknown", [], url

    def add(self, url: str, classify_by: str = "path") -> None:
        """
        classify_by: "path" | "domain" | "ext"
        """
        with self._lock:
            domain, segments, full_url = self._parse_url(url)
            if classify_by == "domain":
                keys = [domain] + segments
            elif classify_by == "ext":
                ext = self._extract_ext(url)
                keys = [domain, ext] + segments
            else:
                keys = [domain] + segments
            node = self._root
            path_parts = []
            for k in keys:
                if not k:
                    continue
                path_parts.append(k)
                full_path = "/".join(path_parts)
                if k not in node.children:
                    node.children[k] = URLNode(k, full_path)
                node = node.children[k]
            if full_url not in node.urls:
                node.urls.append(full_url)

    def _extract_ext(self, url: str) -> str:
        path = urlparse(url).path
        m = re.search(r"\.([a-zA-Z0-9]+)(?:\?|$)", path)
        return m.group(1) if m else "other"

    def get_node(self, *path_keys: str) -> Optional[URLNode]:
        with self._lock:
            node = self._root
            for k in path_keys:
                if k not in node.children:
                    return None
                node = node.children[k]
            return node

    def collect_all_urls(self) -> List[str]:
        with self._lock:
            return self._collect(self._root)

    def _collect(self, node: URLNode) -> List[str]:
        out = list(node.urls)
        for child in node.children.values():
            out.extend(self._collect(child))
        return out

    def flatten(self) -> List[tuple]:
        """回傳 (path, urls) 列表"""
        with self._lock:
            return self._flatten(self._root, "")

    def _flatten(self, node: URLNode, prefix: str) -> List[tuple]:
        out = []
        path = "/".join(filter(None, [prefix.rstrip("/"), node.name])) if node.name else (prefix or "/")
        if node.urls:
            out.append((path, node.urls))
        for child in node.children.values():
            out.extend(self._flatten(child, path))
        return out

    def render_ascii(self, indent: str = "  ", max_depth: int = 5) -> str:
        with self._lock:
            return self._render(self._root, 0, indent, max_depth)

    def _render(self, node: URLNode, depth: int, indent: str, max_depth: int) -> str:
        if depth > max_depth:
            return ""
        lines = []
        prefix = indent * depth
        for name, child in sorted(node.children.items()):
            cnt = len(child.urls)
            badge = f" ({cnt})" if cnt else ""
            lines.append(f"{prefix}|-- {name}{badge}")
            lines.append(self._render(child, depth + 1, indent, max_depth))
        return "\n".join(filter(None, lines))


def _concurrent_add_demo():
    import concurrent.futures
    tree = URLTree()
    base = "https://site{}.com/path/a/b/c"
    urls = [base.format(i % 10) for i in range(1000)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(tree.add, urls))
    print(f"Thread-safe add 1000 URLs, total: {len(tree.collect_all_urls())}")


if __name__ == "__main__":
    tree = URLTree()
    urls = [
        "https://example.com/api/v1/users",
        "https://example.com/api/v1/orders",
        "https://example.com/static/js/main.js",
        "https://cdn.example.com/static/img/logo.png",
        "https://other.com/page",
    ]
    for u in urls:
        tree.add(u)
    print(tree.render_ascii())
    print("\nFlatten:")
    for path, urls in tree.flatten():
        if urls:
            print(f"  {path}: {len(urls)} urls")
    print("\nConcurrent:")
    _concurrent_add_demo()
