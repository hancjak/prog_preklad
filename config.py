# -*- coding: utf-8 -*-

"""Konfigurační konstanty pro CSV nástroje."""

# Obecné
ENCODING_FILE = "znakova_sada.txt"
DEFAULT_ENCODING = "utf-8" # Fallback kódování
OUTPUT_SUFFIX = "_upr"
CSV_DELIMITER = ';' # Hlavní oddělovač pro CSV

# Texty CSV
TEXTY_SUFFIX = "_texty.csv"
TEXTY_COLUMN_FILTER = "Text"
TEXTY_REQUIRED_CHARS = ['/', ':']
TEXTY_FORBIDDEN_CHAR = " "

# Symboly CSV
SYMBOLY_SUFFIX = "_symboly.csv"
SYMBOLY_COL_TYP = "Typ"
SYMBOLY_COL_SYMBOL = "Symbol"
SYMBOLY_TYP_REQUIRED_CHARS = TEXTY_REQUIRED_CHARS
SYMBOLY_TYP_FORBIDDEN_CHARS = [" ", "-"]
SYMBOLY_SYMBOL_REQUIRED_VALUE = "sipka"

# Čáry CSV
CARY_SUFFIX = "_cary.csv"
CARY_COL_ZNACENI = "Značení"
CARY_COL_SPECIFIKACE = "Specifikace"
CARY_ZNACENI_REQUIRED_CHARS = TEXTY_REQUIRED_CHARS
CARY_ZNACENI_FORBIDDEN_CHARS = [" ", "-"]

# Sloučení a Editace
FINAL_OUTPUT_FILENAME = "priprava.csv" # Výstup sloučení
EDITED_OUTPUT_FILENAME = "priprava_upr.csv" # Výstup editoru
DEFAULT_SPECIFICATION = "neni spec" # Výchozí text pro chybějící specifikaci

# !!!!! PŘIDÁNO: Soubor pro předdefinované texty editoru !!!!!
EDITOR_PRESETS_FILE = "editor_presets.txt"