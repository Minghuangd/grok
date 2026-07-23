#!/usr/bin/env python3
"""Score recommended-version specific adult tags across platforms."""
from __future__ import annotations
import csv, json, math, re
from pathlib import Path
from collections import OrderedDict, Counter

ROOT = Path(__file__).resolve().parent
DANBOORU = ROOT / "raw" / "danbooru-2026-02-04.csv"
CIVITAI = ROOT / "raw" / "civitai_tag_counts_est.json"

# Illustration SFW-overlap penalties (tag also massively used in non-adult art)
SFW_PENALTY = {
    "school_uniform": 0.72, "serafuku": 0.75, "swimsuit": 0.78, "bikini": 0.80,
    "thighhighs": 0.82, "panties": 0.78, "bra": 0.75, "high_heels": 0.85,
    "elbow_gloves": 0.85, "leotard": 0.88, "bodysuit": 0.90, "miko": 0.90,
    "tongue_out": 0.70, "saliva": 0.85, "trembling": 0.80, "kissing": 0.85,
    "collar": 0.70, "rope": 0.65, "gloves_generic": 0.5,
}

def load_danbooru():
    by = {}
    for line in DANBOORU.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^([^,]+),(\d+),(\d+),", line)
        if m:
            by[m.group(1)] = int(m.group(3))
    return by

def dcount(by, tags):
    vals = [by[t] for t in tags if t in by]
    if not vals:
        return 0
    if len(vals) == 1:
        return vals[0]
    return int(max(vals) + 0.15 * sum(sorted(vals)[:-1]))

def lognorm(x, ref):
    if x <= 0:
        return 0.0
    return 100.0 * math.log1p(x) / math.log1p(ref)

def build_lex():
    # zh, cat, danbooru tags, civitai keys, pixiv, tube, fanza, x
    raw = [
        ("fellatio", "口交", "act", ["fellatio"], ["blowjob", "oral"], 0, 88, 85, 70),
        ("deepthroat", "深喉", "act", ["deepthroat"], ["deepthroat"], 0, 45, 30, 40),
        ("irrumatio", "强制口插", "act", ["irrumatio"], [], 0, 25, 15, 20),
        ("cunnilingus", "舔阴", "act", ["cunnilingus"], [], 0, 55, 40, 35),
        ("anilingus", "舔肛", "act", ["anilingus"], [], 0, 30, 20, 25),
        ("anal", "肛交", "act", ["anal"], ["anal"], 0, 95, 55, 75),
        ("vaginal", "阴道性交", "act", ["vaginal"], [], 0, 70, 50, 40),
        ("paizuri", "乳交", "act", ["paizuri"], ["paizuri", "titjob"], 0, 50, 70, 35),
        ("handjob", "手交", "act", ["handjob"], ["handjob"], 0, 55, 45, 45),
        ("footjob", "足交", "act", ["footjob"], ["footjob"], 0, 48, 40, 50),
        ("thigh_sex", "腿交", "act", ["thigh_sex"], [], 0, 20, 25, 15),
        ("buttjob", "臀交摩擦", "act", ["buttjob"], [], 0, 25, 15, 15),
        ("fingering", "指交", "act", ["fingering"], [], 0, 40, 35, 30),
        ("masturbation", "自慰", "act", ["masturbation"], [], 0, 60, 45, 40),
        ("sex_from_behind", "后入", "act", ["sex_from_behind", "doggystyle"], [], 0, 65, 55, 45),
        ("cowgirl", "骑乘", "act", ["cowgirl_position"], [], 0, 60, 60, 40),
        ("reverse_cowgirl", "反向骑乘", "act", ["reverse_cowgirl_position"], [], 0, 45, 40, 30),
        ("missionary", "传教士", "act", ["missionary"], [], 0, 50, 35, 30),
        ("spooning", "侧入", "act", ["spooning"], [], 0, 30, 25, 20),
        ("mating_press", "挤压打桩位", "act", ["mating_press"], [], 0, 20, 30, 15),
        ("prone_bone", "俯卧后入", "act", ["prone_bone"], [], 0, 35, 25, 25),
        ("full_nelson", "全尼尔森", "act", ["full_nelson"], [], 0, 25, 20, 20),
        ("standing_sex", "站立性交", "act", ["standing_sex"], [], 0, 40, 30, 25),
        ("facesitting", "颜面骑乘", "act", ["sitting_on_face"], [], 0, 42, 25, 35),
        ("kissing", "接吻", "act", ["kiss"], [], 20, 35, 55, 30),
        ("breast_sucking", "吸乳", "act", ["breast_sucking"], [], 0, 30, 35, 20),
        ("spitroast", "前后夹击", "act", ["spitroast"], [], 0, 40, 25, 30),
        ("double_penetration", "双插入", "act", ["double_penetration"], [], 0, 45, 30, 35),
        ("skirt_lift", "掀裙", "act", ["skirt_lift"], [], 40, 20, 20, 15),
        ("undressing", "脱衣过程", "act", ["undressing"], [], 15, 25, 20, 15),
        ("facial", "颜射", "finish", ["facial"], ["facial", "cumshot"], 0, 70, 50, 65),
        ("cum_in_mouth", "口爆/口内射精", "finish", ["cum_in_mouth"], [], 0, 60, 55, 55),
        ("cum_in_pussy", "中出/内射", "finish", ["cum_in_pussy"], ["creampie"], 0, 75, 95, 60),
        ("cum_in_ass", "肛内射精", "finish", ["cum_in_ass"], [], 0, 45, 35, 35),
        ("bukkake", "群射", "finish", ["bukkake"], ["bukkake"], 0, 40, 35, 40),
        ("cum_on_body", "体射", "finish", ["cum_on_body"], ["cumshot"], 0, 50, 30, 40),
        ("cum_on_breasts", "胸射", "finish", ["cum_on_breasts"], [], 0, 40, 30, 30),
        ("cum_on_hair", "射发", "finish", ["cum_on_hair"], [], 0, 25, 20, 20),
        ("drinking_cum", "吞精", "finish", ["drinking_cum"], [], 0, 35, 30, 30),
        ("cum_drip", "精液滴落/溢出", "finish", ["cum_drip"], [], 0, 30, 25, 20),
        ("black_pantyhose", "黑丝/黑连裤袜", "clothing", ["black_pantyhose"], ["pantyhose", "stockings"], 70, 35, 25, 55),
        ("pantyhose", "连裤袜", "clothing", ["pantyhose"], ["pantyhose"], 65, 30, 20, 45),
        ("thighhighs", "过膝袜", "clothing", ["thighhighs"], ["thighhighs", "stockings"], 90, 25, 20, 40),
        ("black_thighhighs", "黑过膝袜", "clothing", ["black_thighhighs"], ["stockings"], 75, 25, 20, 45),
        ("white_thighhighs", "白丝/白过膝袜", "clothing", ["white_thighhighs"], ["stockings"], 70, 20, 15, 40),
        ("white_pantyhose", "白连裤袜", "clothing", ["white_pantyhose"], ["pantyhose"], 45, 15, 10, 25),
        ("fishnets", "网袜", "clothing", ["fishnets", "fishnet_pantyhose"], ["fishnet"], 50, 35, 20, 40),
        ("garter_straps", "吊带袜", "clothing", ["garter_straps", "garter_belt"], [], 80, 25, 20, 35),
        ("maid", "女仆装", "clothing", ["maid"], ["maid"], 85, 40, 45, 50),
        ("playboy_bunny", "兔女郎", "clothing", ["playboy_bunny"], ["bunny"], 85, 45, 40, 55),
        ("bikini", "比基尼", "clothing", ["bikini"], ["bikini"], 95, 50, 35, 50),
        ("swimsuit", "泳装", "clothing", ["swimsuit"], ["swimsuit"], 95, 45, 35, 45),
        ("micro_bikini", "微型比基尼", "clothing", ["micro_bikini"], ["bikini"], 40, 35, 25, 30),
        ("school_uniform", "校服制服", "clothing", ["school_uniform"], ["school uniform"], 98, 40, 70, 45),
        ("serafuku", "水手服", "clothing", ["serafuku"], ["school uniform"], 90, 30, 55, 35),
        ("nurse", "护士装", "clothing", ["nurse"], ["nurse"], 70, 40, 40, 40),
        ("miko", "巫女服", "clothing", ["miko"], ["miko"], 80, 20, 30, 25),
        ("nun", "修女装", "clothing", ["nun"], ["nun"], 70, 25, 20, 30),
        ("china_dress", "旗袍", "clothing", ["china_dress", "qipao"], ["china dress", "qipao"], 55, 25, 20, 35),
        ("latex", "乳胶衣", "clothing", ["latex"], ["latex"], 30, 45, 25, 50),
        ("leather", "皮革装", "clothing", ["leather"], [], 20, 40, 20, 40),
        ("lingerie", "情趣内衣", "clothing", ["lingerie"], ["lingerie"], 50, 55, 40, 50),
        ("leotard", "连体衣/高叉", "clothing", ["leotard"], [], 40, 25, 20, 25),
        ("bodysuit", "紧身衣", "clothing", ["bodysuit"], [], 35, 30, 20, 30),
        ("elbow_gloves", "长手套", "clothing", ["elbow_gloves"], [], 35, 15, 15, 20),
        ("high_heels", "高跟鞋", "clothing", ["high_heels"], ["heels"], 40, 35, 25, 40),
        ("panties", "内裤", "clothing", ["panties"], [], 45, 40, 25, 35),
        ("bra", "胸罩", "clothing", ["bra"], [], 30, 30, 20, 25),
        ("dildo", "假阳具", "toy", ["dildo"], ["dildo"], 10, 50, 40, 40),
        ("vibrator", "振动棒", "toy", ["vibrator"], ["vibrator"], 10, 45, 40, 35),
        ("hitachi_magic_wand", "AV棒", "toy", ["hitachi_magic_wand"], ["vibrator"], 5, 40, 35, 30),
        ("anal_beads", "肛珠", "toy", ["anal_beads"], [], 0, 35, 25, 30),
        ("butt_plug", "肛塞", "toy", ["butt_plug"], [], 0, 35, 25, 30),
        ("sex_toy", "性玩具", "toy", ["sex_toy"], [], 5, 40, 30, 25),
        ("collar", "项圈", "toy", ["collar"], ["collar"], 25, 30, 25, 35),
        ("ball_gag", "口塞", "toy", ["ball_gag", "gag"], ["gag"], 10, 35, 25, 30),
        ("blindfold", "眼罩", "toy", ["blindfold"], ["blindfold"], 10, 30, 20, 25),
        ("handcuffs", "手铐", "toy", ["handcuffs"], [], 10, 35, 25, 30),
        ("rope", "绳索", "toy", ["rope"], [], 15, 30, 25, 25),
        ("nipple_clamps", "乳夹", "toy", ["nipple_clamps"], [], 5, 30, 25, 25),
        ("condom", "避孕套", "toy", ["condom"], [], 5, 35, 30, 20),
        ("ahegao", "阿嘿颜", "reaction", ["ahegao"], ["ahegao"], 40, 35, 30, 55),
        ("female_ejaculation", "潮吹", "reaction", ["female_ejaculation"], ["squirt"], 10, 55, 50, 45),
        ("orgasm", "高潮", "reaction", ["orgasm", "female_orgasm"], [], 15, 50, 40, 40),
        ("pussy_juice", "爱液", "reaction", ["pussy_juice"], [], 10, 30, 25, 20),
        ("saliva", "唾液/口水", "reaction", ["saliva"], [], 20, 25, 20, 20),
        ("tongue_out", "吐舌", "reaction", ["tongue_out"], [], 35, 20, 15, 25),
        ("rolling_eyes", "翻白眼", "reaction", ["rolling_eyes"], [], 15, 20, 15, 25),
        ("trembling", "颤抖", "reaction", ["trembling"], [], 10, 15, 15, 10),
        ("peeing", "失禁/排尿", "reaction", ["peeing"], [], 5, 40, 25, 35),
        ("femdom", "女支配", "interaction", ["femdom"], ["femdom"], 15, 45, 40, 50),
        ("assertive_female", "主动女性/痴女", "interaction", ["assertive_female"], [], 20, 40, 75, 35),
        ("bdsm", "BDSM", "interaction", ["bdsm"], ["bdsm"], 20, 55, 50, 55),
        ("bondage", "束缚", "interaction", ["bondage", "bound"], ["bondage"], 20, 50, 45, 50),
        ("shibari", "绳缚", "interaction", ["shibari"], ["shibari"], 25, 35, 40, 40),
        ("spanked", "打屁股", "interaction", ["spanked"], ["spanking"], 10, 40, 30, 35),
        ("hair_grab", "抓发/拉发", "interaction", ["grabbing_another's_hair"], [], 5, 25, 20, 20),
    ]
    lex = OrderedDict()
    for cid, zh, cat, d, c, p, t, f, x in raw:
        lex[cid] = dict(zh=zh, cat=cat, d=d, c=c, pixiv=p, tube=t, fanza=f, x=x)
    return lex

def score_all():
    by = load_danbooru()
    civitai = json.loads(CIVITAI.read_text())
    lex = build_lex()
    d_ref = max(dcount(by, v["d"]) for v in lex.values()) or 1
    c_nums = []
    for v in lex.values():
        s = 0
        for k in v["c"]:
            info = civitai.get(k)
            if info and "count" in info:
                s = max(s, info["count"] + (200 if info.get("truncated") else 0))
        c_nums.append(s)
    c_ref = max(c_nums) or 1

    rows = []
    for cid, meta in lex.items():
        d_raw = dcount(by, meta["d"])
        pen = SFW_PENALTY.get(cid, 1.0)
        d = d_raw * pen
        c = 0
        c_detail = []
        for k in meta["c"]:
            info = civitai.get(k)
            if info and "count" in info:
                val = info["count"] + (200 if info.get("truncated") else 0)
                if val >= c:
                    c = val
                c_detail.append(f"{k}:{info['count']}{'+' if info.get('truncated') else ''}")
        d_s = lognorm(d, d_ref)
        c_s = lognorm(c, c_ref)
        p_s = float(meta["pixiv"]) * (0.85 if pen < 0.9 else 1.0)
        t_s = float(meta["tube"])
        f_s = float(meta["fanza"])
        x_s = float(meta["x"])
        score = 0.30 * d_s + 0.25 * c_s + 0.15 * p_s + 0.20 * t_s + 0.05 * f_s + 0.05 * x_s
        sources = sum([d_raw > 0, c > 0, p_s > 0, t_s >= 40, f_s >= 40, x_s >= 40])
        if sources >= 4 and d_raw > 0 and (c > 0 or t_s >= 60):
            conf = "A"
        elif sources >= 3 or (d_raw > 5000 and t_s >= 40):
            conf = "B"
        else:
            conf = "C"
        rows.append({
            "id": cid, "zh": meta["zh"], "cat": meta["cat"], "score": round(score, 2),
            "conf": conf, "danbooru": d_raw, "danbooru_adj": int(d), "sfw_penalty": pen,
            "civitai": ";".join(c_detail) or "—",
            "d_s": round(d_s, 1), "c_s": round(c_s, 1), "p_s": round(p_s, 1),
            "t_s": t_s, "f_s": f_s, "x_s": x_s,
            "aliases": ",".join(meta["d"] + meta["c"]),
        })
    rows.sort(key=lambda r: (-r["score"], -r["danbooru"], r["id"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows

def main():
    rows = score_all()
    out = ROOT / "top_specific_tags.csv"
    fields = ["rank","id","zh","cat","score","conf","danbooru","danbooru_adj","sfw_penalty","civitai","d_s","c_s","p_s","t_s","f_s","x_s","aliases"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    (ROOT / "raw" / "lexicon_scores.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ranked {len(rows)}")
    for r in rows[:40]:
        print(f"{r['rank']:3d} {r['score']:6.2f} [{r['conf']}] {r['zh']:12s} {r['id']}")
    print("cats", Counter(r["cat"] for r in rows))

if __name__ == "__main__":
    main()
