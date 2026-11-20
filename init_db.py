# -*- coding: utf-8 -*-
"""
Generate initial db.json file from data/kanji-n3.json for local Guest fallback.
"""

import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "kanji-n3.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "db.json")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    all_kanji = json.load(f)

cards = {}
for k in all_kanji:
    kid = k["id"]
    cards[str(kid)] = {
        "id": kid,
        "kanji": k["kanji"],
        "chapter": k["chapter"],
        "hv": k.get("hv", ""),
        "status": "new",
        "repetitions": 0,
        "intervalDays": 0,
        "easeFactor": 2.5,
        "lastReviewed": None,
        "nextReview": None,
        "correctCount": 0,
        "incorrectCount": 0,
    }

db = {
    "meta": {
        "version": 1,
        "level": "N3",
        "title": "Kanji Master N3 Study Database (Vietnamese Edition)",
        "createdAt": "2026-11-19T21:30:00Z",
        "lastSavedAt": "2026-11-19T21:30:00Z",
    },
    "session": {
        "active": False,
        "level": "N3",
        "mode": "flashcard",
        "filter": "all",
        "chapter": 1,
        "queue": [],
        "currentIndex": 0,
        "completed": 0,
        "lastKanjiId": None,
        "lastKanjiChar": None,
    },
    "cards": cards,
    "bookmarks": [],
    "stats": {
        "totalReviews": 0,
        "totalCorrect": 0,
        "totalIncorrect": 0,
        "currentStreak": 0,
        "bestStreak": 0,
        "lastActiveDate": None,
        "dailyHistory": {},
    },
    "settings": {
        "theme": "light",
        "showFurigana": True,
        "autoAudio": False,
        "shuffleQueue": False,
        "dailyGoal": 20,
    },
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"Generated initial {OUTPUT_PATH} with {len(cards)} card records!")
