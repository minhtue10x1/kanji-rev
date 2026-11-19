# -*- coding: utf-8 -*-
"""
Generate initial db.json file with all 376 Kanji pre-registered into cards catalog.
"""

import json
from make_data_vn import CH_1_5_VN
from make_data_vn_part2 import CH_6_10_VN
from make_data_vn_part3 import CH_11_15_VN
from make_data_vn_part4 import CH_16_20_VN, SPECIAL_READINGS_VN

all_kanji = CH_1_5_VN + CH_6_10_VN + CH_11_15_VN + CH_16_20_VN

cards = {}
for idx, k in enumerate(all_kanji, start=1):
    cards[str(idx)] = {
        "id": idx,
        "kanji": k["k"],
        "chapter": k["ch"],
        "hv": k.get("hv", ""),
        "status": "new",  # "new" | "learning" | "mastered"
        "repetitions": 0,
        "intervalDays": 0,
        "easeFactor": 2.5,
        "lastReviewed": None,
        "nextReview": None,
        "correctCount": 0,
        "incorrectCount": 0
    }

db = {
    "meta": {
        "version": 1,
        "title": "Kanji Master N3 Study Database (Vietnamese Edition)",
        "createdAt": "2026-11-19T21:30:00Z",
        "lastSavedAt": "2026-11-19T21:30:00Z"
    },
    "session": {
        "active": False,
        "mode": "flashcard",
        "filter": "all",
        "chapter": 1,
        "queue": [],
        "currentIndex": 0,
        "completed": 0,
        "lastKanjiId": None,
        "lastKanjiChar": None
    },
    "cards": cards,
    "bookmarks": [],
    "stats": {
        "totalReviews": 0,
        "totalCorrect": 0,
        "totalIncorrect": 0,
        "currentStreak": 1,
        "bestStreak": 1,
        "lastActiveDate": "2026-11-19",
        "dailyHistory": {}
    },
    "settings": {
        "theme": "light",
        "showFurigana": True,
        "autoAudio": False,
        "shuffleQueue": False,
        "dailyGoal": 20
    }
}

output_path = r"d:\Projects\kanji-rev\db.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"Generated initial {output_path} with {len(cards)} card records!")
