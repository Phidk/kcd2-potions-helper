from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Dict, List, Tuple
import webbrowser

from kcd2_potions_tool import (
    compute_max_brews,
    load_prices,
    normalize_name,
    parse_readme_to_potions,
    GUIDE_FILENAME,
)


PROJECT_ROOT = Path(__file__).resolve().parent
GUIDE_PATH = PROJECT_ROOT / GUIDE_FILENAME
PRICES_PATH = PROJECT_ROOT / "prices.json"
UPSTREAM_URL = "https://github.com/Omricon/Henrys-Moste-Potente-Potions"
AUTO_RECOMPUTE_DELAY = 400


class PotionGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("KCD2 Potions Helper")
        self.geometry("1300x980")
        self.minsize(1150, 860)

        self.colors = {
            "bg": "#f4f4f6",
            "toolbar": "#e0e0e5",
            "accent": "#4f6fa9",
            "warning": "#9c4d4d",
        }

        self.potions: Dict[str, object] = {}
        self.prices: Dict[str, Dict[str, float]] = {}
        self.ing_lookup: Dict[str, str] = {}
        self.inv_entries: Dict[str, ttk.Spinbox] = {}
        self.inv_pairs: Dict[str, ttk.Frame] = {}
        self.inv_order: List[str] = []
        self.inv_cols = 1
        self._inv_debounce_after: str | None = None
        self.sort_dir: Dict[str, bool] = {}
        self.active_sort: Dict[str, Tuple[str, bool]] = {}
        self.tree_all: ttk.Treeview | None = None
        self.tree: ttk.Treeview | None = None
        self.notebook: ttk.Notebook | None = None
        self.library_tab: ttk.Frame | None = None
        self.detail_text: tk.Text | None = None
        self.tree_plan: ttk.Treeview | None = None
        self.shop_tree: ttk.Treeview | None = None
        self.plan: Dict[str, int] = {}
        self.plan_qty_var = tk.StringVar(value="1")
        self.plan_footer_var = tk.StringVar(value="Total brews: 0 • Total priced value: 0.00")
        self.last_selected: str | None = None
        self.plan_selected_label: ttk.Label | None = None
        self.inventory_filter_var = tk.StringVar()
        self.craftable_search_var = tk.StringVar()
        self.library_search_var = tk.StringVar()
        self.auto_recompute_var = tk.BooleanVar(value=True)
        self.craftable_rows: List[Dict[str, object]] = []
        self.library_rows: List[Dict[str, object]] = []

        self._configure_style()
        self._build_menu()
        self._build_layout()
        self._load_data()

    def _configure_style(self) -> None:
        self.configure(background=self.colors["bg"])
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        base_font = ("Segoe UI", 11)
        heading_font = ("Segoe UI Semibold", 11)

        style.configure(".", font=base_font, background=self.colors["bg"])
        style.configure("TLabel", background=self.colors["bg"])
        style.configure("TButton", padding=4)
        style.configure("App.TFrame", background=self.colors["bg"])
        style.configure("Toolbar.TFrame", background=self.colors["toolbar"], padding=4)
        style.configure("Section.TLabelframe", background=self.colors["bg"], padding=8)
        style.configure("Section.TLabelframe.Label", background=self.colors["bg"], font=heading_font)
        style.configure(
            "Modern.Treeview",
            font=base_font,
            rowheight=26,
        )
        style.configure("Modern.Treeview.Heading", font=heading_font)
        style.configure(
            "TSpinbox",
            fieldbackground="white",
            selectbackground="white",
            selectforeground="black",
        )
        style.map(
            "Modern.Treeview",
            background=[("selected", self.colors["accent"])],
            foreground=[("selected", "white")],
        )

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Reload guide", command=self._load_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu_bar.add_cascade(label="File", menu=file_menu)

        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label="Reset layout", command=self.reset_layout)
        menu_bar.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Open Omricon's GitHub page...", command=self.open_github)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menu_bar)

    def _build_layout(self) -> None:
        # Header / toolbar row (status inline with controls)
        header_row = ttk.Frame(self, style="Toolbar.TFrame", padding="8 8 8 8")
        header_row.pack(fill="x")
        ttk.Button(header_row, text="Reset", command=self.on_reset_all).pack(side="left", padx=(0, 8))
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(header_row, textvariable=self.status_var).pack(side="left")
        ttk.Checkbutton(
            header_row,
            text="Auto-recompute",
            variable=self.auto_recompute_var,
            command=self.on_auto_toggle,
        ).pack(side="right", padx=(6, 0))
        ttk.Button(header_row, text="Compute craftable", command=self.on_compute).pack(
            side="right", padx=(6, 0)
        )

        # Main panes
        self.main_panes = ttk.PanedWindow(self, orient="horizontal")
        self.main_panes.pack(fill="both", expand=True, padx=6, pady=6)

        self._build_left_pane()
        self._build_right_pane()

        # Default pane ratio
        self.after(50, self.reset_layout)

    def _build_left_pane(self) -> None:
        left_frame = ttk.Frame(self.main_panes, style="App.TFrame", padding=8)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=3)
        left_frame.rowconfigure(1, weight=2)
        left_frame.rowconfigure(2, weight=2)
        self.main_panes.add(left_frame, weight=2)

        # Inventory
        inv_frame = ttk.Labelframe(
            left_frame, text="Inventory", style="Section.TLabelframe", padding=8
        )
        inv_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        filter_row = ttk.Frame(inv_frame, style="App.TFrame")
        filter_row.pack(fill="x", pady=(0, 6))
        ttk.Label(filter_row, text="Filter ingredients…").pack(side="left")
        filter_entry = ttk.Entry(filter_row, textvariable=self.inventory_filter_var)
        filter_entry.pack(side="left", fill="x", expand=True, padx=(6, 0))
        filter_entry.bind("<KeyRelease>", self.on_inventory_filter)

        inv_canvas = tk.Canvas(inv_frame, highlightthickness=0, bg=self.colors["bg"])
        inv_scroll = ttk.Scrollbar(inv_frame, orient="vertical", command=inv_canvas.yview)
        inv_canvas.configure(yscrollcommand=inv_scroll.set)
        inv_scroll.pack(side="right", fill="y")
        inv_canvas.pack(side="left", fill="both", expand=True)
        self.inv_canvas = inv_canvas
        self.inv_scrollable = ttk.Frame(inv_canvas, style="App.TFrame")
        self.inv_window = inv_canvas.create_window((0, 0), window=self.inv_scrollable, anchor="nw")
        self.inv_scrollable.bind("<Configure>", self._update_inventory_scrollregion)
        inv_canvas.bind("<Configure>", self.on_inventory_resize)

        # Brew plan
        plan_frame = ttk.Labelframe(
            left_frame, text="Brew plan", style="Section.TLabelframe", padding=8
        )
        plan_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 8))

        plan_top = ttk.Frame(plan_frame, style="App.TFrame")
        plan_top.pack(fill="x", pady=(0, 6))
        self.plan_selected_label = ttk.Label(plan_top, text="No potion selected")
        self.plan_selected_label.pack(side="left")
        qty_frame = ttk.Frame(plan_top, style="App.TFrame")
        qty_frame.pack(side="right")
        ttk.Label(qty_frame, text="Desired brews:").pack(side="left")
        qty_spin = ttk.Spinbox(
            qty_frame,
            from_=0,
            to=999,
            width=6,
            textvariable=self.plan_qty_var,
            command=self.update_plan_button_state,
            validate="key",
            validatecommand=(self.register(self._validate_nonneg), "%P"),
        )
        qty_spin.pack(side="left", padx=(4, 0))
        qty_spin.bind("<KeyRelease>", lambda _e: self.update_plan_button_state())

        plan_actions = ttk.Frame(plan_frame, style="App.TFrame")
        plan_actions.pack(fill="x", pady=(0, 6))
        self.add_to_plan_btn = ttk.Button(
            plan_actions, text="Add to plan", command=self.on_add_to_plan, state="disabled"
        )
        self.add_to_plan_btn.pack(side="left")
        ttk.Button(plan_actions, text="Remove from plan", command=self.on_remove_from_plan).pack(
            side="left", padx=4
        )
        ttk.Button(plan_actions, text="Clear plan", command=self.on_clear_plan).pack(side="left", padx=4)

        plan_table_frame = ttk.Frame(plan_frame, style="App.TFrame")
        plan_table_frame.pack(fill="both", expand=True)
        self.tree_plan = ttk.Treeview(
            plan_table_frame,
            columns=("name", "qty", "value"),
            show="headings",
            style="Modern.Treeview",
        )
        self.tree_plan.heading("name", text="Potion")
        self.tree_plan.heading("qty", text="Brews")
        self.tree_plan.heading("value", text="Total value")
        self.tree_plan.column("name", width=220, anchor="w")
        self.tree_plan.column("qty", width=80, anchor="center")
        self.tree_plan.column("value", width=110, anchor="center")
        plan_vsb = ttk.Scrollbar(plan_table_frame, orient="vertical", command=self.tree_plan.yview)
        self.tree_plan.configure(yscrollcommand=plan_vsb.set)
        plan_vsb.pack(side="right", fill="y")
        self.tree_plan.pack(fill="both", expand=True)
        self.tree_plan.bind("<Double-1>", self.on_edit_plan_quantity)
        self.tree_plan.bind("<Delete>", self.on_remove_from_plan)
        self.tree_plan.bind("<BackSpace>", self.on_remove_from_plan)
        self.tree_plan.bind("<Button-3>", self.on_plan_context_menu)
        self.tree_plan.bind("<<TreeviewSelect>>", lambda _e: self.update_plan_button_state())
        self.plan_menu = tk.Menu(self, tearoff=0)
        self.plan_menu.add_command(label="Edit quantity...", command=self.on_edit_plan_quantity)
        self.plan_menu.add_command(label="Remove from plan", command=self.on_remove_from_plan)

        ttk.Label(plan_frame, textvariable=self.plan_footer_var).pack(anchor="w", pady=(6, 0))

        # Shopping list
        shop_frame = ttk.Labelframe(
            left_frame, text="Shopping list", style="Section.TLabelframe", padding=8
        )
        shop_frame.grid(row=2, column=0, sticky="nsew")
        shop_inner = ttk.Frame(shop_frame, style="App.TFrame")
        shop_inner.pack(fill="both", expand=True)
        self.shop_tree = ttk.Treeview(
            shop_inner,
            columns=("ingredient", "need", "have", "buy", "sell"),
            show="headings",
            style="Modern.Treeview",
        )
        for col, text, width, anchor in [
            ("ingredient", "Ingredient", 220, "w"),
            ("need", "Need", 70, "center"),
            ("have", "Have", 70, "center"),
            ("buy", "Buy", 70, "center"),
            ("sell", "Sell", 70, "center"),
        ]:
            self.shop_tree.heading(col, text=text)
            self.shop_tree.column(col, width=width, anchor=anchor)
        shop_vsb = ttk.Scrollbar(shop_inner, orient="vertical", command=self.shop_tree.yview)
        self.shop_tree.configure(yscrollcommand=shop_vsb.set)
        shop_vsb.pack(side="right", fill="y")
        self.shop_tree.pack(fill="both", expand=True)
        self.shop_tree.tag_configure("buy", foreground=self.colors["accent"])
        self.shop_tree.tag_configure("sell", foreground="#7a5c2f")

    def _build_right_pane(self) -> None:
        right_frame = ttk.Frame(self.main_panes, style="App.TFrame", padding=8)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=3)
        right_frame.rowconfigure(1, weight=2)
        self.main_panes.add(right_frame, weight=3)

        # Notebook with craftable + all potions
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self._build_craftable_tab()
        self._build_library_tab()

        # Shared details pane
        detail_frame = ttk.Labelframe(
            right_frame, text="Potion details", style="Section.TLabelframe", padding=8
        )
        detail_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        detail_frame.rowconfigure(0, weight=1)
        detail_frame.columnconfigure(0, weight=1)
        detail_inner = ttk.Frame(detail_frame, style="App.TFrame")
        detail_inner.grid(row=0, column=0, sticky="nsew")
        detail_inner.columnconfigure(0, weight=1)
        detail_inner.rowconfigure(0, weight=1)
        self.detail_text = tk.Text(
            detail_inner,
            wrap="word",
            font=("Segoe UI", 11),
            padx=10,
            pady=10,
            bg="white",
        )
        detail_vsb = ttk.Scrollbar(detail_inner, orient="vertical", command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_vsb.set, state="disabled")
        self.detail_text.grid(row=0, column=0, sticky="nsew")
        detail_vsb.grid(row=0, column=1, sticky="ns")

    def _build_craftable_tab(self) -> None:
        craft_tab = ttk.Frame(self.notebook, style="App.TFrame", padding=8)
        self.notebook.add(craft_tab, text="Craftable")

        toolbar = ttk.Frame(craft_tab, style="Toolbar.TFrame", padding="6 4")
        toolbar.pack(fill="x", pady=(0, 6))
        ttk.Label(toolbar, text="Search potions…").pack(side="left")
        search_entry = ttk.Entry(toolbar, textvariable=self.craftable_search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=(6, 6))
        search_entry.bind("<KeyRelease>", lambda _e: self.filter_craftable_tree())
        ttk.Label(toolbar, text="Sort by:").pack(side="left", padx=(6, 2))
        self.craft_sort_var = tk.StringVar(value="Name")
        craft_sort = ttk.Combobox(
            toolbar,
            state="readonly",
            width=14,
            textvariable=self.craft_sort_var,
            values=["Name", "Max brews", "Price", "Total value"],
        )
        craft_sort.pack(side="left", padx=(0, 6))
        craft_sort.bind("<<ComboboxSelected>>", self.on_sort_craftable)
        ttk.Checkbutton(
            toolbar,
            text="Auto-recompute",
            variable=self.auto_recompute_var,
            command=self.on_auto_toggle,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Recompute", command=self.on_compute).pack(side="left", padx=(6, 0))

        tree_frame = ttk.Frame(craft_tab, style="App.TFrame")
        tree_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("name", "brews", "price", "total"),
            show="headings",
            style="Modern.Treeview",
        )
        self.tree.heading(
            "name",
            text="Potion",
            command=lambda: self.sort_tree(self.tree, "name", "brew"),
        )
        self.tree.heading(
            "brews",
            text="Max brews",
            command=lambda: self.sort_tree(self.tree, "brews", "brew"),
        )
        self.tree.heading(
            "price",
            text="Price/bottle",
            command=lambda: self.sort_tree(self.tree, "price", "brew"),
        )
        self.tree.heading(
            "total",
            text="Total value",
            command=lambda: self.sort_tree(self.tree, "total", "brew"),
        )
        self.tree.column("name", width=260, anchor="w")
        self.tree.column("brews", width=90, anchor="center")
        self.tree.column("price", width=110, anchor="center")
        self.tree.column("total", width=110, anchor="center")
        brew_vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        brew_hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=brew_vsb.set, xscrollcommand=brew_hsb.set)
        brew_vsb.pack(side="right", fill="y")
        brew_hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def _build_library_tab(self) -> None:
        self.library_tab = ttk.Frame(self.notebook, style="App.TFrame", padding=8)
        self.notebook.add(self.library_tab, text="All potions")

        toolbar = ttk.Frame(self.library_tab, style="Toolbar.TFrame", padding="6 4")
        toolbar.pack(fill="x", pady=(0, 6))
        ttk.Label(toolbar, text="Search potions…").pack(side="left")
        search_entry = ttk.Entry(toolbar, textvariable=self.library_search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=(6, 6))
        search_entry.bind("<KeyRelease>", lambda _e: self.filter_library_tree())
        ttk.Label(toolbar, text="Sort by:").pack(side="left", padx=(6, 2))
        self.library_sort_var = tk.StringVar(value="Name")
        lib_sort = ttk.Combobox(
            toolbar,
            state="readonly",
            width=14,
            textvariable=self.library_sort_var,
            values=["Name", "Price"],
        )
        lib_sort.pack(side="left", padx=(0, 6))
        lib_sort.bind("<<ComboboxSelected>>", self.on_sort_library)

        tree_frame = ttk.Frame(self.library_tab, style="App.TFrame")
        tree_frame.pack(fill="both", expand=True)
        self.tree_all = ttk.Treeview(
            tree_frame,
            columns=("name", "price"),
            show="headings",
            style="Modern.Treeview",
        )
        self.tree_all.heading(
            "name",
            text="Potion",
            command=lambda: self.sort_tree(self.tree_all, "name", "lib"),
        )
        self.tree_all.heading(
            "price",
            text="Price/bottle",
            command=lambda: self.sort_tree(self.tree_all, "price", "lib"),
        )
        self.tree_all.column("name", width=280, anchor="w")
        self.tree_all.column("price", width=120, anchor="center")
        lib_vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_all.yview)
        lib_hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree_all.xview)
        self.tree_all.configure(yscrollcommand=lib_vsb.set, xscrollcommand=lib_hsb.set)
        lib_vsb.pack(side="right", fill="y")
        lib_hsb.pack(side="bottom", fill="x")
        self.tree_all.pack(fill="both", expand=True)
        self.tree_all.bind("<<TreeviewSelect>>", self.on_select_library)

    # ----------------- data -----------------
    def _load_data(self) -> None:
        readme_error = None
        price_error = None
        try:
            if not GUIDE_PATH.exists():
                raise FileNotFoundError(f"{GUIDE_FILENAME} not found at {GUIDE_PATH}")
            self.potions = parse_readme_to_potions(GUIDE_PATH)
        except Exception as exc:
            readme_error = str(exc)
            self.potions = {}

        try:
            self.prices = load_prices(PRICES_PATH)
        except Exception as exc:
            price_error = str(exc)
            self.prices = {}

        self.ing_lookup = {
            normalize_name(ing): ing
            for p in self.potions.values()
            for ing in p.ingredients
        }

        ing_list = sorted({ing for p in self.potions.values() for ing in p.ingredients})
        self._populate_inventory_inputs(ing_list)
        self._populate_library_tree()

        status_parts = []
        if self.potions:
            status_parts.append(f"Loaded {len(self.potions)} potions")
        else:
            status_parts.append("No potions loaded")
        status_parts.append(f"prices {'found' if self.prices else 'not found'}")
        self.status_var.set(" • ".join(status_parts))

        if readme_error:
            messagebox.showwarning("Guide not loaded", f"Could not load {GUIDE_FILENAME}: {readme_error}")
        if price_error:
            messagebox.showwarning("Prices not loaded", f"Could not load prices.json: {price_error}")

        self.on_compute()

    def _populate_library_tree(self) -> None:
        if not self.tree_all:
            return
        self.library_rows = []
        for name, potion in sorted(self.potions.items()):
            price = self.price_for_potion(potion)
            price_display = f"{price:.2f}" if isinstance(price, (int, float)) else ""
            self.library_rows.append({"name": name, "price": price_display})
        self.filter_library_tree()

    # ----------------- inventory -----------------
    def _populate_inventory_inputs(self, ingredients: List[str]) -> None:
        for child in self.inv_scrollable.winfo_children():
            child.destroy()
        self.inv_entries.clear()
        self.inv_pairs.clear()
        self.inv_order = ingredients

        vcmd = (self.register(self._validate_nonneg), "%P")
        for ing in ingredients:
            pair = ttk.Frame(self.inv_scrollable, style="App.TFrame")
            ttk.Label(pair, text=ing, width=22, anchor="w").pack(side="left", padx=(0, 6))
            spin = ttk.Spinbox(
                pair,
                from_=0,
                to=999,
                width=6,
                validate="key",
                validatecommand=vcmd,
                command=self.on_inventory_change,
            )
            spin.set("0")
            spin.pack(side="left")
            spin.bind("<KeyRelease>", self.on_inventory_change)
            spin.bind("<FocusOut>", self.on_inventory_change)
            self.inv_entries[ing] = spin
            self.inv_pairs[ing] = pair

        self._layout_inventory_grid()

    def _visible_ingredients(self) -> List[str]:
        query = self.inventory_filter_var.get().strip().lower()
        if not query:
            return list(self.inv_order)
        return [ing for ing in self.inv_order if query in ing.lower()]

    def _layout_inventory_grid(self, cols: int | None = None) -> None:
        visible = self._visible_ingredients()
        if cols is None:
            width = max(1, self.inv_canvas.winfo_width())
            cols = max(1, min(3, width // 260))

        if cols != self.inv_cols:
            self.inv_cols = cols

        for frame in self.inv_pairs.values():
            frame.grid_forget()

        for idx, ing in enumerate(visible):
            r, c = divmod(idx, cols)
            self.inv_pairs[ing].grid(row=r, column=c, sticky="ew", padx=4, pady=2)

        for c in range(cols):
            self.inv_scrollable.columnconfigure(c, weight=1, uniform="invcols")

        self._update_inventory_scrollregion()

    def _update_inventory_scrollregion(self, _event=None) -> None:
        try:
            self.inv_canvas.itemconfigure(self.inv_window, width=self.inv_canvas.winfo_width())
        except Exception:
            pass
        self.inv_canvas.configure(scrollregion=self.inv_canvas.bbox("all"))

    def on_inventory_filter(self, _event=None) -> None:
        self._layout_inventory_grid()

    def on_inventory_resize(self, event) -> None:
        width = event.width if event else self.inv_canvas.winfo_width()
        try:
            self.inv_canvas.itemconfigure(self.inv_window, width=width)
        except Exception:
            pass
        cols = max(1, min(3, width // 260))
        if cols != self.inv_cols:
            self._layout_inventory_grid(cols)
        else:
            self._update_inventory_scrollregion()

    def _validate_nonneg(self, value: str) -> bool:
        return value == "" or value.isdigit()

    def get_inventory(self) -> Dict[str, int]:
        inventory: Dict[str, int] = {}
        for ing, entry in self.inv_entries.items():
            raw = entry.get().strip()
            if not raw:
                continue
            try:
                qty = int(raw)
            except ValueError:
                qty = 0
            if qty > 0:
                inventory[ing] = qty
        return inventory

    def on_inventory_change(self, _event=None) -> None:
        if self._inv_debounce_after:
            self.after_cancel(self._inv_debounce_after)
        self._inv_debounce_after = self.after(AUTO_RECOMPUTE_DELAY, self._maybe_auto_recompute)

    def _maybe_auto_recompute(self) -> None:
        self._inv_debounce_after = None
        if self.auto_recompute_var.get():
            self.on_compute()

    # ----------------- plan & shopping -----------------
    def update_plan_button_state(self) -> None:
        qty_str = self.plan_qty_var.get().strip()
        has_qty = qty_str.isdigit() and int(qty_str) > 0
        enable = bool(self.last_selected and self.last_selected in self.potions and has_qty)
        if self.add_to_plan_btn:
            self.add_to_plan_btn.configure(state="normal" if enable else "disabled")

    def refresh_plan_outputs(self) -> None:
        if self.tree_plan:
            for item in self.tree_plan.get_children():
                self.tree_plan.delete(item)

            total_value = 0.0
            total_brews = 0
            for name in sorted(self.plan.keys()):
                qty = self.plan[name]
                total_brews += qty
                pot = self.potions.get(name)
                if not pot:
                    continue
                price = self.price_for_potion(pot)
                plan_val = (price * qty) if price is not None else None
                if plan_val is not None:
                    total_value += plan_val
                val_display = f"{plan_val:.2f}" if plan_val is not None else ""
                self.tree_plan.insert("", "end", iid=name, values=(name, qty, val_display))

            self.plan_footer_var.set(
                f"Total brews: {total_brews} • Total priced value: {total_value:.2f}"
            )

        self.render_shopping_list()

    def render_shopping_list(self) -> None:
        if not self.shop_tree:
            return

        for item in self.shop_tree.get_children():
            self.shop_tree.delete(item)

        inventory = self.get_inventory()
        required: Dict[str, int] = {}

        for name, qty in self.plan.items():
            pot = self.potions.get(name)
            if not pot:
                continue
            for ing, need in pot.ingredients.items():
                required[ing] = required.get(ing, 0) + need * qty

        relevant_inventory = {k for k, v in inventory.items() if v > 0}
        all_ings = sorted(set(required.keys()) | relevant_inventory)

        if not all_ings:
            self.shop_tree.insert(
                "",
                "end",
                values=("", "", "", "", ""),
            )
            return

        for ing in all_ings:
            need = required.get(ing, 0)
            have = inventory.get(ing, 0)
            buy = max(0, need - have)
            sell = max(0, have - need)
            tags = []
            if buy > 0:
                tags.append("buy")
            if sell > 0:
                tags.append("sell")
            self.shop_tree.insert(
                "",
                "end",
                iid=f"shop-{ing}",
                values=(ing, need, have, buy, sell),
                tags=tags,
            )

    def on_edit_plan_quantity(self, _event=None) -> None:
        if not self.tree_plan:
            return
        selection = self.tree_plan.selection()
        if not selection:
            return
        name = selection[0]
        current = self.plan.get(name, 0)
        new_qty = simpledialog.askinteger(
            "Edit quantity", f"Set brews for {name}:", parent=self, initialvalue=current, minvalue=0
        )
        if new_qty is None:
            return
        if new_qty <= 0:
            self.plan.pop(name, None)
        else:
            self.plan[name] = new_qty
        self.refresh_plan_outputs()
        self.update_plan_button_state()

    def on_plan_context_menu(self, event) -> None:
        selection = self.tree_plan.identify_row(event.y)
        if selection:
            self.tree_plan.selection_set(selection)
        try:
            self.plan_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.plan_menu.grab_release()

    def on_reset_all(self) -> None:
        if self._inv_debounce_after:
            self.after_cancel(self._inv_debounce_after)
            self._inv_debounce_after = None

        for spin in self.inv_entries.values():
            spin.set("0")

        self.plan.clear()
        if self.plan_selected_label:
            self.plan_selected_label.config(text="No potion selected")
        self.refresh_plan_outputs()
        self.on_compute()

    def on_add_to_plan(self) -> None:
        qty_str = self.plan_qty_var.get().strip()
        try:
            qty = int(qty_str)
        except ValueError:
            qty = 0
        if qty <= 0:
            return

        name = self.last_selected
        if (not name or name not in self.potions) and self.tree and self.tree.selection():
            name = self.tree.selection()[0]
        if (not name or name not in self.potions) and self.tree_all and self.tree_all.selection():
            name = self.tree_all.selection()[0]
        if not name or name not in self.potions:
            if self.plan_selected_label:
                self.plan_selected_label.config(text="Select a potion first")
            return

        self.last_selected = name
        if self.plan_selected_label:
            self.plan_selected_label.config(text=f"Selected: {name}")

        self.plan[name] = self.plan.get(name, 0) + qty
        self.refresh_plan_outputs()
        self.update_plan_button_state()

    def on_remove_from_plan(self, _event=None) -> None:
        targets: List[str] = []
        if self.tree_plan and self.tree_plan.selection():
            targets.extend(self.tree_plan.selection())
        elif self.last_selected and self.last_selected in self.plan:
            targets.append(self.last_selected)

        changed = False
        for name in targets:
            if name in self.plan:
                self.plan.pop(name, None)
                changed = True

        if changed:
            self.refresh_plan_outputs()
        self.update_plan_button_state()

    def on_clear_plan(self) -> None:
        self.plan.clear()
        self.refresh_plan_outputs()
        self.update_plan_button_state()

    # ----------------- craftable & library -----------------
    def price_for_potion(self, potion) -> float | None:
        price_info = self.prices.get(normalize_name(potion.name), {})
        if not price_info:
            return None
        if "Henry's" in price_info:
            return price_info["Henry's"]
        if len(price_info) == 1:
            return next(iter(price_info.values()))
        return None

    def on_compute(self) -> None:
        if not self.potions:
            self.status_var.set("No potion data loaded")
            return

        inventory = self.get_inventory()
        craftable = compute_max_brews(self.potions, inventory)

        self.craftable_rows = []
        total_value = 0.0
        for name in sorted(craftable.keys()):
            brews = craftable[name]
            pot = self.potions[name]
            price = self.price_for_potion(pot)
            price_display = f"{price:.2f}" if isinstance(price, (int, float)) else ""
            total_val = price * brews if price is not None else None
            total_display = f"{total_val:.2f}" if total_val is not None else ""
            if total_val is not None:
                total_value += total_val
            self.craftable_rows.append(
                {
                    "name": name,
                    "brews": brews,
                    "price": price_display,
                    "total": total_display,
                }
            )

        self.filter_craftable_tree()

        if craftable:
            self.status_var.set(
                f"{len(craftable)} craftable potions • total craftable value {total_value:.2f}"
            )
        else:
            self.status_var.set("No craftable potions with current inventory")

        self.refresh_plan_outputs()

    def filter_craftable_tree(self) -> None:
        if not self.tree:
            return
        search = self.craftable_search_var.get().strip().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.craftable_rows:
            name = str(row["name"])
            if search and search not in name.lower():
                continue
            self.tree.insert(
                "",
                "end",
                iid=name,
                values=(name, row.get("brews", ""), row.get("price", ""), row.get("total", "")),
            )
        self._reapply_sort(self.tree, "brew")

    def filter_library_tree(self) -> None:
        if not self.tree_all:
            return
        search = self.library_search_var.get().strip().lower()
        for item in self.tree_all.get_children():
            self.tree_all.delete(item)
        for row in self.library_rows:
            name = row["name"]
            if search and search not in name.lower():
                continue
            self.tree_all.insert("", "end", iid=name, values=(name, row.get("price", "")))
        self._reapply_sort(self.tree_all, "lib")

    def on_sort_craftable(self, _event=None) -> None:
        col_map = {"Name": "name", "Max brews": "brews", "Price": "price", "Total value": "total"}
        column = col_map.get(self.craft_sort_var.get())
        if column and self.tree:
            self.sort_dir[f"brew:{column}"] = False
            self.sort_tree(self.tree, column, "brew")

    def on_sort_library(self, _event=None) -> None:
        col_map = {"Name": "name", "Price": "price"}
        column = col_map.get(self.library_sort_var.get())
        if column and self.tree_all:
            self.sort_dir[f"lib:{column}"] = False
            self.sort_tree(self.tree_all, column, "lib")

    def sort_tree(self, tree: ttk.Treeview, column: str, key_prefix: str, reverse: bool | None = None) -> None:
        dir_key = f"{key_prefix}:{column}"
        if reverse is None:
            reverse = not self.sort_dir.get(dir_key, False)
        self.sort_dir[dir_key] = reverse
        self.active_sort[key_prefix] = (column, reverse)

        items = list(tree.get_children())

        def sort_key(item_id: str):
            val = tree.set(item_id, column)
            if column in ("brews", "price", "total", "value", "need", "have", "buy", "sell"):
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return float("-inf") if reverse else float("inf")
            return val.lower()

        items.sort(key=sort_key, reverse=reverse)
        for idx, iid in enumerate(items):
            tree.move(iid, "", idx)

    def _reapply_sort(self, tree: ttk.Treeview, key_prefix: str) -> None:
        if key_prefix in self.active_sort:
            col, reverse = self.active_sort[key_prefix]
            self.sort_tree(tree, col, key_prefix, reverse=reverse)

    def on_select(self, _event=None) -> None:
        if not self.tree:
            return
        selection = self.tree.selection()
        if not selection:
            return
        name = selection[0]
        self.last_selected = name
        if self.plan_selected_label:
            self.plan_selected_label.config(text=f"Selected: {name}")
        potion = self.potions.get(name)
        if not potion:
            return
        brews = self.tree.set(name, "brews") or None
        if self.notebook:
            self.notebook.select(0)
        self.render_potion_detail(self.detail_text, potion, brews)
        self.update_plan_button_state()

    def on_select_library(self, _event=None) -> None:
        if not self.tree_all:
            return
        selection = self.tree_all.selection()
        if not selection:
            return
        name = selection[0]
        self.last_selected = name
        if self.plan_selected_label:
            self.plan_selected_label.config(text=f"Selected: {name}")
        potion = self.potions.get(name)
        if not potion:
            return
        if self.notebook:
            self.notebook.select(self.library_tab)
        self.render_potion_detail(self.detail_text, potion, brews=None)
        self.update_plan_button_state()

    # ----------------- details & markdown -----------------
    def render_potion_detail(self, widget: tk.Text | None, potion, brews: str | None) -> None:
        if widget is None:
            return
        price_info = self.prices.get(normalize_name(potion.name), {})

        lines: List[str] = []
        lines.append(f"**{potion.name}** (No. {potion.id if potion.id is not None else '?'})")
        lines.append(f"**Liquid:** {potion.liquid}")
        lines.append("**Ingredients per brew:**")
        for ing, qty in potion.ingredients.items():
            lines.append(f"  - {qty} x {ing}")
        if brews is not None:
            lines.append(f"**Max brews with current inventory:** {brews}")

        lines.append("")
        lines.append("**Quantity per brew (Omricon guide):**")
        if potion.quantity_table:
            lines.extend("  " + row for row in potion.quantity_table)
        else:
            lines.append("  (not provided)")

        lines.append("")
        lines.append("**Effects by quality (Omricon guide):**")
        if potion.effects_table:
            lines.extend("  " + row for row in potion.effects_table)
        else:
            lines.append("  (not provided)")

        lines.append("")
        lines.append("**Prices per bottle (fill prices.json to enable):**")
        if price_info:
            for tier in ["Weak", "Standard", "Strong", "Henry's"]:
                if tier in price_info:
                    lines.append(f"  {tier}: {price_info[tier]}")
        else:
            lines.append("  (no prices configured)")

        lines.append("")
        lines.append("**Instructions:**")
        for variant, steps in potion.instructions.items():
            lines.append(f"  **[{variant}]**")
            lines.extend("   " + s for s in steps)
            lines.append("")

        if potion.notes:
            lines.append("**Notes:**")
            lines.extend("  " + n for n in potion.notes)

        self.write_markdown_lines(widget, lines)

    def write_markdown_lines(self, widget: tk.Text, lines: List[str]) -> None:
        self._ensure_tags(widget)
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        for line in lines:
            self._insert_markdown_line(widget, line)
            widget.insert("end", "\n")
        widget.configure(state="disabled")

    def _ensure_tags(self, widget: tk.Text) -> None:
        widget.tag_configure("bold", font=("Segoe UI Semibold", 11))
        widget.tag_configure("italic", font=("Segoe UI", 11, "italic"))
        widget.tag_configure("code", font=("Consolas", 10))
        widget.tag_configure("heading", font=("Segoe UI Semibold", 13, "underline"))
        widget.tag_configure("table", font=("Consolas", 10))

    def _insert_markdown_line(self, widget: tk.Text, line: str) -> None:
        stripped = line.lstrip()
        if stripped.startswith("|"):
            widget.insert("end", line, ["table"])
            return
        m = re.match(r"^(#+)\s*(.*)$", line)
        if m:
            text = m.group(2)
            self._insert_inline(widget, text, base_tags=["heading"])
            return
        self._insert_inline(widget, line, base_tags=[])

    def _insert_inline(self, widget: tk.Text, text: str, base_tags: List[str]) -> None:
        pattern = re.compile(
            r"(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*]+\*|_[^_]+_|!\[[^\]]*\]\([^)]+\)|\[[^\]]+\]\([^)]+\))"
        )
        pos = 0
        for m in pattern.finditer(text):
            start, end = m.span()
            if start > pos:
                widget.insert("end", text[pos:start], base_tags)
            token = m.group(0)
            tags = list(base_tags)
            content = token
            if token.startswith("**") or token.startswith("__"):
                content = token[2:-2]
                tags.append("bold")
            elif token.startswith("`"):
                content = token[1:-1]
                tags.append("code")
            elif token.startswith("*") or token.startswith("_"):
                content = token[1:-1]
                tags.append("italic")
            elif token.startswith("!"):
                content = ""
            elif token.startswith("["):
                content = re.sub(r"^\[([^\]]+)\]\([^)]+\)$", r"\1", token)
            widget.insert("end", content, tags)
            pos = end
        if pos < len(text):
            widget.insert("end", text[pos:], base_tags)

    # ----------------- layout helpers -----------------
    def reset_layout(self) -> None:
        try:
            self.main_panes.sash_place(0, int(self.winfo_width() * 0.42), 0)
        except Exception:
            pass

    def on_auto_toggle(self) -> None:
        if self.auto_recompute_var.get():
            self.status_var.set("Auto-recompute enabled")
            self.on_compute()
        else:
            self.status_var.set("Auto-recompute paused")

    def open_github(self) -> None:
        try:
            webbrowser.open(UPSTREAM_URL)
        except Exception:
            messagebox.showinfo("Open GitHub", f"Visit: {UPSTREAM_URL}")


def main() -> None:
    app = PotionGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
