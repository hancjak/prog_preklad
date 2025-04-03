# -*- coding: utf-8 -*-

"""Funkce pro specifické zpracování a slučování CSV souborů."""

import csv
import os
from tkinter import messagebox # Potřebujeme pro process_... funkce (zobrazují chyby)

# Importy z našich modulů
import config
from utils import (parse_connection, write_output_file,
                   handle_processing_error, check_overwrite)

# --- Definice get_canonical zde, protože ji používá jen merge ---
def get_canonical(connection_string):
    """Vrátí kanonickou formu spojení A/B -> min(A,B)/max(A,B)."""
    parsed = parse_connection(connection_string)
    if not parsed: return None, None, None
    # Sestavíme zpět A a B části pro kanonický klíč
    part_a = f"{parsed['a']['name']}{parsed['a']['num'] or ''}:{parsed['a']['pin']}"
    part_b = f"{parsed['b']['name']}{parsed['b']['num'] or ''}:{parsed['b']['pin']}"
    canonical = f"{min(part_a, part_b)}/{max(part_a, part_b)}"
    return canonical, part_a, part_b


# --- Funkce pro zpracování jednotlivých CSV ---

def process_texty_csv(input_filepath, encoding, output_filepath):
    """Zpracuje _texty.csv soubor. Vrací (True/False, output_path)."""
    print(f"+ Zpracovávám texty: {os.path.basename(input_filepath)}")
    reader = None
    try:
        filtered_data = []; header = [config.TEXTY_COLUMN_FILTER]; rows_processed = 0; rows_written = 0
        with open(input_filepath, 'r', encoding=encoding, newline='') as infile:
            reader = csv.reader(infile, delimiter=config.CSV_DELIMITER)
            try:
                input_header = next(reader); rows_processed += 1
                try: text_column_index = input_header.index(config.TEXTY_COLUMN_FILTER)
                except ValueError: messagebox.showerror("Chyba", f"Sloupec '{config.TEXTY_COLUMN_FILTER}' nebyl nalezen v '{os.path.basename(input_filepath)}'."); return False, ""
            except StopIteration: messagebox.showerror("Chyba", f"Soubor '{os.path.basename(input_filepath)}' je prázdný."); return False, ""
            for row in reader:
                rows_processed += 1
                if len(row) > text_column_index:
                    text_value = row[text_column_index].strip()
                    contains_required = all(char in text_value for char in config.TEXTY_REQUIRED_CHARS)
                    contains_forbidden = config.TEXTY_FORBIDDEN_CHAR in text_value
                    if contains_required and not contains_forbidden: filtered_data.append([row[text_column_index]]); rows_written += 1
                else: print(f"! Varování ({os.path.basename(input_filepath)}): Řádek {rows_processed} má méně sloupců.")
        success = write_output_file(output_filepath, encoding, header, filtered_data)
        if success:
            print(f"+ Texty zpracovány: {rows_written} řádků zapsáno do {os.path.basename(output_filepath)}")
            return True, output_filepath
        else:
            return False, ""
    except Exception as e:
        handle_processing_error(e, input_filepath, reader, None) # Status label předáme jindy
        return False, ""


def process_symboly_csv(input_filepath, encoding, output_filepath):
    """Zpracuje _symboly.csv, uloží POUZE Typ. Vrací (True/False, output_path)."""
    print(f"\n--- Zpracování {os.path.basename(input_filepath)} (Typ a Symbol, ukládám Typ) ---")
    reader = None
    try:
        filtered_data = []; header = [config.SYMBOLY_COL_TYP]; rows_processed = 0; rows_written = 0
        typ_col_idx = -1; symbol_col_idx = -1
        with open(input_filepath, 'r', encoding=encoding, newline='') as infile:
            reader = csv.reader(infile, delimiter=config.CSV_DELIMITER)
            try:
                input_header = next(reader); rows_processed += 1; print(f"DEBUG Hlavička: {input_header}")
                try:
                    typ_col_idx = input_header.index(config.SYMBOLY_COL_TYP); symbol_col_idx = input_header.index(config.SYMBOLY_COL_SYMBOL)
                    print(f"DEBUG Indexy: '{config.SYMBOLY_COL_TYP}'={typ_col_idx}, '{config.SYMBOLY_COL_SYMBOL}'={symbol_col_idx}")
                except ValueError as ve:
                     missing_col = str(ve).split("'")[1] if "'" in str(ve) else "Neznámý"; expected = f"'{config.SYMBOLY_COL_TYP}' nebo '{config.SYMBOLY_COL_SYMBOL}'"
                     print(f"! CHYBA: Chybí sloupec '{missing_col}'."); messagebox.showerror("Chyba", f"Sloupec {expected} nebyl nalezen v '{os.path.basename(input_filepath)}'."); return False, ""
            except StopIteration: print("! CHYBA: Soubor je prázdný."); messagebox.showerror("Chyba", f"Soubor '{os.path.basename(input_filepath)}' je prázdný."); return False, ""
            for row_index, row in enumerate(reader, start=2):
                rows_processed += 1
                try:
                    if len(row) > max(typ_col_idx, symbol_col_idx):
                        original_typ = row[typ_col_idx]; typ_value = original_typ.strip(); symbol_value = row[symbol_col_idx].strip()
                        typ_ok = ('/' in typ_value and ':' in typ_value) and not (' ' in typ_value or '-' in typ_value)
                        symbol_ok = (symbol_value == config.SYMBOLY_SYMBOL_REQUIRED_VALUE)
                        if typ_ok and symbol_ok: filtered_data.append([original_typ]); rows_written += 1
                    else: print(f"DEBUG: Řádek {row_index} (_symboly) má málo sloupců ({len(row)})")
                except IndexError: print(f"! CHYBA: IndexError řádek {row_index} (_symboly)!")
                except Exception as inner_e: print(f"! CHYBA: Jiná chyba řádek {row_index} (_symboly): {inner_e}")
        print(f"--- Ukončeno {os.path.basename(input_filepath)}, Zpracováno: {rows_processed}, Nalezeno: {rows_written} ---")
        success = write_output_file(output_filepath, encoding, header, filtered_data)
        if success:
            print(f"+ Symboly zpracovány: {rows_written} řádků zapsáno do {os.path.basename(output_filepath)}")
            return True, output_filepath
        else:
            return False, ""
    except Exception as e: handle_processing_error(e, input_filepath, reader, None); return False, ""

def process_cary_csv(input_filepath, encoding, output_filepath):
    """Zpracuje _cary.csv (Značení a Specifikace). Vrací (True/False, output_path)."""
    print(f"\n--- Zpracování {os.path.basename(input_filepath)} (Značení a Specifikace) ---")
    reader = None
    try:
        filtered_data = []; header = [config.CARY_COL_ZNACENI, config.CARY_COL_SPECIFIKACE]; rows_processed = 0; rows_written = 0
        znaceni_col_idx = -1; specifikace_col_idx = -1
        with open(input_filepath, 'r', encoding=encoding, newline='') as infile:
            reader = csv.reader(infile, delimiter=config.CSV_DELIMITER)
            try:
                input_header = next(reader); rows_processed += 1; print(f"DEBUG Hlavička: {input_header}")
                for idx, col_name in enumerate(input_header):
                    if col_name == config.CARY_COL_ZNACENI and znaceni_col_idx == -1: znaceni_col_idx = idx
                    if col_name == config.CARY_COL_SPECIFIKACE: specifikace_col_idx = idx
                    if znaceni_col_idx != -1 and specifikace_col_idx != -1: break
                if znaceni_col_idx == -1: print(f"! CHYBA: Sloupec '{config.CARY_COL_ZNACENI}' nenalezen."); messagebox.showerror("Chyba", f"Sloupec '{config.CARY_COL_ZNACENI}' nebyl nalezen v '{os.path.basename(input_filepath)}'."); return False, ""
                if specifikace_col_idx == -1: print(f"! CHYBA: Sloupec '{config.CARY_COL_SPECIFIKACE}' nenalezen."); messagebox.showerror("Chyba", f"Sloupec '{config.CARY_COL_SPECIFIKACE}' nebyl nalezen v '{os.path.basename(input_filepath)}'."); return False, ""
                print(f"DEBUG Indexy: '{config.CARY_COL_ZNACENI}'={znaceni_col_idx}, '{config.CARY_COL_SPECIFIKACE}'={specifikace_col_idx}")
            except StopIteration: print("! CHYBA: Soubor je prázdný."); messagebox.showerror("Chyba", f"Soubor '{os.path.basename(input_filepath)}' je prázdný."); return False, ""
            for row_index, row in enumerate(reader, start=2):
                rows_processed += 1
                try:
                    if len(row) > max(znaceni_col_idx, specifikace_col_idx):
                        original_znaceni = row[znaceni_col_idx]; original_specifikace = row[specifikace_col_idx]; znaceni_value = original_znaceni.strip()
                        znaceni_ok = ('/' in znaceni_value and ':' in znaceni_value) and not (' ' in znaceni_value or '-' in znaceni_value)
                        if znaceni_ok: filtered_data.append([original_znaceni, original_specifikace]); rows_written += 1
                    else: print(f"DEBUG: Řádek {row_index} (_cary) má málo sloupců ({len(row)})")
                except IndexError: print(f"! CHYBA: IndexError řádek {row_index} (_cary)!")
                except Exception as inner_e: print(f"! CHYBA: Jiná chyba řádek {row_index} (_cary): {inner_e}")
        print(f"--- Ukončeno {os.path.basename(input_filepath)}, Zpracováno: {rows_processed}, Nalezeno: {rows_written} ---")
        success = write_output_file(output_filepath, encoding, header, filtered_data)
        if success:
            print(f"+ Čáry zpracovány: {rows_written} řádků zapsáno do {os.path.basename(output_filepath)}")
            return True, output_filepath
        else:
             return False, ""
    except Exception as e: handle_processing_error(e, input_filepath, reader, None); return False, ""


# --- Funkce pro Sloučení ---
def merge_and_deduplicate(cary_upr_path, symboly_upr_path, texty_upr_path, output_path, encoding, message_queue=None):
    """Sloučí data, odstraní duplicity a uloží výsledek. Posílá stav do fronty."""
    if message_queue: message_queue.put(('status', f"Slučuji data -> {os.path.basename(output_path)}"))
    print(f"\n--- Slučování a deduplikace ---"); print(f"-> {output_path}")
    unique_connections: dict = {}
    processed_count = 0; skipped_no_parse = 0; success = True

    # Zpracování souborů...
    for file_path, file_type_label in [(cary_upr_path, "_cary"), (symboly_upr_path, "_symboly"), (texty_upr_path, "_texty")]:
        print(f"+ Zpracovávám pro sloučení: {os.path.basename(file_path)}")
        if message_queue: message_queue.put(('status', f"Čtení {os.path.basename(file_path)}..."))
        try:
            with open(file_path, 'r', encoding=encoding, newline='') as infile:
                reader = csv.reader(infile, delimiter=config.CSV_DELIMITER)
                try: header_line = next(reader, None)
                except StopIteration: header_line = None
                if header_line is None: print(f"- Soubor {os.path.basename(file_path)} je prázdný."); continue

                for row_idx, row in enumerate(reader, start=2):
                    processed_count += 1
                    if not row: continue
                    connection = row[0]
                    spec = row[1].strip() if file_path == cary_upr_path and len(row) > 1 else ""

                    canonical, _, _ = get_canonical(connection)

                    if canonical:
                        spec_to_store = spec if spec else config.DEFAULT_SPECIFICATION
                        if canonical not in unique_connections:
                            unique_connections[canonical] = spec_to_store if file_path == cary_upr_path else config.DEFAULT_SPECIFICATION
                        elif file_path == cary_upr_path and unique_connections[canonical] == config.DEFAULT_SPECIFICATION and spec_to_store != config.DEFAULT_SPECIFICATION:
                            unique_connections[canonical] = spec_to_store
                    else:
                        skipped_no_parse += 1
                        print(f"! Varování ({file_type_label} řádek {row_idx}): Nelze zpracovat spojení '{connection}'")

        except FileNotFoundError: print(f"! Chyba: {os.path.basename(file_path)} nenalezen."); success = False; break
        except Exception as e: print(f"! Chyba čtení {os.path.basename(file_path)}: {e}"); success = False; break

    if not success:
        if message_queue: message_queue.put(('error', "Chyba sloučení", "Nepodařilo se načíst data pro sloučení."))
        return False

    print(f"--- Nalezeno {len(unique_connections)} unikátních spojení (zpracováno {processed_count}, přeskočeno {skipped_no_parse}) ---")
    if message_queue: message_queue.put(('status', f"Zapisuji {len(unique_connections)} spojení -> {os.path.basename(output_path)}"))

    try: # Zápis
        success_write = write_output_file(output_path, encoding, ["Spojeni", "Specifikace"],
                                          [[conn, spec] for conn, spec in sorted(unique_connections.items())])
        if not success_write: return False
    except Exception as e:
         if message_queue: message_queue.put(('error', "Chyba zápisu", f"Nepodařilo se zapsat výsledný soubor '{output_path}':\n{e}"))
         return False

    try: # Kontrola duplicit
        if message_queue: message_queue.put(('status', f"Kontrola duplicit v {os.path.basename(output_path)}..."))
        connections_in_final = set(); duplicates_found = 0
        with open(output_path, 'r', encoding=encoding, newline='') as f:
            reader = csv.reader(f, delimiter=config.CSV_DELIMITER); next(reader)
            for row_idx, row in enumerate(reader, start=2):
                 if not row: continue; connection = row[0]
                 if connection in connections_in_final: duplicates_found += 1; print(f"! Varování: Duplicita v {os.path.basename(output_path)} řádek {row_idx}: '{connection}'")
                 connections_in_final.add(connection)

        final_status_msg = f"Soubor {os.path.basename(output_path)} vytvořen a zkontrolován."
        if duplicates_found > 0:
             final_status_msg = f"Hotovo, ale nalezeny duplicity ({duplicates_found})."
             if message_queue: message_queue.put(('warning', "Kontrola duplicit", f"Nalezeno {duplicates_found} duplicit v '{os.path.basename(output_path)}'."))
        else: print("+ Kontrola duplicit OK.")

        if message_queue: message_queue.put(('status', final_status_msg))
        return True
    except Exception as e:
        print(f"! Chyba kontroly duplicit {output_path}: {e}")
        if message_queue: message_queue.put(('error', "Chyba kontroly", f"Chyba kontroly '{output_path}':\n{e}"))
        return False

# Pomocná funkce pro zobrazení výsledku zpracování
def write_output_file_message(output_filepath, rows_processed, rows_written, status_label_widget=None):
    """Pomocná funkce pro zobrazení výsledku zpracování jednotlivých CSV."""
    # Tato funkce nyní není volána z process_... funkcí, protože status řeší worker/hlavní vlákno
    # Můžeme ji prozatím ponechat, pokud bychom ji chtěli použít jinde, nebo ji smazat.
    pass