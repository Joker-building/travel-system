"""灌入知识库 starter 种子语料（写入 knowledge_doc 表）。

用途：一次性为 RAG 知识库补齐「静态知识」整类语料的 starter 版本——
  城市知识(city) / 深度攻略(guide) / 行程模板(itinerary) / 主题专题(topic) / 常见问题(faq)。
  行程模板与攻略会引用 scenic_spot 表里【真实存在的景点名】，保证检索命中即真实。

重要说明：
  - 本脚本生成的是「starter 种子」，城市概况/美食/贴士为通用可读内容，
    准确性有限，请在上线前替换为你的真实攻略（数据都在 MySQL，随时可改）。
  - 可重复运行：每次会先清空 source='seed' 的旧种子再重新灌入，便于迭代。
  - 不触碰 scenic_spot，也不删除你手动 source='user' 的语料。

运行（backend 目录下）：
  python scripts/seed_knowledge_corpus.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

from config import settings
from database import Base, engine
from models.knowledge_doc import KnowledgeDoc
from models.scenic_spot import ScenicSpot


# ===================== 13 城通用画像（starter，待替换为真实内容） =====================
CITY_PROFILES = {
    "武汉": {
        "overview": "湖北省会，长江与汉江在此交汇，素有「九省通衢」之称，是中部地区的交通与文教中心，市内有东湖、黄鹤楼、江汉路等代表性地标。",
        "best_season": "春季（3-5 月）与秋季（9-11 月）气候最宜人；夏季炎热潮湿，冬季湿冷。",
        "food": "热干面、鸭脖、豆皮、糊汤粉是本地招牌，户部巷与吉庆街是集中体验地。",
        "tips": "夏季高温高湿注意防暑补水；跨江通行留意桥隧与轮渡时刻；热门景区周末人流大，建议错峰。",
    },
    "三亚": {
        "overview": "海南岛最南端的热带滨海旅游城市，拥有亚龙湾、大东海、天涯海角等海滨资源，是国内著名的避寒度假目的地。",
        "best_season": "每年 10 月至次年 4 月为最佳避寒季；夏季多台风，出行前关注预警。",
        "food": "海鲜、椰子鸡、清补凉、文昌鸡值得一试，第一市场可自选海鲜加工。",
        "tips": "紫外线强务必防晒；水上项目认准正规运营商；旺季房价波动大，尽早预订。",
    },
    "北京": {
        "overview": "中华人民共和国首都，三千余年建城史、八百余年建都史，故宫、长城、颐和园等世界遗产密集，是历史与当代交汇的超大城市。",
        "best_season": "春秋两季（4-5 月、9-10 月）最舒适；冬季干冷，夏季闷热多雨。",
        "food": "北京烤鸭、炸酱面、涮羊肉、驴打滚等京味小吃遍布老城。",
        "tips": "故宫、国博等热门场馆需提前预约；地铁网络发达，市内优先公共交通；旺季景区排队久。",
    },
    "济南": {
        "overview": "山东省会，以「泉城」闻名，趵突泉、大明湖、千佛山构成城市核心景致，泉水文化是最大特色。",
        "best_season": "春季与秋季宜人；夏季雨水较多，冬季偏冷。",
        "food": "鲁菜发源地之一，把子肉、甜沫、油旋、奶汤蒲菜值得品尝。",
        "tips": "赏泉最佳在丰水期；老城区景点集中，步行或骑行即可串联；部分泉水冬季水量小。",
    },
    "南京": {
        "overview": "江苏省会，六朝古都、十朝都会，钟山风景区、夫子庙、明城墙承载厚重历史，兼有大学校园与滨江风光。",
        "best_season": "春秋最佳，春季樱花、秋季梧桐大道尤为出片。",
        "food": "盐水鸭、鸭血粉丝汤、汤包、皮肚面是本地经典。",
        "tips": "历史类场馆众多，建议规划主题线路；地铁覆盖好；夏季闷热注意防暑。",
    },
    "广州": {
        "overview": "广东省会、千年商都，岭南文化中心，骑楼、珠江夜游、早茶与商贸氛围共同构成独特城市气质。",
        "best_season": "秋冬季（10-12 月）最舒适；春季回南天潮湿，夏季炎热多雨。",
        "food": "早茶、烧腊、肠粉、艇仔粥、双皮奶是广府美食代表。",
        "tips": "饮食偏清淡鲜甜；市内地铁发达；回南天注意防潮。",
    },
    "长沙": {
        "overview": "湖南省会，近年热门「网红」城市，岳麓山、橘子洲、湖南博物院与烟火气十足的夜经济共同出圈。",
        "best_season": "春秋最舒适；夏季酷热，冬季湿冷。",
        "food": "臭豆腐、糖油粑粑、剁椒鱼头、茶颜悦色等网红与湘菜并存。",
        "tips": "网红店排队普遍，错峰或提前取号；夜生活丰富，注意作息；湖南博物院需预约。",
    },
    "南昌": {
        "overview": "江西省会，因「军旗升起的地方」而著名，滕王阁临赣江而立，八一起义纪念馆承载红色记忆。",
        "best_season": "春秋宜人；夏季炎热，冬季阴冷。",
        "food": "赣菜口味鲜辣，米粉、瓦罐汤、藜蒿炒腊肉是代表。",
        "tips": "滕王阁可结合赣江夜景；红色景点集中，适合半日主题游；夏季注意防暑。",
    },
    "宜昌": {
        "overview": "湖北西部城市，因三峡大坝、葛洲坝而知名，是长江三峡门户与水电梯级开发的核心，兼具工程奇观与峡江风光。",
        "best_season": "春秋最佳；夏季峡区较热，冬季偏冷。",
        "food": "峡江鱼、凉虾、萝卜饺子、土家腊肉有地方特色。",
        "tips": "观坝需走专用景区；峡区游船受水位与天气影响；自驾注意山路。",
    },
    "杭州": {
        "overview": "浙江省会，以西湖闻名天下，「淡妆浓抹总相宜」，兼具江南水乡韵味与数字经济活力。",
        "best_season": "春季（3-5 月）与秋季（9-11 月）最佳，西湖四季皆景。",
        "food": "杭帮菜清淡鲜美，西湖醋鱼、龙井虾仁、东坡肉、片儿川值得一试。",
        "tips": "西湖景区周末人流大，建议早出；环湖步道骑行体验好；梅雨季节备伞。",
    },
    "重庆": {
        "overview": "西部直辖市，山城、雾都、桥都多重气质叠加，洪崖洞、长江索道、磁器口与火锅共同构成魔幻立体的城市体验。",
        "best_season": "春秋最舒适；夏季闷热（「火炉」），冬季多雾湿冷。",
        "food": "重庆火锅、小面、酸辣粉、江湖菜麻辣鲜香。",
        "tips": "地形立体、导航易飘，多留时间找路；轻轨穿楼等打卡点多；夏季防暑。",
    },
    "恩施": {
        "overview": "湖北恩施土家族苗族自治州，以喀斯特地貌、大峡谷、腾龙洞与土家风情著称，是华中地区的自然秘境。",
        "best_season": "春夏季（4-9 月）水量充沛、绿意最盛；冬季部分山区寒冷。",
        "food": "土家腊肉、合渣、炕土豆、榨广椒风味独特。",
        "tips": "景区多山路，自驾慎行；峡谷步道湿滑穿防滑鞋；天气多变带雨具。",
    },
    "成都": {
        "overview": "四川省会，天府之国，以悠闲节奏、大熊猫、川菜与周边世界级自然文化景观（都江堰、青城山等）著称。",
        "best_season": "春秋最佳；冬季多阴天湿冷，夏季闷热。",
        "food": "火锅、串串、担担面、夫妻肺片、龙抄手麻辣鲜香。",
        "tips": "看大熊猫建议早去；周边景区距离市区较远，预留交通时间；生活节奏慢，行程别排太满。",
    },
}

TRANSPORT_GENERIC = "飞机与高铁均可直达，市内地铁 / 公交网络完善，市内景点间多可公共交通串联。"


def _spot_bullets(spot_names, limit=6):
    return "\n".join(f"- {n}" for n in spot_names[:limit]) or "- （本库暂未收录该城市景点）"


def build_city_doc(city, profile, spot_names):
    content = (
        f"# {city} · 城市旅游知识\n\n"
        f"## 城市概况\n{profile['overview']}\n\n"
        f"## 最佳旅游季节\n{profile['best_season']}\n\n"
        f"## 交通到达\n{TRANSPORT_GENERIC}\n\n"
        f"## 必玩景点（节选自本库真实景点）\n{_spot_bullets(spot_names)}\n\n"
        f"## 特色美食\n{profile['food']}\n\n"
        f"## 出行贴士\n{profile['tips']}\n\n"
        f"> 注：本篇为 starter 种子语料，请在上线前替换为更详实的真实内容。"
    )
    return KnowledgeDoc(doc_type="city", title=f"{city}城市旅游知识",
                        city=city, category="城市知识", content=content,
                        tags=f"{city},城市知识,旅游攻略", source="seed")


def build_guide_doc(city, profile, spot_names):
    content = (
        f"# {city} · 深度游玩攻略\n\n"
        f"{profile['overview']}\n\n"
        f"## 经典玩法\n结合本库真实景点，建议这样安排：\n{_spot_bullets(spot_names)}\n\n"
        f"## 美食地图\n{profile['food']}\n\n"
        f"## 避坑与贴士\n{profile['tips']}\n\n"
        f"> 注：本篇为 starter 种子语料，请在上线前替换为更详实的真实攻略。"
    )
    return KnowledgeDoc(doc_type="guide", title=f"{city}深度游玩攻略",
                        city=city, category="深度攻略", content=content,
                        tags=f"{city},深度攻略,玩法", source="seed")


def build_itinerary_doc(city, profile, spot_names):
    names = spot_names[:6]
    def day(block):
        lines = []
        for label, name in block:
            lines.append(f"- {label}：{name}" if name else f"- {label}：自由活动 / 机动")
        return "\n".join(lines)
    d1 = day([("上午", names[0] if len(names) > 0 else None),
              ("下午", names[1] if len(names) > 1 else None),
              ("晚上", names[2] if len(names) > 2 else None)])
    d2 = day([("上午", names[3] if len(names) > 3 else None),
              ("下午", names[4] if len(names) > 4 else None),
              ("晚上", names[5] if len(names) > 5 else None)])
    content = (
        f"# {city} · 三日游行程模板\n\n"
        f"> 本模板引用本库真实景点名，可按体力与季节自行增减。\n\n"
        f"## 第 1 天\n{d1}\n\n"
        f"## 第 2 天\n{d2}\n\n"
        f"## 第 3 天\n- 上午：周边漫步 / 美食打卡 / 机动\n- 下午：返程或自由活动\n\n"
        f"## 出行贴士\n{profile['tips']}\n\n"
        f"> 注：本篇为 starter 种子模板，实际行程请结合开放时间与交通动态调整。"
    )
    return KnowledgeDoc(doc_type="itinerary", title=f"{city}三日游行程模板",
                        city=city, category="行程模板", content=content,
                        tags=f"{city},行程模板,三日游", source="seed")


# ===================== 全局 FAQ =====================
FAQ_ITEMS = [
    ("怎么规划一次旅行？",
     "规划一次旅行可分四步：① 定目的地与出行时间（结合季节、假期）；② 估算预算（交通+住宿+门票+餐饮+购物）；"
     "③ 列必玩清单并按地理就近排程，避免绕路；④ 提前订票订房、查天气与预约要求。本系统的 AI 可据你的城市、天数、预算与偏好直接生成行程。"),
    ("带老人或小孩出游要注意什么？",
     "优先选步道平缓、配套设施完善的景点，控制每日步行强度；备好常用药与证件；景点优先选可坐缆车 / 游船减负的；"
     "餐饮兼顾清淡与卫生；行程留足休息时间，避免赶场。"),
    ("旅游预算一般怎么估算？",
     "常见占比参考：交通 30%、住宿 30%、餐饮 20%、门票与游玩 15%、机动 5%。城市与淡旺季差异大，"
     "可先定总预算再反向压缩弹性项。本系统支持按预算档位（经济 / 舒适 / 轻奢）生成方案。"),
    ("景点门票需要提前预约吗？",
     "热门城市的核心场馆（如北京故宫、湖南博物院等）普遍需提前线上预约，且限流；自然景区多可现场或线上购票。"
     "建议出行前 1-3 天确认预约政策，避免白跑。"),
    ("怎么查目的地天气？",
     "可通过本系统天气查询（后端代理和风天气）获取目的地未来几日预报，据此带衣物与雨具、安排室内外活动。山区与海滨需额外关注预警。"),
    ("自由行和跟团怎么选？",
     "自由行灵活、深度，适合有规划能力的人群；跟团省心、成本低，适合首次到访或语言 / 交通不便的目的地。"
     "折中方案是「半自由行」：大交通与住宿自订，当地参加一日游。"),
    ("出行要带哪些证件？",
     "身份证（住宿与购票必备）、学生证 / 老年证（部分景点优惠）、驾照（自驾）、护照（跨境）。建议手机存电子版备份，并买份短期旅行险。"),
    ("行程排得太赶怎么办？",
     "遵循「少而精」：每天核心景点不超过 2-3 个，按地理就近聚类；把赶路日与休整日交替；预留机动时间应对排队与天气。"
     "宁可少去一个景点，也别把旅行变成拉练。"),
]


def build_faq_docs():
    docs = []
    for i, (title, content) in enumerate(FAQ_ITEMS, 1):
        docs.append(KnowledgeDoc(doc_type="faq", title=f"FAQ{i}：{title}",
                                city="", category="常见问题",
                                content=f"# {title}\n\n{content}",
                                tags="FAQ,通用,出行问答", source="seed"))
    return docs


# ===================== 全局主题专题 =====================
TOPIC_ITEMS = [
    ("美食之旅主题专题", "美食",
     "跨城「美食之旅」怎么玩：以城市代表性小吃与餐厅为主线，把餐饮本身当作景点。"
     "例如武汉热干面与户部巷、长沙臭豆腐与茶饮、广州早茶、成都火锅、北京烤鸭。"
     "建议每天安排 1-2 顿特色餐 + 一条美食街区漫步，其余正餐从简，避免肠胃负担。"),
    ("亲子游主题专题", "亲子",
     "跨城「亲子游」怎么排：优先动物园、海洋馆、主题乐园、科技馆等互动强的项目，"
     "控制单日步行与车程，午休留白；备好推车、零食、常用药；选择亲子友好酒店。"
     "本库景点可按 category 筛选「主题乐园 / 自然风光」类。"),
    ("自然风光之旅主题专题", "自然",
     "跨城「自然风光之旅」怎么排：以山水峡谷、湖泊湿地为主线，如杭州西湖、宜昌三峡、"
     "恩施大峡谷、重庆山城地貌。这类行程受天气影响大，出行前查预报；穿防滑鞋、带雨具，"
     "预留体力应对步道与台阶。"),
    ("历史古迹之旅主题专题", "历史",
     "跨城「历史古迹之旅」怎么排：以古都、遗迹、博物馆为主线，如北京故宫长城、"
     "南京明城墙与中山陵、南昌滕王阁与八一起义纪念馆、济南趵突泉大明湖。"
     "建议提前预约并搭配讲解，单点放慢节奏，比走马观花更有收获。"),
]


def build_topic_docs():
    docs = []
    for title, cat, content in TOPIC_ITEMS:
        docs.append(KnowledgeDoc(doc_type="topic", title=title,
                                city="", category=cat,
                                content=f"# {title}\n\n{content}",
                                tags=f"主题,{cat},专题", source="seed"))
    return docs


def main():
    # 确保 knowledge_doc 表存在（与后端 create_all 一致；脚本独立运行也安全）
    Base.metadata.create_all(bind=engine)

    SessionLocal = __import__("database").SessionLocal
    db = SessionLocal()
    try:
        # 1) 拉取 scenic_spot 的真实城市与景点名（供攻略 / 行程模板引用）
        rows = db.query(ScenicSpot.city, ScenicSpot.name).all()
        spots_by_city = {}
        for city, name in rows:
            spots_by_city.setdefault(city, []).append(name)

        # 2) 清空旧 seed（保留用户手动 source='user' 的语料），便于重复运行
        deleted = db.query(KnowledgeDoc).filter(KnowledgeDoc.source == "seed").delete()
        print(f"[清理] 删除旧 seed 语料 {deleted} 条")

        # 3) 逐城生成 city / guide / itinerary
        total = 0
        for city, profile in CITY_PROFILES.items():
            spot_names = spots_by_city.get(city, [])
            if not spot_names:
                print(f"[跳过] {city} 在 scenic_spot 中无景点，未生成语料")
                continue
            db.add(build_city_doc(city, profile, spot_names))
            db.add(build_guide_doc(city, profile, spot_names))
            db.add(build_itinerary_doc(city, profile, spot_names))
            total += 3
            print(f"[生成] {city}: 城市知识 + 深度攻略 + 行程模板（引用 {len(spot_names)} 个真实景点）")

        # 4) 全局 FAQ 与主题专题
        faq_docs = build_faq_docs()
        topic_docs = build_topic_docs()
        for d in faq_docs + topic_docs:
            db.add(d)
        total += len(faq_docs) + len(topic_docs)
        print(f"[生成] 全局 FAQ {len(faq_docs)} 条 + 主题专题 {len(topic_docs)} 条")

        db.commit()
        print(f"[完成] 共写入 starter 种子语料 {total} 条到 knowledge_doc 表。"
              f"后续运行 build 脚本重建向量索引即可生效。")
    except Exception as e:
        db.rollback()
        print("[失败]", repr(e))
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
