# -*- coding: utf-8 -*-
"""
築未科技 — 代碼模擬器：文件管理器 + SQLite 版本歷史
"""
import os
import json
import shutil
import sqlite3
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class FileManager:
    """項目文件管理 + 版本歷史"""

    def __init__(self, projects_root: str, db_path: str = ""):
        self.projects_root = Path(projects_root)
        self.projects_root.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or str(self.projects_root / "workspace_history.db")
        self._init_db()

    # ── DB ──────────────────────────────────────────────
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                file_path TEXT NOT NULL,
                content TEXT NOT NULL,
                hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                message TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_project_file
            ON file_versions(project, file_path)
        """)
        conn.commit()
        conn.close()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # ── Projects ────────────────────────────────────────
    def list_projects(self) -> List[Dict[str, Any]]:
        results = []
        for p in sorted(self.projects_root.iterdir()):
            if p.is_dir() and not p.name.startswith("."):
                files = list(p.rglob("*"))
                file_count = sum(1 for f in files if f.is_file())
                results.append({
                    "name": p.name,
                    "file_count": file_count,
                    "created_at": datetime.fromtimestamp(p.stat().st_ctime).isoformat(),
                })
        return results

    def create_project(self, name: str, template: str = "html") -> Dict[str, Any]:
        project_dir = self.projects_root / name
        if project_dir.exists():
            return {"error": f"Project '{name}' already exists"}
        project_dir.mkdir(parents=True)

        templates = {
            "html": {
                "index.html": '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>My Project</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n  <h1>Hello World</h1>\n  <script src="script.js"></script>\n</body>\n</html>',
                "style.css": "* { margin: 0; padding: 0; box-sizing: border-box; }\nbody { font-family: system-ui, sans-serif; padding: 2rem; }\nh1 { color: #333; }",
                "script.js": 'console.log("Hello from script.js");',
            },
            "react": {
                "index.html": '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>React App</title>\n  <script src="https://unpkg.com/react@18/umd/react.development.js"></script>\n  <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>\n  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n  <div id="root"></div>\n  <script type="text/babel" src="App.jsx"></script>\n</body>\n</html>',
                "App.jsx": 'const App = () => {\n  const [count, setCount] = React.useState(0);\n  return (\n    <div className="app">\n      <h1>React App</h1>\n      <p>Count: {count}</p>\n      <button onClick={() => setCount(c => c + 1)}>+1</button>\n    </div>\n  );\n};\nReactDOM.createRoot(document.getElementById("root")).render(<App />);',
                "style.css": "* { margin: 0; padding: 0; box-sizing: border-box; }\nbody { font-family: system-ui, sans-serif; padding: 2rem; }\n.app { text-align: center; }\nbutton { margin-top: 1rem; padding: 0.5rem 1.5rem; font-size: 1rem; cursor: pointer; }",
            },
            "vue": {
                "index.html": '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>Vue App</title>\n  <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n  <div id="app">\n    <h1>{{ message }}</h1>\n    <p>Count: {{ count }}</p>\n    <button @click="count++">+1</button>\n  </div>\n  <script src="app.js"></script>\n</body>\n</html>',
                "app.js": "const { createApp, ref } = Vue;\ncreateApp({\n  setup() {\n    const message = ref('Vue App');\n    const count = ref(0);\n    return { message, count };\n  }\n}).mount('#app');",
                "style.css": "* { margin: 0; padding: 0; box-sizing: border-box; }\nbody { font-family: system-ui, sans-serif; padding: 2rem; text-align: center; }\nbutton { margin-top: 1rem; padding: 0.5rem 1.5rem; font-size: 1rem; cursor: pointer; }",
            },
            "empty": {},
        }

        for fname, content in templates.get(template, templates["html"]).items():
            fpath = project_dir / fname
            fpath.write_text(content, encoding="utf-8")
            self._save_version(name, fname, content, "Initial template")

        return {"name": name, "template": template, "files": list(templates.get(template, {}).keys())}

    def delete_project(self, name: str) -> Dict[str, Any]:
        project_dir = self.projects_root / name
        if not project_dir.exists():
            return {"error": f"Project '{name}' not found"}
        shutil.rmtree(project_dir)
        conn = self._conn()
        conn.execute("DELETE FROM file_versions WHERE project = ?", (name,))
        conn.commit()
        conn.close()
        return {"deleted": name}

    # ── Files ───────────────────────────────────────────
    def list_files(self, project: str) -> List[Dict[str, Any]]:
        project_dir = self.projects_root / project
        if not project_dir.exists():
            return []
        results = []
        for f in sorted(project_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(project_dir).as_posix()
                results.append({
                    "path": rel,
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    "language": self._detect_language(rel),
                })
        return results

    def read_file(self, project: str, file_path: str) -> Dict[str, Any]:
        fpath = self.projects_root / project / file_path
        if not fpath.exists():
            return {"error": f"File not found: {file_path}"}
        content = fpath.read_text(encoding="utf-8", errors="replace")
        return {
            "path": file_path,
            "content": content,
            "language": self._detect_language(file_path),
            "size": len(content),
        }

    def save_file(self, project: str, file_path: str, content: str, message: str = "") -> Dict[str, Any]:
        project_dir = self.projects_root / project
        project_dir.mkdir(parents=True, exist_ok=True)
        fpath = project_dir / file_path
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding="utf-8")
        version_id = self._save_version(project, file_path, content, message)
        return {"path": file_path, "size": len(content), "version_id": version_id}

    def delete_file(self, project: str, file_path: str) -> Dict[str, Any]:
        fpath = self.projects_root / project / file_path
        if not fpath.exists():
            return {"error": f"File not found: {file_path}"}
        fpath.unlink()
        return {"deleted": file_path}

    def rename_file(self, project: str, old_path: str, new_path: str) -> Dict[str, Any]:
        old = self.projects_root / project / old_path
        new = self.projects_root / project / new_path
        if not old.exists():
            return {"error": f"File not found: {old_path}"}
        new.parent.mkdir(parents=True, exist_ok=True)
        old.rename(new)
        return {"old_path": old_path, "new_path": new_path}

    # ── Version History ─────────────────────────────────
    def _save_version(self, project: str, file_path: str, content: str, message: str = "") -> int:
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO file_versions (project, file_path, content, hash, created_at, message) VALUES (?, ?, ?, ?, ?, ?)",
            (project, file_path, content, h, datetime.now().isoformat(), message),
        )
        vid = cur.lastrowid
        conn.commit()
        conn.close()
        return vid

    def get_file_history(self, project: str, file_path: str, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT id, hash, created_at, message, length(content) as size FROM file_versions WHERE project = ? AND file_path = ? ORDER BY id DESC LIMIT ?",
            (project, file_path, limit),
        ).fetchall()
        conn.close()
        return [{"id": r[0], "hash": r[1], "created_at": r[2], "message": r[3], "size": r[4]} for r in rows]

    def get_version_content(self, version_id: int) -> Dict[str, Any]:
        conn = self._conn()
        row = conn.execute(
            "SELECT project, file_path, content, hash, created_at, message FROM file_versions WHERE id = ?",
            (version_id,),
        ).fetchone()
        conn.close()
        if not row:
            return {"error": "Version not found"}
        return {"id": version_id, "project": row[0], "file_path": row[1], "content": row[2], "hash": row[3], "created_at": row[4], "message": row[5]}

    def restore_version(self, version_id: int) -> Dict[str, Any]:
        ver = self.get_version_content(version_id)
        if "error" in ver:
            return ver
        return self.save_file(ver["project"], ver["file_path"], ver["content"], f"Restored from version #{version_id}")

    # ── Helpers ─────────────────────────────────────────
    @staticmethod
    def _detect_language(path: str) -> str:
        ext_map = {
            ".html": "html", ".htm": "html",
            ".css": "css", ".scss": "css", ".less": "css",
            ".js": "javascript", ".mjs": "javascript",
            ".jsx": "jsx",
            ".ts": "typescript", ".tsx": "tsx",
            ".vue": "vue",
            ".py": "python",
            ".json": "json",
            ".md": "markdown",
            ".xml": "xml", ".svg": "xml",
            ".yaml": "yaml", ".yml": "yaml",
            ".wxml": "html", ".wxss": "css",
        }
        ext = Path(path).suffix.lower()
        return ext_map.get(ext, "text")
