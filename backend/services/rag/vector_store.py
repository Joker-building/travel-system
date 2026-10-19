"""纯 Langchain 检索层 · pgvector 向量库

本模块把「景点本体（scenic_spot）」与「知识库语料（knowledge_doc）」统一做成
可被 Langchain 语义检索的 PGVector 索引。

设计要点（相对旧版的关键升级）：
- 统一集合（默认 travel_kb），靠 doc_type 元数据区分语料类型：
    scenic_spot 景点本体 / city 城市知识 / guide 深度攻略
    / topic 主题专题 / itinerary 行程模板 / faq 常见问题。
- 检索可按 doc_type 与 city 组合精确过滤（cmetadata @> '{...}'），
  例如 search_scenic_rag 只召回 scenic_spot，rag_qa 召回全部。
- 知识库长文（攻略 / 城市知识）经 RecursiveCharacterTextSplitter 分块入库，
  召回更精准；景点简介较短，不强行分块。
- 向量库：本机 PostgreSQL 17 + pgvector 扩展（库名 vector_db）。
- Embedding：本地 bge-m3，默认经 Ollama（langchain_ollama），可切 HF。
- PGVector 由 langchain_postgres 提供（psycopg3 驱动，非 psycopg2）。

参考 Postgres.pdf 的 LangChain + PGVector 范式。
"""

from typing import List, Optional, Tuple

from langchain_core.documents import Document
# 1.x 关键变化：PGVector 已从 langchain_community 迁到 langchain_postgres（psycopg3 驱动）
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings

try:
    from langchain_ollama import OllamaEmbeddings
except ImportError:  # Ollama 未安装时仅在 backend=hf 模式下才需要它
    OllamaEmbeddings = None

# 知识库长文分块参数：块约 500 字、重叠 50 字，兼顾语义完整与召回精度
_KB_CHUNK_SIZE = 500
_KB_CHUNK_OVERLAP = 50

# 知识块细分类型（subtype）推断关键词与映射
_FOOD_KW = ("美食", "小吃", "餐厅", "菜系", "餐饮", "烤鸭", "火锅", "早茶",
            "美食地图", "特色美食", "吃食", "味道", "口味", "夜市", "大餐")
_CULTURE_KW = ("历史", "古迹", "文化", "博物馆", "人文", "遗产", "古都", "底蕴",
               "建城", "千年", "遗址", "风俗", "纪念馆", "古城", "朝代", "皇家", "古刹")

# topic 的 category → subtype 直接映射
_TOPIC_CAT_SUBTYPE = {
    "美食": "food", "历史": "culture", "人文": "culture", "文化": "culture",
    "亲子": "family", "自然": "nature",
}


def _infer_subtype(doc_type: str, category: str, chunk_text: str) -> str:
    """推断一块知识语料的细分类型（food / culture / family / nature / itinerary / faq / general）。

    - topic：按 category 直接映射（美食→food，历史/人文→culture…）。
    - city / guide：同一篇往往混合美食与人文，按【块内容】命中关键词判定，
      实现 food 与 culture 在同一篇里精准分离（如「特色美食」段→food、「城市底蕴」段→culture）。
    - itinerary / faq：整体标记，互不混入。
    """
    if doc_type == "topic":
        return _TOPIC_CAT_SUBTYPE.get((category or "").strip(), "general")
    if doc_type in ("city", "guide"):
        t = chunk_text or ""
        has_food = any(k in t for k in _FOOD_KW)
        has_culture = any(k in t for k in _CULTURE_KW)
        if has_food and not has_culture:
            return "food"
        if has_culture and not has_food:
            return "culture"
        if has_food and has_culture:
            # 同时命中：以关键词最早出现位置决定主导类型
            fi = min((t.find(k) for k in _FOOD_KW if k in t), default=10 ** 9)
            ci = min((t.find(k) for k in _CULTURE_KW if k in t), default=10 ** 9)
            return "food" if fi <= ci else "culture"
        return "general"
    if doc_type == "itinerary":
        return "itinerary"
    if doc_type == "faq":
        return "faq"
    return "general"


def get_embeddings():
    """返回 bge-m3 的 Embedding 封装（Langchain 接口）。

    默认 backend=ollama：走本机 Ollama 已部署的 bge-m3（维度 1024，纯本地推理）。
    可选 backend=hf：改用 sentence-transformers 加载本地 HF 权重（需另装依赖）。
    """
    backend = (settings.RAG_EMBED_BACKEND or "ollama").lower()
    if backend == "ollama":
        if OllamaEmbeddings is None:
            raise ImportError(
                "未找到 langchain-ollama，请先安装：pip install langchain-ollama"
            )
        return OllamaEmbeddings(
            model=settings.RAG_OLLAMA_MODEL,
            base_url=settings.RAG_OLLAMA_BASE_URL,
        )
    # 回退：本地 sentence-transformers（需 pip install langchain-huggingface sentence-transformers）
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name=settings.RAG_EMBED_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _scenic_rows_to_documents(rows) -> List[Document]:
    """把 ScenicSpot 行转成 Langchain Document（doc_type=scenic_spot）。

    - page_content：用于语义检索的正文（简介 + 推荐理由拼接）。
    - metadata：结构化字段，既用于「按城市 / 类型过滤检索」，也用于结果卡片展示。
      spot_id 保留，便于检索命中后回查数据库拿最新字段。
    """
    docs = []
    for s in rows:
        content = "\n".join(filter(None, [s.introduction or "", s.recommendation or ""]))
        docs.append(Document(
            page_content=content or (s.name or ""),
            metadata={
                "doc_type": "scenic_spot",
                "spot_id": s.id,
                "title": s.name or "",
                "name": s.name or "",
                "city": s.city or "",
                "category": s.category or "",
                "address": s.address or "",
                "price": s.price or 0,
                "rating": s.rating or 0,
                "tags": s.tags or "",
            },
        ))
    return docs


def _knowledge_rows_to_documents(rows) -> List[Document]:
    """把 KnowledgeDoc 行转成 Langchain Document（按 doc_type 入库，长文分块）。

    - page_content：正文（长文经 RecursiveCharacterTextSplitter 切分为若干块）。
    - metadata：doc_type / doc_id / title / city / category / tags，
      并带 chunk_index 便于回溯；检索过滤靠 doc_type + city。
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=_KB_CHUNK_SIZE,
        chunk_overlap=_KB_CHUNK_OVERLAP,
        separators=["\n## ", "\n# ", "\n", "。", ""],
    )
    docs = []
    for k in rows:
        chunks = splitter.split_text(k.content or "")
        if not chunks:
            chunks = [k.title or ""]
        for idx, chunk in enumerate(chunks):
            subtype = _infer_subtype(k.doc_type or "knowledge", k.category or "", chunk)
            docs.append(Document(
                page_content=chunk,
                metadata={
                    "doc_type": k.doc_type or "knowledge",
                    "doc_id": k.id,
                    "title": k.title or "",
                    "city": k.city or "",
                    "category": k.category or "",
                    "tags": k.tags or "",
                    "subtype": subtype,
                    "chunk_index": idx,
                },
            ))
    return docs


class ScenicPGVectorStore:
    """景点 + 知识库 PGVector 索引的薄封装，编排层只跟它打交道。"""

    def __init__(self):
        self.embeddings = get_embeddings()
        self.collection = settings.RAG_PG_COLLECTION
        self.connection_string = settings.RAG_PG_CONNECTION_STRING

    def build_from_db(self, db) -> None:
        """从 scenic_spot + knowledge_doc 两张表全量建统一索引（首次或重建时调用）。

        pre_delete_collection=True：重建前先清空旧集合，避免脏数据 / 维度不一致。
        """
        from models.scenic_spot import ScenicSpot
        from models.knowledge_doc import KnowledgeDoc

        scenic_rows = db.query(ScenicSpot).all()
        scenic_docs = _scenic_rows_to_documents(scenic_rows)

        knowledge_rows = db.query(KnowledgeDoc).all()
        knowledge_docs = _knowledge_rows_to_documents(knowledge_rows)

        docs = scenic_docs + knowledge_docs
        if not docs:
            raise RuntimeError(
                "scenic_spot 与 knowledge_doc 均为空，无法构建向量索引。"
                "请先运行 seed_knowledge_corpus.py 灌入语料，并确保 scenic_spot 有数据。"
            )
        print(f"[建索引] 景点文档={len(scenic_docs)}  知识库文档(分块后)={len(knowledge_docs)}")
        PGVector.from_documents(
            embedding=self.embeddings,
            documents=docs,
            collection_name=self.collection,
            connection=self.connection_string,
            pre_delete_collection=True,
            use_jsonb=True,
        )

    def _build_filter(self, city: Optional[str] = None, doc_type: Optional[str] = None,
                      doc_types: Optional[List[str]] = None,
                      subtypes: Optional[List[str]] = None) -> Optional[dict]:
        """构造 PGVector 元数据过滤条件（city / doc_type / doc_types / subtypes 可组合）。

        - doc_type：单值精确匹配（向后兼容 search_scenic_rag 等）。
        - doc_types：多值 OR 匹配（{"$in": [...]}），用于 subtopic 细分检索。
        - subtypes：多值 OR 匹配（{"$in": [...]}），用于 food/culture 在同一 doc_type
          内进一步精准分离（均为 AND 关系组合进同一 filter dict）。
        """
        f = {}
        if city:
            f["city"] = city
        if doc_types:
            f["doc_type"] = {"$in": list(doc_types)}
        elif doc_type:
            f["doc_type"] = doc_type
        if subtypes:
            f["subtype"] = {"$in": list(subtypes)}
        return f or None

    def get_retriever(self, city: Optional[str] = None,
                      doc_type: Optional[str] = None,
                      doc_types: Optional[List[str]] = None,
                      subtypes: Optional[List[str]] = None):
        """返回 Langchain BaseRetriever。可按 city / doc_type(s) / subtype(s) 过滤（混合检索）。

        例：
          get_retriever()                                       召回全部（rag_qa 兜底用）
          get_retriever(doc_type='scenic_spot')                  仅景点（search_scenic 用）
          get_retriever(doc_types=['topic','city','guide'])      美食/人文细分（排除 itinerary/faq）
          get_retriever(doc_types=['topic','city','guide'],
                       subtypes=['food'])                        仅美食（food 与 culture 分离）
          get_retriever(city='北京')                             北京全部语料
        """
        store = PGVector.from_existing_index(
            embedding=self.embeddings,
            collection_name=self.collection,
            connection=self.connection_string,
            use_jsonb=True,
        )
        search_kwargs = {"k": settings.RAG_TOP_K}
        f = self._build_filter(city, doc_type, doc_types, subtypes)
        if f:
            search_kwargs["filter"] = f
        return store.as_retriever(search_kwargs=search_kwargs)

    def similarity_search(self, query: str, city: Optional[str] = None,
                          doc_type: Optional[str] = None,
                          doc_types: Optional[List[str]] = None,
                          subtypes: Optional[List[str]] = None,
                          k: Optional[int] = None) -> List[Tuple[Document, float]]:
        """返回 [(Document, score)]，score 为向量距离（越小越相似）。

        支持按 city / doc_type / doc_types / subtypes 过滤。供 search_scenic_rag 与调试使用。
        """
        store = PGVector.from_existing_index(
            embedding=self.embeddings,
            collection_name=self.collection,
            connection=self.connection_string,
            use_jsonb=True,
        )
        k = k or settings.RAG_TOP_K
        f = self._build_filter(city, doc_type, doc_types, subtypes)
        if f:
            return store.similarity_search_with_score(query, k=k, filter=f)
        return store.similarity_search_with_score(query, k=k)
