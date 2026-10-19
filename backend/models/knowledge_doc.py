"""知识库语料表（RAG 静态知识入库源）

与 scenic_spot 同级，承载 RAG 知识库规划里的「静态知识」整类语料：
  - city       城市知识（某城市的概览 / 最佳季节 / 交通 / 美食 / 必玩）
  - guide      深度攻略（某城市或某主题的玩法深度解析）
  - topic      主题专题（美食之旅 / 亲子游 / 自然风光 / 历史古迹等跨城主题）
  - itinerary  行程模板（X 日游模板，引用真实景点名）
  - faq        常见问题（通用出行问答）

这些文档经 scripts/seed_knowledge_corpus.py 灌入，再由建索引脚本统一索引进
pgvector（与 scenic_spot 共用同一集合，靠 doc_type 元数据区分）。
后续你可用自己的真实攻略批量替换 / 追加，数据始终在你手里的 MySQL。
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text

from database import Base


class KnowledgeDoc(Base):
    """知识库语料表"""

    __tablename__ = "knowledge_doc"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="语料id")
    doc_type = Column(String(30), nullable=False, index=True,
                      comment="类型: city/guide/topic/itinerary/faq")
    title = Column(String(200), nullable=False, comment="标题")
    city = Column(String(50), default="", index=True,
                 comment="所属城市（通用类如 FAQ/主题可为空）")
    category = Column(String(50), default="", comment="分类 / 主题标签")
    content = Column(Text, nullable=False, comment="正文（用于语义检索）")
    tags = Column(String(500), default="", comment="标签，逗号分隔")
    source = Column(String(100), default="seed",
                   comment="来源: seed(脚本生成) / llm / user(人工)")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
