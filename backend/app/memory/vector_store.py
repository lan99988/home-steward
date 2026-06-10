"""向量存储——语义检索接口（ChromaDB 适配器）"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class VectorStore:
    """向量存储适配器

    封装 ChromaDB，提供语义检索能力。
    支持记忆向量索引和声纹存储。
    """

    def __init__(self, persist_dir: str = "data/vector_store"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collections = {}
        self._ready = False

    def initialize(self):
        """初始化向量数据库"""
        try:
            import chromadb
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir)
            )
            self._ready = True
            logger.info("✅ 向量存储已初始化 (ChromaDB)")
        except ImportError:
            logger.warning("ChromaDB 未安装，使用 JSON 后备存储")
            self._ready = False
        except Exception as e:
            logger.warning(f"向量存储初始化失败: {e}，使用后备存储")
            self._ready = False

    def get_or_create_collection(self, name: str):
        """获取或创建集合"""
        if not self._ready:
            return None
        if name not in self.collections:
            try:
                self.collections[name] = self.client.get_or_create_collection(name)
            except Exception as e:
                logger.error(f"创建集合 '{name}' 失败: {e}")
                return None
        return self.collections[name]

    def add_memory(self, memory_id: str, text: str, metadata: Dict = None):
        """添加记忆到向量索引"""
        collection = self.get_or_create_collection("memories")
        if not collection:
            self._fallback_store(memory_id, text, metadata)
            return

        try:
            collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[memory_id],
            )
        except Exception as e:
            logger.error(f"向量存储添加失败: {e}")
            self._fallback_store(memory_id, text, metadata)

    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """语义搜索记忆"""
        collection = self.get_or_create_collection("memories")
        if not collection:
            return self._fallback_search(query, n_results)

        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
            )
            return [
                {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
                for i in range(len(results["ids"][0]))
            ] if results["ids"] else []
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return self._fallback_search(query, n_results)

    def _fallback_store(self, memory_id: str, text: str, metadata: Dict = None):
        """无 ChromaDB 时的 JSON 后备存储"""
        fallback_path = self.persist_dir / "fallback_memories.json"
        memories = []
        if fallback_path.exists():
            try:
                memories = json.loads(fallback_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        memories.append({
            "id": memory_id,
            "text": text,
            "metadata": metadata or {},
        })
        fallback_path.write_text(
            json.dumps(memories[-1000:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _fallback_search(self, query: str, n_results: int) -> List[Dict]:
        """后备搜索（关键词匹配）"""
        fallback_path = self.persist_dir / "fallback_memories.json"
        if not fallback_path.exists():
            return []
        try:
            memories = json.loads(fallback_path.read_text(encoding="utf-8"))
            # 简单关键词匹配
            keywords = set(query.lower().split())
            scored = []
            for m in memories:
                text_kw = set(m["text"].lower().split())
                overlap = len(keywords & text_kw)
                if overlap > 0:
                    scored.append((overlap, m))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [
                {"id": m["id"], "text": m["text"], "metadata": m.get("metadata", {})}
                for _, m in scored[:n_results]
            ]
        except Exception:
            return []

    def delete_collection(self, name: str):
        """删除集合"""
        if self._ready:
            try:
                self.client.delete_collection(name)
                self.collections.pop(name, None)
            except Exception as e:
                logger.error(f"删除集合 '{name}' 失败: {e}")
