"""一次性归一化 scenic_spot 城市名 + 清理占位脏值。

问题背景（已核验真实数据）：
  1) city='武汉市' 的 6 行（id 101~106）地址均为「武汉市xxx」，是真·武汉景点，
     仅城市名多写「市」→ 归一为 '武汉'。
  2) city='北京延庆区' 的 1 行（id 32 八达岭长城）地址为「北京市延庆区」，
     延庆是北京辖区 → 归一为 '北京'。
  3) id=41 整行是占位假数据（name/address/introduction 全为 'string'，
     经纬度 30/104 为通用假坐标，rating=0）→ 删除。

为什么必须归一化：RAG 检索按 city 元数据精确过滤
  (cmetadata @> '{"city":"..."}')，若用户问「武汉」而库里标的是「武汉市」，
  那 6 条会漏检。归一化后召回一致。

安全：脚本先建备份表 scenic_spot_backup_YYYYMMDD 再改数据，可回滚。

运行（backend 目录下）：
  python scripts/clean_scenic_city.py
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from config import settings


def main():
    pwd = getattr(settings, "DB_PASSWORD", None) or "root123456"
    url = (f"mysql+pymysql://{settings.DB_USER}:{pwd}"
           f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}?charset=utf8mb4")
    eng = create_engine(url)
    backup_tbl = f"scenic_spot_backup_{date.today():%Y%m%d}"

    with eng.begin() as c:  # begin() 自动开启事务，异常回滚
        # —— 0) 备份（可重跑：已存在则跳过）——
        exists = c.execute(text(f"SHOW TABLES LIKE '{backup_tbl}'")).fetchone()
        if not exists:
            c.execute(text(f"CREATE TABLE {backup_tbl} AS SELECT * FROM scenic_spot"))
            print(f"[备份] 已建备份表 {backup_tbl}（回滚用）")
        else:
            print(f"[备份] {backup_tbl} 已存在，跳过")

        before = c.execute(text("SELECT COUNT(*), "
                                "SUM(city='武汉市'), SUM(city='北京延庆区'), "
                                "SUM(id=41) FROM scenic_spot")).fetchone()
        print(f"[变更前] 总行数={before[0]}  武汉市={before[1]}  北京延庆区={before[2]}  id41={before[3]}")

        # —— 1) 城市名归一化 ——
        u1 = c.execute(text("UPDATE scenic_spot SET city='武汉' WHERE city='武汉市'"))
        u2 = c.execute(text("UPDATE scenic_spot SET city='北京' WHERE city='北京延庆区'"))
        print(f"[归一化] 武汉市→武汉: {u1.rowcount} 行；北京延庆区→北京: {u2.rowcount} 行")

        # —— 2) 清理占位脏值（id=41）——
        d = c.execute(text("DELETE FROM scenic_spot WHERE id=41"))
        print(f"[清理] 删除占位脏值 id=41: {d.rowcount} 行")

        after = c.execute(text("SELECT COUNT(*), "
                               "SUM(city='武汉市'), SUM(city='北京延庆区'), SUM(id=41) "
                               "FROM scenic_spot")).fetchone()
        print(f"[变更后] 总行数={after[0]}  武汉市={after[1]}  北京延庆区={after[2]}  id41={after[3]}")

        # —— 3) 归一化后城市分布 ——
        print("[城市分布]")
        for row in c.execute(text("SELECT city, COUNT(*) FROM scenic_spot "
                                  "GROUP BY city ORDER BY COUNT(*) DESC")).fetchall():
            print(f"    {row[0]}: {row[1]}")

    print("[完成] 归一化 + 清理结束。如需回滚：")
    print(f"    INSERT INTO scenic_spot SELECT * FROM {backup_tbl};")


if __name__ == "__main__":
    main()
