# -*- coding: utf-8 -*-
"""Funkce pro specifické zpracování a slučování CSV souborů."""
import csv
import os
# from collections import Counter, OrderedDict, defaultdict # Odebráno
from tkinter import messagebox # Tento zůstává

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
    # Předpokládáme, že parse_connection vrátilo validní data
    part_a = f"{parsed['a']['name']}{parsed['a']['num'] or ''}:{parsed['a']['pin']}"
    part_b = f"{parsed['b']['name']}{parsed['b']['num'] or ''}:{parsed['b']['pin']}"
    canonical = f"{min(part_a, part_b)}/{max(part_a, part_b)}"
    return canonical, part_a, part_b


# --- Funkce pro zpracování jednotlivých CSV ---

def process_texty_csv(input_filepath, encoding, status_label_widget=None):
    """Zpracuje _texty.csv soubor."""
    if status_label_widget: status_label_widget.config(text=f"Zpracovávám: {os.path.basename(input_filepath)}...")
    output_filepath = "" # Definujeme pro případ chyby před přiřazením
    reader = None # Definujeme pro případ chyby v 'with'
    try:
        directory = os.path.dirname(input_filepath); filename, extension = os.path.splitext(os.path.basename(input_filepath))
        output_filename = f"{filename}{config.OUTPUT_SUFFIX}{extension}"; output_filepath = os.path.join(directory, output_filename)
        if not check_overwrite(output_filepath):
            if status_label_widget: status_label_widget.config(text=f"Zpracování {output_filename} zrušeno.")
            return False, "" # Vracíme i cestu (prázdnou, pokud neúspěch)

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
            write_output_file_message(output_filepath, rows_processed, rows_written, status_label_widget)
            return True, output_filepath
        else:
            return False, ""

    except (FileNotFoundError, LookupError, PermissionError, csv.Error, Exception) as e:
        handle_processing_error(e, input_filepath, reader, status_label_widget)
        return False, ""


def process_symboly_csv(input_filepath, encoding, status_label_widget=None):
    """Zpracuje _symboly.csv soubor podle sloupců Typ a Symbol, uloží POUZE Typ."""
    if status_label_widget: status_label_widget.config(text=f"Zpracovávám: {os.path.basename(input_filepath)}...")
    print(f"\n--- Zpracování {os.path.basename(input_filepath)} (sloupce Typ a Symbol, ukládám jen Typ) ---")
    output_filepath = ""
    reader = None
    try:
        directory = os.path.dirname(input_filepath); filename, extension = os.path.splitext(os.path.basename(input_filepath))
        output_filename = f"{filename}{config.OUTPUT_SUFFIX}{extension}"; output_filepath = os.path.join(directory, output_filename)
        if not check_overwrite(output_filepath):
            if status_label_widget: status_label_widget.config(text=f"Zpracování {output_filename} zrušeno.")
            return False, ""
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
                    print(f"! CHYBA: Chybí sloupec '{missing_col}'. Očekáván {expected}.")
                    messagebox.showerror("Chyba", f"Sloupec {expected} nebyl nalezen v '{os.path.basename(input_filepath)}'."); return False, ""
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
                except IndexError: print(f"! CHYBA: IndexError na řádku {row_index} (_symboly)!")
                except Exception as inner_e: print(f"! CHYBA: Neočekávaná chyba řádek {row_index} (_symboly): {type(inner_e).__name__} - {inner_e}")
        print(f"--- Ukončeno {os.path.basename(input_filepath)}, Zpracováno: {rows_processed}, Nalezeno: {rows_written} ---")
        success = write_output_file(output_filepath, encoding, header, filtered_data)
        if success:
            write_output_file_message(output_filepath, rows_processed, rows_written, status_label_widget)
            return True, output_filepath
        else:
            return False, ""
    except (FileNotFoundError, LookupError, PermissionError, csv.Error, Exception) as e: print(f"--- CHYBA: {os.path.basename(input_filepath)} ---"); handle_processing_error(e, input_filepath, reader, status_label_widget); return False, ""

def process_cary_csv(input_filepath, encoding, status_label_widget=None):
    """Zpracuje _cary.csv soubor podle sloupců Značení (první) a Specifikace."""
    if status_label_widget: status_label_widget.config(text=f"Zpracovávám: {os.path.basename(input_filepath)}...")
    print(f"\n--- Zpracování {os.path.basename(input_filepath)} (sloupce Značení a Specifikace) ---")
    output_filepath = ""
    reader = None
    try:
        directory = os.path.dirname(input_filepath); filename, extension = os.path.splitext(os.path.basename(input_filepath))
        output_filename = f"{filename}{config.OUTPUT_SUFFIX}{extension}"; output_filepath = os.path.join(directory, output_filename)
        if not check_overwrite(output_filepath):
            if status_label_widget: status_label_widget.config(text=f"Zpracování {output_filename} zrušeno.")
            return False, ""
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
                except IndexError: print(f"! CHYBA: IndexError na řádku {row_index} (_cary)!")
                except Exception as inner_e: print(f"! CHYBA: Neočekávaná chyba řádek {row_index} (_cary): {type(inner_e).__name__} - {inner_e}")
        print(f"--- Ukončeno {os.path.basename(input_filepath)}, Zpracováno: {rows_processed}, Nalezeno: {rows_written} ---")
        success = write_output_file(output_filepath, encoding, header, filtered_data)
        if success:
            write_output_file_message(output_filepath, rows_processed, rows_written, status_label_widget)
            return True, output_filepath
        else:
            return False, ""
    except (FileNotFoundError, LookupError, PermissionError, csv.Error, Exception) as e: print(f"--- CHYBA: {os.path.basename(input_filepath)} ---"); handle_processing_error(e, input_filepath, reader, status_label_widget); return False, ""


# --- Funkce pro Sloučení ---
def merge_and_deduplicate(cary_upr_path, symboly_upr_path, texty_upr_path, output_path, encoding, status_label_widget=None):
    """Sloučí data, odstraní duplicity a uloží výsledek."""
    if status_label_widget: status_label_widget.config(text=f"Slučuji data -> {os.path.basename(output_path)}")
    print("\n--- Slučování a deduplikace ---"); print(f"-> {output_path}")
    unique_connections: dict = {} # Type hint
    processed_count = 0; skipped_no_parse = 0

    # Zpracování souborů...
    for file_path in [cary_upr_path, symboly_upr_path, texty_upr_path]:
        is_cary = file_path == cary_upr_path
        print(f"+ Zpracovávám pro sloučení: {os.path.basename(file_path)}")
        try:
            with open(file_path, 'r', encoding=encoding, newline='') as infile:
                reader = csv.reader(infile, delimiter=config.CSV_DELIMITER)
                try:
                    header_line = next(reader, None) # Přečíst hlavičku, nebo None pokud prázdný
                    if header_line is None:
                        print(f"- Soubor {os.path.basename(file_path)} je prázdný.")
                        continue # Přeskočit na další soubor
                except StopIteration:
                    print(f"- Soubor {os.path.basename(file_path)} je prázdný.")
                    continue

                for row_idx, row in enumerate(reader, start=2):
                    processed_count += 1
                    if not row: continue
                    connection = row[0]
                    spec = row[1].strip() if is_cary and len(row) > 1 else "" # Specifikaci bereme jen z _cary

                    canonical, _, _ = get_canonical(connection)

                    if canonical:
                        spec_to_store = spec if spec else config.DEFAULT_SPECIFICATION
                        # Přidat nebo aktualizovat podle priority
                        if canonical not in unique_connections:
                            # Pokud záznam neexistuje, přidáme ho
                            unique_connections[canonical] = spec_to_store if is_cary else config.DEFAULT_SPECIFICATION
                        elif is_cary and unique_connections[canonical] == config.DEFAULT_SPECIFICATION and spec_to_store != config.DEFAULT_SPECIFICATION:
                            # Pokud záznam existuje s defaultní specifikací a my máme novou platnou z _cary, aktualizujeme
                            unique_connections[canonical] = spec_to_store
                    else:
                        skipped_no_parse += 1
                        print(f"! Varování ({os.path.basename(file_path)} řádek {row_idx}): Nelze zpracovat spojení '{connection}'")

        except FileNotFoundError: print(f"! Chyba: {os.path.basename(file_path)} nenalezen."); return False
        except Exception as e: print(f"! Chyba čtení {os.path.basename(file_path)}: {e}"); return False

    print(f"--- Nalezeno {len(unique_connections)} unikátních spojení (zpracováno {processed_count}, přeskočeno {skipped_no_parse}) ---")
    if status_label_widget: status_label_widget.config(text=f"Zapisuji {len(unique_connections)} spojení -> {os.path.basename(output_path)}")

    # Zápis výsledku
    success_write = write_output_file(output_path, encoding, ["Spojeni", "Specifikace"],
                                      [[conn, spec] for conn, spec in sorted(unique_connections.items())]) # Seřazený výstup
    if not success_write: return False

    # Kontrola duplicit
    try:
        if status_label_widget: status_label_widget.config(text=f"Kontrola duplicit v {os.path.basename(output_path)}...")
        connections_in_final = set(); duplicates_found = 0
        with open(output_path, 'r', encoding=encoding, newline='') as f:
            reader = csv.reader(f, delimiter=config.CSV_DELIMITER); next(reader)
            for row_idx, row in enumerate(reader, start=2):
                if not row: continue; connection = row[0]
                if connection in connections_in_final: duplicates_found += 1; print(f"! Varování: Duplicita v {os.path.basename(output_path)} řádek {row_idx}: '{connection}'")
                connections_in_final.add(connection)
        if duplicates_found > 0:
            messagebox.showwarning("Kontrola duplicit", f"Nalezeno {duplicates_found} duplicit v '{os.path.basename(output_path)}'.")
            if status_label_widget: status_label_widget.config(text=f"Hotovo, ale nalezeny duplicity ({duplicates_found}).")
        else:
            print("+ Kontrola duplicit OK.")
            if status_label_widget: status_label_widget.config(text=f"Soubor {os.path.basename(output_path)} vytvořen a zkontrolován.")
        return True
    except Exception as e: print(f"! Chyba kontroly duplicit {output_path}: {e}"); messagebox.showerror("Chyba kontroly", f"Chyba kontroly '{output_path}':\n{e}"); return False

def write_output_file_message(output_filepath, rows_processed, rows_written, status_label_widget):
    """Pomocná funkce pro zobrazení výsledku zpracování jednotlivých CSV."""
    output_filename = os.path.basename(output_filepath)
    if rows_written == 0 and rows_processed > 1:
        messagebox.showwarning("Prázdný výsledek", f"Pro '{output_filename}' nezůstaly žádné řádky.")
        msg = f"'{output_filename}': Žádná data."
    elif rows_processed <= 1:
        msg = f"'{output_filename}': Vstup prázdný."
    else:
        msg = f"'{output_filename}' zpracován ({rows_written} řádků)."

    if status_label_widget:
        status_label_widget.config(text=msg)