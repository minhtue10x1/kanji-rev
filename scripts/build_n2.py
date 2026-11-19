# -*- coding: utf-8 -*-
"""
Builder for Kanji Master N2 dataset (18 chapters + special readings).
"""

import os
import json
import sys
sys.path.append(os.path.dirname(__file__))
from fetcher import fetch_batch_mazii, format_kanji_record

N2_CURRICULUM = [
    {
        "chapter": 1,
        "name": "1章 生活-1 (Đời sống 1)",
        "page": 10,
        "sections": [
            ("贈り物1", ["配", "届", "渡", "券", "招", "贈"]),
            ("料理", ["含", "混", "溶", "汁", "丼", "盛"]),
            ("引っ越し", ["契", "越", "賃", "仮", "証", "域"]),
            ("雑誌", ["雑", "誌", "刊", "並", "巻", "著"]),
            ("掃除", ["居", "庭", "清", "掃", "整", "汚"])
        ]
    },
    {
        "chapter": 2,
        "name": "2章 町 (Phố xá & Giao thông)",
        "page": 16,
        "sections": [
            ("交通1", ["駐", "輪", "港", "到", "途", "過"]),
            ("交通2", ["符", "停", "標", "普", "刻", "達"]),
            ("産業", ["漁", "輸", "製", "郵", "航", "融"]),
            ("銀行1", ["戻", "換", "払", "込", "両", "替"]),
            ("銀行2", ["照", "預", "札", "貨", "帳", "振"])
        ]
    },
    {
        "chapter": 3,
        "name": "3章 文化 (Văn hóa & Nghệ thuật)",
        "page": 26,
        "sections": [
            ("花1", ["桜", "梅", "松", "杉", "美", "香"]),
            ("ファッション1", ["脱", "掛", "姿", "勢", "柔", "軟"]),
            ("様子を表す言葉1", ["固", "純", "快", "甘", "濃", "薄"]),
            ("文化1", ["劇", "舞", "堂", "展", "宗", "恵"]),
            ("歴史", ["宝", "城", "栄", "蔵", "昭", "士"])
        ]
    },
    {
        "chapter": 4,
        "name": "4章 健康-1 (Sức khỏe 1)",
        "page": 32,
        "sections": [
            ("健康1", ["健", "康", "診", "療", "命", "異"]),
            ("体1", ["背", "腹", "肩", "腕", "胸", "腰"]),
            ("体2", ["脳", "臓", "胃", "筋", "骨", "節"]),
            ("診察1", ["症", "状", "因", "況", "態", "圧"]),
            ("治療", ["傷", "処", "触", "針", "抜", "完"])
        ]
    },
    {
        "chapter": 5,
        "name": "5章 仕事 (Công việc & Kinh doanh)",
        "page": 42,
        "sections": [
            ("ビジネスマン", ["忙", "疲", "慣", "競", "養", "兼"]),
            ("労働", ["就", "従", "応", "訪", "課", "論"]),
            ("採用", ["採", "募", "雇", "適", "般", "総"]),
            ("営業", ["企", "案", "依", "頼", "比", "較"]),
            ("人事", ["評", "価", "改", "善", "勤", "務"])
        ]
    },
    {
        "chapter": 6,
        "name": "6章 会社 (Doanh nghiệp & Tài chính)",
        "page": 48,
        "sections": [
            ("経営", ["営", "景", "資", "益", "株", "債"]),
            ("販売", ["販", "購", "値", "額", "財", "納"]),
            ("利益", ["増", "減", "損", "得", "拡", "縮"]),
            ("戦略", ["略", "充", "加", "除", "余"]),
            ("出版", ["片", "裏", "幅", "版", "章"])
        ]
    },
    {
        "chapter": 7,
        "name": "7章 ドラマ (Kịch tính & Cảm xúc)",
        "page": 58,
        "sections": [
            ("サスペンス1", ["毒", "殺", "責", "逃", "暴", "恐"]),
            ("サスペンス2", ["緊", "張", "破", "割", "別", "離"]),
            ("ロマンス1", ["印", "象", "与", "齢", "籍", "際"]),
            ("ロマンス2", ["遊", "誘", "勧", "寄", "迷", "占"])
        ]
    },
    {
        "chapter": 8,
        "name": "8章 人間関係-1 (Mối quan hệ 1)",
        "page": 64,
        "sections": [
            ("仲間1", ["周", "囲", "協", "互", "共", "我"]),
            ("仲間2", ["皆", "緒", "援", "精", "抱", "氏"]),
            ("敬語1", ["尊", "敬", "申", "参", "致", "御"])
        ]
    },
    {
        "chapter": 9,
        "name": "9章 自然-1 (Thiên nhiên 1)",
        "page": 72,
        "sections": [
            ("砂浜", ["湾", "沖", "浜", "江", "層", "砂"]),
            ("水1", ["泉", "源", "浮", "沈", "井", "沢"]),
            ("地球", ["宇", "宙", "環", "境", "極", "昇"]),
            ("災害1", ["災", "害", "震", "防", "影", "響"])
        ]
    },
    {
        "chapter": 10,
        "name": "10章 社会-1 (Xã hội 1)",
        "page": 78,
        "sections": [
            ("教育1", ["講", "義", "導", "専", "限", "修"]),
            ("教育2", ["述", "将", "博", "策", "詩", "基"]),
            ("法律", ["条", "令", "司", "制", "省", "庁"]),
            ("警察", ["警", "察", "署", "捕", "訓", "乱"]),
            ("政治1", ["党", "民", "挙", "委", "権", "票"]),
            ("攻撃", ["攻", "撃", "操", "討", "射", "武"])
        ]
    },
    {
        "chapter": 11,
        "name": "11章 生活-2 (Đời sống 2)",
        "page": 94,
        "sections": [
            ("住宅1", ["畳", "床", "軒", "玄", "壁", "廊"]),
            ("住宅2", ["寮", "隣", "敷", "狭", "荘"]),
            ("贈り物2", ["封", "筒", "歳", "暮", "宛", "菓"]),
            ("調味料", ["詰", "瓶", "粒", "酢", "糖", "辛"]),
            ("交通3", ["渋", "滞", "街", "往", "距", "灯"])
        ]
    },
    {
        "chapter": 12,
        "name": "12章 働く (Lao động & Nghề nghiệp)",
        "page": 100,
        "sections": [
            ("サラリーマン", ["携", "即", "稼", "需", "拒", "厳"]),
            ("コピー", ["刷", "枠", "縦", "斜", "端", "隅"]),
            ("様子を表す言葉2", ["堅", "硬", "鋭", "鈍", "詳", "簡"]),
            ("様子を表す言葉3", ["潔", "頑", "勇", "賢", "偉", "珍"]),
            ("美容", ["肌", "粧", "髪", "脚", "華", "鏡"]),
            ("ファッション2", ["帽", "傘", "革", "靴", "柄", "装"])
        ]
    },
    {
        "chapter": 13,
        "name": "13章 健康-2 (Sức khỏe 2)",
        "page": 112,
        "sections": [
            ("健康2", ["睡", "眠", "喫", "煙", "脂", "肪"]),
            ("出産", ["妊", "娠", "双", "誕", "脈", "拍"]),
            ("診察2", ["看", "患", "視", "眼", "舌", "刺"]),
            ("診察3", ["菌", "剤"])
        ]
    },
    {
        "chapter": 14,
        "name": "14章 自然-2 (Thiên nhiên 2)",
        "page": 118,
        "sections": [
            ("花2", ["咲", "枯", "散", "飾", "菊", "枝"]),
            ("色", ["紺", "紫", "紅", "灰", "鮮", "彩"]),
            ("動物1", ["飼", "畜", "猫", "羊", "豚", "巣"]),
            ("動物2", ["放", "牧"]),
            ("水2", ["滝", "沼", "滴", "凍", "瀬", "浄"]),
            ("地質調査1", ["掘", "埋", "泥", "炭", "鉱", "鋼"]),
            ("地質調査2", ["穴", "洞"])
        ]
    },
    {
        "chapter": 15,
        "name": "15章 人間関係-2 (Mối quan hệ 2)",
        "page": 130,
        "sections": [
            ("サスペンス3", ["殴", "叫", "怖", "嫌", "憎", "恥"]),
            ("サスペンス4", ["誤", "謝", "励", "冗", "握", "絶"]),
            ("宴会1", ["宴", "催", "渇", "酌", "泡", "吐"]),
            ("宴会2", ["騒", "延", "超", "更", "徹", "憶"]),
            ("仲間3", ["僕", "僚", "輩", "誰", "偶"]),
            ("仲間4", ["孫", "祖", "似"]),
            ("敬語2", ["召", "拝", "了", "承", "伺", "頂"])
        ]
    },
    {
        "chapter": 16,
        "name": "16章 自然現象 (Hiện tượng tự nhiên & Khí hậu)",
        "page": 138,
        "sections": [
            ("災害2", ["被", "壊", "傾", "崩", "噴", "炎"]),
            ("災害3", ["洪", "津", "波", "荒", "激", "吹"]),
            ("気候", ["乾", "燥", "湿", "涼", "雷", "嵐"])
        ]
    },
    {
        "chapter": 17,
        "name": "17章 社会-2 (Xã hội 2)",
        "page": 146,
        "sections": [
            ("教育3", ["俳", "句", "詞", "覧", "簿", "塾"]),
            ("文化2", ["踊", "像", "殿", "坊", "跡", "祈"]),
            ("犯罪", ["刑", "罰", "盗", "捜", "裁"]),
            ("政治2", ["統", "衆", "秩", "序", "閣", "批"]),
            ("軍事1", ["敵", "砲", "領", "侵", "銃", "核"]),
            ("軍事2", ["護", "衛", "盟", "隊", "屈"])
        ]
    },
    {
        "chapter": 18,
        "name": "18章 地名 (Địa danh & Địa lý)",
        "page": 154,
        "sections": [
            ("地名1", ["阪", "埼", "栃", "茨", "梨", "群"]),
            ("地名2", ["鹿", "奈", "媛", "阜"]),
            ("地名3", ["岡", "崎", "丘", "丁", "塚"])
        ]
    }
]

SPECIAL_READINGS_N2 = [
    {"word": "明日", "reading": "あす", "meaning": "ngày mai (trang trọng)"},
    {"word": "景色", "reading": "けしき", "meaning": "phong cảnh, cảnh sắc"},
    {"word": "二十", "reading": "はたち", "meaning": "hai mươi tuổi"},
    {"word": "二十日", "reading": "はつか", "meaning": "ngày 20, 20 ngày"},
    {"word": "海女", "reading": "あま", "meaning": "nữ thợ lặn mò ngọc trai"},
    {"word": "今年", "reading": "ことし", "meaning": "năm nay"},
    {"word": "田舎", "reading": "いなか", "meaning": "miền quê, vùng nông thôn"},
    {"word": "差し支える", "reading": "さしつかえる", "meaning": "gây cản trở, làm phiền, ảnh hưởng"},
    {"word": "一人", "reading": "ひとり", "meaning": "một người"},
    {"word": "笑顔", "reading": "えがお", "meaning": "khuôn mặt cười tươi rạng rỡ"},
    {"word": "尻尾", "reading": "しっぽ", "meaning": "cái đuôi (con vật)"},
    {"word": "二人", "reading": "ふたり", "meaning": "hai người"},
    {"word": "老舗", "reading": "しにせ", "meaning": "cửa hàng lâu đời truyền thống có uy tín"},
    {"word": "二日", "reading": "ふつか", "meaning": "ngày mùng hai, 2 ngày"},
    {"word": "伯父", "reading": "おじ", "meaning": "bác trai (anh của cha hoặc mẹ)"},
    {"word": "芝生", "reading": "しばふ", "meaning": "bãi cỏ, thảm cỏ"},
    {"word": "吹雪", "reading": "ふぶき", "meaning": "bão tuyết gió lốc"},
    {"word": "叔父", "reading": "おじ", "meaning": "chú, cậu (em của cha hoặc mẹ)"},
    {"word": "上手", "reading": "じょうず", "meaning": "giỏi giang, thành thạo"},
    {"word": "下手", "reading": "へた", "meaning": "kém, vụng về"},
    {"word": "白髪", "reading": "しらが", "meaning": "tóc bạc"},
    {"word": "部屋", "reading": "へや", "meaning": "căn phòng"},
    {"word": "大人", "reading": "おとな", "meaning": "người lớn, trưởng thành"},
    {"word": "素人", "reading": "しろうと", "meaning": "người nghiệp dư, chưa có kinh nghiệm"},
    {"word": "迷子", "reading": "まいご", "meaning": "trẻ lạc đường"},
    {"word": "伯母", "reading": "おば", "meaning": "bác gái (chị của cha mẹ)"},
    {"word": "相撲", "reading": "すもう", "meaning": "võ vật truyền thống Sumo của Nhật"},
    {"word": "真面目", "reading": "まじめ", "meaning": "chăm chỉ, nghiêm túc, đứng đắn"},
    {"word": "叔母", "reading": "おば", "meaning": "cô, dì (em gái của cha mẹ)"},
    {"word": "足袋", "reading": "たび", "meaning": "tất truyền thống Nhật rẽ ngón cái"},
    {"word": "真っ赤", "reading": "まっか", "meaning": "đỏ rực, đỏ bừng"},
    {"word": "お巡りさん", "reading": "おまわりさん", "meaning": "chú cảnh sát tuần tra"},
    {"word": "一日", "reading": "ついたち", "meaning": "ngày mùng một"},
    {"word": "真っ青", "reading": "まっさお", "meaning": "xanh ngắt, tái mét mặt"},
    {"word": "鍛冶", "reading": "かじ", "meaning": "nghề thợ rèn"},
    {"word": "梅雨", "reading": "つゆ", "meaning": "mùa mưa đầu hè ở Nhật Bản"},
    {"word": "土産", "reading": "みやげ", "meaning": "quà lưu niệm đặc sản"},
    {"word": "風邪", "reading": "かぜ", "meaning": "cảm cúm, cảm lạnh"},
    {"word": "凸凹", "reading": "でこぼこ", "meaning": "lồi lõm, gồ ghề, không bằng phẳng"},
    {"word": "息子", "reading": "むすこ", "meaning": "con trai"},
    {"word": "固唾", "reading": "かたず", "meaning": "nước bọt (nuốt nước bọt nín thở hồi hộp)"},
    {"word": "手伝う", "reading": "てつだう", "meaning": "giúp đỡ, phụ giúp một tay"},
    {"word": "眼鏡", "reading": "めがね", "meaning": "kính mắt"},
    {"word": "仮名", "reading": "かな", "meaning": "chữ cái tiếng Nhật Kana"},
    {"word": "時計", "reading": "とけい", "meaning": "đồng hồ"},
    {"word": "紅葉", "reading": "もみじ", "meaning": "lá đỏ phong mùa thu"},
    {"word": "為替", "reading": "かわせ", "meaning": "hối đoái ngoại tệ, ngân phiếu"},
    {"word": "友達", "reading": "ともだち", "meaning": "bạn bè"},
    {"word": "木綿", "reading": "もめん", "meaning": "vải cotton, bông sợi tự nhiên"},
    {"word": "八百屋", "reading": "やおや", "meaning": "tiệm bán rau củ hoa quả"},
    {"word": "弥生", "reading": "やよい", "meaning": "tháng 3 âm lịch (mùa xuân sang)"},
    {"word": "果物", "reading": "くだもの", "meaning": "trái cây, hoa quả"},
    {"word": "博士", "reading": "はかせ", "meaning": "tiến sĩ, bác học"},
    {"word": "浴衣", "reading": "ゆかた", "meaning": "áo kimono mùa hè bằng vải mỏng"},
    {"word": "行方", "reading": "ゆくえ", "meaning": "tung tích, hướng đi, nơi đến"}
]

def build():
    all_kanji = []
    for ch in N2_CURRICULUM:
        for sec_name, k_list in ch["sections"]:
            all_kanji.extend(k_list)
    print(f"Total N2 kanji to process: {len(all_kanji)}")

    mazii_map = fetch_batch_mazii(all_kanji)

    dataset = []
    kid = 1
    for ch in N2_CURRICULUM:
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

    out_kanji_file = os.path.join(os.path.dirname(__file__), "..", "data", "kanji-n2.json")
    out_special_file = os.path.join(os.path.dirname(__file__), "..", "data", "special-n2.json")

    with open(out_kanji_file, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(dataset)} kanji to {out_kanji_file}")

    with open(out_special_file, "w", encoding="utf-8") as f:
        json.dump(SPECIAL_READINGS_N2, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(SPECIAL_READINGS_N2)} special readings to {out_special_file}")

if __name__ == "__main__":
    build()
