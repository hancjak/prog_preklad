# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox, simpledialog
import csv
import os
import sys
import re
import shutil
from collections import OrderedDict, Counter, defaultdict # Vráceno defaultdict

# --- Konfigurace ---
ENCODING_FILE = "znakova_sada.txt"; DEFAULT_ENCODING = "utf-8"; OUTPUT_SUFFIX = "_upr"; CSV_DELIMITER = ';'
TEXTY_SUFFIX = "_texty.csv"; TEXTY_COLUMN_FILTER = "Text"; TEXTY_REQUIRED_CHARS = ['/', ':']; TEXTY_FORBIDDEN_CHAR = " "
SYMBOLY_SUFFIX = "_symboly.csv"; SYMBOLY_COL_TYP = "Typ"; SYMBOLY_COL_SYMBOL = "Symbol"; SYMBOLY_TYP_REQUIRED_CHARS = TEXTY_REQUIRED_CHARS; SYMBOLY_TYP_FORBIDDEN_CHARS = [" ", "-"]; SYMBOLY_SYMBOL_REQUIRED_VALUE = "sipka"
CARY_SUFFIX = "_cary.csv"; CARY_COL_ZNACENI = "Značení"; CARY_COL_SPECIFIKACE = "Specifikace"; CARY_ZNACENI_REQUIRED_CHARS = TEXTY_REQUIRED_CHARS; CARY_ZNACENI_FORBIDDEN_CHARS = [" ", "-"]
FINAL_OUTPUT_FILENAME = "priprava.csv"; EDITED_OUTPUT_FILENAME = "priprava_upr.csv"; DEFAULT_SPECIFICATION = "neni spec"

# --- Globální proměnné ---
texty_filepath = None; symboly_filepath = None; cary_filepath = None; main_root = None; status_label = None

# --- Parser Funkce ---
def parse_component(comp_str):
    """Naparsuje část spojení (např. 'PUC1:1') na název, číslo, pin."""
    match_comp_pin = re.match(r"^(.*?):(.*)$", comp_str)
    if not match_comp_pin: comp_part = comp_str; pin = None
    else: comp_part = match_comp_pin.group(1).strip(); pin = match_comp_pin.group(2).strip()
    match_name_num = re.match(r"^([a-zA-Z_]+)(\d*)$", comp_part)
    if match_name_num: name = match_name_num.group(1); num_str = match_name_num.group(2); num = int(num_str) if num_str else None
    else: name = comp_part; num = None
    return {"name": name, "num": num, "pin": pin}

def parse_connection(connection_string):
    """Naparsuje celý řetězec spojení A/B."""
    if '/' not in connection_string: return None
    parts = connection_string.split('/', 1); part_a_str = parts[0].strip(); part_b_str = parts[1].strip()
    if not part_a_str or not part_b_str: return None
    comp_a = parse_component(part_a_str); comp_b = parse_component(part_b_str)
    if not comp_a or not comp_b or comp_a['pin'] is None or comp_b['pin'] is None: return None
    return {"a": comp_a, "b": comp_b}

# --- Pomocné Funkce ---
def read_encoding(filename=ENCODING_FILE):
    """Načte znakovou sadu."""
    try:
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0])); encoding_filepath = os.path.join(script_dir, filename)
        # Použijeme utf-8 pro čtení konfiguračního souboru, mělo by být bezpečné
        with open(encoding_filepath, 'r', encoding='utf-8') as f: first_line = f.readline().strip() # Opraveno: explicitní encoding
        if first_line:
            try: "test".encode(first_line); print(f"+ Znak. sada: {first_line}"); return first_line
            except LookupError: print(f"! Chyba: Neplatná znak. sada '{first_line}'. Používám: {DEFAULT_ENCODING}"); messagebox.showwarning("Chyba kódování", f"Neplatná sada '{first_line}'.\nBude použito: {DEFAULT_ENCODING}"); return DEFAULT_ENCODING
        else: print(f"! Chyba: Soubor '{filename}' prázdný. Používám: {DEFAULT_ENCODING}"); messagebox.showwarning("Chyba kódování", f"Soubor '{filename}' prázdný.\nBude použito: {DEFAULT_ENCODING}"); return DEFAULT_ENCODING
    except FileNotFoundError: print(f"! Chyba: Soubor '{filename}' nenalezen. Používám: {DEFAULT_ENCODING}"); messagebox.showwarning("Chyba konfigurace", f"Soubor '{filename}' nenalezen.\nBude použito: {DEFAULT_ENCODING}"); return DEFAULT_ENCODING
    except Exception as e: print(f"! Chyba při čtení '{filename}': {e}. Používám: {DEFAULT_ENCODING}"); messagebox.showerror("Chyba konfigurace", f"Chyba při čtení '{filename}':\n{e}\nBude použito: {DEFAULT_ENCODING}"); return None

def check_overwrite(output_filepath):
    """Zkontroluje existenci souboru a zeptá se na přepsání."""
    if os.path.exists(output_filepath):
        output_filename = os.path.basename(output_filepath)
        overwrite = messagebox.askyesno("Soubor existuje", f"Soubor '{output_filename}' již existuje.\nPřejete si ho přepsat?", icon='warning')
        if not overwrite: print(f"- Přepis '{output_filename}' zrušen."); return False
        else: print(f"+ Přepisuji '{output_filename}'."); return True
    return True

def write_output_file(output_filepath, encoding, header, data, rows_processed, rows_written, success_status_msg):
    """Zapíše data do výstupního CSV souboru a aktualizuje status."""
    global status_label
    output_filename = os.path.basename(output_filepath)
    final_status = success_status_msg
    if not data and rows_processed > 1 : messagebox.showwarning("Prázdný výsledek", f"Pro '{output_filename}' nezůstaly žádné řádky."); final_status = f"'{output_filename}': Žádná data."
    elif not data and rows_processed <= 1: final_status = f"'{output_filename}': Vstup prázdný."
    else:
        if status_label: status_label.config(text=f"Zapisuji {rows_written} řádků do {output_filename}...")
    try:
        print(f"+ Zapisuji {rows_written} řádků do '{output_filename}'...")
        with open(output_filepath, 'w', encoding=encoding, newline='') as outfile:
            writer = csv.writer(outfile, delimiter=CSV_DELIMITER); writer.writerow(header); writer.writerows(data)
        print(f"+ Soubor '{output_filename}' uložen.")
        if final_status and status_label: status_label.config(text=final_status)
    except PermissionError:
        if status_label: status_label.config(text=f"Chyba zápisu: {output_filename}.")
        messagebox.showerror("Chyba oprávnění", f"Nelze zapsat:\n'{output_filepath}'.")
        raise # Předáme dál
    except Exception as e:
        if status_label: status_label.config(text=f"Chyba zápisu: {output_filename}.")
        messagebox.showerror("Chyba zápisu", f"Chyba při zápisu '{output_filename}':\n{e}")
        raise # Předáme dál

def handle_processing_error(e, input_filepath, encoding, reader):
    """Zpracuje a zobrazí chyby."""
    global status_label
    input_filename = os.path.basename(input_filepath); error_type = type(e).__name__; error_msg = str(e); line_num_msg = ""
    status_update = f"! Chyba: '{input_filename}'."
    if isinstance(e, FileNotFoundError): messagebox.showerror("Chyba souboru", f"Soubor nenalezen:\n{input_filepath}"); status_update = f"! Chyba: '{input_filename}' nenalezen."
    elif isinstance(e, LookupError): messagebox.showerror("Chyba kódování", f"Nepodporovaná sada: '{encoding}'.\nZkontrolujte '{ENCODING_FILE}'."); status_update = f"! Chyba: Neplatné kódování '{encoding}'."
    elif isinstance(e, PermissionError): messagebox.showerror("Chyba oprávnění", "Nedostatečná oprávnění."); status_update = "! Chyba: Oprávnění."
    elif isinstance(e, csv.Error): line_num_msg = f" řádek {reader.line_num}" if reader and hasattr(reader, 'line_num') else ""; messagebox.showerror("Chyba CSV", f"Chyba CSV '{input_filename}'{line_num_msg}:\n{error_msg}"); status_update = f"! Chyba CSV: '{input_filename}'."
    else: current_line = reader.line_num if reader and hasattr(reader, 'line_num') else 'N/A'; line_num_msg = f" řádek ~{current_line}"; messagebox.showerror("Neočekávaná chyba", f"Chyba '{error_type}'{line_num_msg} v '{input_filename}':\n{error_msg}"); status_update = f"! Chyba: '{input_filename}'."; import traceback; print(f"! Detail chyby '{input_filename}': {error_type} - {error_msg}"); traceback.print_exc()
    if status_label: status_label.config(text=status_update)


# --- Funkce pro zpracování CSV ---
def process_texty_csv(input_filepath, encoding):
    """Zpracuje _texty.csv soubor."""
    global status_label
    if status_label: status_label.config(text=f"Zpracovávám: {os.path.basename(input_filepath)}...")
    try:
        directory = os.path.dirname(input_filepath); filename, extension = os.path.splitext(os.path.basename(input_filepath))
        output_filename = f"{filename}{OUTPUT_SUFFIX}{extension}"; output_filepath = os.path.join(directory, output_filename)
        if not check_overwrite(output_filepath):
            if status_label: status_label.config(text=f"Zpracování {output_filename} zrušeno.")
            return False # Opraveno: unreachable code
        filtered_data = []; header = [TEXTY_COLUMN_FILTER]; rows_processed = 0; rows_written = 0; reader = None
        with open(input_filepath, 'r', encoding=encoding, newline='') as infile:
            reader = csv.reader(infile, delimiter=CSV_DELIMITER)
            try:
                input_header = next(reader); rows_processed += 1
                try: text_column_index = input_header.index(TEXTY_COLUMN_FILTER)
                except ValueError: messagebox.showerror("Chyba", f"Sloupec '{TEXTY_COLUMN_FILTER}' nebyl nalezen v '{os.path.basename(input_filepath)}'."); return False
            except StopIteration: messagebox.showerror("Chyba", f"Soubor '{os.path.basename(input_filepath)}' je prázdný."); return False
            for row in reader:
                rows_processed += 1
                if len(row) > text_column_index:
                    text_value = row[text_column_index].strip()
                    contains_required = all(char in text_value for char in TEXTY_REQUIRED_CHARS)
                    contains_forbidden = TEXTY_FORBIDDEN_CHAR in text_value
                    if contains_required and not contains_forbidden: filtered_data.append([row[text_column_index]]); rows_written += 1
                else: print(f"! Varování ({os.path.basename(input_filepath)}): Řádek {rows_processed} má méně sloupců.")
        write_output_file(output_filepath, encoding, header, filtered_data, rows_processed, rows_written, f"'{output_filename}' zpracován.")
        return True
    except (FileNotFoundError, LookupError, PermissionError, csv.Error, Exception) as e: handle_processing_error(e, input_filepath, encoding, reader); return False

def process_symboly_csv(input_filepath, encoding):
    """Zpracuje _symboly.csv soubor podle sloupců Typ a Symbol, uloží POUZE Typ."""
    global status_label
    if status_label: status_label.config(text=f"Zpracovávám: {os.path.basename(input_filepath)}...")
    print(f"\n--- Zpracování {os.path.basename(input_filepath)} (sloupce Typ a Symbol, ukládám jen Typ) ---")
    try:
        directory = os.path.dirname(input_filepath); filename, extension = os.path.splitext(os.path.basename(input_filepath))
        output_filename = f"{filename}{OUTPUT_SUFFIX}{extension}"; output_filepath = os.path.join(directory, output_filename)
        if not check_overwrite(output_filepath):
            if status_label: status_label.config(text=f"Zpracování {output_filename} zrušeno.")
            return False # Opraveno: unreachable code
        filtered_data = []; header = [SYMBOLY_COL_TYP]; rows_processed = 0; rows_written = 0
        reader = None; typ_col_idx = -1; symbol_col_idx = -1
        with open(input_filepath, 'r', encoding=encoding, newline='') as infile:
            reader = csv.reader(infile, delimiter=CSV_DELIMITER)
            try:
                input_header = next(reader); rows_processed += 1; print(f"DEBUG Hlavička: {input_header}")
                try:
                    typ_col_idx = input_header.index(SYMBOLY_COL_TYP); symbol_col_idx = input_header.index(SYMBOLY_COL_SYMBOL)
                    print(f"DEBUG Indexy: '{SYMBOLY_COL_TYP}'={typ_col_idx}, '{SYMBOLY_COL_SYMBOL}'={symbol_col_idx}")
                except ValueError as ve:
                     missing_col = str(ve).split("'")[1] if "'" in str(ve) else "Neznámý"; expected = f"'{SYMBOLY_COL_TYP}' nebo '{SYMBOLY_COL_SYMBOL}'"
                     print(f"! CHYBA: Chybí sloupec '{missing_col}'. Očekáván {expected}.")
                     messagebox.showerror("Chyba", f"Sloupec {expected} nebyl nalezen v '{os.path.basename(input_filepath)}'."); return False
            except StopIteration: print("! CHYBA: Soubor je prázdný."); messagebox.showerror("Chyba", f"Soubor '{os.path.basename(input_filepath)}' je prázdný."); return False
            for row_index, row in enumerate(reader, start=2):
                rows_processed += 1
                try:
                    if len(row) > max(typ_col_idx, symbol_col_idx):
                        original_typ = row[typ_col_idx]; typ_value = original_typ.strip(); symbol_value = row[symbol_col_idx].strip()
                        typ_ok = ('/' in typ_value and ':' in typ_value) and not (' ' in typ_value or '-' in typ_value)
                        symbol_ok = (symbol_value == SYMBOLY_SYMBOL_REQUIRED_VALUE)
                        if typ_ok and symbol_ok: filtered_data.append([original_typ]); rows_written += 1 # Ukládáme jen Typ
                    else: print(f"DEBUG: Řádek {row_index} (_symboly) má málo sloupců ({len(row)})")
                except IndexError: print(f"! CHYBA: IndexError na řádku {row_index} (_symboly)!")
                except Exception as inner_e: print(f"! CHYBA: Neočekávaná chyba řádek {row_index} (_symboly): {type(inner_e).__name__} - {inner_e}")
        print(f"--- Ukončeno {os.path.basename(input_filepath)}, Zpracováno: {rows_processed}, Nalezeno: {rows_written} ---")
        write_output_file(output_filepath, encoding, header, filtered_data, rows_processed, rows_written, f"'{output_filename}' zpracován.")
        return True
    except (FileNotFoundError, LookupError, PermissionError, csv.Error, Exception) as e: print(f"--- CHYBA: {os.path.basename(input_filepath)} ---"); handle_processing_error(e, input_filepath, encoding, reader); return False

def process_cary_csv(input_filepath, encoding):
    """Zpracuje _cary.csv soubor podle sloupců Značení (první) a Specifikace."""
    global status_label
    if status_label: status_label.config(text=f"Zpracovávám: {os.path.basename(input_filepath)}...")
    print(f"\n--- Zpracování {os.path.basename(input_filepath)} (sloupce Značení a Specifikace) ---")
    try:
        directory = os.path.dirname(input_filepath); filename, extension = os.path.splitext(os.path.basename(input_filepath))
        output_filename = f"{filename}{OUTPUT_SUFFIX}{extension}"; output_filepath = os.path.join(directory, output_filename)
        if not check_overwrite(output_filepath):
             if status_label: status_label.config(text=f"Zpracování {output_filename} zrušeno.")
             return False # Opraveno: unreachable code
        filtered_data = []; header = [CARY_COL_ZNACENI, CARY_COL_SPECIFIKACE]; rows_processed = 0; rows_written = 0
        reader = None; znaceni_col_idx = -1; specifikace_col_idx = -1
        with open(input_filepath, 'r', encoding=encoding, newline='') as infile:
            reader = csv.reader(infile, delimiter=CSV_DELIMITER)
            try:
                input_header = next(reader); rows_processed += 1; print(f"DEBUG Hlavička: {input_header}")
                for idx, col_name in enumerate(input_header):
                    if col_name == CARY_COL_ZNACENI and znaceni_col_idx == -1: znaceni_col_idx = idx
                    if col_name == CARY_COL_SPECIFIKACE: specifikace_col_idx = idx
                    if znaceni_col_idx != -1 and specifikace_col_idx != -1: break
                if znaceni_col_idx == -1: print(f"! CHYBA: Sloupec '{CARY_COL_ZNACENI}' nenalezen."); messagebox.showerror("Chyba", f"Sloupec '{CARY_COL_ZNACENI}' nebyl nalezen v '{os.path.basename(input_filepath)}'."); return False
                if specifikace_col_idx == -1: print(f"! CHYBA: Sloupec '{CARY_COL_SPECIFIKACE}' nenalezen."); messagebox.showerror("Chyba", f"Sloupec '{CARY_COL_SPECIFIKACE}' nebyl nalezen v '{os.path.basename(input_filepath)}'."); return False
                print(f"DEBUG Indexy: '{CARY_COL_ZNACENI}'={znaceni_col_idx}, '{CARY_COL_SPECIFIKACE}'={specifikace_col_idx}")
            except StopIteration: print("! CHYBA: Soubor je prázdný."); messagebox.showerror("Chyba", f"Soubor '{os.path.basename(input_filepath)}' je prázdný."); return False
            for row_index, row in enumerate(reader, start=2):
                rows_processed += 1
                try:
                    # Odsazení opraveno zde
                    if len(row) > max(znaceni_col_idx, specifikace_col_idx):
                        original_znaceni = row[znaceni_col_idx]; original_specifikace = row[specifikace_col_idx]; znaceni_value = original_znaceni.strip()
                        znaceni_ok = ('/' in znaceni_value and ':' in znaceni_value) and not (' ' in znaceni_value or '-' in znaceni_value)
                        if znaceni_ok: filtered_data.append([original_znaceni, original_specifikace]); rows_written += 1
                    else:
                        print(f"DEBUG: Řádek {row_index} (_cary) má málo sloupců ({len(row)})")
                except IndexError: print(f"! CHYBA: IndexError na řádku {row_index} (_cary)!")
                except Exception as inner_e: print(f"! CHYBA: Neočekávaná chyba řádek {row_index} (_cary): {type(inner_e).__name__} - {inner_e}")
        print(f"--- Ukončeno {os.path.basename(input_filepath)}, Zpracováno: {rows_processed}, Nalezeno: {rows_written} ---")
        write_output_file(output_filepath, encoding, header, filtered_data, rows_processed, rows_written, f"'{output_filename}' zpracován.")
        return True
    except (FileNotFoundError, LookupError, PermissionError, csv.Error, Exception) as e: print(f"--- CHYBA: {os.path.basename(input_filepath)} ---"); handle_processing_error(e, input_filepath, encoding, reader); return False


# --- Funkce pro Sloučení ---
def merge_and_deduplicate(cary_upr_path, symboly_upr_path, texty_upr_path, output_path, encoding):
    """Sloučí data, odstraní duplicity a uloží výsledek."""
    global status_label
    if status_label: status_label.config(text=f"Slučuji data -> {os.path.basename(output_path)}")
    print(f"\n--- Slučování a deduplikace ---"); print(f"-> {output_path}")
    unique_connections: dict = {} # Type hint
    processed_count = 0; skipped_no_slash = 0

    def get_canonical(connection_string):
        parsed = parse_connection(connection_string)
        if not parsed: return None, None, None
        part_a = f"{parsed['a']['name']}{parsed['a']['num'] or ''}:{parsed['a']['pin']}"
        part_b = f"{parsed['b']['name']}{parsed['b']['num'] or ''}:{parsed['b']['pin']}"
        canonical = f"{min(part_a, part_b)}/{max(part_a, part_b)}"; return canonical, part_a, part_b

    # Zpracování souborů... (kód s opraveným odsazením a syntaxí)
    try: # Cary
        with open(cary_upr_path, 'r', encoding=encoding, newline='') as infile:
            reader = csv.reader(infile, delimiter=CSV_DELIMITER); next(reader, None)
            for row_idx, row in enumerate(reader, start=2):
                processed_count += 1
                if not row: continue
                connection = row[0]
                spec = row[1] if len(row) > 1 else ""
                canonical, _, _ = get_canonical(connection)
                if canonical:
                    spec_to_store = spec.strip() if spec.strip() else DEFAULT_SPECIFICATION
                    if canonical not in unique_connections or unique_connections[canonical] == DEFAULT_SPECIFICATION:
                         unique_connections[canonical] = spec_to_store
                else: skipped_no_slash += 1; print(f"! Varování (_cary {row_idx}): Chybí/nelze parsovat '/' v '{connection}'")
    except FileNotFoundError: print(f"! Chyba: {os.path.basename(cary_upr_path)} nenalezen."); return False
    except Exception as e: print(f"! Chyba čtení {os.path.basename(cary_upr_path)}: {e}"); return False
    try: # Symboly
        with open(symboly_upr_path, 'r', encoding=encoding, newline='') as infile:
            reader = csv.reader(infile, delimiter=CSV_DELIMITER); next(reader, None)
            for row_idx, row in enumerate(reader, start=2):
                 processed_count += 1
                 if not row: continue
                 connection = row[0]
                 canonical, _, _ = get_canonical(connection)
                 if canonical:
                     if canonical not in unique_connections: unique_connections[canonical] = DEFAULT_SPECIFICATION
                 else: skipped_no_slash += 1; print(f"! Varování (_symboly {row_idx}): Chybí/nelze parsovat '/' v '{connection}'")
    except FileNotFoundError: print(f"! Chyba: {os.path.basename(symboly_upr_path)} nenalezen."); return False
    except Exception as e: print(f"! Chyba čtení {os.path.basename(symboly_upr_path)}: {e}"); return False
    try: # Texty
        with open(texty_upr_path, 'r', encoding=encoding, newline='') as infile:
            reader = csv.reader(infile, delimiter=CSV_DELIMITER); next(reader, None)
            for row_idx, row in enumerate(reader, start=2):
                 processed_count += 1
                 if not row: continue
                 connection = row[0]
                 canonical, _, _ = get_canonical(connection)
                 if canonical:
                     if canonical not in unique_connections: unique_connections[canonical] = DEFAULT_SPECIFICATION
                 else: skipped_no_slash += 1; print(f"! Varování (_texty {row_idx}): Chybí/nelze parsovat '/' v '{connection}'")
    except FileNotFoundError: print(f"! Chyba: {os.path.basename(texty_upr_path)} nenalezen."); return False
    except Exception as e: print(f"! Chyba čtení {os.path.basename(texty_upr_path)}: {e}"); return False

    print(f"--- Nalezeno {len(unique_connections)} unikátních spojení (zpracováno {processed_count}, přeskočeno {skipped_no_slash}) ---")
    if status_label: status_label.config(text=f"Zapisuji {len(unique_connections)} spojení -> {os.path.basename(output_path)}")
    try: # Zápis
        with open(output_path, 'w', encoding=encoding, newline='') as outfile:
            writer = csv.writer(outfile, delimiter=CSV_DELIMITER); writer.writerow(["Spojeni", "Specifikace"])
            for connection in sorted(unique_connections.keys()): # Seřazený výstup
                writer.writerow([connection, unique_connections[connection]])
        print(f"+ Soubor '{output_path}' vytvořen.")
    except Exception as e: print(f"! Chyba zápisu {output_path}: {e}"); messagebox.showerror("Chyba zápisu", f"Nelze zapsat '{output_path}':\n{e}"); return False
    try: # Kontrola duplicit
        if status_label: status_label.config(text=f"Kontrola duplicit v {os.path.basename(output_path)}...")
        connections_in_final = set(); duplicates_found = 0
        with open(output_path, 'r', encoding=encoding, newline='') as f:
            reader = csv.reader(f, delimiter=CSV_DELIMITER); next(reader)
            for row_idx, row in enumerate(reader, start=2):
                 if not row: continue; connection = row[0]
                 if connection in connections_in_final: duplicates_found += 1; print(f"! Varování: Duplicita v {os.path.basename(output_path)} řádek {row_idx}: '{connection}'")
                 connections_in_final.add(connection)
        if duplicates_found > 0: messagebox.showwarning("Kontrola duplicit", f"Nalezeno {duplicates_found} duplicit v '{os.path.basename(output_path)}'."); status_label.config(text=f"Hotovo, ale nalezeny duplicity ({duplicates_found}).")
        else: print("+ Kontrola duplicit OK."); status_label.config(text=f"Soubor {os.path.basename(output_path)} vytvořen a zkontrolován.")
        # Opraveno: Unreachable code
        return True # Vždy vrátíme True, pokud kontrola proběhla (i s duplicitami)
    except Exception as e:
        print(f"! Chyba kontroly duplicit {output_path}: {e}")
        messagebox.showerror("Chyba kontroly", f"Chyba kontroly '{output_path}':\n{e}")
        return False # Chyba při kontrole

# --- Funkce pro výběr souboru v GUI ---
def select_file(file_type_var, label_widget, suffix_filter):
    """Otevře dialog pro výběr souboru a aktualizuje globální proměnnou a label."""
    global texty_filepath, symboly_filepath, cary_filepath, status_label
    try: initial_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception: initial_dir = os.getcwd()
    filetypes = ((f"*{suffix_filter}", f"*{suffix_filter}"), ("CSV soubory", "*.csv"), ("Všechny soubory", "*.*"))
    filepath = filedialog.askopenfilename( initialdir=initial_dir, title=f"Vyberte soubor končící na {suffix_filter}", filetypes=filetypes)
    if filepath:
        if not filepath.lower().endswith(suffix_filter.lower()): messagebox.showwarning("Nesprávný typ souboru", f"Vybraný soubor '{os.path.basename(filepath)}' nekončí na '{suffix_filter}'."); return
        filename = os.path.basename(filepath)
        if file_type_var == 'texty': texty_filepath = filepath; label_widget.config(text=f"{filename}")
        elif file_type_var == 'symboly': symboly_filepath = filepath; label_widget.config(text=f"{filename}")
        elif file_type_var == 'cary': cary_filepath = filepath; label_widget.config(text=f"{filename}")
        if status_label: status_label.config(text=f"Soubor '{filename}' vybrán.")
    else:
         if status_label: status_label.config(text="Výběr souboru zrušen.")

# --- Třída Editoru ---
# from collections import Counter # Odstraněn reimport
class SpecEditorApp:
    def __init__(self, parent, input_file, output_file, encoding):
        self.parent = parent; self.input_file = input_file; self.output_file = output_file; self.encoding = encoding
        self.all_data = []; self.items_to_edit_ids = set(); self.group_keys = OrderedDict()
        self.component_specs = defaultdict(list); self.suggested_specs = {} # Opraveno: Použije se defaultdict z importu
        self.editor_window = tk.Toplevel(parent); self.editor_window.title("Editor Specifikací (priprava.csv)"); self.editor_window.geometry("900x600")
        self.editor_window.protocol("WM_DELETE_WINDOW", self.on_close)
        if not self.load_data(): self.on_close(); return
        self.create_widgets(); self.populate_treeview()

    def on_close(self): print("- Editor zavřen."); self.editor_window.destroy()

    def load_data(self):
        global status_label
        if status_label: status_label.config(text="Načítám a analyzuji data pro editor...")
        print(f"+ Načítám editor: {self.input_file}"); component_names_a = set(); component_names_b = set()
        self.component_specs.clear()
        try:
            with open(self.input_file, 'r', encoding=self.encoding, newline='') as f:
                reader = csv.reader(f, delimiter=CSV_DELIMITER); header = next(reader)
                if header != ["Spojeni", "Specifikace"]: messagebox.showerror("Chybný formát", f"'{os.path.basename(self.input_file)}' nemá hlavičku 'Spojeni;Specifikace'.", parent=self.editor_window); return False
                for i, row in enumerate(reader):
                    if len(row) != 2: print(f"! Varování editor: Přeskakuji řádek {i+2}: {row}"); continue
                    spojeni, spec_raw = row; spec = spec_raw.strip(); parsed_data = parse_connection(spojeni); item_id = f"item_{i}"
                    self.all_data.append({"id": item_id, "spojeni": spojeni, "spec": spec, "parsed": parsed_data})
                    current_spec_lower = spec.lower(); is_default_spec = current_spec_lower == DEFAULT_SPECIFICATION.lower() or not spec
                    if is_default_spec: self.items_to_edit_ids.add(item_id)
                    if parsed_data:
                        comp_a = parsed_data.get('a'); comp_b = parsed_data.get('b')
                        comp_a_name = comp_a.get('name') if comp_a else None; comp_b_name = comp_b.get('name') if comp_b else None
                        if comp_a_name: component_names_a.add(comp_a_name)
                        if comp_b_name: component_names_b.add(comp_b_name)
                        if not is_default_spec:
                            if comp_a_name: self.component_specs[comp_a_name].append(spec)
                            if comp_b_name: self.component_specs[comp_b_name].append(spec)
            self.suggested_specs.clear(); print("+ Analyzuji specifikace...");
            for comp_name, spec_list in self.component_specs.items():
                if spec_list:
                    spec_counts = Counter(spec_list); most_common_spec, count = spec_counts.most_common(1)[0]
                    if count > 1: self.suggested_specs[comp_name] = most_common_spec
            self.group_keys.clear(); self.group_keys["Všechny 'neni spec'"] = lambda item: item['id'] in self.items_to_edit_ids
            for name in sorted(list(component_names_a)):
                suggestion = self.suggested_specs.get(name); key = f"Název A: {name}"
                if suggestion: key += f" (návrh: '{suggestion}')"
                self.group_keys[key] = lambda item, n=name: item['id'] in self.items_to_edit_ids and item['parsed'] and item['parsed']['a']['name'] == n
            for name in sorted(list(component_names_b)):
                suggestion = self.suggested_specs.get(name); key_base = f"Název B: {name}"; key = key_base
                if suggestion: key += f" (návrh: '{suggestion}')"
                if key in self.group_keys:
                     if " (návrh: '" in key: key = key_base + " (B)";
                     else: key += " (B)"
                     if key in self.group_keys: key += "_2" # Extrémní případ
                self.group_keys[key] = lambda item, n=name: item['id'] in self.items_to_edit_ids and item['parsed'] and item['parsed']['b']['name'] == n
            print(f"+ Editor data: {len(self.all_data)} řádků, {len(self.items_to_edit_ids)} k editaci. Návrhů: {len(self.suggested_specs)}.")
            if status_label: status_label.config(text=f"Editor načten: {len(self.items_to_edit_ids)} položek k editaci.")
            if not self.items_to_edit_ids: messagebox.showinfo("Není co editovat", "V souboru nejsou žádné řádky s 'neni spec'.", parent=self.editor_window); return False
            return True
        except FileNotFoundError: messagebox.showerror("Chyba souboru", f"Vstup '{self.input_file}' nenalezen.", parent=self.editor_window); return False
        except Exception as e: messagebox.showerror("Chyba načítání", f"Chyba načítání editoru:\n{e}", parent=self.editor_window); print(f"! Chyba load_data: {e}"); import traceback; traceback.print_exc(); return False

    def create_widgets(self):
        top_frame = ttk.Frame(self.editor_window, padding="10"); top_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(top_frame, text="Zobrazit skupinu:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.group_combo = ttk.Combobox(top_frame, values=list(self.group_keys.keys()), state="readonly", width=60); self.group_combo.grid(row=0, column=1, padx=(0, 20), sticky=tk.W)
        if self.group_keys: self.group_combo.current(0); self.group_combo.bind("<<ComboboxSelected>>", self.on_group_select)
        ttk.Label(top_frame, text="Nová specifikace:").grid(row=0, column=2, padx=(10, 5), sticky=tk.W)
        self.spec_entry = ttk.Entry(top_frame, width=40); self.spec_entry.grid(row=0, column=3, padx=(0, 10), sticky=tk.W+tk.E)
        self.apply_button = ttk.Button(top_frame, text="Přiřadit skupině", command=self.apply_to_group); self.apply_button.grid(row=0, column=4, padx=(0, 5))
        tree_frame = ttk.Frame(self.editor_window, padding="10"); tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        columns = ("#0", "spojeni", "spec"); self.tree = ttk.Treeview(tree_frame, columns=columns[1:], show="headings", height=15)
        self.tree.heading("spojeni", text="Spojení"); self.tree.heading("spec", text="Specifikace")
        self.tree.column("spojeni", width=400, anchor=tk.W); self.tree.column("spec", width=300, anchor=tk.W)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set); vsb.pack(side=tk.RIGHT, fill=tk.Y); hsb.pack(side=tk.BOTTOM, fill=tk.X); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.config(selectmode='extended'); self.tree.bind("<Double-1>", self.edit_selected_item_popup)
        bottom_frame = ttk.Frame(self.editor_window, padding="10"); bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.save_button = ttk.Button(bottom_frame, text="Uložit změny do " + os.path.basename(self.output_file), command=self.save_changes); self.save_button.pack(side=tk.RIGHT)
        self.cancel_button = ttk.Button(bottom_frame, text="Zavřít editor", command=self.on_close); self.cancel_button.pack(side=tk.RIGHT, padx=10)

    def populate_treeview(self, filter_func=None):
        for item in self.tree.get_children(): self.tree.delete(item)
        if filter_func is None: filter_key = self.group_combo.get(); filter_func = self.group_keys.get(filter_key, lambda item: False)
        for item_data in self.all_data:
            if filter_func(item_data): self.tree.insert("", tk.END, iid=item_data['id'], values=(item_data['spojeni'], item_data['spec']))

    def on_group_select(self, _event=None): # Opraveno: _event
        filter_key = self.group_combo.get(); filter_func = self.group_keys.get(filter_key)
        self.spec_entry.delete(0, tk.END)
        match = re.search(r"\(návrh: '(.*)'\)", filter_key)
        if match: suggested_spec = match.group(1); self.spec_entry.insert(0, suggested_spec); print(f"+ Návrh: '{suggested_spec}' pro '{filter_key}'")
        if filter_func: self.populate_treeview(filter_func)
        else: print(f"! Chyba filtru: '{filter_key}'")

    def apply_to_group(self):
        new_spec = self.spec_entry.get().strip()
        if not new_spec: messagebox.showwarning("Chybí specifikace", "Zadejte novou specifikaci.", parent=self.editor_window); return
        visible_item_ids = self.tree.get_children()
        if not visible_item_ids: messagebox.showinfo("Žádné položky", "Ve skupině nejsou položky k úpravě.", parent=self.editor_window); return
        confirm = messagebox.askyesno("Potvrdit změnu", f"Opravdu nastavit '{new_spec}'\npro {len(visible_item_ids)} zobrazených položek?", parent=self.editor_window)
        if not confirm: return
        updated_count = 0
        for item_id in visible_item_ids:
            for item_data in self.all_data:
                if item_data['id'] == item_id:
                    item_data['spec'] = new_spec
                    if item_id in self.items_to_edit_ids: self.items_to_edit_ids.remove(item_id)
                    try: self.tree.item(item_id, values=(item_data['spojeni'], new_spec))
                    except tk.TclError: print(f"! Varování: Aktualizace Treeview selhala pro {item_id}.")
                    updated_count += 1; break
        print(f"+ Spec '{new_spec}' aplikována na {updated_count} položek.")
        if updated_count > 0: messagebox.showinfo("Aktualizováno", f"{updated_count} položek aktualizováno.\nZůstávají zobrazeny.", parent=self.editor_window)

    def edit_selected_item_popup(self, _event=None): # Opraveno: _event
        selected_items = self.tree.selection()
        if not selected_items or len(selected_items) > 1: return
        item_id = selected_items[0]; item_data = next((item for item in self.all_data if item['id'] == item_id), None)
        if not item_data: return
        new_spec = simpledialog.askstring("Upravit specifikaci", f"Nová specifikace pro:\n{item_data['spojeni']}", initialvalue=item_data['spec'], parent=self.editor_window)
        if new_spec is not None:
            new_spec = new_spec.strip(); item_data['spec'] = new_spec if new_spec else DEFAULT_SPECIFICATION
            new_spec_lower = item_data['spec'].lower(); is_default = new_spec_lower == DEFAULT_SPECIFICATION.lower() or not new_spec_lower
            if item_id in self.items_to_edit_ids and not is_default: self.items_to_edit_ids.remove(item_id)
            elif item_id not in self.items_to_edit_ids and is_default: self.items_to_edit_ids.add(item_id)
            self.tree.item(item_id, values=(item_data['spojeni'], item_data['spec'])); print(f"+ Položka {item_id} upravena na '{item_data['spec']}'")

    def save_changes(self):
        global status_label
        output_basename = os.path.basename(self.output_file); print(f"+ Ukládám změny do: {self.output_file}")
        if os.path.exists(self.output_file):
             overwrite = messagebox.askyesno("Soubor existuje", f"Soubor '{output_basename}' již existuje.\nPřepsat?", icon='warning', parent=self.editor_window)
             if not overwrite: print("- Ukládání zrušeno."); return
        try:
            written_count = 0
            with open(self.output_file, 'w', encoding=self.encoding, newline='') as outfile:
                writer = csv.writer(outfile, delimiter=CSV_DELIMITER); writer.writerow(["Spojeni", "Specifikace"])
                for item_data in self.all_data:
                    spec_to_write = item_data['spec'] if item_data['spec'] else DEFAULT_SPECIFICATION
                    writer.writerow([item_data['spojeni'], spec_to_write]); written_count +=1
            print(f"+ Změny uloženy do '{output_basename}'. Zapsáno {written_count} řádků.")
            messagebox.showinfo("Uloženo", f"Změny uloženy do:\n{self.output_file}", parent=self.editor_window)
            if status_label: status_label.config(text=f"Změny uloženy do {output_basename}.")
            self.on_close()
        except Exception as e: print(f"! Chyba ukládání: {e}"); messagebox.showerror("Chyba ukládání", f"Nelze uložit '{output_basename}':\n{e}", parent=self.editor_window)


# --- Funkce pro tlačítka GUI ---
def run_filter_and_merge():
    """Spustí Fázi 1 (filtrování) a Fázi 2 (sloučení)."""
    global status_label, texty_filepath, symboly_filepath, cary_filepath # Odebráno global main_root
    if not texty_filepath or not symboly_filepath or not cary_filepath: messagebox.showerror("Chybí", "Vyberte prosím všechny 3 vstupní soubory."); return
    file_encoding = read_encoding(ENCODING_FILE);
    if file_encoding is None:
        if status_label: status_label.config(text="Chyba kódování.")
        return # Opraveno: Chyběl return
    if status_label: status_label.config(text="Fáze 1: Zpracování vstupů...")
    # Opraveno odsazení a f-string
    dir1=os.path.dirname(texty_filepath); fn1,e1=os.path.splitext(os.path.basename(texty_filepath)); texty_upr_path=os.path.join(dir1, f"{fn1}{OUTPUT_SUFFIX}{e1}")
    dir2=os.path.dirname(symboly_filepath); fn2,e2=os.path.splitext(os.path.basename(symboly_filepath)); symboly_upr_path=os.path.join(dir2, f"{fn2}{OUTPUT_SUFFIX}{e2}")
    dir3=os.path.dirname(cary_filepath); fn3,e3=os.path.splitext(os.path.basename(cary_filepath)); cary_upr_path=os.path.join(dir3, f"{fn3}{OUTPUT_SUFFIX}{e3}")
    if not process_texty_csv(texty_filepath, file_encoding): return
    if not process_symboly_csv(symboly_filepath, file_encoding): return
    if not process_cary_csv(cary_filepath, file_encoding): return
    print("--- Fáze 1 (Filtrování) dokončena ---")
    if status_label: status_label.config(text="Fáze 1 OK. Zahajuji Fázi 2: Slučování...")
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    priprava_csv_path = os.path.join(script_dir, FINAL_OUTPUT_FILENAME)
    if not os.path.exists(texty_upr_path) or not os.path.exists(symboly_upr_path) or not os.path.exists(cary_upr_path): messagebox.showerror("Chyba", "Některý z '_upr.csv' souborů nebyl nalezen pro sloučení."); return
    merge_success = merge_and_deduplicate(cary_upr_path, symboly_upr_path, texty_upr_path, priprava_csv_path, file_encoding)
    if merge_success: messagebox.showinfo("Dokončeno", f"Filtrování a sloučení dokončeno.\nVýsledek: {priprava_csv_path}")
    else: messagebox.showerror("Selhání", "Fáze 2 (slučování) selhala."); status_label.config(text="Chyba při slučování dat.")

def run_editor():
    """Spustí editor specifikací pro priprava.csv."""
    global main_root, status_label # main_root je potřeba pro Toplevel
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    priprava_csv_path = os.path.join(script_dir, FINAL_OUTPUT_FILENAME)
    edited_output_path = os.path.join(script_dir, EDITED_OUTPUT_FILENAME)
    if not os.path.exists(priprava_csv_path): messagebox.showerror("Chyba", f"Soubor '{FINAL_OUTPUT_FILENAME}' nenalezen.\nNejprve spusťte 'Zpracovat a Sloučit'."); status_label.config(text=f"Soubor {FINAL_OUTPUT_FILENAME} nenalezen."); return
    file_encoding = read_encoding(ENCODING_FILE);
    if file_encoding is None:
         if status_label: status_label.config(text="Chyba kódování pro editor.")
         return
    if status_label: status_label.config(text="Spouštím editor specifikací...")
    # Instance editoru se vytvoří, ale nemusíme ji ukládat do proměnné
    SpecEditorApp(main_root, priprava_csv_path, edited_output_path, file_encoding)
    # Status se aktualizuje uvnitř editoru

def run_overwrite_original():
    """Přepíše priprava.csv souborem priprava_upr.csv."""
    global status_label # main_root zde nepotřebujeme
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    priprava_csv_path = os.path.join(script_dir, FINAL_OUTPUT_FILENAME)
    edited_output_path = os.path.join(script_dir, EDITED_OUTPUT_FILENAME)
    if not os.path.exists(edited_output_path): messagebox.showerror("Chyba", f"Soubor '{EDITED_OUTPUT_FILENAME}' nenalezen.\nSpusťte editor a uložte změny."); status_label.config(text=f"Soubor {EDITED_OUTPUT_FILENAME} nenalezen."); return
    confirm = messagebox.askyesno("Potvrdit přepsání", f"Opravdu přepsat '{FINAL_OUTPUT_FILENAME}'\nobsahem souboru '{EDITED_OUTPUT_FILENAME}'?\n\nTato akce je nevratná!", icon='warning')
    if not confirm:
        if status_label: status_label.config(text="Přepsání originálu zrušeno.")
        return # Opraveno: Chyběl return
    try:
        print(f"+ Přesouvám '{edited_output_path}' -> '{priprava_csv_path}'")
        shutil.move(edited_output_path, priprava_csv_path)
        messagebox.showinfo("Hotovo", f"Soubor '{FINAL_OUTPUT_FILENAME}' byl úspěšně přepsán.")
        if status_label: status_label.config(text=f"Soubor {FINAL_OUTPUT_FILENAME} přepsán.")
        print(f"+ Soubor '{FINAL_OUTPUT_FILENAME}' přepsán.")
    except Exception as e:
        print(f"! Chyba při přepisování: {e}")
        messagebox.showerror("Chyba", f"Nepodařilo se přepsat '{FINAL_OUTPUT_FILENAME}':\n{e}")
        if status_label: status_label.config(text="Chyba při přepisování.")


# --- Hlavní spuštění GUI ---
if __name__ == "__main__":
    main_root = tk.Tk()
    main_root.title("CSV Nástroje v1.2") # Opět zvýšena verze

    style = ttk.Style()
    try: style.theme_use('vista')
    except tk.TclError: print("Poznámka: Téma 'vista' není dostupné.")

    file_frame = ttk.Frame(main_root, padding="10", borderwidth=2, relief=tk.GROOVE); file_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(file_frame, text="1. Výběr vstupních CSV souborů:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0,5), sticky=tk.W)
    select_texty_button = ttk.Button(file_frame, text=f"Vybrat {TEXTY_SUFFIX}", width=20, command=lambda: select_file('texty', texty_label, TEXTY_SUFFIX)); select_texty_button.grid(row=1, column=0, padx=5, pady=2, sticky=tk.W+tk.E)
    texty_label = ttk.Label(file_frame, text="(nevybrán)", anchor=tk.W, width=45); texty_label.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
    select_symboly_button = ttk.Button(file_frame, text=f"Vybrat {SYMBOLY_SUFFIX}", width=20, command=lambda: select_file('symboly', symboly_label, SYMBOLY_SUFFIX)); select_symboly_button.grid(row=2, column=0, padx=5, pady=2, sticky=tk.W+tk.E)
    symboly_label = ttk.Label(file_frame, text="(nevybrán)", anchor=tk.W, width=45); symboly_label.grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)
    select_cary_button = ttk.Button(file_frame, text=f"Vybrat {CARY_SUFFIX}", width=20, command=lambda: select_file('cary', cary_label, CARY_SUFFIX)); select_cary_button.grid(row=3, column=0, padx=5, pady=2, sticky=tk.W+tk.E)
    cary_label = ttk.Label(file_frame, text="(nevybrán)", anchor=tk.W, width=45); cary_label.grid(row=3, column=1, padx=5, pady=2, sticky=tk.W)

    action_frame = ttk.Frame(main_root, padding="10", borderwidth=2, relief=tk.GROOVE); action_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(action_frame, text="2. Zpracování a Editace:", font=('Segoe UI', 9, 'bold')).pack(anchor=tk.W, pady=(0,5))
    process_button = ttk.Button(action_frame, text=f"Zpracovat vstupy a Sloučit do '{FINAL_OUTPUT_FILENAME}'", command=run_filter_and_merge); process_button.pack(pady=5, fill=tk.X)
    edit_button = ttk.Button(action_frame, text=f"Editovat Specifikace v '{FINAL_OUTPUT_FILENAME}'", command=run_editor); edit_button.pack(pady=5, fill=tk.X)
    overwrite_button = ttk.Button(action_frame, text=f"Aktualizovat '{FINAL_OUTPUT_FILENAME}' upraveným souborem", command=run_overwrite_original); overwrite_button.pack(pady=5, fill=tk.X)

    # Uložení reference na status_label do globální proměnné
    status_label = ttk.Label(main_root, text="Připraven. Vyberte vstupní soubory.", relief=tk.SUNKEN, anchor=tk.W, padding=(5,2)); status_label.pack(fill=tk.X, side=tk.BOTTOM, ipady=2)

    main_root.mainloop()