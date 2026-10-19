"""数据库模型汇总"""

from models.user import User
from models.trip import Trip
from models.trip_detail import TripDetail
from models.scenic_spot import ScenicSpot
from models.chat import ChatSession, ChatMessage
from models.knowledge_doc import KnowledgeDoc

__all__ = ["User", "Trip", "TripDetail", "ScenicSpot", "ChatSession",
           "ChatMessage", "KnowledgeDoc"]
