# -*- coding: utf-8 -*-
"""
Merges and compiles all 5 JLPT levels into kanji-data.js with backward compatibility.
"""

import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

LEVELS = ["N5", "N4", "N3", "N2", "N1"]

def compile_data():
    kanji_by_level = {}
    special_by_level = {}

    for lvl in LEVELS:
        k_file = os.path.join(DATA_DIR, f"kanji-{lvl.lower()}.json")
        s_file = os.path.join(DATA_DIR, f"special-{lvl.lower()}.json")

        if os.path.exists(k_file):
            with open(k_file, "r", encoding="utf-8") as f:
                kanji_by_level[lvl] = json.load(f)
            print(f"Loaded {lvl}: {len(kanji_by_level[lvl])} kanji")
        else:
            print(f"Warning: {k_file} not found yet")
            kanji_by_level[lvl] = []

        if os.path.exists(s_file):
            with open(s_file, "r", encoding="utf-8") as f:
                special_by_level[lvl] = json.load(f)
            print(f"Loaded {lvl} special: {len(special_by_level[lvl])} readings")
        else:
            special_by_level[lvl] = []

    out_file = os.path.join(BASE_DIR, "kanji-data.js")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("// Auto-generated Kanji Master 5-Level Data (N5 - N1)\n")
        f.write("window.KANJI_DATA_BY_LEVEL = ")
        json.dump(kanji_by_level, f, ensure_ascii=False)
        f.write(";\n\n")

        f.write("window.SPECIAL_READINGS_BY_LEVEL = ")
        json.dump(special_by_level, f, ensure_ascii=False)
        f.write(";\n\n")

        f.write("// Default backwards-compatible exports\n")
        f.write("window.KANJI_DATA = window.KANJI_DATA_BY_LEVEL['N3'] || [];\n")
        f.write("window.SPECIAL_READINGS = window.SPECIAL_READINGS_BY_LEVEL['N3'] || [];\n")

    print(f"Successfully generated {out_file} (Size: {os.path.getsize(out_file) / 1024:.1f} KB)")

if __name__ == "__main__":
    compile_data()
