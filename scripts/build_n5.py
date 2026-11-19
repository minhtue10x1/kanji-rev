# -*- coding: utf-8 -*-
"""
Builder for Kanji Master N5 dataset (118 kanji, 15 chapters + special readings).
"""

import os
import json
from fetcher import fetch_batch_mazii, format_kanji_record

N5_CURRICULUM = [
    {
        "chapter": 1,
        "name": "1章 すうじ (Số đếm)",
        "page": 11,
        "kanji": ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "百", "千", "万", "円"]
    },
    {
        "chapter": 2,
        "name": "2章 カレンダー (Lịch & Ngày tháng)",
        "page": 23,
        "kanji": ["月", "火", "水", "木", "金", "土", "日", "年"]
    },
    {
        "chapter": 3,
        "name": "3章 人 (Con người & Bộ phận)",
        "page": 31,
        "kanji": ["人", "口", "目", "耳", "手", "足", "力"]
    },
    {
        "chapter": 4,
        "name": "4章 しぜん-1 (Tự nhiên 1)",
        "page": 39,
        "kanji": ["山", "川", "田", "石", "花", "竹", "雨"]
    },
    {
        "chapter": 5,
        "name": "5章 ばしょ (Vị trí & Phương hướng)",
        "page": 47,
        "kanji": ["上", "下", "左", "右", "外", "内", "中"]
    },
    {
        "chapter": 6,
        "name": "6章 学校-1 (Trường học 1)",
        "page": 57,
        "kanji": ["学", "校", "先", "生", "名", "字", "本", "体"]
    },
    {
        "chapter": 7,
        "name": "7章 学校-2 (Trường học 2)",
        "page": 65,
        "kanji": ["大", "小", "高", "友", "入", "出", "門"]
    },
    {
        "chapter": 8,
        "name": "8章 かぞく (Gia đình & Động vật)",
        "page": 73,
        "kanji": ["父", "母", "子", "男", "女", "犬", "鳥"]
    },
    {
        "chapter": 9,
        "name": "9章 どうし-1 (Động từ 1)",
        "page": 81,
        "kanji": ["立", "休", "見", "聞", "行", "来", "帰"]
    },
    {
        "chapter": 10,
        "name": "10章 たべもの (Thực phẩm & Đồ ăn)",
        "page": 89,
        "kanji": ["米", "茶", "牛", "肉", "魚", "貝", "好", "物"]
    },
    {
        "chapter": 11,
        "name": "11章 しぜん-2 (Tự nhiên 2)",
        "page": 99,
        "kanji": ["林", "森", "畑", "岩", "音", "明", "暗"]
    },
    {
        "chapter": 12,
        "name": "12章 どうし-2 (Động từ 2)",
        "page": 107,
        "kanji": ["言", "書", "読", "話", "食", "飲", "買"]
    },
    {
        "chapter": 13,
        "name": "13章 町 (Phố xá & Phương tiện)",
        "page": 115,
        "kanji": ["町", "寺", "電", "車", "東", "西", "南", "北"]
    },
    {
        "chapter": 14,
        "name": "14章 時間 (Thời gian)",
        "page": 123,
        "kanji": ["時", "間", "半", "分", "今", "何", "夕"]
    },
    {
        "chapter": 15,
        "name": "15章 けいようし (Tính từ)",
        "page": 131,
        "kanji": ["新", "古", "長", "安", "多", "少", "元", "気"]
    }
]

SPECIAL_READINGS_N5 = [
    {"word": "一人", "reading": "ひとり", "meaning": "một người, đơn độc"},
    {"word": "二人", "reading": "ふたり", "meaning": "hai người"},
    {"word": "一日", "reading": "ついたち", "meaning": "ngày mùng một"},
    {"word": "二日", "reading": "ふつか", "meaning": "ngày mùng hai, 2 ngày"},
    {"word": "三日", "reading": "みっか", "meaning": "ngày mùng ba, 3 ngày"},
    {"word": "四日", "reading": "よっか", "meaning": "ngày mùng bốn, 4 ngày"},
    {"word": "五日", "reading": "いつか", "meaning": "ngày mùng năm, 5 ngày"},
    {"word": "六日", "reading": "むいか", "meaning": "ngày mùng sáu, 6 ngày"},
    {"word": "七日", "reading": "なのか", "meaning": "ngày mùng bảy, 7 ngày"},
    {"word": "八日", "reading": "ようか", "meaning": "ngày mùng tám, 8 ngày"},
    {"word": "九日", "reading": "ここのか", "meaning": "ngày mùng chín, 9 ngày"},
    {"word": "十日", "reading": "とおか", "meaning": "ngày mùng mười, 10 ngày"},
    {"word": "十四日", "reading": "じゅうよっか", "meaning": "ngày 14, 14 ngày"},
    {"word": "二十日", "reading": "はつか", "meaning": "ngày 20, 20 ngày"},
    {"word": "二十四日", "reading": "にじゅうよっか", "meaning": "ngày 24, 24 ngày"},
    {"word": "一昨年", "reading": "おととし", "meaning": "năm kia"},
    {"word": "去年", "reading": "きょねん", "meaning": "năm ngoái"},
    {"word": "今年", "reading": "ことし", "meaning": "năm nay"},
    {"word": "今朝", "reading": "けさ", "meaning": "sáng nay"},
    {"word": "今晩", "reading": "こんばん", "meaning": "tối nay"},
    {"word": "今日", "reading": "きょう", "meaning": "hôm nay"},
    {"word": "昨日", "reading": "きのう", "meaning": "hôm qua"},
    {"word": "明日", "reading": "あした", "meaning": "ngày mai"},
    {"word": "大人", "reading": "おとな", "meaning": "người lớn"},
    {"word": "二十歳", "reading": "はたち", "meaning": "20 tuổi"}
]

def build():
    all_kanji = []
    for ch in N5_CURRICULUM:
        all_kanji.extend(ch["kanji"])
    print(f"Total N5 kanji to process: {len(all_kanji)}")

    mazii_map = fetch_batch_mazii(all_kanji)

    dataset = []
    kid = 1
    for ch in N5_CURRICULUM:
        ch_num = ch["chapter"]
        ch_name = ch["name"]
        page = ch["page"]
        for k in ch["kanji"]:
            item = mazii_map.get(k, {})
            record = format_kanji_record(
                kid=kid,
                kanji=k,
                chapter=ch_num,
                chapter_name=ch_name,
                section=ch_name.split()[1] if len(ch_name.split()) > 1 else ch_name,
                page=page,
                raw_item=item
            )
            dataset.append(record)
            kid += 1

    out_kanji_file = os.path.join(os.path.dirname(__file__), "..", "data", "kanji-n5.json")
    out_special_file = os.path.join(os.path.dirname(__file__), "..", "data", "special-n5.json")

    with open(out_kanji_file, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(dataset)} kanji to {out_kanji_file}")

    with open(out_special_file, "w", encoding="utf-8") as f:
        json.dump(SPECIAL_READINGS_N5, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(SPECIAL_READINGS_N5)} special readings to {out_special_file}")

if __name__ == "__main__":
    build()
