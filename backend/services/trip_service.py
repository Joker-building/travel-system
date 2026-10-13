"""行程服务：行程CRUD、行程节点管理"""

from datetime import datetime, date

from sqlalchemy.orm import Session

from models.trip import Trip
from models.trip_detail import TripDetail
from schemas.trip import (
    TripCreateRequest,
    TripUpdateRequest,
    TripDetailUpdateRequest,
)


class TripService:
    """行程管理服务"""

    @staticmethod
    def get_trip_status(trip: Trip) -> str:
        """根据当前时间和行程日期判断状态"""
        today = date.today()
        if not trip.start_date or not trip.end_date:
            return "准备中"

        if today < trip.start_date:
            days_until = (trip.start_date - today).days
            if days_until > 3:
                return "准备中"
            else:
                return "即将出发"
        elif trip.start_date <= today <= trip.end_date:
            return "进行中"
        else:
            return "已完成"

    @staticmethod
    def get_user_trips(db: Session, user_id: int) -> list:
        """获取用户所有行程"""
        trips = (
            db.query(Trip)
            .filter(Trip.user_id == user_id)
            .order_by(Trip.create_time.desc())
            .all()
        )
        result = []
        for trip in trips:
            result.append(
                {
                    "id": trip.id,
                    "user_id": trip.user_id,
                    "trip_name": trip.trip_name,
                    "dest_city": trip.dest_city,
                    "start_date": trip.start_date.isoformat() if trip.start_date else None,
                    "end_date": trip.end_date.isoformat() if trip.end_date else None,
                    "total_budget": trip.total_budget,
                    "travel_days": trip.travel_days,
                    "create_time": trip.create_time.strftime("%Y-%m-%d %H:%M:%S")
                    if trip.create_time
                    else "",
                    "status": TripService.get_trip_status(trip),
                }
            )
        return result

    @staticmethod
    def create_trip(db: Session, user_id: int, req: TripCreateRequest) -> dict:
        """创建新行程"""
        travel_days = 1
        if req.start_date and req.end_date:
            travel_days = (req.end_date - req.start_date).days + 1
            travel_days = max(travel_days, 1)

        trip = Trip(
            user_id=user_id,
            trip_name=req.trip_name,
            dest_city=req.dest_city,
            start_date=req.start_date,
            end_date=req.end_date,
            total_budget=req.total_budget,
            travel_days=travel_days,
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        db.add(trip)
        db.commit()
        db.refresh(trip)

        return {
            "id": trip.id,
            "trip_name": trip.trip_name,
            "dest_city": trip.dest_city,
            "start_date": trip.start_date.isoformat() if trip.start_date else None,
            "end_date": trip.end_date.isoformat() if trip.end_date else None,
            "total_budget": trip.total_budget,
            "travel_days": trip.travel_days,
            "message": "行程创建成功",
        }

    @staticmethod
    def update_trip(db: Session, trip_id: int, req: TripUpdateRequest) -> dict:
        """更新行程信息"""
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            return {"success": False, "message": "行程不存在"}

        if req.trip_name is not None:
            trip.trip_name = req.trip_name
        if req.dest_city is not None:
            trip.dest_city = req.dest_city
        if req.start_date is not None:
            trip.start_date = req.start_date
        if req.end_date is not None:
            trip.end_date = req.end_date
        if req.total_budget is not None:
            trip.total_budget = req.total_budget

        # 重新计算天数
        if trip.start_date and trip.end_date:
            trip.travel_days = max((trip.end_date - trip.start_date).days + 1, 1)

        trip.update_time = datetime.now()
        db.commit()
        db.refresh(trip)

        return {"success": True, "message": "行程更新成功"}

    @staticmethod
    def delete_trip(db: Session, trip_id: int) -> dict:
        """删除行程（级联删除行程节点）"""
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            return {"success": False, "message": "行程不存在"}

        # 先删除关联的行程节点
        db.query(TripDetail).filter(TripDetail.trip_id == trip_id).delete()
        db.delete(trip)
        db.commit()

        return {"success": True, "message": "行程删除成功"}

    @staticmethod
    def get_trip_detail(db: Session, trip_id: int) -> dict:
        """获取行程详情（含景点信息）"""
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            return None

        details = (
            db.query(TripDetail)
            .filter(TripDetail.trip_id == trip_id)
            .order_by(TripDetail.day_num, TripDetail.sort_order)
            .all()
        )

        detail_list = []
        for d in details:
            scenic = None
            if d.scenic_spot:
                scenic = {
                    "id": d.scenic_spot.id,
                    "name": d.scenic_spot.name,
                    "city": d.scenic_spot.city,
                    "introduction": d.scenic_spot.introduction,
                    "address": d.scenic_spot.address,
                    "open_time": d.scenic_spot.open_time,
                    "price": d.scenic_spot.price,
                    "latitude": d.scenic_spot.latitude,
                    "longitude": d.scenic_spot.longitude,
                    "special_notice": d.scenic_spot.special_notice,
                    "suggested_duration": d.scenic_spot.suggested_duration,
                }
            detail_list.append(
                {
                    "id": d.id,
                    "trip_id": d.trip_id,
                    "scenic_id": d.scenic_id,
                    "start_time": d.start_time.strftime("%H:%M") if d.start_time else None,
                    "end_time": d.end_time.strftime("%H:%M") if d.end_time else None,
                    "remark": d.remark,
                    "day_num": d.day_num,
                    "sort_order": d.sort_order,
                    "spot_budget": d.spot_budget,
                    "scenic_spot": scenic,
                }
            )

        # 计算总预算
        total_budget = sum(d.spot_budget for d in details if d.spot_budget)

        return {
            "id": trip.id,
            "user_id": trip.user_id,
            "trip_name": trip.trip_name,
            "dest_city": trip.dest_city,
            "start_date": trip.start_date.isoformat() if trip.start_date else None,
            "end_date": trip.end_date.isoformat() if trip.end_date else None,
            "total_budget": trip.total_budget,
            "travel_days": trip.travel_days,
            "status": TripService.get_trip_status(trip),
            "details": detail_list,
            "calculated_budget": total_budget,
        }

    @staticmethod
    def update_trip_detail(db: Session, detail_id: int, req: TripDetailUpdateRequest) -> dict:
        """更新行程节点"""
        detail = db.query(TripDetail).filter(TripDetail.id == detail_id).first()
        if not detail:
            return {"success": False, "message": "行程节点不存在"}

        if req.start_time is not None:
            detail.start_time = req.start_time
        if req.end_time is not None:
            detail.end_time = req.end_time
        if req.remark is not None:
            detail.remark = req.remark
        if req.spot_budget is not None:
            detail.spot_budget = req.spot_budget
        if req.sort_order is not None:
            detail.sort_order = req.sort_order
        if req.day_num is not None:
            detail.day_num = req.day_num

        db.commit()
        return {"success": True, "message": "行程节点更新成功"}

    @staticmethod
    def delete_trip_detail(db: Session, detail_id: int) -> dict:
        """删除行程节点"""
        detail = db.query(TripDetail).filter(TripDetail.id == detail_id).first()
        if not detail:
            return {"success": False, "message": "行程节点不存在"}

        db.delete(detail)
        db.commit()
        return {"success": True, "message": "景点已删除"}

    @staticmethod
    def add_travel_day(db: Session, trip_id: int) -> dict:
        """新增行程天数"""
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            return {"success": False, "message": "行程不存在"}

        trip.travel_days += 1
        if trip.end_date:
            from datetime import timedelta

            trip.end_date = trip.end_date + timedelta(days=1)
        trip.update_time = datetime.now()
        db.commit()
        return {"success": True, "message": "新增天数成功", "travel_days": trip.travel_days}

    @staticmethod
    def delete_travel_day(db: Session, trip_id: int, day_num: int) -> dict:
        """删除行程天数"""
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            return {"success": False, "message": "行程不存在"}

        if trip.travel_days <= 1:
            return {"success": False, "message": "至少保留一天行程"}

        # 删除该天所有节点
        db.query(TripDetail).filter(
            TripDetail.trip_id == trip_id, TripDetail.day_num == day_num
        ).delete()

        # 将后续天数的 day_num 依次减1
        db.query(TripDetail).filter(
            TripDetail.trip_id == trip_id, TripDetail.day_num > day_num
        ).update({TripDetail.day_num: TripDetail.day_num - 1})

        trip.travel_days -= 1
        if trip.end_date:
            from datetime import timedelta

            trip.end_date = trip.end_date - timedelta(days=1)
        trip.update_time = datetime.now()
        db.commit()
        return {"success": True, "message": "删除天数成功", "travel_days": trip.travel_days}
