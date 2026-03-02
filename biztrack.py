"""
BizTrack - Business Sales, Expenses & Cash Management
Run with: python business_tracker.py
No external libraries required — uses only Python built-ins (tkinter + sqlite3)
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import sqlite3
import json
from datetime import datetime, date
import os

# ─────────────────────────────────────────
#  DATABASE SETUP
# ─────────────────────────────────────────
DB_FILE = "biztrack.db"

def migrate_from_old_db(old_path):
    """Copy data from an old biztrack.db into the current one."""
    import shutil
    if not os.path.exists(old_path):
        return 0
    try:
        old = sqlite3.connect(old_path)
        old.row_factory = sqlite3.Row
        new = get_db()
        copied = 0

        # Migrate products
        for r in old.execute("SELECT name,unit_price,description,created_at FROM products").fetchall():
            try:
                new.execute("INSERT INTO products (name,unit_price,description,created_at) VALUES (?,?,?,?)",
                    (r[0],r[1],r[2],r[3]))
                copied += 1
            except: pass

        # Migrate transactions
        for r in old.execute("SELECT date,product_name,quantity,unit_price,total,payment_mode,notes,created_at FROM transactions").fetchall():
            try:
                new.execute("INSERT INTO transactions (date,product_name,quantity,unit_price,total,payment_mode,notes,created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7]))
                copied += 1
            except: pass

        # Migrate expenses
        for r in old.execute("SELECT date,category,description,amount,payment_mode,notes,created_at FROM expenses").fetchall():
            try:
                new.execute("INSERT INTO expenses (date,category,description,amount,payment_mode,notes,created_at) VALUES (?,?,?,?,?,?,?)",
                    (r[0],r[1],r[2],r[3],r[4],r[5],r[6]))
                copied += 1
            except: pass

        # Migrate cash_ledger
        for r in old.execute("SELECT date,type,payment_mode,amount,description,created_at FROM cash_ledger").fetchall():
            try:
                new.execute("INSERT INTO cash_ledger (date,type,payment_mode,amount,description,created_at) VALUES (?,?,?,?,?,?)",
                    (r[0],r[1],r[2],r[3],r[4],r[5]))
                copied += 1
            except: pass

        new.commit()
        new.close()
        old.close()
        return copied
    except Exception as e:
        return -1

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit_price REAL NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            total REAL NOT NULL,
            payment_mode TEXT NOT NULL,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_mode TEXT NOT NULL,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS cash_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            payment_mode TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()
    conn.close()

# ─────────────────────────────────────────
#  THEME / COLORS
# ─────────────────────────────────────────
C = {
    "bg":        "#0E1117",
    "surface":   "#161B25",
    "surface2":  "#1C2333",
    "surface3":  "#222B3D",
    "border":    "#2A3548",
    "text":      "#E6EDF4",
    "text2":     "#8B95AB",
    "text3":     "#515D78",
    "accent":    "#4F8EF7",
    "accent_dk": "#3A7DE8",
    "green":     "#34D399",
    "green_bg":  "#0D2B21",
    "red":       "#F87171",
    "red_bg":    "#2B0D0D",
    "yellow":    "#FBBF24",
    "yellow_bg": "#2B1F0A",
    "purple":    "#A78BFA",
    "cash":      "#34D399",
    "gcash":     "#4F8EF7",
    "bank":      "#FBBF24",
    "sidebar":   "#0B0F18",
}

PAYMENT_MODES = ["Cash", "GCash", "Bank Transfer"]
EXPENSE_CATEGORIES = [
    "Supplies", "Utilities", "Rent", "Salaries", "Maintenance",
    "Marketing", "Transport", "Food", "Office", "Miscellaneous"
]

# ─────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────
def fmt_money(v):
    try:
        return f"₱{float(v):,.2f}"
    except:
        return "₱0.00"

def today_str():
    return date.today().strftime("%Y-%m-%d")

def get_balance(mode=None):
    conn = get_db()
    c = conn.cursor()
    modes = [mode] if mode else PAYMENT_MODES
    total = 0.0
    for m in modes:
        # Cash in from sales
        c.execute("SELECT COALESCE(SUM(total),0) FROM transactions WHERE payment_mode=?", (m,))
        sales = c.fetchone()[0]
        # Cash in from petty cash deposits
        c.execute("SELECT COALESCE(SUM(amount),0) FROM cash_ledger WHERE payment_mode=? AND type='add'", (m,))
        adds = c.fetchone()[0]
        # Cash out from expenses
        c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE payment_mode=?", (m,))
        exp = c.fetchone()[0]
        # Cash out from withdrawals
        c.execute("SELECT COALESCE(SUM(amount),0) FROM cash_ledger WHERE payment_mode=? AND type='withdraw'", (m,))
        wds = c.fetchone()[0]
        total += sales + adds - exp - wds
    conn.close()
    return total

# ─────────────────────────────────────────
#  CUSTOM WIDGETS
# ─────────────────────────────────────────
class StyledEntry(tk.Entry):
    def __init__(self, parent, placeholder="", **kw):
        super().__init__(parent,
            bg=C["surface3"], fg=C["text"], insertbackground=C["text"],
            relief="flat", font=("Segoe UI", 10),
            highlightthickness=1, highlightbackground=C["border"],
            highlightcolor=C["accent"], **kw)
        self._ph = placeholder
        self._has_ph = False
        if placeholder:
            self._show_placeholder()
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

    def _show_placeholder(self):
        self.insert(0, self._ph)
        self.config(fg=C["text3"])
        self._has_ph = True

    def _on_focus_in(self, e):
        if self._has_ph:
            self.delete(0, "end")
            self.config(fg=C["text"])
            self._has_ph = False

    def _on_focus_out(self, e):
        if not self.get() and self._ph:
            self._show_placeholder()

    def get_value(self):
        if self._has_ph:
            return ""
        return self.get()


class StyledCombo(ttk.Combobox):
    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.configure(font=("Segoe UI", 10))


class SectionTitle(tk.Label):
    def __init__(self, parent, text, **kw):
        super().__init__(parent, text=text, bg=C["surface"],
            fg=C["text"], font=("Segoe UI", 12, "bold"), anchor="w", **kw)


class CardFrame(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C["surface"], relief="flat",
            highlightthickness=1, highlightbackground=C["border"], **kw)


class NavButton(tk.Label):
    def __init__(self, parent, text, icon, page_name, app, **kw):
        super().__init__(parent, text=f"  {icon}  {text}",
            bg=C["sidebar"], fg=C["text2"],
            font=("Segoe UI", 10), anchor="w",
            cursor="hand2", pady=8, padx=6, **kw)
        self.page_name = page_name
        self.app = app
        self.bind("<Button-1>", lambda e: self.app.show_page(page_name))
        self.bind("<Enter>", self._hover)
        self.bind("<Leave>", self._unhover)

    def _hover(self, e):
        if self.app.current_page != self.page_name:
            self.config(bg=C["surface2"], fg=C["text"])

    def _unhover(self, e):
        if self.app.current_page != self.page_name:
            self.config(bg=C["sidebar"], fg=C["text2"])

    def set_active(self, active):
        if active:
            self.config(bg=C["surface3"], fg=C["accent"])
        else:
            self.config(bg=C["sidebar"], fg=C["text2"])


# ─────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────
class BizTrackApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BizTrack — Business Manager")
        self.root.geometry("1200x750")
        self.root.configure(bg=C["bg"])
        self.root.minsize(1000, 650)

        init_db()
        self.current_page = "dashboard"
        self.nav_buttons = {}
        self.pages = {}

        self._build_ui()
        self.show_page("dashboard")

    # ─── BUILD UI ───────────────────────
    def _build_ui(self):
        # Outer layout
        self.sidebar = tk.Frame(self.root, bg=C["sidebar"], width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(self.root, bg=C["bg"])
        self.content.pack(side="left", fill="both", expand=True)

        self._build_sidebar()
        self._build_pages()

    def _build_sidebar(self):
        # Logo
        logo_frame = tk.Frame(self.sidebar, bg=C["sidebar"])
        logo_frame.pack(fill="x", padx=16, pady=(20, 10))
        tk.Label(logo_frame, text="Biz", bg=C["sidebar"], fg=C["accent"],
            font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(logo_frame, text="Track", bg=C["sidebar"], fg=C["text"],
            font=("Segoe UI", 18, "bold")).pack(side="left")

        tk.Frame(self.sidebar, bg=C["border"], height=1).pack(fill="x", padx=12, pady=8)

        nav_items = [
            ("Dashboard", "⊡", "dashboard"),
            ("Add Sale", "＋", "add_sale"),
            ("Add Expense", "▼", "add_expense"),
            ("Cash Manager", "◈", "cash_manager"),
            ("Products", "◧", "products"),
            ("Reports", "◫", "reports"),
            ("Daily Summary", "◉", "daily_summary"),
        ]
        for label, icon, page in nav_items:
            sections = {
                "dashboard": "OVERVIEW",
                "add_sale": "TRANSACTIONS",
                "add_expense": None,
                "cash_manager": None,
                "products": "MANAGEMENT",
                "reports": None,
            }
            if sections.get(page):
                tk.Frame(self.sidebar, bg=C["border"], height=1).pack(fill="x", padx=12, pady=(8,2))
                tk.Label(self.sidebar, text=sections[page], bg=C["sidebar"], fg=C["text3"],
                    font=("Segoe UI", 8, "bold"), anchor="w", padx=18).pack(fill="x")

            btn = NavButton(self.sidebar, label, icon, page, self)
            btn.pack(fill="x", padx=8, pady=1)
            self.nav_buttons[page] = btn

        # Version tag
        tk.Frame(self.sidebar, bg=C["sidebar"]).pack(fill="y", expand=True)
        tk.Button(self.sidebar, text="⤓ Import Old Data", bg=C["surface3"], fg=C["accent"],
            font=("Segoe UI", 9, "bold"), relief="flat", bd=0, padx=8, pady=6,
            cursor="hand2", command=self._import_old_data).pack(fill="x", padx=10, pady=(0,2))
        tk.Button(self.sidebar, text="⊠ Clear All Data", bg=C["surface3"], fg=C["red"],
            font=("Segoe UI", 9, "bold"), relief="flat", bd=0, padx=8, pady=6,
            cursor="hand2", command=self._clear_all_data).pack(fill="x", padx=10, pady=(0,4))
        tk.Label(self.sidebar, text="v1.1  •  BizTrack", bg=C["sidebar"],
            fg=C["text3"], font=("Segoe UI", 8)).pack(pady=(0,10))

    def _build_pages(self):
        for page_id in ["dashboard", "add_sale", "add_expense", "cash_manager", "products", "reports", "daily_summary"]:
            frame = tk.Frame(self.content, bg=C["bg"])
            frame.place(relwidth=1, relheight=1)
            frame.lower()
            self.pages[page_id] = frame

        self._build_dashboard(self.pages["dashboard"])
        self._build_add_sale(self.pages["add_sale"])
        self._build_add_expense(self.pages["add_expense"])
        self._build_cash_manager(self.pages["cash_manager"])
        self._build_products(self.pages["products"])
        self._build_reports(self.pages["reports"])
        self._build_daily_summary(self.pages["daily_summary"])

    def show_page(self, page_name):
        self.current_page = page_name
        for pid, frame in self.pages.items():
            if pid == page_name:
                frame.lift()
            else:
                frame.lower()
        for pid, btn in self.nav_buttons.items():
            btn.set_active(pid == page_name)
        # Refresh
        if page_name == "dashboard":
            self.refresh_dashboard()
        elif page_name == "reports":
            self.refresh_reports()
        elif page_name == "daily_summary":
            self.refresh_daily_summary()

    def _import_old_data(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select your old biztrack.db file",
            filetypes=[("SQLite Database", "*.db"), ("All files", "*.*")]
        )
        if not path:
            return
        if path == os.path.abspath(DB_FILE):
            messagebox.showwarning("Same File", "That is the current database — please select a different file.")
            return
        result = migrate_from_old_db(path)
        if result == -1:
            messagebox.showerror("Import Failed", "Could not read the selected file.\nMake sure it is a valid BizTrack database.")
        elif result == 0:
            messagebox.showinfo("Nothing Imported", "No data was found in the selected file.")
        else:
            messagebox.showinfo("Import Complete", f"Successfully imported {result} records from the old database!\n\nAll your previous data is now available.")
            self.refresh_dashboard()

    def _clear_all_data(self):
        answer = messagebox.askyesno(
            "Clear All Data",
            "⚠ WARNING: This will permanently delete ALL data:\n\n"
            "  • All sales transactions\n"
            "  • All expenses\n"
            "  • All cash ledger entries\n"
            "  • All products\n\n"
            "This CANNOT be undone. Are you sure?",
        )
        if not answer:
            return
        # Second confirmation
        answer2 = messagebox.askyesno(
            "Final Confirmation",
            "Last chance — delete everything permanently?"
        )
        if not answer2:
            return
        conn = get_db()
        conn.executescript("""
            DELETE FROM transactions;
            DELETE FROM expenses;
            DELETE FROM cash_ledger;
            DELETE FROM products;
        """)
        conn.commit()
        conn.close()
        messagebox.showinfo("Cleared", "All data has been deleted.")
        self.refresh_dashboard()

    # ─────────────────────────────────────
    #  PAGE: DASHBOARD
    # ─────────────────────────────────────
    def _build_dashboard(self, parent):
        self.dash_parent = parent
        self._render_dashboard()

    def _render_dashboard(self):
        # Fully destroy and rebuild the canvas + inner frame every time
        for w in self.dash_parent.winfo_children():
            w.destroy()

        canvas = tk.Canvas(self.dash_parent, bg=C["bg"], highlightthickness=0)
        scroll = tk.Scrollbar(self.dash_parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        self.dash_inner = tk.Frame(canvas, bg=C["bg"])
        self.dash_win = canvas.create_window((0, 0), window=self.dash_inner, anchor="nw")
        self.dash_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self.dash_win, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._fill_dashboard()

    def refresh_dashboard(self):
        self._render_dashboard()

    def _fill_dashboard(self):
        pad = 24
        # Header
        hdr = tk.Frame(self.dash_inner, bg=C["bg"])
        hdr.pack(fill="x", padx=pad, pady=(pad, 16))
        tk.Label(hdr, text="Dashboard", bg=C["bg"], fg=C["text"],
            font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(hdr, text=datetime.now().strftime("  ◦  %A, %B %d %Y"), bg=C["bg"],
            fg=C["text2"], font=("Segoe UI", 10)).pack(side="left")

        # Balance cards — always fresh from DB
        bal_frame = tk.Frame(self.dash_inner, bg=C["bg"])
        bal_frame.pack(fill="x", padx=pad, pady=(0, 16))
        for i in range(4):
            bal_frame.columnconfigure(i, weight=1, uniform="col")

        cards = [
            ("Total Balance", get_balance(),              C["accent"], "◈"),
            ("Cash",          get_balance("Cash"),        C["cash"],   "◯"),
            ("GCash",         get_balance("GCash"),       C["gcash"],  "◉"),
            ("Bank Transfer", get_balance("Bank Transfer"), C["bank"], "◑"),
        ]
        for i, (lbl, val, color, icon) in enumerate(cards):
            c = CardFrame(bal_frame)
            c.grid(row=0, column=i, padx=(0 if i == 0 else 6, 0), sticky="nsew")
            tk.Frame(c, bg=color, height=3).pack(fill="x")
            inner = tk.Frame(c, bg=C["surface"], padx=16, pady=14)
            inner.pack(fill="both", expand=True)
            tk.Label(inner, text=f"{icon} {lbl}", bg=C["surface"], fg=C["text2"],
                font=("Segoe UI", 9, "bold")).pack(anchor="w")
            tk.Label(inner, text=fmt_money(val), bg=C["surface"], fg=color,
                font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(4, 0))

        # Recent transactions + expenses — always fresh from DB
        twin = tk.Frame(self.dash_inner, bg=C["bg"])
        twin.pack(fill="both", expand=True, padx=pad, pady=(0, 16))
        twin.columnconfigure(0, weight=3)
        twin.columnconfigure(1, weight=2)

        # Recent sales
        lc = CardFrame(twin)
        lc.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        tk.Label(lc, text="  Recent Sales", bg=C["surface"], fg=C["text"],
            font=("Segoe UI", 11, "bold"), anchor="w", pady=10).pack(fill="x")
        tk.Frame(lc, bg=C["border"], height=1).pack(fill="x")
        tree = self._make_tree(lc, ("Date", "Product", "Qty", "Amount", "Mode"), heights=8)
        conn = get_db()
        for r in conn.execute("SELECT date,product_name,quantity,total,payment_mode FROM transactions ORDER BY id DESC LIMIT 10").fetchall():
            tree.insert("", "end", values=(r[0], r[1], r[2], fmt_money(r[3]), r[4]))

        # Recent expenses
        rc = CardFrame(twin)
        rc.grid(row=0, column=1, sticky="nsew")
        tk.Label(rc, text="  Recent Expenses", bg=C["surface"], fg=C["text"],
            font=("Segoe UI", 11, "bold"), anchor="w", pady=10).pack(fill="x")
        tk.Frame(rc, bg=C["border"], height=1).pack(fill="x")
        tree2 = self._make_tree(rc, ("Date", "Category", "Amount", "Mode"), heights=8)
        for r in conn.execute("SELECT date,category,amount,payment_mode FROM expenses ORDER BY id DESC LIMIT 10").fetchall():
            tree2.insert("", "end", values=(r[0], r[1], fmt_money(r[2]), r[3]))
        conn.close()

    # ─────────────────────────────────────
    #  PAGE: ADD SALE
    # ─────────────────────────────────────
    def _build_add_sale(self, parent):
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        scroll = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        inner = tk.Frame(canvas, bg=C["bg"])
        win = canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))

        pad = 24
        tk.Label(inner, text="Add Sale / Transaction", bg=C["bg"], fg=C["text"],
            font=("Segoe UI", 18, "bold"), anchor="w").pack(fill="x", padx=pad, pady=(pad,4))
        tk.Label(inner, text="Record a new sales transaction", bg=C["bg"], fg=C["text2"],
            font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=pad, pady=(0,16))

        card = CardFrame(inner)
        card.pack(fill="x", padx=pad, pady=(0,12))
        form = tk.Frame(card, bg=C["surface"], padx=20, pady=20)
        form.pack(fill="both")

        # Date row
        dr = tk.Frame(form, bg=C["surface"])
        dr.pack(fill="x", pady=(0,10))
        tk.Label(dr, text="Date", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI", 9, "bold")).pack(anchor="w")
        date_row = tk.Frame(dr, bg=C["surface"])
        date_row.pack(fill="x", pady=(4,0))
        self.sale_use_today = tk.BooleanVar(value=True)
        tk.Checkbutton(date_row, text="Use today's date", variable=self.sale_use_today,
            bg=C["surface"], fg=C["text2"], selectcolor=C["surface3"],
            activebackground=C["surface"], font=("Segoe UI",10),
            command=self._toggle_sale_date).pack(side="left")
        self.sale_date_entry = StyledEntry(date_row, placeholder="YYYY-MM-DD", width=14)
        self.sale_date_entry.pack(side="left", padx=(10,0), ipady=5)
        self.sale_date_entry.config(state="disabled", disabledbackground=C["surface2"],
            disabledforeground=C["text3"])

        # Product row
        pr = tk.Frame(form, bg=C["surface"])
        pr.pack(fill="x", pady=(0,10))
        tk.Label(pr, text="Product / Item Name", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI", 9, "bold")).pack(anchor="w")
        prod_row = tk.Frame(pr, bg=C["surface"])
        prod_row.pack(fill="x", pady=(4,0))
        self.sale_product_var = tk.StringVar()
        self.sale_product_combo = StyledCombo(prod_row, textvariable=self.sale_product_var, width=35)
        self.sale_product_combo.pack(side="left", ipady=5)
        self.sale_product_combo.bind("<<ComboboxSelected>>", self._fill_product_price)
        tk.Button(prod_row, text="⟳ Load Products", bg=C["surface3"], fg=C["accent"],
            font=("Segoe UI",9), relief="flat", bd=0, padx=8, cursor="hand2",
            command=self._load_sale_products).pack(side="left", padx=(8,0), ipady=4)
        self._load_sale_products()

        # Qty / Price / Total
        nums = tk.Frame(form, bg=C["surface"])
        nums.pack(fill="x", pady=(0,10))
        nums.columnconfigure(0, weight=1)
        nums.columnconfigure(1, weight=1)
        nums.columnconfigure(2, weight=1)

        lf = tk.Frame(nums, bg=C["surface"])
        lf.grid(row=0, column=0, padx=(0,8), sticky="nsew")
        tk.Label(lf, text="Quantity", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.sale_qty = StyledEntry(lf, placeholder="1")
        self.sale_qty.pack(fill="x", pady=(4,0), ipady=5)
        self.sale_qty.bind("<KeyRelease>", self._calc_sale_total)

        mf = tk.Frame(nums, bg=C["surface"])
        mf.grid(row=0, column=1, padx=(0,8), sticky="nsew")
        tk.Label(mf, text="Unit Price (₱)", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.sale_price = StyledEntry(mf, placeholder="0.00")
        self.sale_price.pack(fill="x", pady=(4,0), ipady=5)
        self.sale_price.bind("<KeyRelease>", self._calc_sale_total)

        rf = tk.Frame(nums, bg=C["surface"])
        rf.grid(row=0, column=2, sticky="nsew")
        tk.Label(rf, text="Total Amount", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.sale_total_label = tk.Label(rf, text="₱0.00", bg=C["surface3"],
            fg=C["green"], font=("Segoe UI", 14, "bold"),
            relief="flat", highlightthickness=1, highlightbackground=C["border"],
            anchor="w", padx=12)
        self.sale_total_label.pack(fill="x", pady=(4,0), ipady=8)

        # Payment mode
        pf = tk.Frame(form, bg=C["surface"])
        pf.pack(fill="x", pady=(0,10))
        tk.Label(pf, text="Payment Mode", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.sale_mode_var = tk.StringVar(value="Cash")
        prow = tk.Frame(pf, bg=C["surface"])
        prow.pack(fill="x", pady=(6,0))
        self.sale_mode_btns = {}
        for m, color in [("Cash", C["cash"]), ("GCash", C["gcash"]), ("Bank Transfer", C["bank"])]:
            btn = tk.Label(prow, text=m, bg=C["surface3"], fg=C["text2"],
                font=("Segoe UI", 10, "bold"), padx=20, pady=8, cursor="hand2",
                relief="flat", highlightthickness=1, highlightbackground=C["border"])
            btn.pack(side="left", padx=(0,8))
            btn.bind("<Button-1>", lambda e, mode=m, b=btn, clr=color: self._select_mode(
                mode, self.sale_mode_var, self.sale_mode_btns))
            self.sale_mode_btns[m] = (btn, color)
        self._select_mode("Cash", self.sale_mode_var, self.sale_mode_btns)

        # Notes
        nf = tk.Frame(form, bg=C["surface"])
        nf.pack(fill="x", pady=(0,14))
        tk.Label(nf, text="Notes (optional)", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.sale_notes = tk.Text(nf, bg=C["surface3"], fg=C["text"],
            font=("Segoe UI", 10), relief="flat", height=2,
            highlightthickness=1, highlightbackground=C["border"], insertbackground=C["text"])
        self.sale_notes.pack(fill="x", pady=(4,0))

        tk.Button(form, text="  ＋  Record Sale", bg=C["accent"], fg="white",
            font=("Segoe UI", 11, "bold"), relief="flat", bd=0, padx=24, pady=10,
            cursor="hand2", activebackground=C["accent_dk"], activeforeground="white",
            command=self.save_sale).pack(anchor="w")

        # Sales table
        tcard = CardFrame(inner)
        tcard.pack(fill="both", expand=True, padx=pad, pady=(0,24))
        hdr_row = tk.Frame(tcard, bg=C["surface"])
        hdr_row.pack(fill="x")
        tk.Label(hdr_row, text="  Sales History", bg=C["surface"], fg=C["text"],
            font=("Segoe UI", 11, "bold"), anchor="w", pady=10).pack(side="left", fill="x", expand=True)
        tk.Button(hdr_row, text="⊠  Delete Selected", bg=C["red_bg"], fg=C["red"],
            font=("Segoe UI", 9, "bold"), relief="flat", bd=0, padx=12, pady=5,
            cursor="hand2", command=self.delete_sale).pack(side="right", padx=10, pady=6)
        tk.Frame(tcard, bg=C["border"], height=1).pack(fill="x")

        cols = ("ID","Date","Product","Qty","Unit Price","Total","Mode","Notes")
        self.sale_tree = self._make_tree(tcard, cols, heights=12)
        self.sale_tree_ref = self.sale_tree
        self._refresh_sale_table()

    def _toggle_sale_date(self):
        if self.sale_use_today.get():
            self.sale_date_entry.config(state="disabled")
        else:
            self.sale_date_entry.config(state="normal")
            if self.sale_date_entry._has_ph:
                pass

    def _load_sale_products(self):
        conn = get_db()
        prods = conn.execute("SELECT name, unit_price FROM products ORDER BY name").fetchall()
        conn.close()
        names = [f"{r[0]} (₱{r[1]:,.2f})" for r in prods]
        self._prod_map = {f"{r[0]} (₱{r[1]:,.2f})": r[1] for r in prods}
        self.sale_product_combo["values"] = names

    def _fill_product_price(self, e):
        sel = self.sale_product_var.get()
        if sel in self._prod_map:
            price = self._prod_map[sel]
            self.sale_price.delete(0, "end")
            self.sale_price._has_ph = False
            self.sale_price.config(fg=C["text"])
            self.sale_price.insert(0, str(price))
            # Extract product name without price
            name = sel.split(" (₱")[0]
            self.sale_product_combo.set(name)
            self._calc_sale_total()

    def _calc_sale_total(self, e=None):
        try:
            qty = float(self.sale_qty.get_value() or 1)
            price = float(self.sale_price.get_value() or 0)
            total = qty * price
            self.sale_total_label.config(text=fmt_money(total))
        except:
            self.sale_total_label.config(text="₱0.00")

    def _select_mode(self, mode, var, btns):
        var.set(mode)
        for m, (btn, color) in btns.items():
            if m == mode:
                btn.config(bg=color, fg=C["bg"],
                    highlightbackground=color)
            else:
                btn.config(bg=C["surface3"], fg=C["text2"],
                    highlightbackground=C["border"])

    def save_sale(self):
        prod = self.sale_product_var.get().strip()
        qty_str = self.sale_qty.get_value()
        price_str = self.sale_price.get_value()
        mode = self.sale_mode_var.get()
        notes = self.sale_notes.get("1.0", "end").strip()

        if not prod:
            messagebox.showerror("Error", "Product name is required."); return
        try:
            qty = float(qty_str)
            price = float(price_str)
        except:
            messagebox.showerror("Error", "Quantity and price must be numbers."); return

        if self.sale_use_today.get():
            trans_date = today_str()
        else:
            trans_date = self.sale_date_entry.get_value().strip()
            if not trans_date:
                trans_date = today_str()

        total = qty * price
        conn = get_db()
        conn.execute("INSERT INTO transactions (date,product_name,quantity,unit_price,total,payment_mode,notes) VALUES (?,?,?,?,?,?,?)",
            (trans_date, prod, qty, price, total, mode, notes))
        conn.commit()
        conn.close()

        messagebox.showinfo("Success", f"Sale recorded!\n{prod} × {qty} = {fmt_money(total)}")
        self.sale_product_var.set("")
        self.sale_qty.delete(0,"end"); self.sale_qty._show_placeholder()
        self.sale_price.delete(0,"end"); self.sale_price._show_placeholder()
        self.sale_total_label.config(text="₱0.00")
        self.sale_notes.delete("1.0","end")
        self._refresh_sale_table()

    def delete_sale(self):
        sel = self.sale_tree_ref.selection()
        if not sel:
            messagebox.showwarning("Warning", "Select a transaction to delete."); return
        item = self.sale_tree_ref.item(sel[0])
        sid = item["values"][0]
        prod = item["values"][2]
        total = item["values"][5]
        if messagebox.askyesno("Confirm Delete", f"Delete sale:\n{prod}  —  {total}\n\nThis cannot be undone."):
            conn = get_db()
            conn.execute("DELETE FROM transactions WHERE id=?", (sid,))
            conn.commit()
            conn.close()
            self._refresh_sale_table()
            self.refresh_dashboard()
            messagebox.showinfo("Deleted", "Transaction deleted.")

    def _refresh_sale_table(self):
        for row in self.sale_tree_ref.get_children():
            self.sale_tree_ref.delete(row)
        conn = get_db()
        rows = conn.execute("SELECT id,date,product_name,quantity,unit_price,total,payment_mode,notes FROM transactions ORDER BY id DESC").fetchall()
        conn.close()
        for r in rows:
            self.sale_tree_ref.insert("", "end", values=(
                r[0], r[1], r[2], r[3], fmt_money(r[4]), fmt_money(r[5]), r[6], r[7] or ""))

    # ─────────────────────────────────────
    #  PAGE: ADD EXPENSE
    # ─────────────────────────────────────
    def _build_add_expense(self, parent):
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        scroll = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        inner = tk.Frame(canvas, bg=C["bg"])
        win = canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))

        pad = 24
        tk.Label(inner, text="Add Expense", bg=C["bg"], fg=C["text"],
            font=("Segoe UI", 18, "bold"), anchor="w").pack(fill="x", padx=pad, pady=(pad,4))
        tk.Label(inner, text="Log a business expense", bg=C["bg"], fg=C["text2"],
            font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=pad, pady=(0,16))

        card = CardFrame(inner)
        card.pack(fill="x", padx=pad, pady=(0,12))
        form = tk.Frame(card, bg=C["surface"], padx=20, pady=20)
        form.pack(fill="both")

        # Date
        dr = tk.Frame(form, bg=C["surface"])
        dr.pack(fill="x", pady=(0,10))
        tk.Label(dr, text="Date", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI", 9, "bold")).pack(anchor="w")
        drow = tk.Frame(dr, bg=C["surface"])
        drow.pack(fill="x", pady=(4,0))
        self.exp_use_today = tk.BooleanVar(value=True)
        tk.Checkbutton(drow, text="Use today's date", variable=self.exp_use_today,
            bg=C["surface"], fg=C["text2"], selectcolor=C["surface3"],
            activebackground=C["surface"], font=("Segoe UI",10),
            command=lambda: self.exp_date_entry.config(
                state="normal" if not self.exp_use_today.get() else "disabled")).pack(side="left")
        self.exp_date_entry = StyledEntry(drow, placeholder="YYYY-MM-DD", width=14)
        self.exp_date_entry.pack(side="left", padx=(10,0), ipady=5)
        self.exp_date_entry.config(state="disabled", disabledbackground=C["surface2"],
            disabledforeground=C["text3"])

        # Category + Description row
        row1 = tk.Frame(form, bg=C["surface"])
        row1.pack(fill="x", pady=(0,10))
        row1.columnconfigure(0, weight=1)
        row1.columnconfigure(1, weight=2)

        cf = tk.Frame(row1, bg=C["surface"])
        cf.grid(row=0, column=0, padx=(0,10), sticky="nsew")
        tk.Label(cf, text="Category", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.exp_cat_var = tk.StringVar(value=EXPENSE_CATEGORIES[0])
        self.exp_cat_combo = StyledCombo(cf, textvariable=self.exp_cat_var,
            values=EXPENSE_CATEGORIES, state="readonly", width=20)
        self.exp_cat_combo.pack(fill="x", pady=(4,0), ipady=5)

        df2 = tk.Frame(row1, bg=C["surface"])
        df2.grid(row=0, column=1, sticky="nsew")
        tk.Label(df2, text="Description", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.exp_desc = StyledEntry(df2, placeholder="What was this expense for?")
        self.exp_desc.pack(fill="x", pady=(4,0), ipady=5)

        # Amount
        af = tk.Frame(form, bg=C["surface"])
        af.pack(fill="x", pady=(0,10))
        tk.Label(af, text="Amount (₱)", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.exp_amount = StyledEntry(af, placeholder="0.00", width=20)
        self.exp_amount.pack(anchor="w", pady=(4,0), ipady=5)

        # Payment mode
        pf2 = tk.Frame(form, bg=C["surface"])
        pf2.pack(fill="x", pady=(0,10))
        tk.Label(pf2, text="Payment Mode", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.exp_mode_var = tk.StringVar(value="Cash")
        prow2 = tk.Frame(pf2, bg=C["surface"])
        prow2.pack(fill="x", pady=(6,0))
        self.exp_mode_btns = {}
        for m, color in [("Cash", C["cash"]), ("GCash", C["gcash"]), ("Bank Transfer", C["bank"])]:
            btn = tk.Label(prow2, text=m, bg=C["surface3"], fg=C["text2"],
                font=("Segoe UI", 10, "bold"), padx=20, pady=8, cursor="hand2",
                relief="flat", highlightthickness=1, highlightbackground=C["border"])
            btn.pack(side="left", padx=(0,8))
            btn.bind("<Button-1>", lambda e, mode=m: self._select_mode(
                mode, self.exp_mode_var, self.exp_mode_btns))
            self.exp_mode_btns[m] = (btn, color)
        self._select_mode("Cash", self.exp_mode_var, self.exp_mode_btns)

        # Notes
        nf2 = tk.Frame(form, bg=C["surface"])
        nf2.pack(fill="x", pady=(0,14))
        tk.Label(nf2, text="Notes (optional)", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.exp_notes = tk.Text(nf2, bg=C["surface3"], fg=C["text"],
            font=("Segoe UI", 10), relief="flat", height=2,
            highlightthickness=1, highlightbackground=C["border"], insertbackground=C["text"])
        self.exp_notes.pack(fill="x", pady=(4,0))

        tk.Button(form, text="  ▼  Record Expense", bg=C["red"], fg="white",
            font=("Segoe UI", 11, "bold"), relief="flat", bd=0, padx=24, pady=10,
            cursor="hand2", activebackground="#d95555", activeforeground="white",
            command=self.save_expense).pack(anchor="w")

        # Expense table
        tcard = CardFrame(inner)
        tcard.pack(fill="both", expand=True, padx=pad, pady=(0,24))
        hdr_row2 = tk.Frame(tcard, bg=C["surface"])
        hdr_row2.pack(fill="x")
        tk.Label(hdr_row2, text="  Expense History", bg=C["surface"], fg=C["text"],
            font=("Segoe UI", 11, "bold"), anchor="w", pady=10).pack(side="left", fill="x", expand=True)
        tk.Button(hdr_row2, text="⊠  Delete Selected", bg=C["red_bg"], fg=C["red"],
            font=("Segoe UI", 9, "bold"), relief="flat", bd=0, padx=12, pady=5,
            cursor="hand2", command=self.delete_expense).pack(side="right", padx=10, pady=6)
        tk.Frame(tcard, bg=C["border"], height=1).pack(fill="x")
        cols = ("ID","Date","Category","Description","Amount","Mode","Notes")
        self.exp_tree = self._make_tree(tcard, cols, heights=12)
        self._refresh_exp_table()

    def save_expense(self):
        cat = self.exp_cat_var.get()
        desc = self.exp_desc.get_value().strip()
        amt_str = self.exp_amount.get_value()
        mode = self.exp_mode_var.get()
        notes = self.exp_notes.get("1.0","end").strip()

        if not desc:
            messagebox.showerror("Error","Description is required."); return
        try:
            amt = float(amt_str)
        except:
            messagebox.showerror("Error","Amount must be a number."); return

        if self.exp_use_today.get():
            exp_date = today_str()
        else:
            exp_date = self.exp_date_entry.get_value().strip() or today_str()

        conn = get_db()
        conn.execute("INSERT INTO expenses (date,category,description,amount,payment_mode,notes) VALUES (?,?,?,?,?,?)",
            (exp_date, cat, desc, amt, mode, notes))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", f"Expense recorded!\n{cat}: {fmt_money(amt)}")
        self.exp_desc.delete(0,"end"); self.exp_desc._show_placeholder()
        self.exp_amount.delete(0,"end"); self.exp_amount._show_placeholder()
        self.exp_notes.delete("1.0","end")
        self._refresh_exp_table()

    def delete_expense(self):
        sel = self.exp_tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Select an expense to delete."); return
        item = self.exp_tree.item(sel[0])
        eid = item["values"][0]
        cat = item["values"][2]
        amt = item["values"][4]
        if messagebox.askyesno("Confirm Delete", f"Delete expense:\n{cat}  —  {amt}\n\nThis cannot be undone."):
            conn = get_db()
            conn.execute("DELETE FROM expenses WHERE id=?", (eid,))
            conn.commit()
            conn.close()
            self._refresh_exp_table()
            self.refresh_dashboard()
            messagebox.showinfo("Deleted", "Expense deleted.")

    def _refresh_exp_table(self):
        for row in self.exp_tree.get_children():
            self.exp_tree.delete(row)
        conn = get_db()
        rows = conn.execute("SELECT id,date,category,description,amount,payment_mode,notes FROM expenses ORDER BY id DESC").fetchall()
        conn.close()
        for r in rows:
            self.exp_tree.insert("", "end", values=(r[0],r[1],r[2],r[3],fmt_money(r[4]),r[5],r[6] or ""))

    # ─────────────────────────────────────
    #  PAGE: CASH MANAGER
    # ─────────────────────────────────────
    def _build_cash_manager(self, parent):
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        scroll = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        inner = tk.Frame(canvas, bg=C["bg"])
        win = canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))

        pad = 24
        tk.Label(inner, text="Cash Manager", bg=C["bg"], fg=C["text"],
            font=("Segoe UI", 18, "bold"), anchor="w").pack(fill="x", padx=pad, pady=(pad,4))
        tk.Label(inner, text="Add petty cash or withdraw funds from Cash, GCash or Bank", bg=C["bg"],
            fg=C["text2"], font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=pad, pady=(0,16))

        # Balance summary
        brow = tk.Frame(inner, bg=C["bg"])
        brow.pack(fill="x", padx=pad, pady=(0,16))
        self.cm_balance_labels = {}
        items = [("Cash", C["cash"]), ("GCash", C["gcash"]), ("Bank Transfer", C["bank"])]
        for i, (m, color) in enumerate(items):
            brow.columnconfigure(i, weight=1)
            c2 = CardFrame(brow)
            c2.grid(row=0, column=i, padx=(0 if i==0 else 8, 0), sticky="nsew")
            bar2 = tk.Frame(c2, bg=color, height=3)
            bar2.pack(fill="x")
            inn2 = tk.Frame(c2, bg=C["surface"], padx=14, pady=12)
            inn2.pack(fill="both")
            tk.Label(inn2, text=m, bg=C["surface"], fg=C["text2"],
                font=("Segoe UI",9,"bold")).pack(anchor="w")
            lbl = tk.Label(inn2, text=fmt_money(get_balance(m)), bg=C["surface"],
                fg=color, font=("Segoe UI",15,"bold"))
            lbl.pack(anchor="w", pady=(4,0))
            self.cm_balance_labels[m] = lbl

        # Form
        form_card = CardFrame(inner)
        form_card.pack(fill="x", padx=pad, pady=(0,12))
        form = tk.Frame(form_card, bg=C["surface"], padx=20, pady=20)
        form.pack(fill="both")

        tk.Label(form, text="Petty Cash Transaction", bg=C["surface"], fg=C["text"],
            font=("Segoe UI",12,"bold")).pack(anchor="w", pady=(0,14))

        # Date
        dr3 = tk.Frame(form, bg=C["surface"])
        dr3.pack(fill="x", pady=(0,10))
        tk.Label(dr3, text="Date", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI",9,"bold")).pack(anchor="w")
        dr3row = tk.Frame(dr3, bg=C["surface"])
        dr3row.pack(fill="x", pady=(4,0))
        self.cm_use_today = tk.BooleanVar(value=True)
        tk.Checkbutton(dr3row, text="Use today's date", variable=self.cm_use_today,
            bg=C["surface"], fg=C["text2"], selectcolor=C["surface3"],
            activebackground=C["surface"], font=("Segoe UI",10),
            command=lambda: self.cm_date_entry.config(
                state="normal" if not self.cm_use_today.get() else "disabled")).pack(side="left")
        self.cm_date_entry = StyledEntry(dr3row, placeholder="YYYY-MM-DD", width=14)
        self.cm_date_entry.pack(side="left", padx=(10,0), ipady=5)
        self.cm_date_entry.config(state="disabled", disabledbackground=C["surface2"],
            disabledforeground=C["text3"])

        # Type
        tf = tk.Frame(form, bg=C["surface"])
        tf.pack(fill="x", pady=(0,10))
        tk.Label(tf, text="Transaction Type", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI",9,"bold")).pack(anchor="w")
        trow = tk.Frame(tf, bg=C["surface"])
        trow.pack(fill="x", pady=(6,0))
        self.cm_type_var = tk.StringVar(value="add")
        self.cm_type_btns = {}
        for t, lbl_t, color in [("add","＋ Add Cash", C["green"]), ("withdraw","− Withdraw", C["red"])]:
            btn = tk.Label(trow, text=lbl_t, bg=C["surface3"], fg=C["text2"],
                font=("Segoe UI",10,"bold"), padx=24, pady=8, cursor="hand2",
                relief="flat", highlightthickness=1, highlightbackground=C["border"])
            btn.pack(side="left", padx=(0,8))
            btn.bind("<Button-1>", lambda e, tp=t: self._select_cm_type(tp))
            self.cm_type_btns[t] = (btn, color)
        self._select_cm_type("add")

        # Amount
        aff = tk.Frame(form, bg=C["surface"])
        aff.pack(fill="x", pady=(0,10))
        tk.Label(aff, text="Amount (₱)", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI",9,"bold")).pack(anchor="w")
        self.cm_amount = StyledEntry(aff, placeholder="0.00", width=20)
        self.cm_amount.pack(anchor="w", pady=(4,0), ipady=5)

        # Payment mode
        pmf = tk.Frame(form, bg=C["surface"])
        pmf.pack(fill="x", pady=(0,10))
        tk.Label(pmf, text="Account / Payment Mode", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI",9,"bold")).pack(anchor="w")
        self.cm_mode_var = tk.StringVar(value="Cash")
        pmrow = tk.Frame(pmf, bg=C["surface"])
        pmrow.pack(fill="x", pady=(6,0))
        self.cm_mode_btns = {}
        for m, color in [("Cash", C["cash"]), ("GCash", C["gcash"]), ("Bank Transfer", C["bank"])]:
            btn = tk.Label(pmrow, text=m, bg=C["surface3"], fg=C["text2"],
                font=("Segoe UI",10,"bold"), padx=20, pady=8, cursor="hand2",
                relief="flat", highlightthickness=1, highlightbackground=C["border"])
            btn.pack(side="left", padx=(0,8))
            btn.bind("<Button-1>", lambda e, mode=m: self._select_mode(
                mode, self.cm_mode_var, self.cm_mode_btns))
            self.cm_mode_btns[m] = (btn, color)
        self._select_mode("Cash", self.cm_mode_var, self.cm_mode_btns)

        # Description
        dff = tk.Frame(form, bg=C["surface"])
        dff.pack(fill="x", pady=(0,14))
        tk.Label(dff, text="Description", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI",9,"bold")).pack(anchor="w")
        self.cm_desc = StyledEntry(dff, placeholder="Reason for transaction")
        self.cm_desc.pack(fill="x", pady=(4,0), ipady=5)

        tk.Button(form, text="  ◈  Confirm Transaction", bg=C["accent"], fg="white",
            font=("Segoe UI",11,"bold"), relief="flat", bd=0, padx=24, pady=10,
            cursor="hand2", activebackground=C["accent_dk"], activeforeground="white",
            command=self.save_cash_transaction).pack(anchor="w")

        # Ledger
        tcard2 = CardFrame(inner)
        tcard2.pack(fill="both", expand=True, padx=pad, pady=(0,24))
        hdr_cm = tk.Frame(tcard2, bg=C["surface"])
        hdr_cm.pack(fill="x")
        tk.Label(hdr_cm, text="  Cash Ledger", bg=C["surface"], fg=C["text"],
            font=("Segoe UI",11,"bold"), anchor="w", pady=10).pack(side="left", fill="x", expand=True)
        tk.Button(hdr_cm, text="⊠  Delete Selected", bg=C["red_bg"], fg=C["red"],
            font=("Segoe UI", 9, "bold"), relief="flat", bd=0, padx=12, pady=5,
            cursor="hand2", command=self.delete_cash_entry).pack(side="right", padx=10, pady=6)
        tk.Frame(tcard2, bg=C["border"], height=1).pack(fill="x")
        cols = ("ID","Date","Type","Mode","Amount","Description")
        self.cm_tree = self._make_tree(tcard2, cols, heights=10)
        self._refresh_cm_table()

    def _select_cm_type(self, tp):
        self.cm_type_var.set(tp)
        for t, (btn, color) in self.cm_type_btns.items():
            if t == tp:
                btn.config(bg=color, fg=C["bg"], highlightbackground=color)
            else:
                btn.config(bg=C["surface3"], fg=C["text2"], highlightbackground=C["border"])

    def save_cash_transaction(self):
        amt_str = self.cm_amount.get_value()
        mode = self.cm_mode_var.get()
        tp = self.cm_type_var.get()
        desc = self.cm_desc.get_value().strip()
        try:
            amt = float(amt_str)
        except:
            messagebox.showerror("Error","Amount must be a number."); return

        if self.cm_use_today.get():
            cm_date = today_str()
        else:
            cm_date = self.cm_date_entry.get_value().strip() or today_str()

        conn = get_db()
        conn.execute("INSERT INTO cash_ledger (date,type,payment_mode,amount,description) VALUES (?,?,?,?,?)",
            (cm_date, tp, mode, amt, desc))
        conn.commit()
        conn.close()

        action = "added to" if tp == "add" else "withdrawn from"
        messagebox.showinfo("Success", f"{fmt_money(amt)} {action} {mode}!")
        self.cm_amount.delete(0,"end"); self.cm_amount._show_placeholder()
        self.cm_desc.delete(0,"end"); self.cm_desc._show_placeholder()
        self._refresh_cm_table()
        self._refresh_cm_balances()

    def delete_cash_entry(self):
        sel = self.cm_tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Select a ledger entry to delete."); return
        item = self.cm_tree.item(sel[0])
        cid = item["values"][0]
        tp  = item["values"][2]
        amt = item["values"][4]
        if messagebox.askyesno("Confirm Delete", f"Delete ledger entry:\n{tp}  —  {amt}\n\nThis cannot be undone."):
            conn = get_db()
            conn.execute("DELETE FROM cash_ledger WHERE id=?", (cid,))
            conn.commit()
            conn.close()
            self._refresh_cm_table()
            self._refresh_cm_balances()
            self.refresh_dashboard()
            messagebox.showinfo("Deleted", "Ledger entry deleted.")

    def _refresh_cm_balances(self):
        for m, lbl in self.cm_balance_labels.items():
            lbl.config(text=fmt_money(get_balance(m)))

    def _refresh_cm_table(self):
        for row in self.cm_tree.get_children():
            self.cm_tree.delete(row)
        conn = get_db()
        rows = conn.execute("SELECT id,date,type,payment_mode,amount,description FROM cash_ledger ORDER BY id DESC").fetchall()
        conn.close()
        for r in rows:
            self.cm_tree.insert("","end", values=(r[0],r[1],r[2].upper(),r[3],fmt_money(r[4]),r[5] or ""))

    # ─────────────────────────────────────
    #  PAGE: PRODUCTS
    # ─────────────────────────────────────
    def _build_products(self, parent):
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        scroll = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        inner = tk.Frame(canvas, bg=C["bg"])
        win = canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))

        pad = 24
        tk.Label(inner, text="Product Catalog", bg=C["bg"], fg=C["text"],
            font=("Segoe UI",18,"bold"), anchor="w").pack(fill="x", padx=pad, pady=(pad,4))
        tk.Label(inner, text="Manage your products for quick access when adding sales", bg=C["bg"],
            fg=C["text2"], font=("Segoe UI",10), anchor="w").pack(fill="x", padx=pad, pady=(0,16))

        card = CardFrame(inner)
        card.pack(fill="x", padx=pad, pady=(0,12))
        form = tk.Frame(card, bg=C["surface"], padx=20, pady=20)
        form.pack(fill="both")
        tk.Label(form, text="Add New Product", bg=C["surface"], fg=C["text"],
            font=("Segoe UI",12,"bold")).pack(anchor="w", pady=(0,14))

        row_a = tk.Frame(form, bg=C["surface"])
        row_a.pack(fill="x", pady=(0,10))
        row_a.columnconfigure(0, weight=2)
        row_a.columnconfigure(1, weight=1)

        nf3 = tk.Frame(row_a, bg=C["surface"])
        nf3.grid(row=0, column=0, padx=(0,10), sticky="nsew")
        tk.Label(nf3, text="Product Name", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI",9,"bold")).pack(anchor="w")
        self.prod_name = StyledEntry(nf3, placeholder="e.g. Coffee, T-Shirt, etc.")
        self.prod_name.pack(fill="x", pady=(4,0), ipady=5)

        pf3 = tk.Frame(row_a, bg=C["surface"])
        pf3.grid(row=0, column=1, sticky="nsew")
        tk.Label(pf3, text="Unit Price (₱)", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI",9,"bold")).pack(anchor="w")
        self.prod_price = StyledEntry(pf3, placeholder="0.00")
        self.prod_price.pack(fill="x", pady=(4,0), ipady=5)

        df3 = tk.Frame(form, bg=C["surface"])
        df3.pack(fill="x", pady=(0,14))
        tk.Label(df3, text="Description (optional)", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI",9,"bold")).pack(anchor="w")
        self.prod_desc2 = StyledEntry(df3, placeholder="Short description...")
        self.prod_desc2.pack(fill="x", pady=(4,0), ipady=5)

        tk.Button(form, text="  ＋  Add Product", bg=C["purple"], fg="white",
            font=("Segoe UI",11,"bold"), relief="flat", bd=0, padx=24, pady=10,
            cursor="hand2", activebackground="#8b6de8", activeforeground="white",
            command=self.save_product).pack(anchor="w")

        tcard3 = CardFrame(inner)
        tcard3.pack(fill="both", expand=True, padx=pad, pady=(0,24))
        tk.Label(tcard3, text="  Product List", bg=C["surface"], fg=C["text"],
            font=("Segoe UI",11,"bold"), anchor="w", pady=10).pack(fill="x")
        tk.Frame(tcard3, bg=C["border"], height=1).pack(fill="x")

        btn_row = tk.Frame(tcard3, bg=C["surface"], padx=12, pady=8)
        btn_row.pack(fill="x")
        tk.Button(btn_row, text="⊠ Delete Selected", bg=C["red_bg"], fg=C["red"],
            font=("Segoe UI",9,"bold"), relief="flat", bd=0, padx=12, pady=5,
            cursor="hand2", command=self.delete_product).pack(side="left")

        cols = ("ID","Name","Unit Price","Description","Created")
        self.prod_tree = self._make_tree(tcard3, cols, heights=14)
        self._refresh_prod_table()

    def save_product(self):
        name = self.prod_name.get_value().strip()
        price_str = self.prod_price.get_value()
        desc = self.prod_desc2.get_value().strip()
        if not name:
            messagebox.showerror("Error","Product name is required."); return
        try:
            price = float(price_str)
        except:
            messagebox.showerror("Error","Price must be a number."); return
        conn = get_db()
        conn.execute("INSERT INTO products (name,unit_price,description) VALUES (?,?,?)",
            (name, price, desc))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", f"Product '{name}' added!")
        self.prod_name.delete(0,"end"); self.prod_name._show_placeholder()
        self.prod_price.delete(0,"end"); self.prod_price._show_placeholder()
        self.prod_desc2.delete(0,"end"); self.prod_desc2._show_placeholder()
        self._refresh_prod_table()

    def delete_product(self):
        sel = self.prod_tree.selection()
        if not sel:
            messagebox.showwarning("Warning","Select a product to delete."); return
        item = self.prod_tree.item(sel[0])
        pid = item["values"][0]
        if messagebox.askyesno("Confirm","Delete this product?"):
            conn = get_db()
            conn.execute("DELETE FROM products WHERE id=?", (pid,))
            conn.commit()
            conn.close()
            self._refresh_prod_table()

    def _refresh_prod_table(self):
        for row in self.prod_tree.get_children():
            self.prod_tree.delete(row)
        conn = get_db()
        rows = conn.execute("SELECT id,name,unit_price,description,created_at FROM products ORDER BY name").fetchall()
        conn.close()
        for r in rows:
            self.prod_tree.insert("","end", values=(r[0],r[1],fmt_money(r[2]),r[3] or "",r[4]))

    # ─────────────────────────────────────
    #  PAGE: REPORTS
    # ─────────────────────────────────────
    def _build_reports(self, parent):
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        scroll = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        self.rpt_inner = tk.Frame(canvas, bg=C["bg"])
        win = canvas.create_window((0,0), window=self.rpt_inner, anchor="nw")
        self.rpt_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        self.rpt_canvas = canvas

        self.refresh_reports()

    def refresh_reports(self):
        for w in self.rpt_inner.winfo_children():
            w.destroy()

        pad = 24
        tk.Label(self.rpt_inner, text="Reports & Analytics", bg=C["bg"], fg=C["text"],
            font=("Segoe UI",18,"bold"), anchor="w").pack(fill="x", padx=pad, pady=(pad,4))
        tk.Label(self.rpt_inner, text="Financial summary with breakdown by payment method and category",
            bg=C["bg"], fg=C["text2"], font=("Segoe UI",10), anchor="w").pack(fill="x", padx=pad, pady=(0,16))

        # Filter
        fcard = CardFrame(self.rpt_inner)
        fcard.pack(fill="x", padx=pad, pady=(0,16))
        fform = tk.Frame(fcard, bg=C["surface"], padx=20, pady=14)
        fform.pack(fill="both")
        frow = tk.Frame(fform, bg=C["surface"])
        frow.pack(fill="x")
        tk.Label(frow, text="From:", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI",9,"bold")).pack(side="left")
        self.rpt_from = StyledEntry(frow, placeholder="YYYY-MM-DD", width=14)
        self.rpt_from.pack(side="left", padx=(6,16), ipady=4)
        tk.Label(frow, text="To:", bg=C["surface"], fg=C["text2"],
            font=("Segoe UI",9,"bold")).pack(side="left")
        self.rpt_to = StyledEntry(frow, placeholder="YYYY-MM-DD", width=14)
        self.rpt_to.pack(side="left", padx=(6,16), ipady=4)
        tk.Button(frow, text="⟳ Generate Report", bg=C["accent"], fg="white",
            font=("Segoe UI",10,"bold"), relief="flat", bd=0, padx=14, pady=6,
            cursor="hand2", activebackground=C["accent_dk"], activeforeground="white",
            command=self.refresh_reports).pack(side="left", padx=(0,8))
        tk.Button(frow, text="Clear Filters", bg=C["surface3"], fg=C["text2"],
            font=("Segoe UI",10), relief="flat", bd=0, padx=14, pady=6,
            cursor="hand2", command=self._clear_rpt_filters).pack(side="left")

        # Get date range
        from_date = self.rpt_from.get_value() if hasattr(self, "rpt_from") else ""
        to_date = self.rpt_to.get_value() if hasattr(self, "rpt_to") else ""

        conn = get_db()

        def q_sales(extra=""):
            base = "SELECT payment_mode, SUM(total) FROM transactions"
            conds = []
            params = []
            if from_date:
                conds.append("date >= ?"); params.append(from_date)
            if to_date:
                conds.append("date <= ?"); params.append(to_date)
            if extra:
                conds.append(f"payment_mode=?"); params.append(extra)
            if conds:
                base += " WHERE " + " AND ".join(conds)
            base += " GROUP BY payment_mode"
            return conn.execute(base, params).fetchall()

        def q_exp_by_mode(extra=""):
            base = "SELECT payment_mode, SUM(amount) FROM expenses"
            conds = []
            params = []
            if from_date:
                conds.append("date >= ?"); params.append(from_date)
            if to_date:
                conds.append("date <= ?"); params.append(to_date)
            if extra:
                conds.append("payment_mode=?"); params.append(extra)
            if conds:
                base += " WHERE " + " AND ".join(conds)
            base += " GROUP BY payment_mode"
            return conn.execute(base, params).fetchall()

        def q_exp_by_cat():
            base = "SELECT category, payment_mode, SUM(amount) FROM expenses"
            conds = []
            params = []
            if from_date:
                conds.append("date >= ?"); params.append(from_date)
            if to_date:
                conds.append("date <= ?"); params.append(to_date)
            if conds:
                base += " WHERE " + " AND ".join(conds)
            base += " GROUP BY category, payment_mode ORDER BY category"
            return conn.execute(base, params).fetchall()

        def q_sales_all():
            base = "SELECT date,product_name,quantity,total,payment_mode FROM transactions"
            conds, params = [], []
            if from_date:
                conds.append("date >= ?"); params.append(from_date)
            if to_date:
                conds.append("date <= ?"); params.append(to_date)
            if conds:
                base += " WHERE " + " AND ".join(conds)
            return conn.execute(base + " ORDER BY date DESC", params).fetchall()

        def q_exp_all():
            base = "SELECT date,category,description,amount,payment_mode FROM expenses"
            conds, params = [], []
            if from_date:
                conds.append("date >= ?"); params.append(from_date)
            if to_date:
                conds.append("date <= ?"); params.append(to_date)
            if conds:
                base += " WHERE " + " AND ".join(conds)
            return conn.execute(base + " ORDER BY date DESC", params).fetchall()

        sales_by_mode = {r[0]: r[1] for r in q_sales()}
        exp_by_mode   = {r[0]: r[1] for r in q_exp_by_mode()}
        exp_by_cat    = q_exp_by_cat()
        all_sales     = q_sales_all()
        all_exp       = q_exp_all()
        conn.close()

        total_sales = sum(sales_by_mode.values())
        total_exp   = sum(exp_by_mode.values())
        net         = total_sales - total_exp

        # Summary cards
        srow = tk.Frame(self.rpt_inner, bg=C["bg"])
        srow.pack(fill="x", padx=pad, pady=(0,16))
        for i in range(3):
            srow.columnconfigure(i, weight=1)

        for i, (lbl, val, color) in enumerate([
            ("Total Sales",    total_sales, C["green"]),
            ("Total Expenses", total_exp,   C["red"]),
            ("Net Profit",     net,         C["accent"] if net >= 0 else C["red"]),
        ]):
            sc = CardFrame(srow)
            sc.grid(row=0, column=i, padx=(0 if i==0 else 10, 0), sticky="nsew")
            tk.Frame(sc, bg=color, height=3).pack(fill="x")
            sin = tk.Frame(sc, bg=C["surface"], padx=16, pady=14)
            sin.pack(fill="both")
            tk.Label(sin, text=lbl, bg=C["surface"], fg=C["text2"],
                font=("Segoe UI",9,"bold")).pack(anchor="w")
            tk.Label(sin, text=fmt_money(val), bg=C["surface"], fg=color,
                font=("Segoe UI",16,"bold")).pack(anchor="w", pady=(4,0))

        # Breakdown by payment mode
        twin2 = tk.Frame(self.rpt_inner, bg=C["bg"])
        twin2.pack(fill="x", padx=pad, pady=(0,16))
        twin2.columnconfigure(0, weight=1)
        twin2.columnconfigure(1, weight=1)

        for col_idx, (title, data_dict, color) in enumerate([
            ("Sales by Payment Mode", sales_by_mode, C["green"]),
            ("Expenses by Payment Mode", exp_by_mode, C["red"]),
        ]):
            bc = CardFrame(twin2)
            bc.grid(row=0, column=col_idx, padx=(0 if col_idx==0 else 12,0), sticky="nsew")
            tk.Label(bc, text=f"  {title}", bg=C["surface"], fg=C["text"],
                font=("Segoe UI",11,"bold"), anchor="w", pady=10).pack(fill="x")
            tk.Frame(bc, bg=C["border"], height=1).pack(fill="x")
            binner = tk.Frame(bc, bg=C["surface"], padx=16, pady=12)
            binner.pack(fill="both")
            mode_colors = {"Cash": C["cash"], "GCash": C["gcash"], "Bank Transfer": C["bank"]}
            total_mode = sum(data_dict.values()) or 1
            for m in PAYMENT_MODES:
                val2 = data_dict.get(m, 0)
                row_f = tk.Frame(binner, bg=C["surface"])
                row_f.pack(fill="x", pady=4)
                mc = mode_colors.get(m, C["text2"])
                tk.Label(row_f, text=m, bg=C["surface"], fg=mc,
                    font=("Segoe UI",10,"bold"), width=14, anchor="w").pack(side="left")
                # bar
                bar_bg = tk.Frame(row_f, bg=C["surface3"], height=10)
                bar_bg.pack(side="left", fill="x", expand=True, padx=(8,8))
                bar_bg.update_idletasks()
                pct = val2 / total_mode
                bar_fill = tk.Frame(bar_bg, bg=mc, height=10)
                bar_fill.place(relwidth=pct, relheight=1)
                tk.Label(row_f, text=fmt_money(val2), bg=C["surface"], fg=C["text"],
                    font=("Courier New",9,"bold"), width=12, anchor="e").pack(side="right")

        # Expenses by category
        catcard = CardFrame(self.rpt_inner)
        catcard.pack(fill="x", padx=pad, pady=(0,16))
        tk.Label(catcard, text="  Expenses by Category & Payment Mode", bg=C["surface"],
            fg=C["text"], font=("Segoe UI",11,"bold"), anchor="w", pady=10).pack(fill="x")
        tk.Frame(catcard, bg=C["border"], height=1).pack(fill="x")

        cols_cat = ("Category","Cash","GCash","Bank Transfer","Total")
        tree_cat = self._make_tree(catcard, cols_cat, heights=8)
        cat_data = {}
        for cat, mode, amt in exp_by_cat:
            if cat not in cat_data:
                cat_data[cat] = {"Cash":0,"GCash":0,"Bank Transfer":0}
            cat_data[cat][mode] = cat_data[cat].get(mode,0) + amt
        for cat, modes in sorted(cat_data.items()):
            tot = sum(modes.values())
            tree_cat.insert("","end", values=(
                cat,
                fmt_money(modes.get("Cash",0)),
                fmt_money(modes.get("GCash",0)),
                fmt_money(modes.get("Bank Transfer",0)),
                fmt_money(tot)
            ))

        # Detailed sales table
        sc2 = CardFrame(self.rpt_inner)
        sc2.pack(fill="x", padx=pad, pady=(0,16))
        tk.Label(sc2, text="  All Sales", bg=C["surface"], fg=C["text"],
            font=("Segoe UI",11,"bold"), anchor="w", pady=10).pack(fill="x")
        tk.Frame(sc2, bg=C["border"], height=1).pack(fill="x")
        stree = self._make_tree(sc2, ("Date","Product","Qty","Total","Mode"), heights=10)
        for r in all_sales:
            stree.insert("","end", values=(r[0],r[1],r[2],fmt_money(r[3]),r[4]))

        # Detailed expense table
        ec2 = CardFrame(self.rpt_inner)
        ec2.pack(fill="x", padx=pad, pady=(0,24))
        tk.Label(ec2, text="  All Expenses", bg=C["surface"], fg=C["text"],
            font=("Segoe UI",11,"bold"), anchor="w", pady=10).pack(fill="x")
        tk.Frame(ec2, bg=C["border"], height=1).pack(fill="x")
        etree = self._make_tree(ec2, ("Date","Category","Description","Amount","Mode"), heights=10)
        for r in all_exp:
            etree.insert("","end", values=(r[0],r[1],r[2],fmt_money(r[3]),r[4]))

    def _build_daily_summary(self, parent):
        # Scroll canvas
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        scroll = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        self.ds_inner = tk.Frame(canvas, bg=C["bg"])
        win = canvas.create_window((0, 0), window=self.ds_inner, anchor="nw")
        self.ds_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        self.ds_canvas = canvas
        self.ds_period = tk.StringVar(value="today")
        self.refresh_daily_summary()

    def refresh_daily_summary(self, period=None):
        from datetime import date, timedelta
        if period:
            self.ds_period.set(period)
        current = self.ds_period.get()

        for w in self.ds_inner.winfo_children():
            w.destroy()

        pad = 24
        today = date.today()

        # Compute date range and label
        if current == "today":
            from_d = to_d = today
            period_label = f"Today  —  {today.strftime('%A, %B %d %Y')}"
        elif current == "yesterday":
            from_d = to_d = today - timedelta(days=1)
            period_label = f"Yesterday  —  {from_d.strftime('%A, %B %d %Y')}"
        elif current == "this_week":
            from_d = today - timedelta(days=today.weekday())
            to_d = today
            period_label = f"This Week  —  {from_d.strftime('%b %d')} to {to_d.strftime('%b %d, %Y')}"
        elif current == "last_week":
            from_d = today - timedelta(days=today.weekday() + 7)
            to_d = from_d + timedelta(days=6)
            period_label = f"Last Week  —  {from_d.strftime('%b %d')} to {to_d.strftime('%b %d, %Y')}"
        elif current == "this_month":
            from_d = today.replace(day=1)
            to_d = today
            period_label = f"This Month  —  {from_d.strftime('%B %Y')}"
        elif current == "last_month":
            first_this = today.replace(day=1)
            to_d = first_this - timedelta(days=1)
            from_d = to_d.replace(day=1)
            period_label = f"Last Month  —  {from_d.strftime('%B %Y')}"
        else:
            from_d = to_d = today
            period_label = today.strftime('%B %d %Y')

        from_str = from_d.strftime("%Y-%m-%d")
        to_str   = to_d.strftime("%Y-%m-%d")

        # ── HEADER ──────────────────────────────
        hdr = tk.Frame(self.ds_inner, bg=C["bg"])
        hdr.pack(fill="x", padx=pad, pady=(pad, 6))
        tk.Label(hdr, text="Daily Summary", bg=C["bg"], fg=C["text"],
            font=("Segoe UI", 18, "bold"), anchor="w").pack(side="left")

        # ── PERIOD BUTTONS ───────────────────────
        btn_card = CardFrame(self.ds_inner)
        btn_card.pack(fill="x", padx=pad, pady=(0, 16))
        btn_inner = tk.Frame(btn_card, bg=C["surface"], padx=16, pady=12)
        btn_inner.pack(fill="x")

        periods = [
            ("Today",      "today"),
            ("Yesterday",  "yesterday"),
            ("This Week",  "this_week"),
            ("Last Week",  "last_week"),
            ("This Month", "this_month"),
            ("Last Month", "last_month"),
        ]
        for lbl, key in periods:
            is_active = (current == key)
            bg  = C["accent"] if is_active else C["surface3"]
            fg  = "white"     if is_active else C["text2"]
            btn = tk.Button(btn_inner, text=lbl, bg=bg, fg=fg,
                font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                padx=14, pady=7, cursor="hand2",
                activebackground=C["accent_dk"], activeforeground="white",
                command=lambda k=key: self.refresh_daily_summary(k))
            btn.pack(side="left", padx=(0, 8))

        # Period label
        tk.Label(self.ds_inner, text=period_label, bg=C["bg"], fg=C["text2"],
            font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x", padx=pad, pady=(0, 14))

        # ── FETCH DATA ───────────────────────────
        conn = get_db()

        def qrange(table, select, extra_conds=None, extra_params=None, tail=""):
            conds  = ["date >= ?", "date <= ?"]
            params = [from_str, to_str]
            if extra_conds:
                for c, p in zip(extra_conds, extra_params):
                    conds.append(c); params.append(p)
            sql = f"SELECT {select} FROM {table} WHERE " + " AND ".join(conds)
            if tail:
                sql += " " + tail
            return conn.execute(sql, params).fetchall()

        # Sales totals
        s_total   = qrange("transactions", "COALESCE(SUM(total),0)")[0][0]
        e_total   = qrange("expenses",     "COALESCE(SUM(amount),0)")[0][0]
        net       = s_total - e_total
        txn_count = qrange("transactions", "COUNT(*)")[0][0]
        exp_count = qrange("expenses",     "COUNT(*)")[0][0]

        # Sales by mode
        s_cash  = qrange("transactions","COALESCE(SUM(total),0)",["payment_mode=?"],["Cash"])[0][0]
        s_gcash = qrange("transactions","COALESCE(SUM(total),0)",["payment_mode=?"],["GCash"])[0][0]
        s_bank  = qrange("transactions","COALESCE(SUM(total),0)",["payment_mode=?"],["Bank Transfer"])[0][0]

        # Expenses by mode
        e_cash  = qrange("expenses","COALESCE(SUM(amount),0)",["payment_mode=?"],["Cash"])[0][0]
        e_gcash = qrange("expenses","COALESCE(SUM(amount),0)",["payment_mode=?"],["GCash"])[0][0]
        e_bank  = qrange("expenses","COALESCE(SUM(amount),0)",["payment_mode=?"],["Bank Transfer"])[0][0]

        # Expenses by category
        exp_cats = qrange("expenses","category, SUM(amount)",
            tail="GROUP BY category ORDER BY SUM(amount) DESC")

        # Top selling products
        top_products = qrange("transactions","product_name, SUM(quantity), SUM(total)",
            tail="GROUP BY product_name ORDER BY SUM(total) DESC LIMIT 5")

        # Individual sales rows
        sales_rows = qrange("transactions","date, product_name, quantity, unit_price, total, payment_mode",
            tail="ORDER BY date DESC, id DESC")

        # Individual expense rows
        exp_rows = qrange("expenses","date, category, description, amount, payment_mode",
            tail="ORDER BY date DESC, id DESC")

        conn.close()

        # ── BIG SUMMARY CARDS ────────────────────
        cards_row = tk.Frame(self.ds_inner, bg=C["bg"])
        cards_row.pack(fill="x", padx=pad, pady=(0, 14))
        for i in range(3): cards_row.columnconfigure(i, weight=1)

        for i, (lbl, val, sub, color) in enumerate([
            ("Total Sales",    fmt_money(s_total), f"{txn_count} transaction{'s' if txn_count != 1 else ''}", C["green"]),
            ("Total Expenses", fmt_money(e_total), f"{exp_count} expense{'s' if exp_count != 1 else ''}", C["red"]),
            ("Net Income",     fmt_money(net),      "Sales minus expenses", C["accent"] if net >= 0 else C["red"]),
        ]):
            card = CardFrame(cards_row)
            card.grid(row=0, column=i, padx=(0 if i == 0 else 10, 0), sticky="nsew")
            tk.Frame(card, bg=color, height=4).pack(fill="x")
            inner = tk.Frame(card, bg=C["surface"], padx=18, pady=14)
            inner.pack(fill="both")
            tk.Label(inner, text=lbl, bg=C["surface"], fg=C["text2"],
                font=("Segoe UI", 9, "bold")).pack(anchor="w")
            tk.Label(inner, text=val, bg=C["surface"], fg=color,
                font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(4, 2))
            tk.Label(inner, text=sub, bg=C["surface"], fg=C["text3"],
                font=("Segoe UI", 9)).pack(anchor="w")

        # ── PAYMENT MODE BREAKDOWN ───────────────
        breakdown_row = tk.Frame(self.ds_inner, bg=C["bg"])
        breakdown_row.pack(fill="x", padx=pad, pady=(0, 14))
        breakdown_row.columnconfigure(0, weight=1)
        breakdown_row.columnconfigure(1, weight=1)

        for col_i, (title, rows_data, color) in enumerate([
            ("Sales by Payment Mode", [
                ("Cash",          s_cash,  C["green"]),
                ("GCash",         s_gcash, C["accent"]),
                ("Bank Transfer", s_bank,  C["yellow"]),
            ], C["green"]),
            ("Expenses by Payment Mode", [
                ("Cash",          e_cash,  C["green"]),
                ("GCash",         e_gcash, C["accent"]),
                ("Bank Transfer", e_bank,  C["yellow"]),
            ], C["red"]),
        ]):
            bc = CardFrame(breakdown_row)
            bc.grid(row=0, column=col_i, padx=(0 if col_i == 0 else 10, 0), sticky="nsew")
            tk.Label(bc, text=f"  {title}", bg=C["surface"], fg=C["text"],
                font=("Segoe UI", 10, "bold"), anchor="w", pady=10).pack(fill="x")
            tk.Frame(bc, bg=C["border"], height=1).pack(fill="x")
            b_inner = tk.Frame(bc, bg=C["surface"], padx=16, pady=12)
            b_inner.pack(fill="both")
            total_for_pct = s_total if col_i == 0 else e_total
            for mode, val, mc in rows_data:
                rr = tk.Frame(b_inner, bg=C["surface"])
                rr.pack(fill="x", pady=5)
                # Mode label + dot
                dot = tk.Label(rr, text="●", bg=C["surface"], fg=mc, font=("Segoe UI", 11))
                dot.pack(side="left")
                tk.Label(rr, text=f"  {mode}", bg=C["surface"], fg=C["text"],
                    font=("Segoe UI", 10), width=14, anchor="w").pack(side="left")
                tk.Label(rr, text=fmt_money(val), bg=C["surface"], fg=C["text"],
                    font=("Segoe UI", 10, "bold")).pack(side="right")
                pct = f"({val/total_for_pct*100:.0f}%)" if total_for_pct else "(0%)"
                tk.Label(rr, text=pct, bg=C["surface"], fg=C["text3"],
                    font=("Segoe UI", 9)).pack(side="right", padx=(0, 6))

        # ── EXPENSE CATEGORIES ───────────────────
        if exp_cats:
            cat_card = CardFrame(self.ds_inner)
            cat_card.pack(fill="x", padx=pad, pady=(0, 14))
            tk.Label(cat_card, text="  Expenses by Category", bg=C["surface"], fg=C["text"],
                font=("Segoe UI", 10, "bold"), anchor="w", pady=10).pack(fill="x")
            tk.Frame(cat_card, bg=C["border"], height=1).pack(fill="x")
            cat_inner = tk.Frame(cat_card, bg=C["surface"], padx=16, pady=12)
            cat_inner.pack(fill="both")
            cat_colors = [C["accent"], C["green"], C["yellow"], C["purple"],
                          "#F97316", "#06B6D4", C["red"], "#8B5CF6", "#EC4899", "#14B8A6"]
            for i, (cat, amt) in enumerate(exp_cats):
                rr2 = tk.Frame(cat_inner, bg=C["surface"])
                rr2.pack(fill="x", pady=4)
                cc = cat_colors[i % len(cat_colors)]
                tk.Label(rr2, text=f"  {cat}", bg=C["surface"], fg=C["text"],
                    font=("Segoe UI", 10), anchor="w", width=20).pack(side="left")
                # progress bar bg
                bar_bg = tk.Frame(rr2, bg=C["surface3"], height=8)
                bar_bg.pack(side="left", fill="x", expand=True, padx=(8, 12))
                bar_bg.update_idletasks()
                pct2 = amt / e_total if e_total else 0
                bar_fill = tk.Frame(bar_bg, bg=cc, height=8)
                bar_fill.place(relwidth=pct2, relheight=1)
                tk.Label(rr2, text=fmt_money(amt), bg=C["surface"], fg=C["text"],
                    font=("Segoe UI", 10, "bold"), width=12, anchor="e").pack(side="right")

        # ── TOP PRODUCTS ─────────────────────────
        if top_products:
            tp_card = CardFrame(self.ds_inner)
            tp_card.pack(fill="x", padx=pad, pady=(0, 14))
            tk.Label(tp_card, text="  Top Products", bg=C["surface"], fg=C["text"],
                font=("Segoe UI", 10, "bold"), anchor="w", pady=10).pack(fill="x")
            tk.Frame(tp_card, bg=C["border"], height=1).pack(fill="x")
            tp_inner = tk.Frame(tp_card, bg=C["surface"], padx=16, pady=12)
            tp_inner.pack(fill="both")
            # Header
            hrow = tk.Frame(tp_inner, bg=C["surface2"], padx=8, pady=6)
            hrow.pack(fill="x", pady=(0, 4))
            for txt, w in [("#", 4), ("Product", 30), ("Qty Sold", 10), ("Revenue", 14)]:
                tk.Label(hrow, text=txt, bg=C["surface2"], fg=C["text2"],
                    font=("Segoe UI", 9, "bold"), width=w, anchor="w").pack(side="left")
            for rank, (name, qty, rev) in enumerate(top_products, 1):
                bg3 = C["surface"] if rank % 2 == 0 else C["surface2"]
                row3 = tk.Frame(tp_inner, bg=bg3, padx=8, pady=7)
                row3.pack(fill="x")
                rank_color = [C["yellow"], C["text2"], C["text3"], C["text3"], C["text3"]][rank - 1]
                tk.Label(row3, text=f"#{rank}", bg=bg3, fg=rank_color,
                    font=("Segoe UI", 9, "bold"), width=4, anchor="w").pack(side="left")
                tk.Label(row3, text=name, bg=bg3, fg=C["text"],
                    font=("Segoe UI", 10), width=30, anchor="w").pack(side="left")
                tk.Label(row3, text=f"{qty:.0f}", bg=bg3, fg=C["text2"],
                    font=("Segoe UI", 10), width=10, anchor="w").pack(side="left")
                tk.Label(row3, text=fmt_money(rev), bg=bg3, fg=C["green"],
                    font=("Segoe UI", 10, "bold"), width=14, anchor="w").pack(side="left")

        # ── TRANSACTION LIST ─────────────────────
        if sales_rows:
            sl_card = CardFrame(self.ds_inner)
            sl_card.pack(fill="x", padx=pad, pady=(0, 14))
            tk.Label(sl_card, text="  Sales Transactions", bg=C["surface"], fg=C["text"],
                font=("Segoe UI", 10, "bold"), anchor="w", pady=10).pack(fill="x")
            tk.Frame(sl_card, bg=C["border"], height=1).pack(fill="x")
            sale_tree = self._make_tree(sl_card,
                ("Date", "Product", "Qty", "Unit Price", "Total", "Mode"), heights=min(len(sales_rows), 10))
            for r in sales_rows:
                sale_tree.insert("", "end", values=(r[0], r[1], r[2], fmt_money(r[3]), fmt_money(r[4]), r[5]))

        # ── EXPENSE LIST ─────────────────────────
        if exp_rows:
            el_card = CardFrame(self.ds_inner)
            el_card.pack(fill="x", padx=pad, pady=(0, 14))
            tk.Label(el_card, text="  Expense Transactions", bg=C["surface"], fg=C["text"],
                font=("Segoe UI", 10, "bold"), anchor="w", pady=10).pack(fill="x")
            tk.Frame(el_card, bg=C["border"], height=1).pack(fill="x")
            exp_tree = self._make_tree(el_card,
                ("Date", "Category", "Description", "Amount", "Mode"), heights=min(len(exp_rows), 8))
            for r in exp_rows:
                exp_tree.insert("", "end", values=(r[0], r[1], r[2], fmt_money(r[3]), r[4]))

        # ── EMPTY STATE ──────────────────────────
        if not sales_rows and not exp_rows:
            empty = CardFrame(self.ds_inner)
            empty.pack(fill="x", padx=pad, pady=(0, 14))
            tk.Label(empty, text="\n  No transactions recorded for this period.\n",
                bg=C["surface"], fg=C["text3"], font=("Segoe UI", 11), anchor="w").pack(fill="x", padx=16)

        # Spacer
        tk.Frame(self.ds_inner, bg=C["bg"], height=24).pack()

    def _clear_rpt_filters(self):
        try:
            self.rpt_from.delete(0,"end"); self.rpt_from._show_placeholder()
            self.rpt_to.delete(0,"end"); self.rpt_to._show_placeholder()
        except:
            pass
        self.refresh_reports()

    # ─────────────────────────────────────
    #  SHARED: TREEVIEW HELPER
    # ─────────────────────────────────────
    def _make_tree(self, parent, cols, heights=10):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Treeview",
            background=C["surface"], fieldbackground=C["surface"],
            foreground=C["text"], rowheight=28,
            borderwidth=0, relief="flat",
            font=("Segoe UI", 9))
        style.configure("Custom.Treeview.Heading",
            background=C["surface2"], foreground=C["text2"],
            borderwidth=0, relief="flat",
            font=("Segoe UI", 9, "bold"))
        style.map("Custom.Treeview",
            background=[("selected", C["surface3"])],
            foreground=[("selected", C["accent"])])
        style.map("Custom.Treeview.Heading",
            background=[("active", C["surface3"])])

        frame = tk.Frame(parent, bg=C["surface"])
        frame.pack(fill="both", expand=True, padx=1, pady=(0,1))

        vsb = tk.Scrollbar(frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = tk.Scrollbar(frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        tree = ttk.Treeview(frame, columns=cols, show="headings",
            style="Custom.Treeview", height=heights,
            yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)
        tree.pack(fill="both", expand=True)

        for col in cols:
            tree.heading(col, text=col)
            w = 80
            if col in ("Product","Description","Notes","Name"): w = 160
            elif col in ("Date","Mode","Payment Mode","Category"): w = 110
            elif col in ("ID",): w = 40
            elif "Amount" in col or "Price" in col or "Total" in col: w = 100
            tree.column(col, width=w, anchor="w", minwidth=40)

        # Alternate row colors
        tree.tag_configure("even", background=C["surface"])
        tree.tag_configure("odd", background=C["surface2"])
        return tree

# ─────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────
if __name__ == "__main__":
    import traceback
    try:
        root = tk.Tk()
        root.configure(bg=C["bg"])
        try:
            root.tk.call("tk", "scaling", 1.2)
        except:
            pass
        app = BizTrackApp(root)
        root.mainloop()
    except Exception as e:
        import os, traceback
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "biztrack_error.log")
        with open(log_path, "w") as lf:
            lf.write(traceback.format_exc())
        try:
            import tkinter.messagebox as mb
            mb.showerror("BizTrack Error", f"Startup error:\n\n{e}\n\nCheck biztrack_error.log next to the script.")
        except:
            pass
        print("\n=== BIZTRACK ERROR ===")
        print(traceback.format_exc())
        input("\nPress Enter to close...")
