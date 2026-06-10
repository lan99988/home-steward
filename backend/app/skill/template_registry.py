"""社区模板仓库——已验证的正确代码片段（外部锚点）"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TemplateRegistry:
    """社区模板仓库

    引入外部人类智慧，打破 LLM 自我验证的递归循环。
    模板来自 verified-patterns 和 built-in skills，
    作为 LLM 生成 Skill 时的参考锚点。
    """

    def __init__(self, paths: List[Path] = None):
        self.paths = paths or [
            Path("skills/verified-patterns"),
            Path("skills/built-in"),
        ]
        self.templates: Dict[str, dict] = {}
        self._load_all()

    def _load_all(self):
        """加载所有模板"""
        for base in self.paths:
            if not base.exists():
                continue
            for item in base.iterdir():
                if not item.is_dir():
                    continue
                manifest = item / "SKILL.md"
                if manifest.exists():
                    try:
                        content = manifest.read_text(encoding="utf-8")
                        self.templates[item.name] = {
                            "path": item,
                            "summary": self._extract_summary(content),
                            "domains": self._extract_domains(content),
                        }
                    except Exception as e:
                        logger.warning(f"加载模板 {item.name} 失败: {e}")

        logger.info(f"📚 已加载 {len(self.templates)} 个社区模板")

    def find_similar(self, skill_code: str, top_n: int = 3) -> List[dict]:
        """查找与当前 Skill 代码相似的已验证模板"""
        keywords = set(skill_code.lower().split())
        matches = []

        for name, tmpl in self.templates.items():
            summary_kw = set(tmpl["summary"].lower().split())
            overlap = len(keywords & summary_kw)
            if overlap > 2:
                matches.append({
                    "template": name,
                    "summary": tmpl["summary"],
                    "overlap": overlap,
                })

        return sorted(matches, key=lambda x: x["overlap"], reverse=True)[:top_n]

    def find_by_domain(self, domain: str) -> List[dict]:
        """按操作域查找模板"""
        results = []
        for name, tmpl in self.templates.items():
            if domain in tmpl.get("domains", []):
                results.append({
                    "template": name,
                    "summary": tmpl["summary"],
                })
        return results

    def get_template_code(self, name: str) -> Optional[str]:
        """获取模板的 main.py 代码"""
        tmpl = self.templates.get(name)
        if not tmpl:
            return None
        main_py = Path(tmpl["path"]) / "main.py"
        if main_py.exists():
            return main_py.read_text(encoding="utf-8")
        return None

    def _extract_summary(self, content: str) -> str:
        """从 SKILL.md 提取描述"""
        try:
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("description:"):
                    return line.split(":", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
        return ""

    def _extract_domains(self, content: str) -> list:
        """从 SKILL.md 提取域列表"""
        try:
            import yaml
            parts = content.split("---")
            if len(parts) >= 2:
                data = yaml.safe_load(parts[1])
                if data:
                    return [d["domain"] for d in data.get("domains", [])]
        except Exception:
            pass
        return []
