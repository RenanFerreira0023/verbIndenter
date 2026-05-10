from __future__ import annotations

import sys
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from tkinter import ttk

from verb_indenter import Verb, suggest


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


HISTORY_FILE = app_base_dir() / "history.txt"


def ensure_history_file() -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text(
            "Verb Indenter history\n"
            "====================\n\n",
            encoding="utf-8",
        )


class VerbIndenterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Verb Indenter")
        self.geometry("920x620")
        self.minsize(780, 520)

        self.executor = ThreadPoolExecutor(max_workers=4)
        self.search_after_id: str | None = None
        self.request_number = 0
        self.selected_verb: Verb | None = None
        self.is_loading = False

        self.query = tk.StringVar()
        self.status = tk.StringVar(value="Digite um verbo ou parte dele.")

        ensure_history_file()
        self.configure(bg="#f5f7fb")
        self.create_styles()
        self.create_widgets()
        self.bind_events()

    def create_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("Root.TFrame", background="#f5f7fb")
        style.configure("Panel.TFrame", background="#ffffff", relief="flat")
        style.configure("Title.TLabel", background="#f5f7fb", foreground="#132238", font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", background="#f5f7fb", foreground="#5b677a", font=("Segoe UI", 10))
        style.configure("Label.TLabel", background="#ffffff", foreground="#324052", font=("Segoe UI", 10, "bold"))
        style.configure("Value.TLabel", background="#ffffff", foreground="#111827", font=("Segoe UI", 13))
        style.configure("Muted.TLabel", background="#ffffff", foreground="#697386", font=("Segoe UI", 9))
        style.configure("Status.TLabel", background="#f5f7fb", foreground="#697386", font=("Segoe UI", 9))
        style.configure("Search.TEntry", fieldbackground="#ffffff", foreground="#111827", bordercolor="#c9d2e3", lightcolor="#c9d2e3")
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 8))
        style.configure("Treeview", rowheight=34, font=("Segoe UI", 10), background="#ffffff", fieldbackground="#ffffff")
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#e9eef7", foreground="#27364a")

    def create_widgets(self) -> None:
        root = ttk.Frame(self, style="Root.TFrame", padding=24)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root, style="Root.TFrame")
        header.pack(fill="x")

        ttk.Label(header, text="Verb Indenter", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Sugestoes de verbos em ingles com infinitivo, passado simples e participio.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 18))

        search_panel = ttk.Frame(root, style="Panel.TFrame", padding=16)
        search_panel.pack(fill="x", pady=(0, 16))

        ttk.Label(search_panel, text="Pesquisar verbo", style="Label.TLabel").pack(anchor="w")
        self.search_entry = ttk.Entry(search_panel, textvariable=self.query, style="Search.TEntry", font=("Segoe UI", 16))
        self.search_entry.pack(fill="x", pady=(8, 0), ipady=8)
        self.search_entry.focus_set()

        content = ttk.Frame(root, style="Root.TFrame")
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        list_panel = ttk.Frame(content, style="Panel.TFrame", padding=14)
        list_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        list_panel.rowconfigure(1, weight=1)
        list_panel.columnconfigure(0, weight=1)

        ttk.Label(list_panel, text="Sugestoes", style="Label.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10))

        columns = ("infinitive", "past", "participle", "kind", "source")
        self.table = ttk.Treeview(list_panel, columns=columns, show="headings", selectmode="browse")
        self.table.heading("infinitive", text="Infinitivo")
        self.table.heading("past", text="Passado")
        self.table.heading("participle", text="Participio")
        self.table.heading("kind", text="Tipo")
        self.table.heading("source", text="Fonte")
        self.table.column("infinitive", minwidth=110, width=130)
        self.table.column("past", minwidth=110, width=130)
        self.table.column("participle", minwidth=120, width=140)
        self.table.column("kind", minwidth=80, width=90)
        self.table.column("source", minwidth=100, width=130)
        self.table.grid(row=1, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_panel, orient="vertical", command=self.table.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)

        detail_panel = ttk.Frame(content, style="Panel.TFrame", padding=18)
        detail_panel.grid(row=0, column=1, sticky="nsew")
        detail_panel.columnconfigure(0, weight=1)
        detail_panel.rowconfigure(1, weight=1)

        detail_header = ttk.Frame(detail_panel, style="Panel.TFrame")
        detail_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        detail_header.columnconfigure(0, weight=1)

        ttk.Label(detail_header, text="Detalhes", style="Label.TLabel").grid(row=0, column=0, sticky="w")
        self.save_button = ttk.Button(
            detail_header,
            text="Salvar",
            style="Primary.TButton",
            command=self.save_selected_verb,
            state="disabled",
        )
        self.save_button.grid(row=0, column=1, sticky="e")

        detail_canvas = tk.Canvas(detail_panel, bg="#ffffff", highlightthickness=0)
        detail_canvas.grid(row=1, column=0, sticky="nsew")

        detail_y_scrollbar = ttk.Scrollbar(detail_panel, orient="vertical", command=detail_canvas.yview)
        detail_y_scrollbar.grid(row=1, column=1, sticky="ns", padx=(8, 0))
        detail_canvas.configure(yscrollcommand=detail_y_scrollbar.set)

        detail_content = ttk.Frame(detail_canvas, style="Panel.TFrame")
        detail_window = detail_canvas.create_window((0, 0), window=detail_content, anchor="nw")

        def sync_detail_scrollregion(_event: tk.Event) -> None:
            detail_canvas.configure(scrollregion=detail_canvas.bbox("all"))

        def sync_detail_width(event: tk.Event) -> None:
            detail_canvas.itemconfigure(detail_window, width=event.width)

        detail_content.bind("<Configure>", sync_detail_scrollregion)
        detail_canvas.bind("<Configure>", sync_detail_width)
        detail_content.columnconfigure(0, weight=1)

        self.infinitive_value = self.add_detail_value(detail_content, "Infinitivo", 1)
        self.past_value = self.add_detail_value(detail_content, "Passado simples", 3)
        self.participle_value = self.add_detail_value(detail_content, "Participio", 5)
        self.kind_value = self.add_detail_value(detail_content, "Classificacao", 7)
        self.source_value = self.add_detail_value(detail_content, "Fonte", 9)

        ttk.Label(detail_content, text="Definicao", style="Label.TLabel").grid(row=11, column=0, sticky="w", pady=(18, 4))
        self.definition_text = tk.Text(
            detail_content,
            height=8,
            wrap="word",
            bg="#ffffff",
            fg="#111827",
            relief="flat",
            font=("Segoe UI", 10),
            padx=0,
            pady=4,
        )
        self.definition_text.grid(row=12, column=0, sticky="nsew")
        definition_y_scrollbar = ttk.Scrollbar(detail_content, orient="vertical", command=self.definition_text.yview)
        definition_y_scrollbar.grid(row=12, column=1, sticky="ns", padx=(8, 0))
        self.definition_text.configure(yscrollcommand=definition_y_scrollbar.set)
        self.definition_text.insert("1.0", "Selecione uma sugestao para ver detalhes.")
        self.definition_text.configure(state="disabled")

        footer = ttk.Frame(root, style="Root.TFrame")
        footer.pack(fill="x", pady=(12, 0))
        footer.columnconfigure(0, weight=1)

        ttk.Label(footer, textvariable=self.status, style="Status.TLabel").grid(row=0, column=0, sticky="w")
        self.loading_bar = ttk.Progressbar(footer, mode="indeterminate", length=150)

    def add_detail_value(self, parent: ttk.Frame, label: str, row: int) -> ttk.Label:
        ttk.Label(parent, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky="w", pady=(18, 2))
        value = ttk.Label(parent, text="-", style="Value.TLabel")
        value.grid(row=row + 1, column=0, sticky="w")
        return value

    def bind_events(self) -> None:
        self.query.trace_add("write", self.schedule_search)
        self.table.bind("<<TreeviewSelect>>", self.show_selected_verb)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def ensure_history_file(self) -> None:
        ensure_history_file()

    def schedule_search(self, *_args: object) -> None:
        if self.search_after_id is not None:
            self.after_cancel(self.search_after_id)
        self.search_after_id = self.after(250, self.start_search)

    def start_search(self) -> None:
        query = self.query.get().strip()
        self.request_number += 1
        current_request = self.request_number

        if not query:
            self.stop_loading()
            self.set_results([])
            self.status.set("Digite um verbo ou parte dele.")
            return

        self.start_loading(f"Procurando por \"{query}\"...")
        future = self.executor.submit(suggest, query, 5, True)
        self.after(80, lambda: self.check_search_result(future, current_request))

    def check_search_result(self, future: object, request_number: int) -> None:
        if request_number != self.request_number:
            return

        if not future.done():
            self.after(80, lambda: self.check_search_result(future, request_number))
            return

        try:
            verbs = future.result()
        except Exception:
            verbs = []
            self.status.set("Nao foi possivel consultar agora.")

        self.stop_loading()
        self.set_results(verbs)
        if verbs:
            self.status.set(f"{len(verbs)} sugestao(oes) encontrada(s).")
        else:
            self.status.set("Nenhum verbo encontrado para essa busca.")

    def start_loading(self, message: str) -> None:
        self.status.set(message)
        if self.is_loading:
            return

        self.is_loading = True
        self.loading_bar.grid(row=0, column=1, sticky="e")
        self.loading_bar.start(12)

    def stop_loading(self) -> None:
        if not self.is_loading:
            return

        self.is_loading = False
        self.loading_bar.stop()
        self.loading_bar.grid_remove()

    def set_results(self, verbs: list[Verb]) -> None:
        self.table.delete(*self.table.get_children())
        self.verbs_by_item: dict[str, Verb] = {}

        for verb in verbs:
            item = self.table.insert(
                "",
                "end",
                values=(verb.infinitive, verb.simple_past, verb.participle, verb.kind, verb.source),
            )
            self.verbs_by_item[item] = verb

        if verbs:
            first_item = self.table.get_children()[0]
            self.table.selection_set(first_item)
            self.table.focus(first_item)
            self.show_selected_verb()
        else:
            self.clear_details()

    def show_selected_verb(self, *_args: object) -> None:
        selected_items = self.table.selection()
        if not selected_items:
            return

        verb = self.verbs_by_item.get(selected_items[0])
        if verb is None:
            return

        self.selected_verb = verb
        self.save_button.configure(state="normal")
        self.infinitive_value.configure(text=verb.infinitive)
        self.past_value.configure(text=verb.simple_past)
        self.participle_value.configure(text=verb.participle)
        self.kind_value.configure(text=verb.kind)
        self.source_value.configure(text=verb.source)
        self.set_definition(verb.definition or "Sem definicao disponivel para esta sugestao.")

    def save_selected_verb(self) -> None:
        if self.selected_verb is None:
            self.status.set("Selecione uma palavra antes de salvar.")
            return

        self.ensure_history_file()
        verb = self.selected_verb
        saved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        definition = verb.definition or "Sem definicao disponivel."
        line = (
            f"[{saved_at}] {verb.infinitive} | past: {verb.simple_past} | "
            f"participle: {verb.participle} | {verb.kind} | source: {verb.source}\n"
            f"definition: {definition}\n\n"
        )

        with HISTORY_FILE.open("a", encoding="utf-8") as file:
            file.write(line)

        self.status.set(f"Salvo em {HISTORY_FILE.name}: {verb.infinitive}")

    def clear_details(self) -> None:
        self.selected_verb = None
        self.save_button.configure(state="disabled")
        for label in (
            self.infinitive_value,
            self.past_value,
            self.participle_value,
            self.kind_value,
            self.source_value,
        ):
            label.configure(text="-")
        self.set_definition("Nenhum verbo encontrado. Verifique se a palavra existe ou tente outro termo.")

    def set_definition(self, text: str) -> None:
        self.definition_text.configure(state="normal")
        self.definition_text.delete("1.0", "end")
        self.definition_text.insert("1.0", text)
        self.definition_text.configure(state="disabled")

    def close(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.destroy()


def main() -> None:
    app = VerbIndenterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
