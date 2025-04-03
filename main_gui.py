# -*- coding: utf-8 -*-

"""Hlavní GUI aplikace pro zpracování CSV a editaci specifikací."""

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import os
import sys
import shutil

# Importy z našich modulů
import config
from utils import read_encoding
from csv_processors import (process_texty_csv, process_symboly_csv,
                            process_cary_csv, merge_and_deduplicate)
from spec_editor_gui import SpecEditorApp

# --- Globální proměnné pro cesty a GUI prvky ---
texty_filepath = None
symboly_filepath = None
cary_filepath = None
main_root = None
status_label = None
texty_label = None
symboly_label = None
cary_label = None

# --- Funkce pro tlačítka GUI ---

def select_file(file_type_var, label_widget, suffix_filter):
    """Otevře dialog pro výběr souboru a aktualizuje globální proměnnou a label."""
    # Global je zde NUTNÝ pro zápis do filepaths
    global texty_filepath, symboly_filepath, cary_filepath
    # Global pro status_label a ostatní labely není nutný pro .config(),
    # ale ponecháme pro explicitnost
    global status_label, texty_label, symboly_label, cary_label

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


def run_filter_and_merge():
    """Spustí Fázi 1 (filtrování) a Fázi 2 (sloučení)."""
    global status_label # Potřebujeme pro .config()
    # !!!!! ODEBRÁNO global pro filepaths !!!!!
    # global texty_filepath, symboly_filepath, cary_filepath

    # Čteme globální proměnné přímo
    if not texty_filepath or not symboly_filepath or not cary_filepath:
        messagebox.showerror("Chybí", "Vyberte prosím všechny 3 vstupní soubory.")
        return

    file_encoding = read_encoding();
    if file_encoding is None:
        if status_label: status_label.config(text="Chyba kódování.")
        return # Opraveno unreachable

    if status_label: status_label.config(text="Fáze 1: Zpracování vstupů...")
    dir1=os.path.dirname(texty_filepath); fn1,e1=os.path.splitext(os.path.basename(texty_filepath)); texty_upr_path=os.path.join(dir1, f"{fn1}{config.OUTPUT_SUFFIX}{e1}")
    dir2=os.path.dirname(symboly_filepath); fn2,e2=os.path.splitext(os.path.basename(symboly_filepath)); symboly_upr_path=os.path.join(dir2, f"{fn2}{config.OUTPUT_SUFFIX}{e2}")
    dir3=os.path.dirname(cary_filepath); fn3,e3=os.path.splitext(os.path.basename(cary_filepath)); cary_upr_path=os.path.join(dir3, f"{fn3}{config.OUTPUT_SUFFIX}{e3}")

    # Předáme status_label do zpracovávacích funkcí
    if not process_texty_csv(texty_filepath, file_encoding, status_label): return
    if not process_symboly_csv(symboly_filepath, file_encoding, status_label): return
    if not process_cary_csv(cary_filepath, file_encoding, status_label): return

    print("--- Fáze 1 (Filtrování) dokončena ---")
    if status_label: status_label.config(text="Fáze 1 OK. Zahajuji Fázi 2: Slučování...")
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    priprava_csv_path = os.path.join(script_dir, config.FINAL_OUTPUT_FILENAME)
    if not os.path.exists(texty_upr_path) or not os.path.exists(symboly_upr_path) or not os.path.exists(cary_upr_path):
        messagebox.showerror("Chyba", "Některý z '_upr.csv' souborů nebyl nalezen pro sloučení.")
        return # Opraveno unreachable

    # Předáme status_label i do merge funkce
    merge_success = merge_and_deduplicate(cary_upr_path, symboly_upr_path, texty_upr_path, priprava_csv_path, file_encoding, status_label)

    if merge_success:
        messagebox.showinfo("Dokončeno", f"Filtrování a sloučení dokončeno.\nVýsledek: {priprava_csv_path}")
         # Status se nastavil v merge_and_deduplicate
    else:
        messagebox.showerror("Selhání", "Fáze 2 (slučování) selhala.")
        if status_label: status_label.config(text="Chyba při slučování dat.")
         # Opraveno unreachable code - zde nic nemá být po return/if


def run_editor():
    """Spustí editor specifikací pro priprava.csv."""
    global main_root, status_label # Potřebujeme oba
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    priprava_csv_path = os.path.join(script_dir, config.FINAL_OUTPUT_FILENAME)
    edited_output_path = os.path.join(script_dir, config.EDITED_OUTPUT_FILENAME)
    if not os.path.exists(priprava_csv_path):
        messagebox.showerror("Chyba", f"Soubor '{config.FINAL_OUTPUT_FILENAME}' nenalezen.\nNejprve spusťte 'Zpracovat a Sloučit'.")
        if status_label: status_label.config(text=f"Soubor {config.FINAL_OUTPUT_FILENAME} nenalezen.")
        return # Opraveno unreachable

    file_encoding = read_encoding();
    if file_encoding is None:
        if status_label: status_label.config(text="Chyba kódování pro editor.")
        return # Opraveno unreachable

    if status_label: status_label.config(text="Spouštím editor specifikací...")
    SpecEditorApp(main_root, priprava_csv_path, edited_output_path, file_encoding, status_label)


def run_overwrite_original():
    """Přepíše priprava.csv souborem priprava_upr.csv."""
    global status_label # main_root nepotřebujeme
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    priprava_csv_path = os.path.join(script_dir, config.FINAL_OUTPUT_FILENAME)
    edited_output_path = os.path.join(script_dir, config.EDITED_OUTPUT_FILENAME)
    if not os.path.exists(edited_output_path):
        messagebox.showerror("Chyba", f"Soubor '{config.EDITED_OUTPUT_FILENAME}' nenalezen.\nSpusťte editor a uložte změny.")
        if status_label: status_label.config(text=f"Soubor {config.EDITED_OUTPUT_FILENAME} nenalezen.")
        return # Opraveno unreachable

    confirm = messagebox.askyesno("Potvrdit přepsání", f"Opravdu přepsat '{config.FINAL_OUTPUT_FILENAME}'\nobsahem souboru '{config.EDITED_OUTPUT_FILENAME}'?\n\nTato akce je nevratná!", icon='warning')
    if not confirm:
        if status_label: status_label.config(text="Přepsání originálu zrušeno.")
        return # Opraveno unreachable
    try:
        print(f"+ Přesouvám '{edited_output_path}' -> '{priprava_csv_path}'")
        shutil.move(edited_output_path, priprava_csv_path)
        messagebox.showinfo("Hotovo", f"Soubor '{config.FINAL_OUTPUT_FILENAME}' byl úspěšně přepsán.")
        if status_label: status_label.config(text=f"Soubor {config.FINAL_OUTPUT_FILENAME} přepsán.")
        print(f"+ Soubor '{config.FINAL_OUTPUT_FILENAME}' přepsán.")
    except Exception as e:
        print(f"! Chyba při přepisování: {e}")
        messagebox.showerror("Chyba", f"Nepodařilo se přepsat '{config.FINAL_OUTPUT_FILENAME}':\n{e}")
        if status_label: status_label.config(text="Chyba při přepisování.")
        # Opraveno unreachable code - zde nic nemá být po return/if


# --- Hlavní spuštění GUI ---
if __name__ == "__main__":
    main_root = tk.Tk()
    main_root.title("CSV Nástroje v1.4 - Modularizováno") # Verze

    style = ttk.Style()
    try: style.theme_use('vista')
    except tk.TclError: print("Poznámka: Téma 'vista' není dostupné.")

    file_frame = ttk.Frame(main_root, padding="10", borderwidth=2, relief=tk.GROOVE); file_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(file_frame, text="1. Výběr vstupních CSV souborů:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0,5), sticky=tk.W)
    texty_label = ttk.Label(file_frame, text="(nevybrán)", anchor=tk.W, width=45); texty_label.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
    symboly_label = ttk.Label(file_frame, text="(nevybrán)", anchor=tk.W, width=45); symboly_label.grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)
    cary_label = ttk.Label(file_frame, text="(nevybrán)", anchor=tk.W, width=45); cary_label.grid(row=3, column=1, padx=5, pady=2, sticky=tk.W)
    select_texty_button = ttk.Button(file_frame, text=f"Vybrat {config.TEXTY_SUFFIX}", width=20, command=lambda: select_file('texty', texty_label, config.TEXTY_SUFFIX)); select_texty_button.grid(row=1, column=0, padx=5, pady=2, sticky=tk.W+tk.E)
    select_symboly_button = ttk.Button(file_frame, text=f"Vybrat {config.SYMBOLY_SUFFIX}", width=20, command=lambda: select_file('symboly', symboly_label, config.SYMBOLY_SUFFIX)); select_symboly_button.grid(row=2, column=0, padx=5, pady=2, sticky=tk.W+tk.E)
    select_cary_button = ttk.Button(file_frame, text=f"Vybrat {config.CARY_SUFFIX}", width=20, command=lambda: select_file('cary', cary_label, config.CARY_SUFFIX)); select_cary_button.grid(row=3, column=0, padx=5, pady=2, sticky=tk.W+tk.E)

    action_frame = ttk.Frame(main_root, padding="10", borderwidth=2, relief=tk.GROOVE); action_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(action_frame, text="2. Zpracování a Editace:", font=('Segoe UI', 9, 'bold')).pack(anchor=tk.W, pady=(0,5))
    process_button = ttk.Button(action_frame, text=f"Zpracovat vstupy a Sloučit do '{config.FINAL_OUTPUT_FILENAME}'", command=run_filter_and_merge); process_button.pack(pady=5, fill=tk.X)
    edit_button = ttk.Button(action_frame, text=f"Editovat Specifikace v '{config.FINAL_OUTPUT_FILENAME}'", command=run_editor); edit_button.pack(pady=5, fill=tk.X)
    overwrite_button = ttk.Button(action_frame, text=f"Aktualizovat '{config.FINAL_OUTPUT_FILENAME}' upraveným souborem", command=run_overwrite_original); overwrite_button.pack(pady=5, fill=tk.X)

    status_label = ttk.Label(main_root, text="Připraven. Vyberte vstupní soubory.", relief=tk.SUNKEN, anchor=tk.W, padding=(5,2)); status_label.pack(fill=tk.X, side=tk.BOTTOM, ipady=2)

    main_root.mainloop()