# -*- coding: utf-8 -*-

"""Třída SpecEditorApp pro GUI editor specifikací."""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, simpledialog
import csv
import os
import re
from collections import Counter, OrderedDict, defaultdict

# Importy z našich modulů
import config
from utils import parse_connection

class SpecEditorApp:
    """GUI Toplevel okno pro editaci specifikací."""
    def __init__(self, parent, input_file, output_file, encoding, status_label_widget=None):
        self.parent = parent; self.input_file = input_file; self.output_file = output_file; self.encoding = encoding
        self.status_label_widget = status_label_widget # Reference na status bar hlavního okna
        self.all_data = []; self.items_to_edit_ids = set(); self.group_keys = OrderedDict()
        self.component_specs = defaultdict(list); self.suggested_specs = {}

        self.editor_window = tk.Toplevel(parent)
        self.editor_window.title(f"Editor Specifikací - {os.path.basename(input_file)}")
        self.editor_window.geometry("900x600")
        self.editor_window.protocol("WM_DELETE_WINDOW", self.on_close)

        if not self.load_data(): self.on_close(); return
        self.create_widgets(); self.populate_treeview()

        # Zaměřit okno editoru
        self.editor_window.transient(parent) # Nastavit jako potomka hlavního okna
        self.editor_window.grab_set() # Blokovat interakci s hlavním oknem
        self.parent.wait_window(self.editor_window) # Počkat, až se toto okno zavře

    def update_main_status(self, text):
        """Aktualizuje status label v hlavním okně (pokud existuje)."""
        if self.status_label_widget:
            try:
                self.status_label_widget.config(text=text)
            except Exception:
                print("! Chyba: Nelze aktualizovat hlavní status label.")

    def on_close(self):
        """Voláno při zavření okna."""
        print("- Editor zavřen.")
        self.update_main_status("Editor zavřen.")
        self.editor_window.grab_release() # Uvolnit grab
        self.editor_window.destroy()

    def load_data(self):
        """Načte data z priprava.csv, naparsuje je a analyzuje specifikace."""
        self.update_main_status(f"Načítám a analyzuji {os.path.basename(self.input_file)}...")
        print(f"+ Načítám editor: {self.input_file}"); component_names_a = set(); component_names_b = set()
        self.component_specs.clear()
        try:
            with open(self.input_file, 'r', encoding=self.encoding, newline='') as f:
                reader = csv.reader(f, delimiter=config.CSV_DELIMITER); header = next(reader)
                if header != ["Spojeni", "Specifikace"]: messagebox.showerror("Chybný formát", f"'{os.path.basename(self.input_file)}' nemá hlavičku 'Spojeni;Specifikace'.", parent=self.editor_window); return False
                for i, row in enumerate(reader):
                    if len(row) != 2: print(f"! Varování editor: Přeskakuji řádek {i+2}: {row}"); continue
                    spojeni, spec_raw = row; spec = spec_raw.strip(); parsed_data = parse_connection(spojeni); item_id = f"item_{i}"
                    self.all_data.append({"id": item_id, "spojeni": spojeni, "spec": spec, "parsed": parsed_data})
                    current_spec_lower = spec.lower(); is_default_spec = current_spec_lower == config.DEFAULT_SPECIFICATION.lower() or not spec
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
                    if count >= 1: # Změněno na >= 1, aby navrhlo i jedinou existující spec.
                        self.suggested_specs[comp_name] = most_common_spec
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
                    if key in self.group_keys: key += "_2"
                self.group_keys[key] = lambda item, n=name: item['id'] in self.items_to_edit_ids and item['parsed'] and item['parsed']['b']['name'] == n
            print(f"+ Editor data: {len(self.all_data)} řádků, {len(self.items_to_edit_ids)} k editaci. Návrhů: {len(self.suggested_specs)}.")
            self.update_main_status(f"Editor načten: {len(self.items_to_edit_ids)} položek k editaci.")
            if not self.items_to_edit_ids: messagebox.showinfo("Není co editovat", "V souboru nejsou žádné řádky s 'neni spec'.", parent=self.editor_window); return False
            return True
        except FileNotFoundError: messagebox.showerror("Chyba souboru", f"Vstup '{self.input_file}' nenalezen.", parent=self.editor_window); return False
        except Exception as e: messagebox.showerror("Chyba načítání", f"Chyba načítání editoru:\n{e}", parent=self.editor_window); print(f"! Chyba load_data: {e}"); import traceback; traceback.print_exc(); return False

    def create_widgets(self):
        """Vytvoří prvky GUI v editor okně."""
        # ... (kód pro tvorbu widgetů - stejný jako předtím) ...
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
        """Naplní Treeview daty podle filtru."""
        # ... (stejné) ...
        for item in self.tree.get_children(): self.tree.delete(item)
        if filter_func is None: filter_key = self.group_combo.get(); filter_func = self.group_keys.get(filter_key, lambda item: False)
        for item_data in self.all_data:
            if filter_func(item_data): self.tree.insert("", tk.END, iid=item_data['id'], values=(item_data['spojeni'], item_data['spec']))

    def on_group_select(self, _event=None):
        """Reakce na změnu výběru ve skupinovém Comboboxu - PŘEDVYPLNÍ NÁVRH."""
        # ... (stejné) ...
        filter_key = self.group_combo.get(); filter_func = self.group_keys.get(filter_key)
        self.spec_entry.delete(0, tk.END)
        match = re.search(r"\(návrh: '(.*)'\)", filter_key)
        if match: suggested_spec = match.group(1); self.spec_entry.insert(0, suggested_spec); print(f"+ Návrh: '{suggested_spec}' pro '{filter_key}'")
        if filter_func: self.populate_treeview(filter_func)
        else: print(f"! Chyba filtru: '{filter_key}'")

    def apply_to_group(self):
        """Aplikuje specifikaci z Entry na všechny viditelné řádky v Treeview,
           ale nechá je viditelné."""
        # ... (stejné) ...
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

    def edit_selected_item_popup(self, _event=None):
        """Otevře malé okno pro editaci specifikace vybraného řádku."""
        # ... (stejné) ...
        selected_items = self.tree.selection()
        if not selected_items or len(selected_items) > 1: return
        item_id = selected_items[0]; item_data = next((item for item in self.all_data if item['id'] == item_id), None)
        if not item_data: return
        new_spec = simpledialog.askstring("Upravit specifikaci", f"Nová specifikace pro:\n{item_data['spojeni']}", initialvalue=item_data['spec'], parent=self.editor_window)
        if new_spec is not None:
            new_spec = new_spec.strip(); item_data['spec'] = new_spec if new_spec else config.DEFAULT_SPECIFICATION
            new_spec_lower = item_data['spec'].lower(); is_default = new_spec_lower == config.DEFAULT_SPECIFICATION.lower() or not new_spec_lower
            if item_id in self.items_to_edit_ids and not is_default: self.items_to_edit_ids.remove(item_id)
            elif item_id not in self.items_to_edit_ids and is_default: self.items_to_edit_ids.add(item_id)
            self.tree.item(item_id, values=(item_data['spojeni'], item_data['spec'])); print(f"+ Položka {item_id} upravena na '{item_data['spec']}'")

    def save_changes(self):
        """Uloží všechna data (včetně upravených) do výstupního souboru."""
        # ... (stejné) ...
        output_basename = os.path.basename(self.output_file); print(f"+ Ukládám změny do: {self.output_file}")
        if os.path.exists(self.output_file):
            overwrite = messagebox.askyesno("Soubor existuje", f"Soubor '{output_basename}' již existuje.\nPřepsat?", icon='warning', parent=self.editor_window)
            if not overwrite: print("- Ukládání zrušeno."); return
        try:
            written_count = 0
            with open(self.output_file, 'w', encoding=self.encoding, newline='') as outfile:
                writer = csv.writer(outfile, delimiter=config.CSV_DELIMITER); writer.writerow(["Spojeni", "Specifikace"])
                for item_data in self.all_data:
                    spec_to_write = item_data['spec'] if item_data['spec'] else config.DEFAULT_SPECIFICATION
                    writer.writerow([item_data['spojeni'], spec_to_write]); written_count +=1
            print(f"+ Změny uloženy do '{output_basename}'. Zapsáno {written_count} řádků.")
            messagebox.showinfo("Uloženo", f"Změny uloženy do:\n{self.output_file}", parent=self.editor_window)
            self.update_main_status(f"Změny uloženy do {output_basename}.")
            self.on_close()
        except Exception as e: print(f"! Chyba ukládání: {e}"); messagebox.showerror("Chyba ukládání", f"Nelze uložit '{output_basename}':\n{e}", parent=self.editor_window)