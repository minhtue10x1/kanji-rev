# -*- coding: utf-8 -*-
"""
Builder for Kanji Master N4 dataset (207 kanji, 9 chapters + special readings).
"""

import os
import json
import sys
sys.path.append(os.path.dirname(__file__))
from fetcher import fetch_batch_mazii, format_kanji_record

N4_CURRICULUM = [
    {
        "chapter": 1,
        "name": "1章 生かつ (Đời sống & Gia đình)",
        "page": 21,
        "sections": [
            ("1 家族", ["家", "族", "兄", "弟", "姉", "妹", "私", "育"]),
            ("2 マンション", ["部", "屋", "広", "低", "近", "遠", "静"]),
            ("3 ファッション", ["洋", "服", "短", "玉", "毛", "糸", "光", "衣"])
        ]
    },
    {
        "chapter": 2,
        "name": "2章 コンビニ (Cửa hàng tiện lợi)",
        "page": 43,
        "sections": [
            ("1 レジ", ["店", "客", "親", "切", "売", "当", "品"]),
            ("2 店内", ["便", "利", "使", "銀", "白", "黒", "紙"]),
            ("3 24時間", ["朝", "晩", "昼", "夜", "前", "後", "午", "早"])
        ]
    },
    {
        "chapter": 3,
        "name": "3章 おくり物 (Gửi quà & Địa chỉ)",
        "page": 65,
        "sections": [
            ("1 荷物", ["荷", "送", "宅", "急", "速", "遅", "重", "軽"]),
            ("2 あて先", ["住", "所", "様", "主", "番", "地", "号", "京"]),
            ("3 都道府県", ["国", "都", "道", "府", "県", "市", "区", "村"])
        ]
    },
    {
        "chapter": 4,
        "name": "4章 スケジュール (Lịch trình & Công việc)",
        "page": 87,
        "sections": [
            ("1 デート", ["毎", "週", "映", "画", "館", "公", "園"]),
            ("2 けっこんきねん日", ["夫", "妻", "特", "思", "料", "理", "有"]),
            ("3 しごと", ["会", "社", "働", "作", "工", "場", "始", "終"])
        ]
    },
    {
        "chapter": 5,
        "name": "5章 町 (Phố xá & Bệnh viện)",
        "page": 111,
        "sections": [
            ("1 駅", ["駅", "鉄", "乗", "降", "開", "閉", "発", "着"]),
            ("2 交さてん", ["交", "通", "台", "止", "色", "赤", "黄", "青"]),
            ("3 病院", ["病", "院", "医", "科", "薬", "待", "合", "計"])
        ]
    },
    {
        "chapter": 6,
        "name": "6章 学生 (Học sinh & Giao tiếp)",
        "page": 133,
        "sections": [
            ("1 研究", ["研", "究", "語", "文", "英", "化", "数", "心"]),
            ("2 コミュニケーション", ["若", "集", "知", "酒", "歌", "声", "楽"]),
            ("3 ラーメン屋", ["味", "油", "太", "細", "皿", "飯", "麦"])
        ]
    },
    {
        "chapter": 7,
        "name": "7章 春夏秋冬 (Bốn mùa & Du lịch)",
        "page": 155,
        "sections": [
            ("1 きせつ", ["春", "夏", "秋", "冬", "空", "星", "雲", "去"]),
            ("2 天気", ["天", "晴", "雪", "風", "強", "弱", "暑", "寒"]),
            ("3 旅行", ["旅", "持", "世", "界", "写", "真", "船"])
        ]
    },
    {
        "chapter": 8,
        "name": "8章 学校 (Trường học & Thư viện)",
        "page": 177,
        "sections": [
            ("1 勉強", ["勉", "漢", "宿", "題", "質", "問", "教", "室"]),
            ("2 テスト", ["試", "験", "答", "考", "正", "丸", "不", "同"]),
            ("3 図書館", ["貸", "借", "返", "冊", "歴", "史", "図"])
        ]
    },
    {
        "chapter": 9,
        "name": "9章 夏休み (Nghỉ hè & Thể thao)",
        "page": 199,
        "sections": [
            ("1 運動", ["運", "動", "練", "習", "走", "歩", "泳", "才"]),
            ("2 リゾート", ["自", "然", "草", "原", "湖", "谷", "海", "辺"]),
            ("3 いなか", ["里", "野", "緑", "池", "鳥", "羽", "馬", "鳴"])
        ]
    }
]

SPECIAL_READINGS_N4 = [
    {"word": "大家", "reading": "おおや", "meaning": "chủ nhà trọ"},
    {"word": "兄弟", "reading": "きょうだい", "meaning": "anh em (nói chung)"},
    {"word": "従兄弟", "reading": "いとこ", "meaning": "anh chị em họ"},
    {"word": "私", "reading": "わたくし", "meaning": "tôi (cách nói trang trọng khiêm nhường)"},
    {"word": "部屋", "reading": "へや", "meaning": "căn phòng"},
    {"word": "八百屋", "reading": "やおや", "meaning": "cửa hàng rau củ"},
    {"word": "時計", "reading": "とけい", "meaning": "đồng hồ"},
    {"word": "田舎", "reading": "いなか", "meaning": "quê hương, nông thôn"},
    {"word": "眼鏡", "reading": "めがね", "meaning": "kính đeo mắt"},
    {"word": "紅葉", "reading": "もみじ", "meaning": "lá đỏ mùa thu"},
    {"word": "土産", "reading": "みやげ", "meaning": "quà lưu niệm đặc sản"},
    {"word": "浴衣", "reading": "ゆかた", "meaning": "áo kimono mùa hè bằng vải cotton"},
    {"word": "足袋", "reading": "たび", "meaning": "tất truyền thống Nhật Bản"},
    {"word": "昨日", "reading": "きのう", "meaning": "hôm qua"},
    {"word": "今日", "reading": "きょう", "meaning": "hôm nay"},
    {"word": "明日", "reading": "あした", "meaning": "ngày mai"},
    {"word": "一昨日", "reading": "おととい", "meaning": "hôm kia"},
    {"word": "明後日", "reading": "あさって", "meaning": "ngày kìa"},
    {"word": "今朝", "reading": "けさ", "meaning": "sáng nay"},
    {"word": "今年", "reading": "ことし", "meaning": "năm nay"},
    {"word": "去年", "reading": "きょねん", "meaning": "năm ngoái"},
    {"word": "一昨年", "reading": "おととし", "meaning": "năm kia"},
    {"word": "下手", "reading": "へた", "meaning": "kém cỏi, vụng về"},
    {"word": "上手", "reading": "じょうず", "meaning": "giỏi giang, khéo léo"}
]

def build():
    all_kanji = []
    for ch in N4_CURRICULUM:
        for sec_name, k_list in ch["sections"]:
            all_kanji.extend(k_list)
    print(f"Total N4 kanji to process: {len(all_kanji)}")

    mazii_map = fetch_batch_mazii(all_kanji)

    dataset = []
    kid = 1
    for ch in N4_CURRICULUM:
        ch_num = ch["chapter"]
        ch_name = ch["name"]
        page = ch["page"]
        for sec_name, k_list in ch["sections"]:
            for k in k_list:
                item = mazii_map.get(k, {})
                record = format_kanji_record(
                    kid=kid,
                    kanji=k,
                    chapter=ch_num,
                    chapter_name=ch_name,
                    section=sec_name,
                    page=page,
                    raw_item=item
                )
                dataset.append(record)
                kid += 1

    out_kanji_file = os.path.join(os.path.dirname(__file__), "..", "data", "kanji-n4.json")
    out_special_file = os.path.join(os.path.dirname(__file__), "..", "data", "special-n4.json")

    with open(out_kanji_file, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(dataset)} kanji to {out_kanji_file}")

    with open(out_special_file, "w", encoding="utf-8") as f:
        json.dump(SPECIAL_READINGS_N4, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(SPECIAL_READINGS_N4)} special readings to {out_special_file}")

if __name__ == "__main__":
    build()
