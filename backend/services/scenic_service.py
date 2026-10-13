"""景点服务：景点搜索、添加景点到行程"""

import json
from datetime import datetime, time

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.scenic_spot import ScenicSpot
from models.trip_detail import TripDetail
from models.trip import Trip


def _parse_tags(tags) -> list:
    """tags 字段统一解析为列表（DB 中存 JSON 字符串或逗号分隔）"""
    if isinstance(tags, list):
        return tags
    if not tags:
        return []
    try:
        parsed = json.loads(tags)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    return [t.strip() for t in str(tags).split(",") if t.strip()]


class ScenicService:
    """景点管理服务"""

    @staticmethod
    def search_scenic_spots(db: Session, keyword: str, city: str = "") -> list:
        """搜索景点（数据库匹配）"""
        query = db.query(ScenicSpot)
        if city:
            query = query.filter(ScenicSpot.city == city)
        if keyword:
            query = query.filter(
                or_(
                    ScenicSpot.name.like(f"%{keyword}%"),
                    ScenicSpot.address.like(f"%{keyword}%"),
                )
            )
        spots = query.limit(20).all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "city": s.city,
                "category": s.category or "",
                "introduction": s.introduction,
                "address": s.address,
                "open_time": s.open_time,
                "price": s.price,
                "rating": s.rating or 0,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "tel": s.tel or "",
                "tags": _parse_tags(s.tags),
                "special_notice": s.special_notice,
                "suggested_duration": s.suggested_duration,
                "recommendation": s.recommendation or "",
            }
            for s in spots
        ]

    @staticmethod
    def add_scenic_to_trip(
        db: Session, scenic_id: int, trip_id: int, day_num: int = 1
    ) -> dict:
        """将已有景点添加到行程"""
        scenic = db.query(ScenicSpot).filter(ScenicSpot.id == scenic_id).first()
        if not scenic:
            return {"success": False, "message": "景点不存在"}

        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            return {"success": False, "message": "行程不存在"}

        # 获取当前天内最大排序号
        max_sort = (
            db.query(TripDetail.sort_order)
            .filter(TripDetail.trip_id == trip_id, TripDetail.day_num == day_num)
            .order_by(TripDetail.sort_order.desc())
            .first()
        )
        next_sort = (max_sort[0] + 1) if max_sort else 1

        detail = TripDetail(
            trip_id=trip_id,
            scenic_id=scenic_id,
            start_time=None,
            end_time=None,
            remark="",
            day_num=day_num,
            sort_order=next_sort,
            spot_budget=scenic.price or 0,
            create_time=datetime.now(),
        )
        db.add(detail)
        db.commit()
        db.refresh(detail)

        return {
            "success": True,
            "message": "景点已添加到行程",
            "detail_id": detail.id,
        }

    @staticmethod
    def get_scenic_by_id(db: Session, scenic_id: int) -> dict | None:
        """根据ID获取景点信息"""
        scenic = db.query(ScenicSpot).filter(ScenicSpot.id == scenic_id).first()
        if not scenic:
            return None
        return {
            "id": scenic.id,
            "name": scenic.name,
            "city": scenic.city,
            "category": scenic.category or "",
            "introduction": scenic.introduction,
            "address": scenic.address,
            "open_time": scenic.open_time,
            "price": scenic.price,
            "rating": scenic.rating or 0,
            "latitude": scenic.latitude,
            "longitude": scenic.longitude,
            "tel": scenic.tel or "",
            "tags": _parse_tags(scenic.tags),
            "special_notice": scenic.special_notice,
            "suggested_duration": scenic.suggested_duration,
            "recommendation": scenic.recommendation or "",
        }
