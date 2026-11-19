# -*- coding: utf-8 -*-
"""
Helper module to fetch kanji metadata and format Vietnamese explanations,
radicals, and compound examples using Mazii API with local caching.
"""

import os
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

CACHE_FILE = os.path.join(os.path.dirname(__file__), "mazii_cache.json")

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

_CACHE = load_cache()

def fetch_single_mazii(kanji):
    if kanji in _CACHE:
        return kanji, _CACHE[kanji]

    url = "https://mazii.net/api/search"
    req = urllib.request.Request(
        url,
        data=json.dumps({"dict": "javi", "type": "kanji", "query": kanji, "page": 1}).encode("utf-8"),
        headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                item = res["results"][0] if res.get("results") else {}
                return kanji, item
        except Exception as e:
            time.sleep(0.5 * (attempt + 1))
    return kanji, {}

def fetch_batch_mazii(kanji_list, max_workers=8):
    to_fetch = [k for k in kanji_list if k not in _CACHE]
    if to_fetch:
        print(f"Fetching {len(to_fetch)} kanji from Mazii API...")
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            results = list(ex.map(fetch_single_mazii, to_fetch))
        for k, item in results:
            _CACHE[k] = item
        save_cache(_CACHE)
    return {k: _CACHE.get(k, {}) for k in kanji_list}

def format_kanji_record(kid, kanji, chapter, chapter_name, section, page, raw_item):
    # 1. On readings
    on_raw = raw_item.get("on", "")
    if isinstance(on_raw, str):
        on_list = [x.strip() for x in on_raw.split() if x.strip()]
    elif isinstance(on_raw, list):
        on_list = [str(x).strip() for x in on_raw if str(x).strip()]
    else:
        on_list = []

    # 2. Kun readings
    kun_raw = raw_item.get("kun", "")
    if isinstance(kun_raw, str):
        kun_list = [x.strip() for x in kun_raw.split() if x.strip()]
    elif isinstance(kun_raw, list):
        kun_list = [str(x).strip() for x in kun_raw if str(x).strip()]
    else:
        kun_list = []

    # 3. Sino-Vietnamese (Âm Hán Việt)
    mean_val = raw_item.get("mean") or raw_item.get("hanviet") or ""
    hv = mean_val.split(",")[0].strip().upper() if mean_val else kanji

    # 4. Meaning (Vietnamese)
    detail = raw_item.get("detail", "") or ""
    lines = [l.strip() for l in detail.split("\n") if l.strip()]
    meanings = []
    for l in lines:
        if l.startswith(("VD:", "vd:", "•", "-", "・")):
            continue
        cleaned = re.sub(r"^\d+\.\s*", "", l).strip()
        if cleaned:
            meanings.append(cleaned.split(";")[0].strip())
    meaning_str = ", ".join(meanings[:3]) if meanings else (hv.lower())

    # 5. Radicals breakdown & Vietnamese mnemonics
    comp = raw_item.get("compDetail")
    comp_parts = []
    if comp and isinstance(comp, list):
        for c in comp:
            w = c.get("w", "").strip()
            h = c.get("h", "").strip() if c.get("h") else ""
            if w:
                comp_parts.append(f"{w} ({h})" if h else w)

    tips_raw = (raw_item.get("tips") or {}).get("vi", "") if isinstance(raw_item.get("tips"), dict) else ""
    tips_clean = re.sub(r"<[^>]+>", " ", tips_raw).strip()
    mnemonic = ""
    if tips_clean:
        # Get the descriptive sentence
        sentences = [s.strip() for s in tips_clean.split(".") if s.strip()]
        if sentences:
            mnemonic = sentences[-1]

    if comp_parts:
        radicals_str = f"Bộ cấu thành: {' + '.join(comp_parts)}"
        if mnemonic and len(mnemonic) > 5:
            radicals_str += f" → Mẹo nhớ: {mnemonic}"
    elif mnemonic and len(mnemonic) > 5:
        radicals_str = f"Mẹo nhớ: {mnemonic}"
    else:
        radicals_str = f"Chữ Hán: {kanji} (Âm Hán Việt: {hv})"

    # 6. Compound Examples (word, reading, meaning)
    examples = []
    raw_examples = raw_item.get("examples", [])
    if isinstance(raw_examples, list):
        for ex in raw_examples:
            w = (ex.get("w") or "").strip()
            p = (ex.get("p") or "").strip()
            m = (ex.get("m") or "").strip()
            if w and p and m and w != kanji:
                # Clean punctuation from reading
                p_clean = re.sub(r"^[^\wぁ-んァ-ヶー]+|[^\wぁ-んァ-ヶー]+$", "", p)
                examples.append({
                    "word": w,
                    "reading": p_clean or p,
                    "meaning": m
                })
            if len(examples) >= 4:
                break

    if not examples:
        default_reading = kun_list[0] if kun_list else (on_list[0] if on_list else "")
        examples.append({
            "word": kanji,
            "reading": default_reading,
            "meaning": meaning_str
        })

    # Stroke count
    stroke_count = int(raw_item.get("stroke_count", 0) or 0)

    return {
        "id": kid,
        "kanji": kanji,
        "chapter": chapter,
        "chapterName": chapter_name,
        "section": section,
        "page": page,
        "strokeCount": stroke_count,
        "on": on_list,
        "kun": kun_list,
        "hv": hv,
        "meaning": meaning_str,
        "radicals": radicals_str,
        "examples": examples
    }
