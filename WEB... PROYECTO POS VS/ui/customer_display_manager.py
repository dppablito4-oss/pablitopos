import os
from typing import Any, Dict, List, Optional, Sequence

import ttkbootstrap as tb
from PIL import Image, ImageTk

try:
    from screeninfo import get_monitors
except ImportError:  # pragma: no cover - optional dependency
    get_monitors = None


class CustomerDisplayManager:
    """Visor del cliente con layout dividido y escalado dinámico."""

    def __init__(self, master_app, settings_repo):
        self.master = master_app
        self.settings_repo = settings_repo
        self.window: Optional[tb.Toplevel] = None
        self.tree: Optional[tb.Treeview] = None
        self.lbl_total: Optional[tb.Label] = None
        self.lbl_phone: Optional[tb.Label] = None
        self.lbl_qr: Optional[tb.Label] = None
        self._qr_photo: Optional[ImageTk.PhotoImage] = None
        self._palette: Dict[str, str] = {}
        self._fonts: Dict[str, int] = {}
        self._qr_max_width: int = 0
        self._qr_max_height: int = 0
        self._tree_style_name = "CustomerSplit.Treeview"
        self._frame_left_style = "CustomerLeft.TFrame"
        self._frame_right_style = "CustomerRight.TFrame"
        self._title_style = "CustomerTitle.TLabel"
        self._heading_style = "CustomerHeading.TLabel"
        self._total_style = "CustomerTotal.TLabel"
        self._phone_style = "CustomerPhone.TLabel"
        self._qr_style = "CustomerQR.TLabel"

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------
    def _fetch_monitors(self) -> List:
        if get_monitors is None:
            return []
        try:
            return get_monitors()
        except Exception:
            return []

    def _resolve_monitor(self, target_index: int):
        monitors = self._fetch_monitors()
        if not monitors:
            return None, []
        idx = max(0, min(target_index, len(monitors) - 1))
        return monitors[idx], monitors

    def get_monitor_options(self) -> List[str]:
        """Retorna descripciones amigables de los monitores detectados."""
        options = []
        monitors = self._fetch_monitors()
        for idx, monitor in enumerate(monitors):
            role = " (Principal)" if getattr(monitor, "is_primary", False) else " (Secundario)"
            options.append(f"Pantalla {idx}: {monitor.width}x{monitor.height}{role}")
        return options

    def _read_saved_screen_index(self) -> int:
        try:
            return int(self.settings_repo.get_setting("customer_screen_index", "0"))
        except (TypeError, ValueError):
            return 0

    def _compute_geometry(self, monitor) -> str:
        return f"{monitor.width}x{monitor.height}+{monitor.x}+{monitor.y}"

    def _calculate_dynamic_sizes(self, screen_height: int, screen_width: int) -> Dict[str, int]:
        base_height = max(screen_height, 600)
        scale = base_height / 1080
        sizes = {
            "title": int(42 * scale),
            "header": int(20 * scale),
            "row": int(18 * scale),
            "total_label": int(28 * scale),
            "total_value": int(72 * scale),
            "phone_label": int(30 * scale),
            "row_height": int(screen_height / 25),
        }
        return {key: max(value, 12 if key != "row_height" else 32) for key, value in sizes.items()}

    def _build_palette(self) -> Dict[str, str]:
        return {
            "window_bg": "#0b1120",
            "left_bg": "#111827",
            "right_bg": "#1f2937",
            "title_fg": "#f9fafb",
            "heading_bg": "#1f2937",
            "heading_fg": "#e5e7eb",
            "tree_bg": "#0f172a",
            "tree_fg": "#f9fafb",
            "tree_sel_bg": "#2563eb",
            "tree_sel_fg": "#f9fafb",
            "total_value_fg": "#22c55e",
            "phone_fg": "#facc15",
            "qr_fg": "#f9fafb",
            "warning_fg": "#f87171",
        }

    def _build_styles(self) -> None:
        style = tb.Style()
        palette = self._palette

        style.configure(self._frame_left_style, background=palette["left_bg"], relief="flat")
        style.configure(self._frame_right_style, background=palette["right_bg"], relief="flat")
        style.configure(self._title_style, background=palette["left_bg"], foreground=palette["title_fg"])
        style.configure(self._heading_style, background=palette["right_bg"], foreground=palette["heading_fg"])
        style.configure(self._total_style, background=palette["right_bg"], foreground=palette["total_value_fg"])
        style.configure(self._phone_style, background=palette["right_bg"], foreground=palette["phone_fg"])
        style.configure(self._qr_style, background=palette["right_bg"], foreground=palette["qr_fg"], wraplength=480)

        style.configure(
            self._tree_style_name,
            font=("Segoe UI", self._fonts.get("row", 18)),
            rowheight=self._fonts.get("row_height", 40),
            background=palette["tree_bg"],
            fieldbackground=palette["tree_bg"],
            foreground=palette["tree_fg"],
            borderwidth=0,
        )
        style.configure(
            f"{self._tree_style_name}.Heading",
            font=("Segoe UI", self._fonts.get("header", 20), "bold"),
            background=palette["heading_bg"],
            foreground=palette["title_fg"],
        )
        style.map(
            self._tree_style_name,
            background=[("selected", palette["tree_sel_bg"])],
            foreground=[("selected", palette["tree_sel_fg"])],
        )

    def _normalize_item(self, item: Any) -> Optional[Dict[str, Any]]:
        if item is None:
            return None
        if isinstance(item, dict):
            name = item.get("name") or item.get("description") or item.get("product")
            qty = item.get("qty") or item.get("quantity")
            price = item.get("price") or item.get("unit_price")
            subtotal = item.get("subtotal") or item.get("total")
        elif isinstance(item, (list, tuple)):
            padded = list(item) + [None] * (4 - len(item))
            name, qty, price, subtotal = padded[:4]
        else:
            return None

        if name is None:
            return None
        try:
            qty_value = float(0 if qty is None else qty)
        except (TypeError, ValueError):
            qty_value = 0.0
        try:
            price_value = float(0 if price is None else price)
        except (TypeError, ValueError):
            price_value = 0.0
        try:
            subtotal_value = float(0 if subtotal is None else subtotal)
        except (TypeError, ValueError):
            subtotal_value = qty_value * price_value

        return {
            "name": str(name),
            "qty": qty_value,
            "price": price_value,
            "subtotal": subtotal_value,
        }

    def _format_currency(self, value: float) -> str:
        return f"S/ {value:,.2f}"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def close(self) -> None:
        if self.window and self.window.winfo_exists():
            try:
                self.window.destroy()
            except Exception:
                pass
        self.window = None
        self.tree = None
        self.lbl_total = None
        self.lbl_phone = None
        self.lbl_qr = None
        self._qr_photo = None
        self._palette = {}

    def open_display(self, screen_index: Optional[int] = None) -> bool:
        target_index = self._read_saved_screen_index() if screen_index is None else screen_index
        monitor, monitors = self._resolve_monitor(target_index)
        if not monitors:
            if hasattr(self.master, "show_warning"):
                self.master.show_warning("Pantallas", "No se detectaron monitores externos disponibles.")
            return False

        if monitor is None:
            monitor = monitors[0]

        self.close()

        self._palette = self._build_palette()
        self._fonts = self._calculate_dynamic_sizes(monitor.height, monitor.width)
        self._build_styles()

        win = tb.Toplevel(self.master)
        win.attributes("-alpha", 0.0)
        win.title("Visor Cliente")
        win.overrideredirect(True)
        try:
            win.attributes("-topmost", True)
        except Exception:
            pass
        win.geometry(self._compute_geometry(monitor))
        win.configure(background=self._palette["window_bg"])
        win.columnconfigure(0, weight=3)
        win.columnconfigure(1, weight=2)
        win.rowconfigure(0, weight=1)

        left_frame = tb.Frame(win, style=self._frame_left_style, padding=12)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)

        title = tb.Label(
            left_frame,
            text="🛒 Detalle de Compra",
            font=("Segoe UI", self._fonts["title"], "bold"),
            style=self._title_style,
            anchor="center",
        )
        title.grid(row=0, column=0, sticky="ew", pady=(12, 12))

        cols = ("product", "qty", "price", "subtotal")
        tree = tb.Treeview(
            left_frame,
            columns=cols,
            show="headings",
            style=self._tree_style_name,
        )
        tree.heading("product", text="PRODUCTO")
        tree.heading("qty", text="CANT.")
        tree.heading("price", text="PRECIO")
        tree.heading("subtotal", text="SUBTOTAL")

        left_width = int(monitor.width * 0.6)
        tree.column("product", width=int(left_width * 0.52), anchor="w", stretch=True)
        tree.column("qty", width=int(left_width * 0.14), anchor="center", stretch=True)
        tree.column("price", width=int(left_width * 0.15), anchor="e", stretch=True)
        tree.column("subtotal", width=int(left_width * 0.19), anchor="e", stretch=True)

        tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        def _on_mousewheel(event):
            delta = event.delta if hasattr(event, "delta") else 0
            if delta == 0 and hasattr(event, "num"):
                delta = 120 if event.num == 4 else -120
            units = int(-1 * (delta / 120)) if delta else 0
            if units:
                tree.yview_scroll(units, "units")
            return "break"

        tree.bind("<MouseWheel>", _on_mousewheel, add="+")
        tree.bind("<Button-4>", lambda e: tree.yview_scroll(-1, "units"), add="+")
        tree.bind("<Button-5>", lambda e: tree.yview_scroll(1, "units"), add="+")

        right_frame = tb.Frame(win, style=self._frame_right_style, padding=12)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(3, weight=1)

        total_label = tb.Label(
            right_frame,
            text="TOTAL A PAGAR",
            font=("Segoe UI", self._fonts["total_label"]),
            style=self._heading_style,
            anchor="center",
        )
        total_label.grid(row=0, column=0, sticky="ew", pady=(16, 12), padx=20)

        lbl_total = tb.Label(
            right_frame,
            text="S/ 0.00",
            font=("Arial", self._fonts["total_value"], "bold"),
            style=self._total_style,
            anchor="center",
        )
        lbl_total.grid(row=1, column=0, sticky="n", padx=20)

        lbl_phone = tb.Label(
            right_frame,
            text="N°: ---",
            font=("Segoe UI", self._fonts["phone_label"], "bold"),
            style=self._phone_style,
            anchor="center",
            wraplength=int(monitor.width * 0.35),
            justify="center",
        )
        lbl_phone.grid(row=2, column=0, sticky="n", padx=20, pady=(20, 10))

        lbl_qr = tb.Label(right_frame, style=self._qr_style, anchor="center")
        lbl_qr.grid(row=3, column=0, sticky="nsew", padx=40, pady=(10, 40))

        right_width = int(monitor.width * 0.4)
        self._qr_max_width = int(right_width * 0.8)
        self._qr_max_height = int(monitor.height * 0.6)

        self.window = win
        self.tree = tree
        self.lbl_total = lbl_total
        self.lbl_phone = lbl_phone
        self.lbl_qr = lbl_qr
        win.deiconify()
        win.update()
        win.attributes("-alpha", 1.0)
        return True

    # ------------------------------------------------------------------
    # Contenido dinámico
    # ------------------------------------------------------------------
    def update_display(
        self,
        cart_items: Sequence[Any],
        total_amount: float,
        qr_path: Optional[str],
        phone_number: Optional[str] = None,
    ) -> None:
        if not (
            self.window
            and self.window.winfo_exists()
            and self.tree
            and self.lbl_total
            and self.lbl_qr
            and self.lbl_phone
        ):
            return

        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        for raw in cart_items or []:
            normalized = self._normalize_item(raw)
            if not normalized:
                continue
            values = (
                normalized["name"],
                f"{normalized['qty']:.2f}",
                self._format_currency(normalized["price"]),
                self._format_currency(normalized["subtotal"]),
            )
            self.tree.insert("", "end", values=values)

        try:
            total_value = float(total_amount)
        except (TypeError, ValueError):
            total_value = 0.0
        self.lbl_total.configure(text=self._format_currency(total_value))

        phone_text = (phone_number or "").strip()
        self.lbl_phone.configure(
            text=f"N°: {phone_text}" if phone_text else "N°: Configura el teléfono empresarial"
        )

        if qr_path and os.path.exists(qr_path):
            try:
                image = Image.open(qr_path)
                # Reducir un poco el tamaño para evitar cortes (60% del espacio disponible)
                target_side = int(min(self._qr_max_width, self._qr_max_height) * 0.6)
                image = image.resize((target_side, target_side), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                self.lbl_qr.configure(image=photo, text="")
                self._qr_photo = photo
            except Exception:
                self.lbl_qr.configure(image="", text="(Error al cargar QR)")
                self._qr_photo = None
        else:
            message = "ESPERANDO QR..."
            if not phone_text:
                message = "Configura el QR y teléfono en Perfil → Configuración de Cobro"
            self.lbl_qr.configure(image="", text=message)
            self._qr_photo = None

    # ------------------------------------------------------------------
    # Flujo de uso
    # ------------------------------------------------------------------
    def show_payment(
        self,
        cart_items: Sequence[Any],
        total_amount: float,
        qr_path: Optional[str],
        phone_number: Optional[str] = None,
        screen_index: Optional[int] = None,
    ) -> bool:
        if not self.open_display(screen_index):
            return False
        self.update_display(cart_items, total_amount, qr_path, phone_number)
        return True

    def show_test_screen(self, screen_index: int = 0) -> bool:
        if not self.open_display(screen_index):
            return False
        demo_items = [
            {"name": "Producto Ejemplo", "qty": 1, "price": 9.9, "subtotal": 9.9},
            {"name": "Servicio Premium", "qty": 2, "price": 19.5, "subtotal": 39.0},
        ]
        self.update_display(demo_items, 48.9, None, "987 654 321")
        if self.window:
            self.window.after(2000, self.close)
        return True
