"""回填 scenic_spot 稀疏字段（recommendation / category / tags）。

背景（已核验真实数据）：
  scenic_spot 共 186 条，但 recommendation / category / tags / rating 仅约 19 条有值，
  price 约 78 条。当前 RAG 索引对多数景点基本只靠 introduction，检索与卡片质量受限。

本脚本只填「空值」，不覆盖已有内容，也不删数据：
  - category：按景点名称启发式归类（自然风光 / 历史古迹 / 主题乐园 / 城市观光）。
  - tags：由 category + 城市 + 是否免费 组合。
  - recommendation：用真实字段（名称/城市/简介首句/建议时长/特殊提醒）拼装推荐语。
  - rating：不编造评分，保持原值（0）；如需真实评分请后续人工 / 接口补全。

安全：先建备份表 scenic_spot_backup_YYYYMMDD，可回滚。

运行（backend 目录下）：
  python scripts/backfill_scenic_fields.py
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

from config import settings
from database import Base, engine, SessionLocal
from models.scenic_spot import ScenicSpot


def infer_category(name: str) -> str:
    """按景点名称关键字启发式归类（仅用于补全缺失分类）。"""
    n = name or ""
    nature = ["山", "峰", "岭", "岳", "湖", "江", "河", "海", "溪", "潭", "泉",
              "谷", "岛", "森林", "湿地", "峡", "瀑布", "草原", "公园"]
    history = ["寺", "庙", "观", "宫", "殿", "陵", "墓", "祠", "阁", "塔", "楼",
               "城墙", "遗址", "故居", "纪念", "博物馆", "古镇", "古城", "碑", "院", "衙"]
    theme = ["乐园", "游乐园", "动物园", "海洋", "滑雪", "游乐", "方特", "欢乐", "迪士尼", "水世界"]
    city = ["街", "道", "广场", "商圈", "中心", "步行街", "市场", "大学", "校区", "书店", "mall"]
    for kw in nature:
        if kw in n:
            return "自然风光"
    for kw in history:
        if kw in n:
            return "历史古迹"
    for kw in theme:
        if kw in n:
            return "主题乐园"
    for kw in city:
        if kw in n:
            return "城市观光"
    return "城市观光"


def build_recommendation(s: ScenicSpot) -> str:
    """用真实字段拼装推荐语（不编造事实）。"""
    intro = (s.introduction or "").strip()
    first_sentence = ""
    if intro:
        # 取简介首句（以句号 / 分号截断，限长避免过长）
        for sep in ["。", "；", ";", "."]:
            if sep in intro:
                first_sentence = intro.split(sep)[0][:60] + "。"
                break
        if not first_sentence:
            first_sentence = intro[:60] + "。"
    duration = (s.suggested_duration or "约半天").strip()
    notice = (s.special_notice or "出行前请确认开放时间与门票政策").strip()
    return (f"{s.name}位于{s.city}，是当地颇具代表性的{s.category or '景点'}。"
            f"{first_sentence}建议游玩{duration}，{notice}")


def main():
    Base.metadata.create_all(bind=engine)
    backup_tbl = f"scenic_spot_backup_{date.today():%Y%m%d}"

    db = SessionLocal()
    try:
        # —— 0) 备份（可重跑：已存在则跳过）——
        exists = db.execute(text(f"SHOW TABLES LIKE '{backup_tbl}'")).fetchone()
        if not exists:
            db.execute(text(f"CREATE TABLE {backup_tbl} AS SELECT * FROM scenic_spot"))
            print(f"[备份] 已建备份表 {backup_tbl}（回滚用）")
        else:
            print(f"[备份] {backup_tbl} 已存在，跳过")

        rows = db.query(ScenicSpot).all()
        n_rec = n_cat = n_tag = 0
        for s in rows:
            changed = False
            if not (s.recommendation or "").strip():
                # 补 category 后再拼 recommendation，保证引用一致
                if not (s.category or "").strip():
                    s.category = infer_category(s.name)
                    n_cat += 1
                s.recommendation = build_recommendation(s)
                n_rec += 1
                changed = True
            else:
                if not (s.category or "").strip():
                    s.category = infer_category(s.name)
                    n_cat += 1
                    changed = True
            if not (s.tags or "").strip():
                free = "免费" if (s.price or 0) == 0 else "门票收费"
                s.tags = f"{s.category or '景点'},{s.city or ''},{free}"
                n_tag += 1
                changed = True
            if changed:
                db.add(s)

        db.commit()
        print(f"[回填] recommendation +{n_rec}  category +{n_cat}  tags +{n_tag}")
        print("[说明] rating 未编造，保持原值；如需真实评分请后续人工 / 接口补全。")
        print(f"[完成] 如需回滚：INSERT INTO scenic_spot SELECT * FROM {backup_tbl};")
    except Exception as e:
        db.rollback()
        print("[失败]", repr(e))
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
