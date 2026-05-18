import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, cast

import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb


class KpiCard:
    def __init__(
        self,
        parent: tk.Widget,
        column: int,
        palette: Dict[str, str],
        *,
        title: str,
        icon: str,
        accent: str,
        value_var: Optional[tk.StringVar] = None,
        sub_var: Optional[tk.StringVar] = None,
    ) -> None:
        self.palette = palette
        self.default_accent = accent
        self.frame = tk.Frame(parent, bg=palette["panel_bg"], highlightthickness=0)
        self.frame.grid(row=0, column=column, sticky="nsew", padx=5)
        self.frame.columnconfigure(0, weight=1)

        outer = tk.Frame(self.frame, bg=palette["card_border"], bd=0, highlightthickness=0)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)

        inner = tk.Frame(outer, bg=palette["card_bg"], bd=0, highlightthickness=0)
        inner.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        inner.columnconfigure(1, weight=1)

        self.accent_bar = tk.Frame(inner, bg=accent, height=3, bd=0, highlightthickness=0)
        self.accent_bar.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.body = tk.Frame(inner, bg=palette["card_bg"], padx=16, pady=14)
        self.body.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.body.columnconfigure(1, weight=1)

        self.icon_label = tk.Label(
            self.body,
            text=icon,
            font=("Segoe UI Emoji", 26),
            bg=palette["card_bg"],
            fg=accent,
        )
        self.icon_label.grid(row=0, column=0, rowspan=3, sticky="nw", padx=(0, 10))

        title_label = tk.Label(
            self.body,
            text=title.upper(),
            font=("Segoe UI", 9, "bold"),
            bg=palette["card_bg"],
            fg=palette["card_title"],
        )
        title_label.grid(row=0, column=1, sticky="w")

        self.value_var = value_var or tk.StringVar(value="--")
        self.value_label = tk.Label(
            self.body,
            textvariable=self.value_var,
            font=("Segoe UI", 24, "bold"),
            bg=palette["card_bg"],
            fg=palette["card_value"],
        )
        self.value_label.grid(row=1, column=1, sticky="w", pady=(2, 0))

        self.sub_var = sub_var or tk.StringVar(value="")
        self.sub_label = tk.Label(
            self.body,
            textvariable=self.sub_var,
            font=("Segoe UI", 10),
            bg=palette["card_bg"],
            fg=palette["muted"],
        )
        self.sub_label.grid(row=2, column=1, sticky="w", pady=(2, 0))

        self.extra_vars: List[tk.StringVar] = []
        self.extra_labels: List[tk.Label] = []

        self.default_value_color = self.value_label.cget("fg")
        self.default_sub_color = self.sub_label.cget("fg")

    def set_value(self, text: str) -> None:
        self.value_var.set(text)

    def set_subtext(self, text: str, *, fg: Optional[str] = None) -> None:
        self.sub_var.set(text)
        if fg:
            self.sub_label.configure(fg=fg)
        else:
            self.sub_label.configure(fg=self.default_sub_color)

    def set_accent(self, color: str, *, value_color: Optional[str] = None) -> None:
        self.accent_bar.configure(bg=color)
        self.icon_label.configure(fg=color)
        if value_color:
            self.value_label.configure(fg=value_color)
        else:
            self.value_label.configure(fg=self.default_value_color)

    def add_extra_line(self, *, font: Tuple[str, int, str] = ("Segoe UI", 9, "normal"), fg: Optional[str] = None) -> tk.StringVar:
        var = tk.StringVar(value="")
        label = tk.Label(
            self.body,
            textvariable=var,
            font=font,
            bg=self.palette["card_bg"],
            fg=fg or self.palette["muted"],
        )
        row_index = 3 + len(self.extra_vars)
        label.grid(row=row_index, column=1, sticky="w", pady=(2, 0))
        self.extra_vars.append(var)
        self.extra_labels.append(label)
        return var

    def reset_styles(self) -> None:
        self.set_accent(self.default_accent, value_color=self.default_value_color)
        self.sub_label.configure(fg=self.default_sub_color)
        for label in self.extra_labels:
            label.configure(fg=self.palette["muted"])


class DashboardUIManager:
    """Encapsula la UI y lógica del panel principal con diseño responsive."""

    def __init__(self, app: Any, frame: tb.Frame, sale_service) -> None:
        self.app = app
        self.frame = frame
        self.sale_service = sale_service

        # Datos dinámicos para tarjetas
        self.var_total_day = tk.StringVar(value="S/ 0.00")
        self.var_ticket_count = tk.StringVar(value="0")
        self.var_avg_ticket = tk.StringVar(value="S/ 0.00")
        self.var_sales_delta = tk.StringVar(value="")
        self.var_ticket_delta = tk.StringVar(value="")
        self.var_avg_delta = tk.StringVar(value="")
        self.var_rus_status = tk.StringVar(value="Sin datos del mes")

        self.payment_vars = {
            "yape": tk.StringVar(value="Yape: S/ 0.00"),
            "cash": tk.StringVar(value="Efectivo: S/ 0.00"),
            "others": tk.StringVar(value="Otros: S/ 0.00"),
            "info": tk.StringVar(value=""),
        }

        self.card_sales: Optional[KpiCard] = None
        self.card_tickets: Optional[KpiCard] = None
        self.card_avg: Optional[KpiCard] = None
        self.progress_rus: Optional[tb.Floodgauge] = None
        self.rus_caption: Optional[tk.Label] = None

        self.refresh_button: Optional[tb.Button] = None
        self.lbl_clock: Optional[tb.Label] = None
        self.lbl_date: Optional[tb.Label] = None
        self.lbl_motivation: Optional[tb.Label] = None
        self.chart_canvas: Optional[tk.Canvas] = None
        self.tree_top_products: Optional[ttk.Treeview] = None

        self._palette: Dict[str, Any] = {}
        self._clock_job: Optional[str] = None
        self._chart_job: Optional[str] = None
        self._scroll_canvas: Optional[tk.Canvas] = None
        self._scroll_frame: Optional[tk.Frame] = None
        self._scroll_targets: List[tk.Widget] = []
        self._rus_limit = 8000.0
        self._motivation_messages = [
            "¡A vender con todo!",
            "Modo gamer activado",
            "Cada ticket cuenta",
            "Sonríe, estás facturando",
            "Tu meta de hoy supera la de ayer",
            "Cliente feliz = negocio feliz",
            "Seguimos sumando",
            "Paso firme hacia la meta",
        ]

    # ------------------------------------------------------------------
    # Inicialización de interfaz
    # ------------------------------------------------------------------
    def build_ui(self) -> None:
        self.dispose()
        self._palette = self._resolve_palette()

        for widget in self.frame.winfo_children():
            widget.destroy()

        content = self._create_scrollable_container(self.frame)
        content.configure(bg=self._palette["panel_bg"])
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=0)
        content.rowconfigure(1, weight=1)

        # --------------------------------------------------------------
        # Sección superior: KPIs
        # --------------------------------------------------------------
        kpi_frame = tk.Frame(content, bg=self._palette["panel_bg"])
        kpi_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 8))
        for col in range(4):
            kpi_frame.columnconfigure(col, weight=1)
        kpi_frame.rowconfigure(0, weight=1)

        self.card_sales = KpiCard(
            kpi_frame,
            column=0,
            palette=self._palette,
            title="Ventas Hoy",
            icon="💰",
            accent=self._palette["accent_sales_positive"],
            value_var=self.var_total_day,
            sub_var=self.var_sales_delta,
        )

        self.card_tickets = KpiCard(
            kpi_frame,
            column=1,
            palette=self._palette,
            title="Boletas Emitidas",
            icon="🧾",
            accent=self._palette["accent_transactions"],
            value_var=self.var_ticket_count,
            sub_var=self.var_ticket_delta,
        )

        self.card_avg = KpiCard(
            kpi_frame,
            column=2,
            palette=self._palette,
            title="Ticket Promedio",
            icon="📉",
            accent=self._palette["accent_payments"],
            value_var=self.var_avg_ticket,
            sub_var=self.var_avg_delta,
        )

        self._create_rus_card(kpi_frame, column=3)

        control_frame = tk.Frame(kpi_frame, bg=self._palette["panel_bg"])
        control_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        control_frame.columnconfigure(0, weight=1)
        self.refresh_button = tb.Button(
            control_frame,
            text="Refrescar 🔄",
            bootstyle="secondary-outline",
            command=self._handle_manual_refresh,
        )
        self.refresh_button.grid(row=0, column=1, sticky="e")

        # --------------------------------------------------------------
        # Sección inferior: gráfico + ranking + resumen
        # --------------------------------------------------------------
        bottom_frame = tk.Frame(content, bg=self._palette["panel_bg"])
        bottom_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        bottom_frame.columnconfigure(0, weight=7)
        bottom_frame.columnconfigure(1, weight=3)
        bottom_frame.rowconfigure(0, weight=1)

        chart_container = tb.Labelframe(
            bottom_frame,
            text="📊 Tendencia de Ventas (7 días)",
            bootstyle="secondary",
        )
        chart_container.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        chart_container.rowconfigure(0, weight=1)
        chart_container.columnconfigure(0, weight=1)

        self.chart_canvas = tk.Canvas(
            chart_container,
            bg=self._palette["chart_bg"],
            highlightthickness=0,
            bd=0,
        )
        self.chart_canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chart_canvas.bind("<Configure>", self._on_chart_configure)

        side_panel = tk.Frame(bottom_frame, bg=self._palette["panel_bg"])
        side_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        side_panel.columnconfigure(0, weight=1)
        side_panel.rowconfigure(0, weight=1)
        side_panel.rowconfigure(1, weight=0)
        side_panel.rowconfigure(2, weight=0)

        # Top productos
        list_frame = tb.Labelframe(side_panel, text="🔥 Top Productos Hoy", bootstyle="warning")
        list_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree_top_products = ttk.Treeview(
            list_frame,
            columns=("pos", "product", "qty", "amount"),
            show="headings",
            height=6,
            selectmode="none",
        )
        self.tree_top_products.heading("pos", text="#")
        self.tree_top_products.heading("product", text="Producto")
        self.tree_top_products.heading("qty", text="Unidades")
        self.tree_top_products.heading("amount", text="Total")
        self.tree_top_products.column("pos", width=36, anchor="center")
        self.tree_top_products.column("product", width=160, anchor="w")
        self.tree_top_products.column("qty", width=70, anchor="center")
        self.tree_top_products.column("amount", width=90, anchor="e")
        self.tree_top_products.grid(row=0, column=0, sticky="nsew")

        top_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree_top_products.yview)
        self.tree_top_products.configure(yscrollcommand=top_scroll.set)
        top_scroll.grid(row=0, column=1, sticky="ns")

        # Medios de pago
        payment_frame = tb.Labelframe(side_panel, text="🏦 Medios de Pago Hoy", bootstyle="primary")
        payment_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        payment_frame.columnconfigure(0, weight=1)

        tb.Label(payment_frame, textvariable=self.payment_vars["yape"], bootstyle="success")\
            .grid(row=0, column=0, sticky="w", padx=10, pady=(6, 0))
        tb.Label(payment_frame, textvariable=self.payment_vars["cash"], bootstyle="secondary")\
            .grid(row=1, column=0, sticky="w", padx=10)
        tb.Label(payment_frame, textvariable=self.payment_vars["others"], bootstyle="info")\
            .grid(row=2, column=0, sticky="w", padx=10, pady=(0, 4))
        tb.Label(
            payment_frame,
            textvariable=self.payment_vars["info"],
            bootstyle="light",
            wraplength=220,
        ).grid(row=3, column=0, sticky="w", padx=10, pady=(0, 6))

        # Reloj y motivación
        clock_frame = tb.Frame(side_panel, bootstyle="dark")
        clock_frame.grid(row=2, column=0, sticky="ew")
        clock_frame.columnconfigure(0, weight=1)

        self.lbl_clock = tb.Label(clock_frame, text="00:00:00", font=("Consolas", 24, "bold"), bootstyle="inverse-dark")
        self.lbl_clock.grid(row=0, column=0, sticky="ew", pady=(8, 0))
        self.lbl_date = tb.Label(clock_frame, text="--", font=("Segoe UI", 10), bootstyle="inverse-dark")
        self.lbl_date.grid(row=1, column=0, sticky="ew")
        self.lbl_motivation = tb.Label(clock_frame, text="Listo para vender", font=("Segoe UI", 10, "bold"), bootstyle="inverse-dark", wraplength=220, justify="center")
        self.lbl_motivation.grid(row=2, column=0, sticky="ew", pady=(4, 8))

        # Scroll con rueda del ratón
        self._register_scroll_target(self._scroll_frame)
        self._register_scroll_target(self.chart_canvas)
        self._register_scroll_target(self.tree_top_products)
        self._register_scroll_target(content)

        self.update_clock()
        self.refresh_dashboard()

    # ------------------------------------------------------------------
    # Construcción de elementos auxiliares
    # ------------------------------------------------------------------
    def _create_scrollable_container(self, parent: tk.Widget) -> tk.Frame:
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(parent, highlightthickness=0, bd=0, bg="#000000")
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = tb.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        content = tk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")

        def _on_frame_configure(_event: tk.Event | None = None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event: tk.Event) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        content.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        self._scroll_canvas = canvas
        self._scroll_frame = content
        return content

    def _create_rus_card(self, parent: tk.Widget, column: int) -> None:
        palette = self._palette
        frame = tk.Frame(parent, bg=palette["panel_bg"], highlightthickness=0)
        frame.grid(row=0, column=column, sticky="nsew", padx=5)
        frame.columnconfigure(0, weight=1)

        outer = tk.Frame(frame, bg=palette["card_border"], bd=0, highlightthickness=0)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)

        inner = tk.Frame(outer, bg=palette["card_bg"], bd=0, highlightthickness=0)
        inner.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        inner.columnconfigure(0, weight=1)

        accent = tk.Frame(inner, bg=palette["accent_sales_negative"], height=3)
        accent.grid(row=0, column=0, sticky="ew")

        body = tk.Frame(inner, bg=palette["card_bg"], padx=16, pady=14)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)

        tk.Label(
            body,
            text="LÍMITE RUS (S/ 8,000)",
            font=("Segoe UI", 9, "bold"),
            bg=palette["card_bg"],
            fg=palette["card_title"],
        ).grid(row=0, column=0, sticky="w")

        self.progress_rus = tb.Floodgauge(
            body,
            orient="horizontal",
            bootstyle="success",
            mask="S/ {}",
            maximum=int(self._rus_limit),
            font=("Segoe UI", 12),
        )
        self.progress_rus.grid(row=1, column=0, sticky="ew", pady=(12, 6))
        self.progress_rus.configure(font=cast(tuple[str, int] | str, ("Segoe UI", 12, "bold")))

        self.rus_caption = tk.Label(
            body,
            textvariable=self.var_rus_status,
            font=("Segoe UI", 10),
            bg=palette["card_bg"],
            fg=palette["muted"],
            justify="left",
            wraplength=200,
        )
        self.rus_caption.grid(row=2, column=0, sticky="w")

    # ------------------------------------------------------------------
    # Interacción y eventos
    # ------------------------------------------------------------------
    def _register_scroll_target(self, widget: Optional[tk.Widget]) -> None:
        if widget is None or widget in self._scroll_targets:
            return
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        widget.bind("<Button-4>", lambda _e: self._on_linux_scroll(-1), add="+")
        widget.bind("<Button-5>", lambda _e: self._on_linux_scroll(1), add="+")
        self._scroll_targets.append(widget)

    def _on_mousewheel(self, event: tk.Event) -> str:
        if not self._scroll_canvas:
            return "break"
        delta = -1 * int(event.delta / 120)
        self._scroll_canvas.yview_scroll(delta, "units")
        return "break"

    def _on_linux_scroll(self, direction: int) -> None:
        if self._scroll_canvas:
            self._scroll_canvas.yview_scroll(direction, "units")

    def _handle_manual_refresh(self) -> None:
        button = self.refresh_button
        if button and button.winfo_exists():
            button.configure(state="disabled")
        self.refresh_dashboard()
        if button and button.winfo_exists():
            button.after(800, lambda btn=button: btn.configure(state="normal"))

    def _on_chart_configure(self, _event: tk.Event) -> None:
        if self._chart_job and self.chart_canvas:
            try:
                self.chart_canvas.after_cancel(self._chart_job)
            except Exception:
                pass
        if self.chart_canvas:
            self._chart_job = self.chart_canvas.after(120, self.draw_sales_chart)

    # ------------------------------------------------------------------
    # Refresco de datos
    # ------------------------------------------------------------------
    def refresh_dashboard(self) -> None:
        try:
            now = datetime.now()
            today_count, today_total = self.sale_service.get_daily_summary()

            get_summary_for_day = getattr(self.sale_service, "get_summary_for_day", None)
            if callable(get_summary_for_day):
                summary = get_summary_for_day(now - timedelta(days=1))
                if isinstance(summary, tuple) and len(summary) == 2:
                    yesterday_count = int(summary[0] or 0)
                    yesterday_total = float(summary[1] or 0.0)
                else:
                    yesterday_count, yesterday_total = (0, 0.0)
            else:
                yesterday_count, yesterday_total = (0, 0.0)

            self.var_total_day.set(f"S/ {today_total:.2f}")
            sales_accent = self._palette["accent_sales_positive"]
            if yesterday_total > 0 and today_total < yesterday_total:
                sales_accent = self._palette["accent_sales_negative"]
            if self.card_sales:
                self.card_sales.set_accent(sales_accent, value_color=sales_accent)
                self.card_sales.set_subtext(
                    self._format_vs_yesterday(today_total, yesterday_total),
                    fg=sales_accent if yesterday_total else None,
                )

            self.var_ticket_count.set(str(today_count))
            if self.card_tickets:
                self.card_tickets.set_subtext(
                    self._format_count_delta(today_count, yesterday_count)
                )

            avg_today = today_total / today_count if today_count else 0.0
            avg_yesterday = yesterday_total / yesterday_count if yesterday_count else 0.0
            self.var_avg_ticket.set(f"S/ {avg_today:.2f}")
            if self.card_avg:
                self.card_avg.set_subtext(self._format_avg_delta(avg_today, avg_yesterday))

            month_total = getattr(self.sale_service, "get_month_sales_total", lambda *_: 0.0)(now)
            self._update_rus_gauge(month_total)

            breakdown = self.sale_service.get_payment_breakdown_today()
            self._update_payment_summary(breakdown)

            top_products = getattr(self.sale_service, "get_top_products_for_day", lambda *_: [])(now, 5)
            self._update_top_products(top_products)

            if self.chart_canvas:
                self.draw_sales_chart()
        except Exception as exc:
            print(f"Error al refrescar dashboard: {exc}")

    def _format_vs_yesterday(self, today_total: float, yesterday_total: float) -> str:
        if yesterday_total > 0:
            diff = today_total - yesterday_total
            percent = (diff / yesterday_total) * 100
            trend = "▲" if diff >= 0 else "▼"
            return f"vs. ayer: {trend} {percent:+.0f}%"
        if today_total > 0:
            return "vs. ayer: +100%"
        return "vs. ayer: sin ventas"

    @staticmethod
    def _format_count_delta(today: int, yesterday: int) -> str:
        if yesterday > 0:
            diff = today - yesterday
            trend = "▲" if diff >= 0 else "▼"
            return f"vs. ayer: {trend} {diff:+d}"
        if today > 0:
            return "vs. ayer: +{today}".format(today=today)
        return "vs. ayer: sin ventas"

    @staticmethod
    def _format_avg_delta(avg_today: float, avg_yesterday: float) -> str:
        if avg_yesterday > 0:
            diff = avg_today - avg_yesterday
            trend = "▲" if diff >= 0 else "▼"
            return f"vs. ticket ayer: {trend} S/ {diff:+.2f}"
        if avg_today > 0:
            return "Primer ticket del día"
        return "Sin tickets aún"

    def _update_rus_gauge(self, month_total: float) -> None:
        if not self.progress_rus:
            return
        value = max(0.0, min(month_total, self._rus_limit))
        self.progress_rus.configure(value=value)
        usage = (month_total / self._rus_limit) * 100 if self._rus_limit else 0.0
        if usage < 55:
            style = "success"
        elif usage < 85:
            style = "warning"
        else:
            style = "danger"
        self.progress_rus.configure(bootstyle=style)
        self.var_rus_status.set(
            f"Acumulado mes: S/ {month_total:.2f}\nUso del límite: {usage:.0f}%"
        )

    def _update_payment_summary(self, breakdown: Dict[str, Any]) -> None:
        yape_total = float(breakdown.get("yape", 0.0) or 0.0)
        cash_total = float(breakdown.get("cash", 0.0) or 0.0)
        other_total = float(breakdown.get("others", 0.0) or 0.0)
        has_split = bool(breakdown.get("has_split"))

        self.payment_vars["yape"].set(f"Yape: S/ {yape_total:.2f}")
        self.payment_vars["cash"].set(f"Efectivo: S/ {cash_total:.2f}")
        self.payment_vars["others"].set(f"Otros: S/ {other_total:.2f}")
        self.payment_vars["info"].set(
            "" if has_split else "Sin desglose guardado; se asume efectivo."
        )

    def _update_top_products(self, products: List[Dict[str, Any]]) -> None:
        if not self.tree_top_products:
            return
        self.tree_top_products.delete(*self.tree_top_products.get_children())
        if not products:
            self.tree_top_products.insert("", "end", values=("-", "Sin datos", "-", "-"))
            return
        for idx, item in enumerate(products, start=1):
            description = item.get("description") or "Sin descripción"
            quantity = float(item.get("quantity") or 0.0)
            amount = float(item.get("amount") or 0.0)
            self.tree_top_products.insert(
                "",
                "end",
                values=(idx, description, f"{quantity:.0f}", f"S/ {amount:.2f}"),
            )

    def draw_sales_chart(self) -> None:
        if not self.chart_canvas or not self.chart_canvas.winfo_exists():
            return

        canvas = self.chart_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 320)
        height = max(canvas.winfo_height(), 220)
        palette = self._palette
        axis = palette["axis"]
        bar_colors = palette["bar_colors"]

        try:
            data = self.sale_service.get_weekly_sales()
        except Exception:
            data = []

        if not data:
            canvas.create_text(
                width / 2,
                height / 2,
                text="Sin datos recientes",
                fill=palette.get("warning_text", axis),
                font=("Segoe UI", 12, "bold"),
            )
            return

        max_val = max(total for _, total in data) or 1

        margin_left = 48
        margin_bottom = 32
        margin_top = 24
        margin_right = 20

        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom
        bar_area = chart_width / max(len(data), 1)
        bar_width = bar_area * 0.55
        spacing = bar_area * 0.45

        canvas.create_line(
            margin_left,
            height - margin_bottom,
            width - margin_right,
            height - margin_bottom,
            fill=axis,
            width=2,
        )
        canvas.create_line(
            margin_left,
            height - margin_bottom,
            margin_left,
            margin_top,
            fill=axis,
            width=2,
        )

        for index, (date_str, total) in enumerate(data):
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                label = date_obj.strftime("%d/%m")
            except Exception:
                label = date_str

            color = bar_colors[index % len(bar_colors)]
            x0 = margin_left + index * (bar_width + spacing) + spacing / 2
            x1 = x0 + bar_width
            bar_height = (total / max_val) * chart_height
            y0 = height - margin_bottom - bar_height
            y1 = height - margin_bottom

            canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
            canvas.create_text(
                (x0 + x1) / 2,
                y0 - 12,
                text=f"S/ {total:.0f}",
                fill=axis,
                font=("Segoe UI", 9),
            )
            canvas.create_text(
                (x0 + x1) / 2,
                height - margin_bottom + 16,
                text=label,
                fill=axis,
                font=("Segoe UI", 9),
            )

    # ------------------------------------------------------------------
    # Reloj en vivo
    # ------------------------------------------------------------------
    @staticmethod
    def _live_widget(widget: Optional[tk.Widget]) -> Optional[tk.Widget]:
        """Devuelve el widget solo si sigue vivo en el árbol de Tk."""
        if widget is None:
            return None
        try:
            return widget if widget.winfo_exists() else None
        except tk.TclError:
            return None

    @staticmethod
    def _safe_configure(widget: Optional[tk.Widget], **options: Any) -> bool:
        """Aplica configure a un widget capturando widgets destruidos."""
        if widget is None:
            return False
        try:
            widget.configure(**options)
            return True
        except tk.TclError:
            return False

    def update_clock(self) -> None:
        try:
            clock_label = self._live_widget(self.lbl_clock)
            date_label = self._live_widget(self.lbl_date)
            motivation_label = self._live_widget(self.lbl_motivation)

            if not any((clock_label, date_label, motivation_label)):
                self._clock_job = None
                return

            now = datetime.now()
            self._safe_configure(clock_label, text=now.strftime("%H:%M:%S"))
            self._safe_configure(date_label, text=now.strftime("%A, %d %b %Y").upper())
            if now.second % 12 == 0:
                self._safe_configure(motivation_label, text=random.choice(self._motivation_messages))

            cycle = self._palette.get("clock_cycle", [])
            if cycle:
                self._safe_configure(clock_label, foreground=cycle[now.second % len(cycle)])

            self._clock_job = self.app.after(1000, self.update_clock)
        except Exception as exc:
            print(f"Error actualizando reloj: {exc}")

    # ------------------------------------------------------------------
    # Limpieza / Tema
    # ------------------------------------------------------------------
    def dispose(self) -> None:
        if self._clock_job:
            try:
                self.app.after_cancel(self._clock_job)
            except Exception:
                pass
            self._clock_job = None
        if self.chart_canvas and self._chart_job:
            try:
                self.chart_canvas.after_cancel(self._chart_job)
            except Exception:
                pass
            self._chart_job = None
        if self.chart_canvas:
            self.chart_canvas.unbind("<Configure>")
        for widget in self._scroll_targets:
            try:
                widget.unbind("<MouseWheel>")
                widget.unbind("<Button-4>")
                widget.unbind("<Button-5>")
            except Exception:
                pass
        self._scroll_targets.clear()

    def on_theme_changed(self) -> None:
        self.build_ui()

    def _resolve_palette(self) -> Dict[str, Any]:
        style = getattr(self.app, "style", tb.Style())
        base_bg = style.lookup("TFrame", "background") or "#ffffff"
        is_dark = self._is_dark_color(base_bg)

        if is_dark:
            return {
                "panel_bg": "#111827",
                "panel_border": "#1f2937",
                "panel_title": "#cbd5f5",
                "text": "#f8fafc",
                "muted": "#cbd5f5",
                "value_fg": "#2dd4bf",
                "motivation_fg": "#fbbf24",
                "clock_cycle": ["#38bdf8", "#22d3ee", "#f97316", "#f43f5e", "#a855f7"],
                "chart_bg": "#0f172a",
                "axis": "#f8fafc",
                "bar_colors": ["#38bdf8", "#22d3ee", "#facc15", "#f97316", "#f43f5e", "#a855f7"],
                "warning_text": "#f87171",
                "card_bg": "#0f172a",
                "card_border": "#1f2937",
                "card_title": "#e2e8f0",
                "card_value": "#f8fafc",
                "accent_sales_positive": "#22c55e",
                "accent_sales_negative": "#f43f5e",
                "accent_transactions": "#38bdf8",
                "accent_payments": "#a855f7",
                "accent_cash": "#34d399",
            }

        return {
            "panel_bg": "#ffffff",
            "panel_border": "#d4d4d8",
            "panel_title": "#0f172a",
            "text": "#1e293b",
            "muted": "#64748b",
            "value_fg": "#16a34a",
            "motivation_fg": "#1d4ed8",
            "clock_cycle": ["#2563eb", "#16a34a", "#f97316", "#d946ef", "#dc2626"],
            "chart_bg": "#f8fafc",
            "axis": "#1e293b",
            "bar_colors": ["#2563eb", "#16a34a", "#f97316", "#d946ef", "#facc15", "#dc2626"],
            "warning_text": "#dc2626",
            "card_bg": "#ffffff",
            "card_border": "#e2e8f0",
            "card_title": "#0f172a",
            "card_value": "#0f172a",
            "accent_sales_positive": "#16a34a",
            "accent_sales_negative": "#dc2626",
            "accent_transactions": "#0284c7",
            "accent_payments": "#7c3aed",
            "accent_cash": "#0f766e",
        }

    @staticmethod
    def _hex_to_rgb(color: str) -> Tuple[int, int, int]:
        color = color.lstrip("#")
        if len(color) == 3:
            color = "".join(ch * 2 for ch in color)
        return (
            int(color[0:2], 16),
            int(color[2:4], 16),
            int(color[4:6], 16),
        )

    def _is_dark_color(self, color: str) -> bool:
        try:
            r, g, b = self._hex_to_rgb(color)
        except Exception:
            return False
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return luminance < 140
