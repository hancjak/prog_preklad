# -*- coding: utf-8 -*-

"""Pomocné funkce pro CSV nástroje."""

import os
import re
import csv
from tkinter import messagebox
# import queue # ODEBRÁNO

import config

# ... (parse_component, parse_connection, read_encoding, check_overwrite zůstávají) ...
def parse_component(comp_str):
    match_comp_pin = re.match(r"^(.*?):(.*)$", comp_str)
    if not match_comp_pin: comp_part = comp_str; pin = None
    else: comp_part = match_comp_pin.group(1).strip(); pin = match_comp_pin.group(2).strip()
    match_name_num = re.match(r"^([a-zA-Z_]+)(\d*)$", comp_part)
    if match_name_num: name = match_name_num.group(1); num_str = match_name_num.group(2); num = int(num_str) if num_str else None
    else: name = comp_part; num = None
    return {"name": name, "num": num, "pin": pin}

def parse_connection(connection_string):
    if '/' not in connection_string: return None
    parts = connection_string.split('/', 1); part_a_str = parts[0].strip(); part_b_str = parts[1].strip()
    if not part_a_str or not part_b_str: return None
    comp_a = parse_component(part_a_str); comp_b = parse_component(part_b_str)
    if not comp_a or not comp_b or comp_a['pin'] is None or comp_b['pin'] is None: return None
    return {"a": comp_a, "b": comp_b}

def read_encoding(base_dir, filename=config.ENCODING_FILE):
    encoding_filepath = os.path.join(base_dir, filename) # Sestavení cesty
    encoding_filename_only = os.path.basename(encoding_filepath) # Pro zprávy
    print(f"+ Hledám znakovou sadu v: {encoding_filepath}")
    try:
        with open(encoding_filepath, 'r', encoding='utf-8') as f: # Čteme konfigurační soubor vždy jako utf-8
            first_line = f.readline().strip()
        if first_line:
            try:
                "test".encode(first_line) # Otestujeme platnost kódování
                print(f"+ Znaková sada nalezena: {first_line}")
                return first_line
            except LookupError:
                print(f"! Chyba: Neplatná znaková sada '{first_line}' v '{encoding_filename_only}'. Používám: {config.DEFAULT_ENCODING}")
                messagebox.showwarning("Chyba kódování", f"Neplatná sada '{first_line}' v '{encoding_filename_only}'.\nBude použito: {config.DEFAULT_ENCODING}")
                return config.DEFAULT_ENCODING
        else:
            print(f"! Chyba: Soubor '{encoding_filename_only}' je prázdný. Používám: {config.DEFAULT_ENCODING}")
            messagebox.showwarning("Chyba kódování", f"Soubor '{encoding_filename_only}' je prázdný.\nBude použito: {config.DEFAULT_ENCODING}")
            return config.DEFAULT_ENCODING
    except FileNotFoundError:
        print(f"! Chyba: Soubor '{encoding_filename_only}' nenalezen v '{base_dir}'. Používám: {config.DEFAULT_ENCODING}")
        messagebox.showwarning("Chyba konfigurace", f"Soubor '{encoding_filename_only}' nenalezen.\nBude použito: {config.DEFAULT_ENCODING}")
        return config.DEFAULT_ENCODING
    except Exception as e:
        print(f"! Chyba při čtení '{encoding_filename_only}': {e}. Používám: {config.DEFAULT_ENCODING}")
        messagebox.showerror("Chyba konfigurace", f"Chyba při čtení '{encoding_filename_only}':\n{e}\nBude použito: {config.DEFAULT_ENCODING}")
        return None # None značí kritickou chybu čtení
        
def check_overwrite(output_filepath):
    """Zkontroluje existenci souboru a zeptá se na přepsání (voláno z hlavního vlákna)."""
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
    except PermissionError as e:
        print(f"! Chyba oprávnění při zápisu: {output_filename}.")
        raise e # Předáme dál, aby to zachytil worker
    except Exception as e:
        print(f"! Chyba zápisu {output_filename}: {e}")
        raise e # Předáme dál

# !!!!! UPRAVENO: Přidán argument 'message_queue' !!!!!
def handle_processing_error(e, input_filepath, reader, message_queue=None):
    """Zpracuje chyby a vloží zprávu do fronty."""
    input_filename = os.path.basename(input_filepath)
    error_type = type(e).__name__; error_msg = str(e); line_num_msg = ""
    status_update = f"! Chyba: '{input_filename}'."
    msg_box_title = "Chyba zpracování"
    msg_box_type = "error" # Může být 'error', 'warning', 'info'

    if isinstance(e, FileNotFoundError):
        msg_box_title = "Chyba souboru"
        msg_box_message = f"Soubor nenalezen:\n{input_filepath}"
        status_update = f"! Chyba: '{input_filename}' nenalezen."
    elif isinstance(e, LookupError):
        msg_box_title = "Chyba kódování"
        msg_box_message = f"Nepodporovaná znaková sada.\nZkontrolujte '{config.ENCODING_FILE}'."
        status_update = "! Chyba: Neplatné kódování."
    elif isinstance(e, PermissionError):
        msg_box_title = "Chyba oprávnění"
        msg_box_message = "Nedostatečná oprávnění pro čtení/zápis."
        status_update = "! Chyba: Oprávnění."
    elif isinstance(e, csv.Error):
        line_num_msg = f" řádek {reader.line_num}" if reader and hasattr(reader, 'line_num') else ""
        msg_box_title = "Chyba CSV"
        msg_box_message = f"Chyba CSV '{input_filename}'{line_num_msg}:\n{error_msg}"
        status_update = f"! Chyba CSV: '{input_filename}'."
    else: # Neočekávaná chyba
        current_line = reader.line_num if reader and hasattr(reader, 'line_num') else 'N/A'
        line_num_msg = f" řádek ~{current_line}"
        msg_box_title = "Neočekávaná chyba"
        msg_box_message = f"Chyba '{error_type}'{line_num_msg} v '{input_filename}':\n{error_msg}"
        status_update = f"! Chyba: '{input_filename}'."
        import traceback
        print(f"! Detail chyby '{input_filename}': {error_type} - {error_msg}")
        traceback.print_exc()

    # Vložit zprávy do fronty, pokud je k dispozici
    if message_queue:
        message_queue.put(('status', status_update))
        message_queue.put(('messagebox', msg_box_type, msg_box_title, msg_box_message))