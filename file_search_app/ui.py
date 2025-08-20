
"""
Main GUI for the Advanced File Search Pro application.
"""
import os
import re
import sys
import csv
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
from datetime import datetime
import threading
import openpyxl

from . import config
from . import file_reader
from . import search
from .utils import Tooltip

class FileSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📁 Advanced File Search Pro")
        self.root.geometry("1100x800")
        self.root.configure(padx=15, pady=15)

        self._setup_styles_and_fonts()
        self.results = []
        self.create_widgets()

    def _setup_styles_and_fonts(self):
        self.default_font = font.nametofont("TkDefaultFont")
        self.bold_font = font.Font(**self.default_font.config())
        self.mono_font = font.Font(family="Courier", size=10)

    def create_widgets(self):
        # Main layout frames
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", pady=(0, 10))

        middle_frame = ttk.Frame(self.root)
        middle_frame.pack(fill="both", expand=True)

        footer_frame = ttk.Frame(self.root)
        footer_frame.pack(fill="x", pady=(10, 0))

        self._create_title(top_frame)
        self._create_input_panel(top_frame)
        self._create_options_panel(top_frame)
        self._create_action_panel(top_frame)
        self._create_results_panel(middle_frame)
        self._create_footer(footer_frame)
        self._create_context_menu()

    def _create_title(self, parent):
        title = ttk.Label(parent, text="Advanced File Search Pro", font=("Helvetica", 16, "bold"))
        title.pack(pady=(0, 15))

    def _create_input_panel(self, parent):
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill="x", expand=True)
        input_frame.columnconfigure(1, weight=1)

        # Directory Selection
        ttk.Label(input_frame, text="Search Directory:").grid(row=0, column=0, sticky="w", pady=5, padx=(0, 5))
        self.directory_var = tk.StringVar(value=os.getcwd())
        dir_entry = ttk.Entry(input_frame, textvariable=self.directory_var)
        dir_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(input_frame, text="Browse...", command=self.browse_directory).grid(row=0, column=2, padx=5)

        # Keywords
        ttk.Label(input_frame, text="Pattern:").grid(row=1, column=0, sticky="w", pady=5, padx=(0, 5))
        self.pattern_var = tk.StringVar()
        pattern_entry = ttk.Entry(input_frame, textvariable=self.pattern_var)
        pattern_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        Tooltip(pattern_entry, "Enter text or regex pattern\nUse space-separated words (non-regex)\nor a full regex like: report_.*2024\\.pdf")

        # Extensions
        ttk.Label(input_frame, text="Extensions:").grid(row=2, column=0, sticky="w", pady=5, padx=(0, 5))
        self.ext_var = tk.StringVar(value="txt pdf docx pptx xlsx csv py js")
        ext_entry = ttk.Entry(input_frame, textvariable=self.ext_var)
        ext_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        Tooltip(ext_entry, "Filter by extensions: pdf docx txt pptx xlsx csv py js\nLeave empty to include all")

    def _create_options_panel(self, parent):
        options_frame = ttk.LabelFrame(parent, text="Search Options", padding=10)
        options_frame.pack(fill="x", expand=True, pady=10)

        self.match_any_var = tk.BooleanVar()
        self.case_sensitive_var = tk.BooleanVar()
        self.search_content_var = tk.BooleanVar()
        self.regex_var = tk.BooleanVar()
        self.sort_var = tk.StringVar(value="name")

        ttk.Checkbutton(options_frame, text="Match any keyword", variable=self.match_any_var).pack(side="left", padx=10)
        ttk.Checkbutton(options_frame, text="Case sensitive", variable=self.case_sensitive_var).pack(side="left", padx=10)
        ttk.Checkbutton(options_frame, text="Search in content", variable=self.search_content_var).pack(side="left", padx=10)
        ttk.Checkbutton(options_frame, text="Use Regex", variable=self.regex_var).pack(side="left", padx=10)

        ttk.Label(options_frame, text="Sort by:").pack(side="left", padx=(20, 5))
        ttk.Combobox(options_frame, textvariable=self.sort_var, values=["name", "date", "size", "none"],
                     state="readonly", width=10).pack(side="left", padx=5)

    def _create_action_panel(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", expand=True, pady=5)

        self.search_btn = ttk.Button(btn_frame, text="🔍 Start Search", command=self.start_search_thread)
        self.search_btn.pack(side="left", padx=2)

        self.export_btn = ttk.Button(btn_frame, text="💾 Export Results", command=self.export_results, state="disabled")
        self.export_btn.pack(side="left", padx=2)

        self.scanned_label = ttk.Label(btn_frame, text="0 / 0")
        self.scanned_label.pack(side="right", padx=(0, 5))
        ttk.Label(btn_frame, text="Files Scanned:").pack(side="right")

        self.progress_bar = ttk.Progressbar(btn_frame, mode="determinate")
        self.progress_bar.pack(side="right", fill="x", expand=True, padx=(5, 10))

    def _create_results_panel(self, parent):
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)

        # Left: Results Tree
        left_frame = ttk.Frame(paned)
        columns = ("Icon", "Name", "Size", "Modified")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=20)
        self.tree.heading("Icon", text="")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Size", text="Size (KB)")
        self.tree.heading("Modified", text="Modified")
        self.tree.column("Icon", width=30, anchor="center")
        self.tree.column("Name", width=300)
        self.tree.column("Size", width=100, anchor="center")
        self.tree.column("Modified", width=150, anchor="center")

        vsb1 = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb1.set)
        vsb1.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<Double-1>", self.open_selected_file)
        self.tree.bind("<<TreeviewSelect>>", self.show_preview)
        self.tree.bind("<Button-3>", self.show_context_menu)
        if sys.platform == "darwin":
            self.tree.bind("<Button-2>", self.show_context_menu)

        # Right: Preview Pane
        right_frame = ttk.Frame(paned)
        ttk.Label(right_frame, text="📄 Content Preview", font=("Helvetica", 11, "bold")).pack(anchor="w", pady=5)
        
        vsb2 = ttk.Scrollbar(right_frame, orient="vertical")
        self.preview_text = tk.Text(right_frame, wrap="word", font=self.mono_font, height=20, bg="#f4f4f4", state="disabled", yscrollcommand=vsb2.set)
        vsb2.config(command=self.preview_text.yview)
        self.preview_text.tag_configure("highlight", background="yellow")

        vsb2.pack(side="right", fill="y")
        self.preview_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        paned.add(left_frame, weight=3)
        paned.add(right_frame, weight=2)

    def _create_footer(self, parent):
        # Create a container frame to hold all footer widgets
        container = ttk.Frame(parent)

        # Pack all widgets into the container frame
        license_label = ttk.Label(container, text="License: MIT | Made with love: ", foreground="gray")
        license_label.pack(side="left")

        creator_label = tk.Label(container, text="Jhenbert", foreground="blue", cursor="hand2", font=("Helvetica", 9, "underline"))
        creator_label.pack(side="left")
        creator_label.bind("<Button-1>", lambda e: webbrowser.open("https://jhenbert.dev"))

        copyright_label = ttk.Label(container, text=f" © {datetime.now().year}", foreground="gray")
        copyright_label.pack(side="left")

        # Pack the container frame into the parent (footer_frame), which will center it by default.
        container.pack()

    def _create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="📂 Open File", command=self.open_selected_file)
        self.context_menu.add_command(label="📁 Open File Location", command=self.open_file_location)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Copy Path", command=self.copy_path_to_clipboard)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            if not self.tree.selection() or item not in self.tree.selection():
                self.tree.selection_set(item)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def browse_directory(self):
        path = filedialog.askdirectory(initialdir=self.directory_var.get())
        if path:
            self.directory_var.set(path)

    def start_search_thread(self):
        params = {
            'directory': self.directory_var.get(),
            'pattern': self.pattern_var.get().strip(),
            'extensions': self.ext_var.get().strip().split() if self.ext_var.get().strip() else None,
            'match_any': self.match_any_var.get(),
            'case_sensitive': self.case_sensitive_var.get(),
            'search_content': self.search_content_var.get(),
            'use_regex': self.regex_var.get(),
        }

        if not params['pattern']:
            messagebox.showwarning("Input Error", "Please enter a search pattern.")
            return

        if not os.path.isdir(params['directory']):
            messagebox.showerror("Directory Error", f"Directory not found:\n{params['directory']}")
            return

        self._prepare_for_search()

        searcher = search.FileSearcher(params)
        search_thread = threading.Thread(
            target=searcher.search,
            args=(self.update_progress, self.add_result, self.search_complete)
        )
        search_thread.daemon = True
        search_thread.start()

    def _prepare_for_search(self):
        self.search_btn.config(state="disabled")
        self.export_btn.config(state="disabled")
        self.tree.delete(*self.tree.get_children())
        self.results = []
        self.preview_text.config(state="normal")
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.config(state="disabled")
        self.progress_bar['value'] = 0
        self.scanned_label.config(text="0 / ?")
        self.root.update_idletasks()

    def update_progress(self, scanned, total):
        self.root.after(0, self._update_progress_ui, scanned, total)

    def _update_progress_ui(self, scanned, total):
        if total > 0:
            self.progress_bar['value'] = (scanned / total) * 100
        self.scanned_label.config(text=f"{scanned} / {total}")

    def add_result(self, result):
        self.root.after(0, self._add_result_ui, result)

    def _add_result_ui(self, result):
        self.results.append(result)

    def search_complete(self):
        self.root.after(0, self._search_complete_ui)

    def _search_complete_ui(self):
        sort_by = self.sort_var.get()
        if sort_by == "name":
            self.results.sort(key=lambda x: x['name'].lower())
        elif sort_by == "date":
            self.results.sort(key=lambda x: x['mtime'], reverse=True)
        elif sort_by == "size":
            self.results.sort(key=lambda x: x['size'], reverse=True)

        for r in self.results:
            size_kb = r['size'] // 1024
            date_str = datetime.fromtimestamp(r['mtime']).strftime("%Y-%m-%d %H:%M")
            icon = config.ICONS.get(r['ext'], config.ICONS['default'])
            self.tree.insert("", "end", values=(icon, r['name'], size_kb, date_str), tags=(r['path'],))

        self.progress_bar['value'] = 100
        self.search_btn.config(state="normal")
        if self.results:
            self.export_btn.config(state="normal")
        messagebox.showinfo("Done", f"Found {len(self.results)} file(s).")

    def _get_selected_filepath(self):
        selected = self.tree.selection()
        if not selected:
            return None
        item = self.tree.item(selected[0])
        return item['tags'][0] if item.get('tags') else None

    def open_selected_file(self, event=None):
        filepath = self._get_selected_filepath()
        if not filepath:
            return
        try:
            if sys.platform == "win32": os.startfile(filepath)
            elif sys.platform == "darwin": os.system(f'open "{filepath}"')
            else: os.system(f'xdg-open "{filepath}"')
        except Exception as e:
            messagebox.showerror("Open Failed", f"Could not open file:\n{str(e)}")

    def open_file_location(self):
        filepath = self._get_selected_filepath()
        if not filepath: return
        folder_path = os.path.dirname(filepath)
        try:
            if sys.platform == "win32": os.startfile(folder_path)
            elif sys.platform == "darwin": os.system(f'open "{folder_path}"')
            else: os.system(f'xdg-open "{folder_path}"')
        except Exception as e:
            messagebox.showerror("Open Failed", f"Could not open folder:\n{str(e)}")

    def copy_path_to_clipboard(self):
        filepath = self._get_selected_filepath()
        if not filepath: return
        self.root.clipboard_clear()
        self.root.clipboard_append(filepath)
        messagebox.showinfo("Copied", "File path copied to clipboard!")

    def show_preview(self, event):
        self.preview_text.config(state="normal")
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.tag_remove("highlight", "1.0", tk.END)

        filepath = self._get_selected_filepath()
        if not filepath:
            self.preview_text.config(state="disabled")
            return

        self.preview_text.insert(tk.END, f"📁 File: {os.path.basename(filepath)}\n")
        self.preview_text.insert(tk.END, f"🔗 Path: {filepath}\n\n")

        if not self.search_content_var.get():
            self.preview_text.insert(tk.END, "ℹ️ Content search was disabled. Re-run with 'Search in content' enabled.")
            self.preview_text.config(state="disabled")
            return

        content = file_reader.read_file_content(filepath)
        if "support not installed" in content or "Error reading" in content:
            self.preview_text.insert(tk.END, f"❌ Could not read content:\n{content}")
        else:
            self.preview_text.insert(tk.END, "📌 Content Preview:\n\n")
            self.preview_text.insert(tk.END, content)
            self._highlight_preview_text()

        self.preview_text.config(state="disabled")

    def _highlight_preview_text(self):
        pattern = self.pattern_var.get().strip()
        if not pattern:
            return

        use_regex = self.regex_var.get()
        case_sensitive = self.case_sensitive_var.get()
        
        text_to_search = self.preview_text.get("1.0", tk.END)
        
        if use_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                for match in re.finditer(pattern, text_to_search, flags):
                    start_index = f"1.0+{match.start()}c"
                    end_index = f"1.0+{match.end()}c"
                    self.preview_text.tag_add("highlight", start_index, end_index)
            except re.error:
                pass # Ignore invalid regex for highlighting
        else:
            keywords = pattern.split()
            for keyword in keywords:
                if not keyword: continue
                start_index = "1.0"
                while True:
                    pos = self.preview_text.search(keyword, start_index, stopindex=tk.END, nocase=not case_sensitive)
                    if not pos:
                        break
                    end_index = f"{pos}+{len(keyword)}c"
                    self.preview_text.tag_add("highlight", pos, end_index)
                    start_index = end_index

    def export_results(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.* ")]
        )
        if not filepath:
            return
        
        headers = ["Filename", "Path", "Size (bytes)", "Modified", "Snippet"]
        try:
            if filepath.endswith(".csv"):
                with open(filepath, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    for r in self.results:
                        writer.writerow([
                            r['name'], r['path'], r['size'],
                            datetime.fromtimestamp(r['mtime']).strftime("%Y-%m-%d %H:%M:%S"),
                            r['snippet']
                        ])
            else:
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Search Results"
                ws.append(headers)
                for r in self.results:
                    ws.append([
                        r['name'], r['path'], r['size'],
                        datetime.fromtimestamp(r['mtime']).strftime("%Y-%m-%d %H:%M:%S"),
                        r['snippet']
                    ])
                wb.save(filepath)
            messagebox.showinfo("Export Success", f"Results saved to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not save file:\n{str(e)}")
 