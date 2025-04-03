# -*- coding: utf-8 -*-

"""Hlavní GUI aplikace pro zpracování CSV a editaci specifikací."""

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import os
import sys
import shutil
import threading # !!!!! Přidáno !!!!!
import queue     # !!!!! Přidáno !!!!!

# Importy z našich modulů
import config
from utils import read_encoding, check_overwrite, handle_processing_error # Přidáno handle_processing_error
from csv_processors import (process_texty_csv, process_symboly_csv,
                            process_cary_csv, merge_and_deduplicate) # Odebráno _worker...
from spec_editor_gui import SpecEditorApp

# --- Globální proměnné ---
texty_filepath = None; symboly_filepath = None; cary_filepath = None
main_root = None; status_label = None
texty_label = None; symboly_label = None; cary_label = None
process_button = None; edit_button = None; overwrite_button = None # Přidány reference na tlačítka
processing_queue = None # Fronta pro komunikaci s workerem
is_processing = False # Flag pro indikaci běžícího procesu

# --- Funkce pro GUI ---

def select_file(file_type_var, label_widget, suffix_filter):
    """Otevře dialog pro výběr souboru."""
    global texty_filepath, symboly_filepath, cary_filepath, status_label
    try: initial_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception: initial_dir = os.getcwd()
    filetypes = ((f"*{suffix_filter}", f"*{suffix_filter}"), ("CSV", "*.csv"), ("Všechny", "*.*"))
    filepath = filedialog.askopenfilename( initialdir=initial_dir, title=f"Vyber {suffix_filter}", filetypes=filetypes)
    if filepath:
        if not filepath.lower().endswith(suffix_filter.lower()): messagebox.showwarning("Nesprávný typ", f"Soubor nekončí na '{suffix_filter}'."); return
        filename = os.path.basename(filepath)
        if file_type_var == 'texty': texty_filepath = filepath; label_widget.config(text=f"{filename}")
        elif file_type_var == 'symboly': symboly_filepath = filepath; label_widget.config(text=f"{filename}")
        elif file_type_var == 'cary': cary_filepath = filepath; label_widget.config(text=f"{filename}")
        if status_label: status_label.config(text=f"Soubor '{filename}' vybrán.")
    else:
        if status_label: status_label.config(text="Výběr souboru zrušen.")

def _disable_buttons():
    """Zakáže akční tlačítka."""
    global process_button, edit_button, overwrite_button
    if process_button: process_button.config(state=tk.DISABLED)
    if edit_button: edit_button.config(state=tk.DISABLED)
    if overwrite_button: overwrite_button.config(state=tk.DISABLED)

def _enable_buttons():
    """Povolí akční tlačítka."""
    global process_button, edit_button, overwrite_button
    if process_button: process_button.config(state=tk.NORMAL)
    if edit_button: edit_button.config(state=tk.NORMAL)
    if overwrite_button: overwrite_button.config(state=tk.NORMAL)

def _check_queue():
    """Periodicky kontroluje frontu zpráv z worker vlákna."""
    global processing_queue, status_label, main_root, is_processing
    try:
        while True: # Zpracovat všechny zprávy ve frontě
            message = processing_queue.get_nowait()
            msg_type = message[0]

            if msg_type == 'status':
                if status_label: status_label.config(text=message[1])
            elif msg_type == 'messagebox':
                msg_level, title, msg = message[1], message[2], message[3]
                if msg_level == 'info': messagebox.showinfo(title, msg)
                elif msg_level == 'warning': messagebox.showwarning(title, msg)
                elif msg_level == 'error': messagebox.showerror(title, msg)
            elif msg_type == 'finished':
                success, final_message = message[1], message[2]
                print("--- Worker vlákno dokončeno ---")
                if success:
                    messagebox.showinfo("Dokončeno", final_message)
                else:
                    # Chybová zpráva by měla být zobrazena už dříve
                    if status_label: status_label.config(text=final_message if final_message else "Zpracování selhalo.")
                is_processing = False
                _enable_buttons()
                return # Ukončit periodickou kontrolu
            else:
                print(f"! Neznámý typ zprávy z fronty: {message}")

    except queue.Empty:
        pass # Žádná zpráva, pokračujeme v čekání

    # Pokud proces stále běží, naplánovat další kontrolu
    if is_processing:
        main_root.after(150, _check_queue) # Zkontrolovat znovu za 150ms

# TOTO PATŘÍ DO main_gui.py (např. před run_filter_and_merge)

def _worker_filter_and_merge(paths, encoding, message_queue):
    """Funkce spouštěná v samostatném vlákně pro filtrování a slučování."""
    texty_path, symboly_path, cary_path, texty_upr, symboly_upr, cary_upr, priprava_csv = paths
    current_input_path = "" # Pro handle_processing_error
    try:
        # Fáze 1: Filtrování
        message_queue.put(('status', "Fáze 1: Filtruji vstupní soubory..."))

        current_input_path = texty_path
        # Voláme funkce importované z csv_processors
        success1, texty_upr_path_ret = process_texty_csv(texty_path, encoding, texty_upr)
        if not success1: raise Exception(f"Selhalo zpracování {os.path.basename(texty_path)}")

        current_input_path = symboly_path
        success2, symboly_upr_path_ret = process_symboly_csv(symboly_path, encoding, symboly_upr)
        if not success2: raise Exception(f"Selhalo zpracování {os.path.basename(symboly_path)}")

        current_input_path = cary_path
        success3, cary_upr_path_ret = process_cary_csv(cary_path, encoding, cary_upr)
        if not success3: raise Exception(f"Selhalo zpracování {os.path.basename(cary_path)}")

        message_queue.put(('status', "Fáze 1 OK. Fáze 2: Slučování..."))

        # Fáze 2: Sloučení
        # Voláme funkci importovanou z csv_processors
        merge_success = merge_and_deduplicate(
            cary_upr_path_ret, symboly_upr_path_ret, texty_upr_path_ret,
            priprava_csv, encoding, message_queue
        )

        if merge_success:
            message_queue.put(('finished', True, f"Filtrování a sloučení dokončeno.\nVýsledek: {priprava_csv}"))
        else:
            message_queue.put(('finished', False, "Fáze 2 (slučování) selhala."))

    except Exception as e:
        print(f"! Neočekávaná chyba ve worker vlákně při zpracování {current_input_path}: {e}")
        import traceback
        traceback.print_exc()
        # Voláme funkci importovanou z utils
        handle_processing_error(e, current_input_path if current_input_path else "Worker Thread", None, message_queue)
        message_queue.put(('finished', False, "Zpracování selhalo kvůli neočekávané chybě."))
        
def run_filter_and_merge():
    """Spustí filtrování a slučování v samostatném vlákně."""
    global status_label, texty_filepath, symboly_filepath, cary_filepath
    global processing_queue, main_root, is_processing

    if is_processing:
        messagebox.showwarning("Zpracování běží", "Počkejte prosím na dokončení aktuálního procesu.")
        return

    if not texty_filepath or not symboly_filepath or not cary_filepath:
        messagebox.showerror("Chybí", "Vyberte prosím všechny 3 vstupní soubory.")
        return

    file_encoding = read_encoding();
    if file_encoding is None:
        if status_label: status_label.config(text="Chyba kódování.")
        return

    # Cesty k výstupním souborům
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    dir1=os.path.dirname(texty_filepath); fn1,e1=os.path.splitext(os.path.basename(texty_filepath)); texty_upr_path=os.path.join(dir1, f"{fn1}{config.OUTPUT_SUFFIX}{e1}")
    dir2=os.path.dirname(symboly_filepath); fn2,e2=os.path.splitext(os.path.basename(symboly_filepath)); symboly_upr_path=os.path.join(dir2, f"{fn2}{config.OUTPUT_SUFFIX}{e2}")
    dir3=os.path.dirname(cary_filepath); fn3,e3=os.path.splitext(os.path.basename(cary_filepath)); cary_upr_path=os.path.join(dir3, f"{fn3}{config.OUTPUT_SUFFIX}{e3}")
    priprava_csv_path = os.path.join(script_dir, config.FINAL_OUTPUT_FILENAME)

    # !!!!! Kontrola přepsání PŘED spuštěním vlákna !!!!!
    output_files_to_check = [texty_upr_path, symboly_upr_path, cary_upr_path, priprava_csv_path]
    for f_path in output_files_to_check:
        if os.path.exists(f_path):
            if not check_overwrite(f_path): # check_overwrite zobrazí dotaz
                if status_label: status_label.config(text="Zpracování zrušeno uživatelem.")
                return # Ukončit, pokud uživatel nechce přepsat

    # Připravit argumenty pro worker
    paths_for_worker = (
        texty_filepath, symboly_filepath, cary_filepath,
        texty_upr_path, symboly_upr_path, cary_upr_path,
        priprava_csv_path
    )

    # Spustit zpracování ve vlákně
    processing_queue = queue.Queue()
    is_processing = True
    _disable_buttons()
    if status_label: status_label.config(text="Zpracovávám ve vlákně...")

    worker_thread = threading.Thread(
        target=_worker_filter_and_merge,
        args=(paths_for_worker, file_encoding, processing_queue),
        daemon=True # Vlákno se ukončí, pokud se ukončí hlavní program
    )
    worker_thread.start()

    # Spustit kontrolu fronty
    main_root.after(100, _check_queue)


def run_editor():
    """Spustí editor specifikací (běží v hlavním vlákně, Toplevel)."""
    global main_root, status_label, is_processing
    if is_processing: messagebox.showwarning("Zpracování běží", "Počkejte na dokončení filtrování/slučování."); return

    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    priprava_csv_path = os.path.join(script_dir, config.FINAL_OUTPUT_FILENAME)
    edited_output_path = os.path.join(script_dir, config.EDITED_OUTPUT_FILENAME)
    if not os.path.exists(priprava_csv_path): messagebox.showerror("Chyba", f"Soubor '{config.FINAL_OUTPUT_FILENAME}' nenalezen."); status_label.config(text=f"{config.FINAL_OUTPUT_FILENAME} nenalezen."); return
    file_encoding = read_encoding();
    if file_encoding is None:
        if status_label: status_label.config(text="Chyba kódování pro editor."); return
    if status_label: status_label.config(text="Spouštím editor...")
    SpecEditorApp(main_root, priprava_csv_path, edited_output_path, file_encoding, status_label)


def run_overwrite_original():
    """Přepíše priprava.csv souborem priprava_upr.csv (běží v hlavním vlákně)."""
    global status_label, is_processing
    if is_processing: messagebox.showwarning("Zpracování běží", "Počkejte na dokončení."); return

    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    priprava_csv_path = os.path.join(script_dir, config.FINAL_OUTPUT_FILENAME)
    edited_output_path = os.path.join(script_dir, config.EDITED_OUTPUT_FILENAME)
    if not os.path.exists(edited_output_path): messagebox.showerror("Chyba", f"'{config.EDITED_OUTPUT_FILENAME}' nenalezen."); status_label.config(text=f"{config.EDITED_OUTPUT_FILENAME} nenalezen."); return
    confirm = messagebox.askyesno("Potvrdit přepsání", f"Opravdu přepsat '{config.FINAL_OUTPUT_FILENAME}'?", icon='warning')
    if not confirm:
        if status_label: status_label.config(text="Přepsání originálu zrušeno."); return
    try:
        print(f"+ Přesouvám '{edited_output_path}' -> '{priprava_csv_path}'")
        shutil.move(edited_output_path, priprava_csv_path)
        messagebox.showinfo("Hotovo", f"'{config.FINAL_OUTPUT_FILENAME}' přepsán.")
        if status_label: status_label.config(text=f"{config.FINAL_OUTPUT_FILENAME} přepsán.")
        print(f"+ '{config.FINAL_OUTPUT_FILENAME}' přepsán.")
    except Exception as e: print(f"! Chyba při přepisování: {e}"); messagebox.showerror("Chyba", f"Nelze přepsat '{config.FINAL_OUTPUT_FILENAME}':\n{e}"); status_label.config(text="Chyba při přepisování.")


# --- Hlavní spuštění GUI ---
if __name__ == "__main__":
    main_root = tk.Tk()
    main_root.title("CSV Nástroje v1.5 - Multithreaded") # Verze

    style = ttk.Style()
    try: style.theme_use('vista')
    except tk.TclError: print("Poznámka: Téma 'vista' není dostupné.")

    file_frame = ttk.Frame(main_root, padding="10", borderwidth=2, relief=tk.GROOVE); file_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(file_frame, text="1. Výběr vstupních CSV:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0,5), sticky=tk.W)
    texty_label = ttk.Label(file_frame, text="(nevybrán)", anchor=tk.W, width=45); texty_label.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
    symboly_label = ttk.Label(file_frame, text="(nevybrán)", anchor=tk.W, width=45); symboly_label.grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)
    cary_label = ttk.Label(file_frame, text="(nevybrán)", anchor=tk.W, width=45); cary_label.grid(row=3, column=1, padx=5, pady=2, sticky=tk.W)
    select_texty_button = ttk.Button(file_frame, text=f"Vybrat {config.TEXTY_SUFFIX}", width=20, command=lambda: select_file('texty', texty_label, config.TEXTY_SUFFIX)); select_texty_button.grid(row=1, column=0, padx=5, pady=2, sticky=tk.W+tk.E)
    select_symboly_button = ttk.Button(file_frame, text=f"Vybrat {config.SYMBOLY_SUFFIX}", width=20, command=lambda: select_file('symboly', symboly_label, config.SYMBOLY_SUFFIX)); select_symboly_button.grid(row=2, column=0, padx=5, pady=2, sticky=tk.W+tk.E)
    select_cary_button = ttk.Button(file_frame, text=f"Vybrat {config.CARY_SUFFIX}", width=20, command=lambda: select_file('cary', cary_label, config.CARY_SUFFIX)); select_cary_button.grid(row=3, column=0, padx=5, pady=2, sticky=tk.W+tk.E)

    action_frame = ttk.Frame(main_root, padding="10", borderwidth=2, relief=tk.GROOVE); action_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(action_frame, text="2. Akce:", font=('Segoe UI', 9, 'bold')).pack(anchor=tk.W, pady=(0,5))
    process_button = ttk.Button(action_frame, text=f"Zpracovat a Sloučit do '{config.FINAL_OUTPUT_FILENAME}'", command=run_filter_and_merge); process_button.pack(pady=5, fill=tk.X)
    edit_button = ttk.Button(action_frame, text=f"Editovat Specifikace ('{config.FINAL_OUTPUT_FILENAME}')", command=run_editor); edit_button.pack(pady=5, fill=tk.X)
    overwrite_button = ttk.Button(action_frame, text=f"Aktualizovat '{config.FINAL_OUTPUT_FILENAME}' upraveným", command=run_overwrite_original); overwrite_button.pack(pady=5, fill=tk.X)

    status_label = ttk.Label(main_root, text="Připraven.", relief=tk.SUNKEN, anchor=tk.W, padding=(5,2)); status_label.pack(fill=tk.X, side=tk.BOTTOM, ipady=2)

    main_root.mainloop()