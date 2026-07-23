#!/usr/bin/env python3
"""
Multi-source adult tag popularity score (research reconstruction).

Primary: Pornhub Insights 2025 Year in Review (global searches + top-20 country
searches/categories, traffic share ~77.5% of Pornhub).
Secondary: 2024 Pornhub top-30 search list adjusted by documented 2025 rank moves.
Tertiary: FANZA/East-Asia genre popularity (2026), used as regional boost only.

This is NOT proprietary platform telemetry. Rankings below ~#25 are reconstructed
estimates with declining confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# Approximate relative traffic weights among Pornhub top-20 countries (sum≈100).
# Order from Pornhub 2025 YIR; magnitudes are heuristic, not official shares.
COUNTRY_WEIGHT = {
    "US": 22.0,
    "MX": 9.0,
    "PH": 8.0,
    "BR": 7.0,
    "DE": 5.5,
    "FR": 4.0,  # partial-year access
    "IT": 4.0,
    "UK": 4.0,
    "ES": 3.5,
    "CA": 3.5,
    "JP": 3.0,
    "PL": 2.5,
    "AR": 2.5,
    "NL": 2.0,
    "CO": 2.0,
    "UA": 2.0,
    "AU": 2.0,
    "EG": 1.5,
    "PE": 1.5,
    "CL": 1.5,
}

# Points by position in a country's disclosed top searches (1-indexed).
POS_POINTS = {1: 100, 2: 80, 3: 65, 4: 55, 5: 45, 6: 38, 7: 32, 8: 28, 9: 24, 10: 20, 11: 16, 12: 13, 13: 11, 14: 9}


def canon(tag: str) -> str:
    aliases = {
        "milf": "milf",
        "mature": "mature",
        "mature woman": "mature",
        "lesbian": "lesbian",
        "lesbianas": "lesbian",
        "lesbicas": "lesbian",
        "anal": "anal",
        "hentai": "hentai",
        "anime": "anime",
        "animation": "animation",
        "japanese": "japanese",
        "asian": "asian",
        "latina": "latina",
        "pinay": "pinay",
        "pinoy": "pinoy",
        "indian": "indian",
        "korean": "korean",
        "chinese": "chinese",
        "ebony": "ebony",
        "arab": "arab",
        "arabic sex": "arab",
        "egyptian sex": "egyptian",
        "egyptian": "egyptian",
        "big ass": "big_ass",
        "culonas": "big_ass",
        "big tits": "big_tits",
        "big boobs": "big_tits",
        "femboy": "femboy",
        "trans": "trans",
        "transgender": "trans",
        "threesome": "threesome",
        "trio": "threesome",
        "creampie": "creampie",
        "blowjob": "blowjob",
        "pompino": "blowjob",
        "pov": "pov",
        "joi": "joi",
        "punheta guiada": "joi",
        "cosplay": "cosplay",
        "amateur": "amateur",
        "amatoriale italiano": "amateur",
        "homemade": "amateur",
        "casero": "amateur",
        "real amateur": "amateur",
        "masturbation": "masturbation",
        "squirting": "squirt",
        "squirt": "squirt",
        "cheating": "cheating",
        "cuckold": "cuckold",
        "hotwife": "hotwife",
        "step mom": "stepmom",
        "stepmother": "stepmom",
        "massage": "massage",
        "gangbang": "gangbang",
        "bbc": "bbc",
        "wife": "wife",
        "3d": "3d",
        "bbw": "bbw",
        "teacher": "teacher",
        "role play": "roleplay",
        "roleplay": "roleplay",
        "feet": "feet",
        "interracial": "interracial",
        "brazilian": "brazilian",
        "brasileira": "brazilian",
        "mexico": "mexican",
        "mexicana": "mexican",
        "colombiana": "colombian",
        "colombia": "colombian",
        "argentina": "argentine",
        "chilena": "chilean",
        "chile": "chilean",
        "peruana": "peruvian",
        "deutsch": "german",
        "german": "german",
        "francaise": "french",
        "french": "french",
        "italiano": "italian",
        "italian": "italian",
        "british": "british",
        "espanol": "spanish",
        "polskie": "polish",
        "polska": "polish",
        "dutch": "dutch",
        "russian porn": "russian",
        "porno es espanol": "spanish",
        "en español": "spanish",
        "couple": "couple",
        "facesitting": "facesitting",
        "pegging": "pegging",
        "furry": "furry",
        "twink": "twink",
        "bareback": "bareback",
        "scissoring": "scissoring",
        "solo female": "solo_female",
        "hardcore": "hardcore",
        "reality": "reality",
        "fetish": "fetish",
        "office sex": "office",
        "gilf": "gilf",
        "cougar": "cougar",
        "bisexual": "bisexual",
        "queer": "queer",
        "stockings": "stockings",
        "pantyhose": "pantyhose",
        "black stockings": "stockings",
        "facial": "facial",
        "bukkake": "bukkake",
        "ntr": "ntr",
        "cuckold / ntr": "ntr",
        "uniform": "uniform",
        "school": "school",
        "pantyhose/stockings": "stockings",
    }
    key = tag.strip().lower()
    return aliases.get(key, key.replace(" ", "_"))


# Country top searches extracted/paraphrased from Pornhub 2025 YIR country sections.
COUNTRY_SEARCHES: Dict[str, List[str]] = {
    "US": ["latina", "milf", "asian", "hentai", "lesbian", "threesome", "ebony", "mature", "trans", "pov", "joi", "cheating"],
    "MX": ["hentai", "lesbian", "big_ass", "mexican", "colombian", "femboy"],
    "PH": ["pinay", "pinoy", "japanese", "threesome", "chinese"],
    "BR": ["hentai", "brazilian", "joi", "anal"],
    "DE": ["german", "milf", "german", "femboy"],
    "FR": ["french", "hentai", "milf", "latina", "anal", "asian", "femboy"],
    "IT": ["italian", "milf", "amateur", "latina"],
    "UK": ["milf", "lesbian", "british", "facesitting", "asian", "pov", "indian", "big_ass"],
    "ES": ["milf", "hentai", "spanish", "lesbian", "anal", "argentine", "trans", "femboy"],
    "CA": ["asian", "milf", "hentai", "latina", "lesbian", "creampie", "anal", "threesome", "indian", "big_ass", "femboy", "joi", "pov"],
    "JP": ["japanese", "masturbation", "amateur", "squirt", "mature", "couple", "cosplay"],
    "PL": ["polish", "milf", "polish", "hentai", "anal", "femboy", "pov"],
    "AR": ["argentine", "hentai", "lesbian", "milf", "anal", "femboy", "spanish"],
    "NL": ["milf", "big_ass", "hentai", "femboy", "pov", "dutch"],
    "CO": ["colombian", "colombian", "spanish"],
    "UA": ["hentai", "milf", "amateur", "anime", "russian"],
    "AU": ["asian", "milf", "hentai", "lesbian", "threesome", "latina", "femboy"],
    "EG": ["egyptian", "arab", "milf", "big_ass", "egyptian", "anal", "latina"],
    "PE": ["big_ass", "colombian", "hentai", "peruvian", "amateur", "milf", "threesome"],
    "CL": ["chilean", "hentai", "chilean", "femboy"],
}

# Official / strongly attested global search ranks (Pornhub 2025 + MTL Blog).
GLOBAL_SEARCH_RANK = {
    "hentai": 1,
    "milf": 2,
    "pinay": 3,
    "lesbian": 4,
    "anal": 5,
    "big_ass": 6,
    "indian": 7,
    "japanese": 8,
    "korean": 9,
    "femboy": 10,
}

# 2024 global top-30 used as prior, overwritten by 2025 attested ranks / moves.
PRIOR_2024 = {
    "hentai": 1,
    "milf": 2,
    "pinay": 3,
    "lesbian": 4,
    "anal": 5,
    "big_ass": 6,
    "anime": 7,
    "japanese": 8,
    "latina": 9,
    "asian": 10,
    "stepmom": 11,
    "creampie": 12,
    "threesome": 13,
    "animation": 14,
    "big_tits": 15,
    "massage": 16,
    "cosplay": 17,
    "ebony": 18,
    "blowjob": 19,
    "trans": 20,
    "gangbang": 21,
    "bbc": 22,
    "wife": 23,
    "3d": 24,
    "pov": 25,
    "joi": 26,
    "amateur": 27,
    "squirt": 28,
    "bbw": 29,
    "teacher": 30,
}

# Documented 2025 moves from Pornhub text (spot deltas where stated).
MOVES_2025 = {
    "femboy": +15,  # landed #10
    "cosplay": +2,
    "trans": +2,
    "cheating": +9,
    "indian": +8,
    "korean": +7,
}

# Most-viewed categories 2025 (Pornhub official).
CATEGORY_VIEW_RANK = {
    "lesbian": 1,
    "trans": 2,
    "milf": 3,
    "anal": 4,
    "mature": 5,
}

# FANZA 2026 cross-category genre popularity (regional secondary signal).
FANZA_2026 = {
    "bishoujo": 1,  # mapped later to asian/japanese-adjacent youth beauty
    "big_tits": 2,
    "creampie": 3,
    "amateur": 4,
    "school": 5,
    "mature": 6,
    "ntr": 7,
    "wife": 8,
    "uniform": 9,
    "blowjob": 10,
    "cosplay": 12,
    "anal": 26,
    "femboy": 29,  # 男の娘
}

# East-Asia / Chinese-audience supply tags frequently over-indexed vs West tubes
# (JavLibrary/JavDB analyses, Chinese portal tag clouds). Soft boost only.
EA_SOFT = [
    "stockings",
    "pantyhose",
    "blowjob",
    "creampie",
    "facial",
    "feet",
    "uniform",
    "ntr",
    "school",
    "big_tits",
    "wife",
    "amateur",
]


@dataclass
class TagScore:
    tag: str
    score: float = 0.0
    components: Dict[str, float] = field(default_factory=dict)
    confidence: str = "C"
    evidence: List[str] = field(default_factory=list)


def score_all() -> List[TagScore]:
    scores: Dict[str, TagScore] = {}

    def add(tag: str, points: float, component: str, note: str = "") -> None:
        t = canon(tag)
        if t not in scores:
            scores[t] = TagScore(tag=t)
        scores[t].score += points
        scores[t].components[component] = scores[t].components.get(component, 0.0) + points
        if note:
            scores[t].evidence.append(note)

    # 1) Global search anchor (very high weight)
    for tag, rank in GLOBAL_SEARCH_RANK.items():
        pts = max(0, 1200 - (rank - 1) * 90)
        add(tag, pts, "global_search_2025", f"Pornhub 2025 global search #{rank}")

    # 2) 2024 prior with 2025 moves for non-attested ranks
    for tag, rank in PRIOR_2024.items():
        if tag in GLOBAL_SEARCH_RANK:
            continue
        adj = rank - MOVES_2025.get(tag, 0)
        adj = max(11, adj)  # keep below attested top10
        pts = max(0, 700 - (adj - 1) * 18)
        add(tag, pts, "prior_2024_adj", f"2024 rank {rank}, adj~{adj}")

    # cheating not in 2024 top30 but +9 in 2025
    add("cheating", 380, "move_2025", "Pornhub: cheating +9 spots in 2025")

    # 3) Category view signal
    for tag, rank in CATEGORY_VIEW_RANK.items():
        pts = max(0, 500 - (rank - 1) * 70)
        add(tag, pts, "category_views_2025", f"Pornhub 2025 most-viewed category #{rank}")

    # category growth mentions
    for tag, pts, note in [
        ("indian", 120, "Indian category +15 spots"),
        ("solo_female", 90, "Solo Female +10 spots"),
        ("blowjob", 80, "Blowjob +7 spots"),
        ("latina", 85, "Latina +9 spots"),
        ("korean", 80, "Korean +8 spots"),
        ("roleplay", 110, "Role Play category +98%"),
        ("trans", 100, "Transgender category +58%"),
    ]:
        add(tag, pts, "category_moves", note)

    # 4) Country search aggregation
    for country, tags in COUNTRY_SEARCHES.items():
        w = COUNTRY_WEIGHT[country]
        seen = set()
        for i, tag in enumerate(tags, start=1):
            c = canon(tag)
            if c in seen:
                continue
            seen.add(c)
            pts = POS_POINTS.get(i, 5) * (w / 10.0)
            add(c, pts, "country_search", f"{country} search~#{i}")

    # 5) FANZA secondary (East Asia)
    for tag, rank in FANZA_2026.items():
        pts = max(0, 180 - (rank - 1) * 5)
        add(tag, pts * 0.55, "fanza_2026", f"FANZA 2026 genre ~#{rank}")

    for tag in EA_SOFT:
        add(tag, 35, "ea_soft", "East-Asia audience soft boost")

    # confidence assignment
    for t in scores.values():
        if t.tag in GLOBAL_SEARCH_RANK or t.tag in CATEGORY_VIEW_RANK:
            t.confidence = "A"
        elif "prior_2024_adj" in t.components or t.components.get("country_search", 0) > 80:
            t.confidence = "B"
        else:
            t.confidence = "C"

    return sorted(scores.values(), key=lambda x: (-x.score, x.tag))


ZH = {
    "hentai": "Hentai/成人动画",
    "milf": "熟女/MILF",
    "pinay": "菲律宾女性/Pinay",
    "lesbian": "女同/Lesbian",
    "anal": "肛交",
    "big_ass": "大屁股/巨尻",
    "indian": "印度",
    "japanese": "日本",
    "korean": "韩国",
    "femboy": "男娘/Femboy",
    "latina": "拉丁裔女性",
    "asian": "亚洲",
    "anime": "动漫",
    "trans": "跨性别/Trans",
    "mature": "成熟女性",
    "creampie": "中出/内射",
    "threesome": "3P",
    "big_tits": "巨乳",
    "ebony": "黑人女性",
    "blowjob": "口交",
    "cosplay": "Cosplay",
    "amateur": "素人/业余",
    "pov": "主观视角/POV",
    "joi": "JOI/指令自慰",
    "stepmom": "继母",
    "animation": "动画",
    "massage": "按摩",
    "gangbang": "轮交",
    "bbc": "BBC",
    "wife": "人妻",
    "3d": "3D",
    "squirt": "潮吹",
    "bbw": "丰满/BBW",
    "teacher": "教师",
    "cheating": "出轨/偷情",
    "roleplay": "角色扮演",
    "stockings": "黑丝/丝袜",
    "pantyhose": "连裤袜",
    "facial": "颜射",
    "feet": "足交/恋足",
    "ntr": "NTR/寝取",
    "school": "校园/制服学园",
    "uniform": "制服",
    "arab": "阿拉伯",
    "brazilian": "巴西",
    "german": "德国",
    "french": "法国",
    "italian": "意大利",
    "british": "英国",
    "mexican": "墨西哥",
    "colombian": "哥伦比亚",
    "spanish": "西班牙/西语",
    "argentine": "阿根廷",
    "polish": "波兰",
    "chilean": "智利",
    "egyptian": "埃及",
    "peruvian": "秘鲁",
    "pinoy": "菲律宾男性",
    "chinese": "中国",
    "russian": "俄罗斯",
    "dutch": "荷兰",
    "masturbation": "自慰",
    "couple": "情侣",
    "facesitting": "颜面骑乘",
    "cuckold": "绿帽/NTR男方视角",
    "hotwife": "热妻",
    "solo_female": "女性自慰",
    "interracial": "跨种族",
    "fetish": "恋物",
    "office": "办公室",
    "gilf": "GILF/更年长熟女",
    "cougar": "熟女猎手对象/Cougar",
    "bisexual": "双性恋",
    "queer": "酷儿",
    "scissoring": "磨镜",
    "hardcore": "重口/Hardcore",
    "reality": "真实/Reality",
    "bukkake": "群射",
    "furry": "福瑞",
    "twink": "Twink",
    "bareback": "无套",
    "pegging": "反向插入/Pegging",
    "bishoujo": "美少女",
}


def main() -> None:
    ranked = score_all()
    print("rank,tag,zh,score,confidence,top_components")
    for i, t in enumerate(ranked[:120], start=1):
        comps = sorted(t.components.items(), key=lambda x: -x[1])[:3]
        comp_s = ";".join(f"{k}:{v:.1f}" for k, v in comps)
        print(
            f"{i},{t.tag},{ZH.get(t.tag, t.tag)},{t.score:.1f},{t.confidence},{comp_s}"
        )


if __name__ == "__main__":
    main()
