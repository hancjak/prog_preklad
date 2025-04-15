# -*- coding: utf-8 -*-

"""Třída SpecEditorApp pro GUI editor specifikací."""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, simpledialog # simpledialog už nebudeme potřebovat
import csv
import os
import re
from collections import Counter, OrderedDict, defaultdict

# Importy z našich modulů
import config
from utils import parse_connection # Přidáno parse_connection

class SpecEditorApp:
    """GUI Toplevel okno pro editaci specifikací."""
    def __init__(self, parent, input_file, output_file, encoding, status_label_widget=None):
        self.parent = parent
        self.input_file = input_file
        self.output_file = output_file
        self.encoding = encoding
        self.status_label_widget = status_label_widget # Reference na status bar hlavního okna
        self.all_data = []
        self.items_to_edit_ids = set()
        self.group_keys = OrderedDict()
        self.component_specs = defaultdict(list)
        self.suggested_specs = {}
        self.presets = [] # !!!!! PŘIDÁNO: Seznam pro presety !!!!!
        self.active_editor_widget = None # !!!!! PŘIDÁNO: Reference na aktivní inline editor !!!!!

        self.editor_window = tk.Toplevel(parent)
        self.editor_window.title(f"Editor Specifikací - {os.path.basename(input_file)}")
        self.editor_window.geometry("900x600") # Možná bude potřeba větší šířka
        self.editor_window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.show_all_var = tk.BooleanVar(value=False)

        if not self.load_presets(): # !!!!! PŘIDÁNO: Načtení presetů !!!!!
            # Chyba byla zobrazena v load_presets
            self.on_close()
            return

        if not self.load_data():
            self.on_close()
            return

        self.create_widgets()
        self.populate_treeview()

        self.editor_window.transient(parent)
        self.editor_window.grab_set()
        self.parent.wait_window(self.editor_window)

    def update_main_status(self, text):
        """Aktualizuje status label v hlavním okně (pokud existuje)."""
        if self.status_label_widget:
            try:
                self.status_label_widget.config(text=text)
            except Exception:
                print("! Chyba: Nelze aktualizovat hlavní status label.")

    def on_close(self):
        """Voláno při zavření okna."""
         # !!!!! PŘIDÁNO: Zničení aktivního editoru, pokud existuje !!!!!
        if self.active_editor_widget:
            self.active_editor_widget.destroy()
            self.active_editor_widget = None
        print("- Editor zavřen.")
        self.update_main_status("Editor zavřen.")
        self.editor_window.grab_release()
        self.editor_window.destroy()
    # !!!!! PŘIDÁNO: Funkce pro načtení presetů !!!!!
    def load_presets(self):
        """Načte předdefinované texty ze souboru."""
        # Předpokládáme, že 'files_dir' je definován v main_gui.py a je dostupný
        # nebo můžeme cestu odvodit z input_file
        base_dir = os.path.dirname(self.input_file) # Předpokládáme, že input_file je v 'files'
        presets_path = os.path.join(base_dir, config.EDITOR_PRESETS_FILE)
        print(f"+ Hledám presety v: {presets_path}")
        try:
            with open(presets_path, 'r', encoding='utf-8') as f: # Presety čteme vždy jako utf-8
                self.presets = [line.strip() for line in f if line.strip()]
            print(f"+ Načteno {len(self.presets)} presetů.")
            return True
        except FileNotFoundError:
            print(f"! Varování: Soubor presetů '{config.EDITOR_PRESETS_FILE}' nenalezen v '{base_dir}'. Editor bude fungovat bez presetů.")
            self.presets = [] # Zajistíme, že je to prázdný list
            return True # Nepovažujeme za fatální chybu
        except Exception as e:
            print(f"! Chyba při čtení presetů '{config.EDITOR_PRESETS_FILE}': {e}")
            messagebox.showerror("Chyba presetů", f"Chyba při čtení souboru presetů:\n{e}", parent=self.editor_window)
            return False # Fatální chyba

    def load_data(self):
        """Načte data z priprava.csv, naparsuje je a analyzuje specifikace."""
        self.update_main_status(f"Načítám a analyzuji {os.path.basename(self.input_file)}...")
        print(f"+ Načítám editor: {self.input_file}")
        component_names_a = set()
        component_names_b = set()
        self.component_specs.clear()
        try:
            with open(self.input_file, 'r', encoding=self.encoding, newline='') as f:
                reader = csv.reader(f, delimiter=config.CSV_DELIMITER)
                header = next(reader)
                if header != ["Spojeni", "Specifikace"]:
                    messagebox.showerror("Chybný formát", f"'{os.path.basename(self.input_file)}' nemá hlavičku 'Spojeni;Specifikace'.", parent=self.editor_window)
                    return False
                
                for i, row in enumerate(reader):
                    if len(row) != 2:
                        print(f"! Varování editor: Přeskakuji řádek {i+2}: {row}")
                        continue
                    spojeni, spec_raw = row
                    spec = spec_raw.strip()
                    parsed_data = parse_connection(spojeni) # Parsování hned zde
                    item_id = f"item_{i}"
                    original_line_number = i + 2

                    # !!! ZMĚNA: Ukládáme i originální spojení a specifikaci pro případnou editaci !!!
                    self.all_data.append({
                        "id": item_id,
                        "spojeni": spojeni.strip(), # Ukládáme i původní (očištěné) spojení
                        "spec": spec,
                        "parsed": parsed_data,
                        "line_num": original_line_number
                    })
                    # Zbytek logiky pro items_to_edit_ids a suggestions zůstává stejný...
                    current_spec_lower = spec.lower()
                    is_default_spec = current_spec_lower == config.DEFAULT_SPECIFICATION.lower() or not spec
                    if is_default_spec:
                        self.items_to_edit_ids.add(item_id)
                        
                    if parsed_data:
                        comp_a = parsed_data.get('a')
                        comp_b = parsed_data.get('b')
                        comp_a_name = comp_a.get('name') if comp_a else None
                        comp_b_name = comp_b.get('name') if comp_b else None
                        if comp_a_name: component_names_a.add(comp_a_name)
                        if comp_b_name: component_names_b.add(comp_b_name)
                        if not is_default_spec:
                            if comp_a_name: self.component_specs[comp_a_name].append(spec)
                            if comp_b_name: self.component_specs[comp_b_name].append(spec)

            # --- Logika pro suggested_specs a group_keys zůstává stejná ---
            self.suggested_specs.clear()
            print("+ Analyzuji specifikace...")
            for comp_name, spec_list in self.component_specs.items():
                if spec_list:
                    spec_counts = Counter(spec_list)
                    most_common_spec, count = spec_counts.most_common(1)[0]
                    if count >= 1:
                        self.suggested_specs[comp_name] = most_common_spec

            self.group_keys.clear()
            self.group_keys["Všechny 'neni spec'"] = lambda item: item['id'] in self.items_to_edit_ids
            for name in sorted(list(component_names_a)):
                suggestion = self.suggested_specs.get(name)
                key = f"Název A: {name}"
                if suggestion: key += f" (návrh: '{suggestion}')"
                self.group_keys[key] = lambda item, n=name: item['id'] in self.items_to_edit_ids and item['parsed'] and item['parsed']['a']['name'] == n
            for name in sorted(list(component_names_b)):
                suggestion = self.suggested_specs.get(name)
                key_base = f"Název B: {name}"
                key = key_base
                if suggestion: key += f" (návrh: '{suggestion}')"
                # Ošetření duplicitních klíčů
                original_key = key
                counter = 2
                while key in self.group_keys:
                     if " (návrh: '" in original_key:
                         key = key_base + f" (B {counter})"
                     else:
                         key = original_key + f" (B {counter})"
                     counter += 1
                     if counter > 10: break # Pojistka

                self.group_keys[key] = lambda item, n=name: item['id'] in self.items_to_edit_ids and item['parsed'] and item['parsed']['b']['name'] == n

            print(f"+ Editor data: {len(self.all_data)} řádků, {len(self.items_to_edit_ids)} k editaci. Návrhů: {len(self.suggested_specs)}.")
            self.update_main_status(f"Editor načten: {len(self.items_to_edit_ids)} položek k editaci.")
            if not self.items_to_edit_ids and not self.show_all_var.get(): # Pokud není nic k editaci A nezobrazujeme vše
                 if not any(True for _ in self.all_data if self.group_keys["Všechny 'neni spec'"](_)): # Ověření, jestli opravdu není nic k editaci
                    messagebox.showinfo("Není co editovat", "V souboru nejsou žádné řádky s 'neni spec'.\n(Zkuste zaškrtnout 'Zobrazit vše' pro zobrazení všech řádků)", parent=self.editor_window)
                    # Vrátíme True, aby se editor zobrazil, i když je prázdný (kvůli "Zobrazit vše")
                    return True # Změna - nevracíme False, necháme editor otevřít
            return True
        except FileNotFoundError:
            messagebox.showerror("Chyba souboru", f"Vstup '{self.input_file}' nenalezen.", parent=self.editor_window)
            return False
        except Exception as e:
            messagebox.showerror("Chyba načítání", f"Chyba načítání editoru:\n{e}", parent=self.editor_window)
            print(f"! Chyba load_data: {e}")
            import traceback
            traceback.print_exc()
            return False
    def create_widgets(self):
        """Vytvoří prvky GUI v editor okně."""
        top_frame = ttk.Frame(self.editor_window, padding="10")
        top_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(top_frame, text="Zobrazit skupinu:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.group_combo = ttk.Combobox(top_frame, values=list(self.group_keys.keys()), state="readonly", width=45)
        self.group_combo.grid(row=0, column=1, padx=(0, 10), sticky=tk.W+tk.E)
        if self.group_keys:
            self.group_combo.current(0)
            self.group_combo.bind("<<ComboboxSelected>>", self.on_filter_change) # <<< ZMĚNA: Volá on_filter_change
    # <<< PŘIDÁNO: Checkbox "Zobrazit vše" >>>
        self.show_all_check = ttk.Checkbutton(
            top_frame,
            text="Zobrazit vše",
            variable=self.show_all_var,
            command=self.on_filter_change # <<< Volá stejnou funkci při změně
        )
        self.show_all_check.grid(row=0, column=2, padx=(5, 20), sticky=tk.W)

        top_frame.columnconfigure(1, weight=1) # Combobox se roztáhne
        top_frame.columnconfigure(4, weight=1) # Entry se roztáhne

        ttk.Label(top_frame, text="Nová specifikace:").grid(row=0, column=3, padx=(10, 5), sticky=tk.W)
        self.spec_entry = ttk.Entry(top_frame, width=30)
        self.spec_entry.grid(row=0, column=4, padx=(0, 10), sticky=tk.W+tk.E)
        self.apply_button = ttk.Button(top_frame, text="Přiřadit skupině", command=self.apply_to_group)
        self.apply_button.grid(row=0, column=5, padx=(0, 5))

        tree_frame = ttk.Frame(self.editor_window, padding="10")
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Sloupce pro Treeview (identifikátory)
        self.columns = ("line", "spojeni", "spec") # ID sloupců

        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show="headings", height=15)

        # Nastavení hlaviček a šířek
        self.tree.heading("line", text="#")
        self.tree.column("line", width=50, anchor=tk.CENTER, stretch=tk.NO)
        self.tree.heading("spojeni", text="Spojení")
        self.tree.column("spojeni", width=400, anchor=tk.W) # Potřebuje více místa
        self.tree.heading("spec", text="Specifikace")
        self.tree.column("spec", width=300, anchor=tk.W) # Potřebuje více místa

        self.tree.tag_configure('oddrow', background='#f0f0f0')
        self.tree.tag_configure('evenrow', background='white')

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        # Odebráno: self.tree.bind("<Double-1>", self.edit_selected_item_popup)

        bottom_frame = ttk.Frame(self.editor_window, padding="10")
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.save_button = ttk.Button(bottom_frame, text="Uložit změny do " + os.path.basename(self.output_file), command=self.save_changes)
        self.save_button.pack(side=tk.RIGHT)
        self.cancel_button = ttk.Button(bottom_frame, text="Zavřít editor", command=self.on_close)
        self.cancel_button.pack(side=tk.RIGHT, padx=10)

    def populate_treeview(self):
        """Naplní Treeview daty podle filtru."""
        # !!!!! PŘIDÁNO: Zničení aktivního editoru před překreslením !!!!!
        if self.active_editor_widget:
            self.active_editor_widget.destroy()
            self.active_editor_widget = None

        for item in self.tree.get_children():
            self.tree.delete(item)

        filter_func = None
        if self.show_all_var.get():
            filter_func = lambda item: True
            print("+ Zobrazuji všechny položky.")
        else:
            filter_key = self.group_combo.get()
            filter_func = self.group_keys.get(filter_key, lambda item: False)
            print(f"+ Filtruji podle skupiny: '{filter_key}'")

        row_counter = 0
        for item_data in self.all_data:
            if filter_func(item_data):
                current_tag = 'oddrow' if row_counter % 2 != 0 else 'evenrow'
                line_num_val = item_data.get('line_num', '')
                # Získání aktuálních hodnot pro 'spojeni' a 'spec' z item_data
                spojeni_val = item_data.get('spojeni', '')
                spec_val = item_data.get('spec', '')
                values_tuple = (line_num_val, spojeni_val, spec_val)

                self.tree.insert("", tk.END, iid=item_data['id'], values=values_tuple, tags=(current_tag,))
                row_counter += 1

        displayed_count = len(self.tree.get_children())
        total_count = len(self.all_data)
        status_text = f"Zobrazeno {displayed_count} z {total_count} položek."
        print(f"+ {status_text}")
        # Možné přidat update_main_status zde, pokud chceme

    def on_filter_change(self, _event=None):
        """Reakce na změnu filtru (Combobox nebo Checkbox)."""
        filter_key = self.group_combo.get()
        self.spec_entry.delete(0, tk.END)
        match = re.search(r"\(návrh: '(.*)'\)", filter_key)
        if match:
            suggested_spec = match.group(1)
            self.spec_entry.insert(0, suggested_spec)
            print(f"+ Návrh: '{suggested_spec}' pro '{filter_key}'")
        # Vždy znovu naplnit Treeview podle aktuálního stavu filtru a checkboxu
        self.populate_treeview()
    # !!!!! NOVÁ METODA pro inline editaci !!!!!
    def on_tree_double_click(self, event):
        """Zpracuje dvojklik v Treeview a spustí inline editaci."""
        # Zničit předchozí editor, pokud existuje
        if self.active_editor_widget:
            self.active_editor_widget.destroy()
            self.active_editor_widget = None

        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return # Kliknuto mimo buňku

        column_id = self.tree.identify_column(event.x) # např. '#1', '#2', atd.
        item_id = self.tree.identify_row(event.y)      # např. 'item_0'

        if not item_id or not column_id: return # Kliknuto mimo data

        try:
            # Získáme index sloupce (0='line', 1='spojeni', 2='spec') z ID sloupce ('#1', '#2', ...)
            # self.columns = ("line", "spojeni", "spec")
            col_index = int(column_id.replace('#', '')) - 1
        except ValueError:
            print(f"! Chyba: Neplatné ID sloupce '{column_id}'")
            return

        # Povolit editaci pouze pro sloupce "Spojeni" (index 1) a "Specifikace" (index 2)
        if col_index not in [1, 2]:
            print(f"- Editace sloupce '{self.columns[col_index]}' není povolena.")
            return

        # Získání rozměrů buňky pro umístění editoru
        bbox = self.tree.bbox(item_id, column=column_id)
        if not bbox: return # Buňka není viditelná?

        x, y, width, height = bbox

        # Získání aktuální hodnoty z Treeview
        values = self.tree.item(item_id, 'values')
        current_value = values[col_index] if len(values) > col_index else ""

        # Vytvoření Comboboxu pro editaci
        # Použijeme Combobox, i když nejsou presety, protože umožňuje i volné psaní
        editor = ttk.Combobox(self.editor_window, values=self.presets)
        editor.place(x=x, y=y, width=width, height=height) # Umístění přesně na buňku
        editor.insert(0, current_value) # Vložení aktuální hodnoty
        editor.select_range(0, tk.END) # Označení textu
        editor.focus_set() # Zaměření na editor

        # Uložení reference na aktivní editor
        self.active_editor_widget = editor

        # Navázání událostí na editor
        # Použití lambda pro předání parametrů (widget, item_id, col_index)
        editor.bind("<Return>", lambda e, w=editor, iid=item_id, idx=col_index: self.save_inline_edit(w, iid, idx))
        editor.bind("<FocusOut>", lambda e, w=editor, iid=item_id, idx=col_index: self.save_inline_edit(w, iid, idx))
        editor.bind("<Escape>", lambda e, w=editor: w.destroy()) # Escape pouze zničí widget

    # !!!!! NOVÁ METODA pro uložení inline editace !!!!!
    def save_inline_edit(self, widget, item_id, col_index):
        """Uloží hodnotu z inline editoru (Comboboxu) a aktualizuje data a Treeview."""
        new_value = widget.get().strip()
        widget.destroy() # Zničení editoru
        self.active_editor_widget = None # Reset reference

        # Najít data pro aktualizaci
        item_data = next((item for item in self.all_data if item['id'] == item_id), None)
        if not item_data:
            print(f"! Chyba: Data pro item '{item_id}' nenalezena při ukládání.")
            return

        column_name = self.columns[col_index] # 'spojeni' nebo 'spec'

        # Získání staré hodnoty pro porovnání
        old_value = item_data.get(column_name, "")

        if new_value == old_value:
            # print(f"- Hodnota pro {item_id}/{column_name} nezměněna.")
            return # Nic se nezměnilo

        print(f"+ Ukládám změnu pro {item_id} (řádek {item_data.get('line_num', '?')}), sloupec '{column_name}': '{old_value}' -> '{new_value}'")

        # Aktualizace dat v self.all_data
        item_data[column_name] = new_value

        # Speciální akce podle sloupce
        if column_name == 'spojeni':
            # Znovu naparsovat spojení
            item_data['parsed'] = parse_connection(new_value)
            if not item_data['parsed']:
                print(f"! Varování: Nové spojení '{new_value}' pro {item_id} nelze naparsovat.")
            # Zde bychom mohli aktualizovat i návrhy nebo skupiny, ale to by bylo složitější
        elif column_name == 'spec':
            # Aktualizovat stav 'items_to_edit_ids'
            is_default = new_value.lower() == config.DEFAULT_SPECIFICATION.lower() or not new_value
            if item_id in self.items_to_edit_ids and not is_default:
                self.items_to_edit_ids.remove(item_id)
                print(f"  - Odebráno z 'items_to_edit_ids'")
            elif item_id not in self.items_to_edit_ids and is_default:
                self.items_to_edit_ids.add(item_id)
                print(f"  - Přidáno do 'items_to_edit_ids'")

        # Aktualizace zobrazení v Treeview
        try:
            # Musíme získat VŠECHNY aktuální hodnoty řádku a vytvořit nový tuple
            current_values = list(self.tree.item(item_id, 'values'))
            if len(current_values) > col_index:
                current_values[col_index] = new_value # Nahradit upravenou hodnotu
                self.tree.item(item_id, values=tuple(current_values))
            else:
                 print(f"! Chyba: Nelze aktualizovat Treeview pro {item_id} - nesprávný počet hodnot.")

        except tk.TclError as e:
            # Může nastat, pokud byl item mezitím smazán (např. změnou filtru)
            print(f"! Varování: Aktualizace Treeview pro {item_id} selhala: {e}")

    def apply_to_group(self):
        """Aplikuje specifikaci z Entry na všechny viditelné řádky v Treeview."""
        new_spec = self.spec_entry.get().strip()
        if not new_spec:
            messagebox.showwarning("Chybí specifikace", "Zadejte novou specifikaci.", parent=self.editor_window)
            return

        visible_item_ids = self.tree.get_children()
        if not visible_item_ids:
            messagebox.showinfo("Žádné položky", "Ve skupině nejsou položky k úpravě.", parent=self.editor_window)
            return

        confirm = messagebox.askyesno("Potvrdit změnu", f"Opravdu nastavit '{new_spec}'\npro {len(visible_item_ids)} zobrazených položek?", parent=self.editor_window)
        if not confirm:
            return

        updated_count = 0
        for item_id in visible_item_ids:
            item_data = next((item for item in self.all_data if item['id'] == item_id), None)
            if item_data:
                # !!!!! ZMĚNA: Aplikujeme pouze na sloupec 'spec' !!!!!
                if item_data['spec'] != new_spec:
                    item_data['spec'] = new_spec
                    # Aktualizace items_to_edit_ids
                    is_default = new_spec.lower() == config.DEFAULT_SPECIFICATION.lower() or not new_spec
                    if item_id in self.items_to_edit_ids and not is_default:
                        self.items_to_edit_ids.remove(item_id)
                    elif item_id not in self.items_to_edit_ids and is_default:
                         self.items_to_edit_ids.add(item_id)

                    # Aktualizace Treeview
                    try:
                        current_values = list(self.tree.item(item_id, 'values'))
                        # Index pro 'spec' je 2 (line=0, spojeni=1, spec=2)
                        if len(current_values) > 2:
                            current_values[2] = new_spec
                            self.tree.item(item_id, values=tuple(current_values))
                        else:
                            print(f"! Chyba apply_to_group: Nelze aktualizovat Treeview pro {item_id}.")
                    except tk.TclError:
                         print(f"! Varování apply_to_group: Aktualizace Treeview selhala pro {item_id}.")
                    updated_count += 1

        print(f"+ Spec '{new_spec}' aplikována na {updated_count} položek.")
        if updated_count > 0:
            messagebox.showinfo("Aktualizováno", f"{updated_count} položek aktualizováno.\nZůstávají zobrazeny.", parent=self.editor_window)

    def save_changes(self):
        """Uloží všechna data (včetně upravených) do výstupního souboru."""
        # !!!!! PŘIDÁNO: Zničení aktivního editoru před uložením !!!!!
        if self.active_editor_widget:
            # Můžeme se pokusit uložit hodnotu nebo jen zničit
            # Pro jistotu jen zničíme, uživatel by měl dokončit editaci před uložením
            print("- Zavírám aktivní editor před uložením.")
            self.active_editor_widget.destroy()
            self.active_editor_widget = None

        output_basename = os.path.basename(self.output_file)
        print(f"+ Ukládám změny do: {self.output_file}")

        if os.path.exists(self.output_file):
            overwrite = messagebox.askyesno("Soubor existuje", f"Soubor '{output_basename}' již existuje.\nPřepsat?", icon='warning', parent=self.editor_window)
            if not overwrite:
                print("- Ukládání zrušeno.")
                return

        try:
            written_count = 0
            with open(self.output_file, 'w', encoding=self.encoding, newline='') as outfile:
                writer = csv.writer(outfile, delimiter=config.CSV_DELIMITER)
                writer.writerow(["Spojeni", "Specifikace"]) # Hlavička
                for item_data in self.all_data:
                    # Použijeme hodnoty přímo z item_data
                    spojeni_to_write = item_data.get('spojeni', '')
                    spec_to_write = item_data.get('spec', '')
                    # Pokud je spec prázdná, zapíšeme defaultní
                    if not spec_to_write:
                        spec_to_write = config.DEFAULT_SPECIFICATION
                    writer.writerow([spojeni_to_write, spec_to_write])
                    written_count += 1

            print(f"+ Změny uloženy do '{output_basename}'. Zapsáno {written_count} řádků.")
            messagebox.showinfo("Uloženo", f"Změny uloženy do:\n{self.output_file}", parent=self.editor_window)
            self.update_main_status(f"Změny uloženy do {output_basename}.")
            self.on_close() # Zavřít editor po úspěšném uložení
        except Exception as e:
            print(f"! Chyba ukládání: {e}")
            messagebox.showerror("Chyba ukládání", f"Nelze uložit '{output_basename}':\n{e}", parent=self.editor_window)