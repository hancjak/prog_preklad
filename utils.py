# -*- coding: utf-8 -*-

"""Pomocné funkce pro CSV nástroje."""

import os
import sys
import re
import csv
from tkinter import messagebox # Potřebujeme pro check_overwrite a handle_error

# Import konfigurace
import config

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

# --- Pomocné Funkce pro soubory a GUI ---
def read_encoding(filename=config.ENCODING_FILE):
    """Načte znakovou sadu."""
    try:
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        encoding_filepath = os.path.join(script_dir, filename)
        with open(encoding_filepath, 'r', encoding='utf-8') as f: # Používáme utf-8 pro čtení konfigurace
            first_line = f.readline().strip()
        if first_line:
            try: "test".encode(first_line); print(f"+ Znak. sada: {first_line}"); return first_line
            except LookupError: print(f"! Chyba: Neplatná znak. sada '{first_line}'. Používám: {config.DEFAULT_ENCODING}"); messagebox.showwarning("Chyba kódování", f"Neplatná sada '{first_line}'.\nBude použito: {config.DEFAULT_ENCODING}"); return config.DEFAULT_ENCODING
        else: print(f"! Chyba: Soubor '{filename}' prázdný. Používám: {config.DEFAULT_ENCODING}"); messagebox.showwarning("Chyba kódování", f"Soubor '{filename}' prázdný.\nBude použito: {config.DEFAULT_ENCODING}"); return config.DEFAULT_ENCODING
    except FileNotFoundError: print(f"! Chyba: Soubor '{filename}' nenalezen. Používám: {config.DEFAULT_ENCODING}"); messagebox.showwarning("Chyba konfigurace", f"Soubor '{filename}' nenalezen.\nBude použito: {config.DEFAULT_ENCODING}"); return config.DEFAULT_ENCODING
    except Exception as e: print(f"! Chyba při čtení '{filename}': {e}. Používám: {config.DEFAULT_ENCODING}"); messagebox.showerror("Chyba konfigurace", f"Chyba při čtení '{filename}':\n{e}\nBude použito: {config.DEFAULT_ENCODING}"); return None

def check_overwrite(output_filepath):
    """Zkontroluje existenci souboru a zeptá se na přepsání."""
    if os.path.exists(output_filepath):
        output_filename = os.path.basename(output_filepath)
        overwrite = messagebox.askyesno("Soubor existuje", f"Soubor '{output_filename}' již existuje.\nPřejete si ho přepsat?", icon='warning')
        if not overwrite: print(f"- Přepis '{output_filename}' zrušen."); return False
        else: print(f"+ Přepisuji '{output_filename}'."); return True
    return True

def write_output_file(output_filepath, encoding, header, data):
    """Zapíše data do výstupního CSV souboru."""
    output_filename = os.path.basename(output_filepath)
    rows_written = len(data)
    print(f"+ Zapisuji {rows_written} řádků do '{output_filename}'...")
    try:
        with open(output_filepath, 'w', encoding=encoding, newline='') as outfile:
            writer = csv.writer(outfile, delimiter=config.CSV_DELIMITER)
            writer.writerow(header)
            writer.writerows(data)
        print(f"+ Soubor '{output_filename}' uložen.")
        return True # Úspěch
    except PermissionError:
        messagebox.showerror("Chyba oprávnění", f"Nelze zapsat:\n'{output_filepath}'.")
        print(f"! Chyba oprávnění při zápisu: {output_filename}.")
        return False # Neúspěch
    except Exception as e:
        messagebox.showerror("Chyba zápisu", f"Chyba při zápisu '{output_filename}':\n{e}")
        print(f"! Chyba zápisu {output_filename}: {e}")
        return False # Neúspěch

def handle_processing_error(e, input_filepath, reader, status_label_widget=None):
    """Zpracuje a zobrazí chyby, volitelně aktualizuje status label."""
    input_filename = os.path.basename(input_filepath)
    error_type = type(e).__name__; error_msg = str(e); line_num_msg = ""
    status_update = f"! Chyba: '{input_filename}'."

    if isinstance(e, FileNotFoundError):
        messagebox.showerror("Chyba souboru", f"Soubor nenalezen:\n{input_filepath}")
        status_update = f"! Chyba: '{input_filename}' nenalezen."
    elif isinstance(e, LookupError):
        # Tato chyba by měla být zachycena už v read_encoding, ale pro jistotu
        messagebox.showerror("Chyba kódování", f"Nepodporovaná znaková sada.\nZkontrolujte '{config.ENCODING_FILE}'.")
        status_update = "! Chyba: Neplatné kódování."
    elif isinstance(e, PermissionError):
        messagebox.showerror("Chyba oprávnění", "Nedostatečná oprávnění pro čtení/zápis.")
        status_update = "! Chyba: Oprávnění."
    elif isinstance(e, csv.Error):
        line_num_msg = f" řádek {reader.line_num}" if reader and hasattr(reader, 'line_num') else ""
        messagebox.showerror("Chyba CSV", f"Chyba CSV '{input_filename}'{line_num_msg}:\n{error_msg}")
        status_update = f"! Chyba CSV: '{input_filename}'."
    else:
        current_line = reader.line_num if reader and hasattr(reader, 'line_num') else 'N/A'
        line_num_msg = f" řádek ~{current_line}"
        messagebox.showerror("Neočekávaná chyba", f"Chyba '{error_type}'{line_num_msg} v '{input_filename}':\n{error_msg}")
        status_update = f"! Chyba: '{input_filename}'."
        import traceback
        print(f"! Detail chyby '{input_filename}': {error_type} - {error_msg}")
        traceback.print_exc()

    if status_label_widget:
        try:
            status_label_widget.config(text=status_update)
        except Exception:
            print("! Chyba: Nelze aktualizovat status label.")