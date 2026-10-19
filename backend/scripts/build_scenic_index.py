"""一次性构建统一向量索引（纯 Langchain + pgvector）。

索引范围（RAG 知识库语料补全后）：
  - scenic_spot 景点本体
  - knowledge_doc 知识库语料（城市知识 / 深度攻略 / 主题专题 / 行程模板 / FAQ）

两张表统一进同一个集合（默认 travel_kb），靠 doc_type 元数据区分，检索时可按
doc_type / city 过滤。

前提：
  1) 本机 PostgreSQL 已启用 pgvector 扩展（库 vector_db，已执行 CREATE EXTENSION vector;）
  2) 已执行：pip install -r requirements_rag.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  3) Ollama 已部署 bge-m3（RAG_EMBED_BACKEND=ollama），Embedding 走本地推理
  4) scenic_spot 已有数据；knowledge_doc 已用 scripts/seed_knowledge_corpus.py 灌入种子
     （否则会报错，这符合 RAG「语料决定上限」的约束）

运行（在 backend 目录下）：
  python scripts/build_scenic_index.py

如需重建（数据变更后），直接再跑一次即可（脚本会先清空旧集合）。
"""

import os
import sys

# 允许以脚本方式直接运行：把 backend 目录加入模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from database import SessionLocal
from services.rag.vector_store import ScenicPGVectorStore


def main():
    if not settings.USE_RAG:
        print("[提示] 当前 USE_RAG=False，但建索引不依赖该开关，将继续构建。")
    print(f"[连接] {settings.RAG_PG_CONNECTION_STRING}  collection={settings.RAG_PG_COLLECTION}")
    db = SessionLocal()
    try:
        ScenicPGVectorStore().build_from_db(db)
        print("[完成] 统一向量索引（景点 + 知识库）已构建/重建完成。可开启 USE_RAG=True 后启动后端。")
    except Exception as e:
        print("[失败]", repr(e))
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
