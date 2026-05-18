"""UI helper controllers extracted from the legacy monolithic window class."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Optional, TYPE_CHECKING, cast

import tkinter as tk
import ttkbootstrap as tb

if TYPE_CHECKING:  # pragma: no cover - imported only for type checking
    from app_boletas import App


class TooltipManager:
    """Centralised tooltip handling with delayed hover behaviour."""

    def __init__(self, app: "App") -> None:
        self.app = app
        self._states: Dict[tk.Widget, Dict[str, Any]] = {}

    def add(
        self,
        widget: Optional[tk.Widget],
        text: str,
        *,
        delay: int = 1500,
        wraplength: int = 260,
    ) -> None:
        if widget is None or not widget.winfo_exists():
            return

        state = self._states.get(widget)
        if state and state.get("bound"):
            state["text"] = text
            state["delay"] = delay
            state["wrap"] = wraplength
            return

        state = {
            "text": text,
            "delay": delay,
            "wrap": wraplength,
            "job": None,
            "tooltip": None,
            "inside": False,
            "last_xy": None,
            "bound": True,
        }
        self._states[widget] = state

        def schedule() -> None:
            if not widget.winfo_exists():
                return
            self._cancel_job(widget)
            state["job"] = widget.after(delay, lambda: self._show(widget))

        def on_enter(event: tk.Event) -> None:
            state["inside"] = True
            state["last_xy"] = (event.x_root, event.y_root)
            schedule()

        def on_motion(event: tk.Event) -> None:
            if not state.get("inside"):
                return
            last = state.get("last_xy")
            current = (event.x_root, event.y_root)
            state["last_xy"] = current
            if last is None or abs(current[0] - last[0]) > 3 or abs(current[1] - last[1]) > 3:
                self._cancel_job(widget)
                self._hide(widget)
                schedule()

        def on_leave(_: tk.Event) -> None:
            state["inside"] = False
            self._cancel_job(widget)
            self._hide(widget)

        def on_button(_: tk.Event) -> None:
            self._cancel_job(widget)
            self._hide(widget)

        def on_destroy(_: tk.Event) -> None:
            self._cancel_job(widget)
            self._hide(widget)
            self._states.pop(widget, None)

        widget.bind("<Enter>", on_enter, add="+")
        widget.bind("<Leave>", on_leave, add="+")
        widget.bind("<Motion>", on_motion, add="+")
        widget.bind("<ButtonPress>", on_button, add="+")
        widget.bind("<Destroy>", on_destroy, add="+")

    def register_defaults(self) -> None:
        mappings: Iterable[tuple[Optional[tk.Widget], str]] = (
            (getattr(self.app, "btn_nav_dashboard", None), "Abre el panel principal con los indicadores clave del negocio."),
            (getattr(self.app, "btn_nav_sales", None), "Gestiona ventas, agrega productos y genera comprobantes."),
            (getattr(self.app, "btn_nav_update", None), "Actualiza la información de la empresa y recursos visuales."),
            (getattr(self.app, "btn_nav_history", None), "Consulta el historial completo de comprobantes emitidos."),
            (getattr(self.app, "btn_verify", None), "Valida un comprobante existente ingresando su número."),
            (getattr(self.app, "btn_export", None), "Exporta tus datos a Excel para respaldo o análisis."),
            (getattr(self.app, "btn_theme_toggle", None), "Alterna entre modo oscuro y claro según tu preferencia."),
            (getattr(self.app, "btn_back", None), "Regresa a la selección de perfiles de empresa."),
        )
        for widget, text in mappings:
            self.add(widget, text, delay=1500, wraplength=320)

    def _cancel_job(self, widget: tk.Widget) -> None:
        state = self._states.get(widget)
        if not state:
            return
        job = state.get("job")
        if job:
            try:
                widget.after_cancel(job)
            except Exception:
                pass
        state["job"] = None

    def _hide(self, widget: tk.Widget) -> None:
        state = self._states.get(widget)
        if not state:
            return
        tooltip = state.get("tooltip")
        if tooltip:
            try:
                tooltip.destroy()
            except Exception:
                pass
        state["tooltip"] = None

    def _show(self, widget: tk.Widget) -> None:
        state = self._states.get(widget)
        if not state or not widget.winfo_exists():
            return
        if state.get("tooltip") and state["tooltip"].winfo_exists():
            return

        text = state.get("text") or ""
        if not text:
            return

        tooltip = tb.Toplevel(master=self.app)
        if hasattr(self.app, "begin_modal_construction"):
            self.app.begin_modal_construction(tooltip)
        else:
            try:
                tooltip.attributes("-alpha", 0.0)
            except Exception:
                pass
        tooltip.overrideredirect(True)
        tooltip.transient(self.app)
        try:
            tooltip.attributes("-topmost", True)
        except Exception:
            pass

        dark_mode = self.app.is_dark_theme()
        bg_color = "#1d4ed8" if dark_mode else "#bfdbfe"
        border_color = "#60a5fa" if dark_mode else "#3b82f6"
        fg_color = "#ffffff" if dark_mode else "#1e3a8a"

        tooltip.configure(bg=border_color)

        frame = tk.Frame(tooltip, bg=bg_color, padx=10, pady=8, highlightthickness=0, bd=0)
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(
            frame,
            text=text,
            wraplength=state.get("wrap", 260),
            justify="left",
            bg=bg_color,
            fg=fg_color,
            padx=2,
            pady=1,
        ).pack(anchor="w")

        tooltip.update_idletasks()

        x = widget.winfo_rootx() + 12
        y = widget.winfo_rooty() + widget.winfo_height() + 8
        screen_w = self.app.winfo_screenwidth()
        screen_h = self.app.winfo_screenheight()
        tip_w = tooltip.winfo_width()
        tip_h = tooltip.winfo_height()

        if x + tip_w > screen_w - 10:
            x = max(10, widget.winfo_rootx() - tip_w - 8)
        if y + tip_h > screen_h - 10:
            y = max(10, widget.winfo_rooty() - tip_h - 8)

        tooltip.geometry(f"+{int(x)}+{int(y)}")
        if hasattr(self.app, "reveal_modal"):
            self.app.reveal_modal(tooltip)
        else:
            tooltip.deiconify()
            tooltip.update()
            try:
                tooltip.attributes("-alpha", 1.0)
            except Exception:
                pass
        state["tooltip"] = tooltip


class OnboardingTour:
    """Interactive walkthrough used the first time the app opens."""

    def __init__(self, app: "App") -> None:
        self.app = app
        self._steps: list[dict[str, Any]] = []
        self._index = 0
        self._window: Optional[tb.Toplevel] = None
        self._active = False

    # ------------------------------------------------------------------
    def maybe_start(self) -> None:
        if self._active:
            return
        try:
            completed = self.app.settings_repo.get_setting("onboarding_completed", "0")
        except Exception:
            completed = "1"
        if completed == "1":
            return
        self.start()

    def start(self, *, force: bool = False) -> None:
        if self._active and not force:
            return

        if not force:
            try:
                completed = self.app.settings_repo.get_setting("onboarding_completed", "0")
            except Exception:
                completed = "1"
            if completed == "1":
                return

        if not hasattr(self.app, "btn_nav_dashboard"):
            return

        self._active = True
        self._steps = [
            {
                "title": "Bienvenido a PABLITO_POS",
                "body": "Te mostraremos las secciones clave en menos de un minuto. Usa ‘Siguiente’ para avanzar o ‘Saltar’ si prefieres explorarlo luego.",
                "target": None,
                "prepare": lambda: self.app.switch_view("dashboard"),
                "wrap": 360,
            },
            {
                "title": "Navegación principal",
                "body": "Estos botones te llevan al Dashboard, Ventas, Actualizar Información y Historial. También puedes usar Ctrl+1 a Ctrl+4 como atajos.",
                "target": lambda: getattr(self.app, "nav_frame", None),
                "wrap": 360,
            },
            {
                "title": "Ventas al instante",
                "body": "En la vista Ventas puedes buscar clientes, agregar productos y generar comprobantes con un clic.",
                "target": lambda: getattr(self.app, "btn_nav_sales", None),
                "prepare": lambda: self.app.switch_view("sales"),
                "wrap": 340,
            },
            {
                "title": "Exportar y verificar",
                "body": "Si un cliente necesita su comprobante o requieres un respaldo, usa Exportar o Verificar desde la barra superior.",
                "target": lambda: getattr(self.app, "btn_export", None),
                "wrap": 340,
            },
            {
                "title": "Ayuda permanente",
                "body": "Pulsa Guía para repetir este tour y deja el puntero quieto sobre cualquier botón para ver tips contextuales.",
                "target": lambda: getattr(self.app, "btn_guided_tour", None),
                "wrap": 340,
            },
            {
                "title": "Listo",
                "body": "Eso es todo. Presiona F1 en cualquier momento para ver los atajos del sistema.",
                "target": None,
                "wrap": 320,
            },
        ]
        self._show_step(0)

    def restart(self) -> None:
        try:
            self.app.settings_repo.set_setting("onboarding_completed", "0")
        except Exception:
            pass
        self._active = False
        self._steps = []
        self._destroy_window()
        self.app.after(200, lambda: self.start(force=True))

    # ------------------------------------------------------------------
    def _show_step(self, index: int) -> None:
        if not self._steps:
            self._complete()
            return
        if index < 0 or index >= len(self._steps):
            self._complete()
            return

        self._destroy_window()

        self._index = index
        step = self._steps[index]
        prepare = step.get("prepare")
        if callable(prepare):
            try:
                prepare()
            except Exception:
                pass

        self.app.after(120, lambda s=step, i=index: self._build_window(s, i))

    def _build_window(self, step: dict[str, Any], index: int) -> None:
        self._destroy_window()

        target_callable = step.get("target")
        target_widget: Optional[tk.Widget] = None
        if callable(target_callable):
            try:
                target_widget = cast(Optional[tk.Widget], target_callable())
            except Exception:
                target_widget = None
        elif target_callable:
            target_widget = cast(Optional[tk.Widget], target_callable)

        if target_widget and not getattr(target_widget, "winfo_exists", lambda: False)():
            target_widget = None

        win = tb.Toplevel(master=self.app)
        if hasattr(self.app, "begin_modal_construction"):
            self.app.begin_modal_construction(win)
        else:
            try:
                win.attributes("-alpha", 0.0)
            except Exception:
                pass
        win.overrideredirect(True)
        win.transient(self.app)
        try:
            win.attributes("-topmost", True)
        except Exception:
            pass
        win.bind("<Escape>", lambda _e: self._skip())

        container = tb.Frame(win, padding=0, bootstyle="secondary")
        container.pack(fill="both", expand=True)

        bubble_border = tb.Frame(container, padding=1, bootstyle="secondary")
        bubble_border.pack(fill="both", expand=True)

        bubble = tb.Frame(bubble_border, padding=16, bootstyle="light")
        bubble.pack(fill="both", expand=True)

        arrow_label = tb.Label(container, text="", font=("Segoe UI Symbol", 26), bootstyle="info")

        title = step.get("title")
        if title:
            tb.Label(bubble, text=title, font=("Segoe UI", 12, "bold"), bootstyle="dark").pack(anchor="w")

        tb.Label(
            bubble,
            text=step.get("body", ""),
            wraplength=step.get("wrap", 320),
            justify="left",
        ).pack(anchor="w", pady=(10, 14))

        btn_frame = tb.Frame(bubble)
        btn_frame.pack(fill="x", pady=(0, 4))

        tb.Button(
            btn_frame,
            text="Saltar",
            bootstyle="secondary",
            command=self._skip,
            width=10,
        ).pack(side="left")

        if index == len(self._steps) - 1:
            next_cmd: Callable[[], None] = self._complete
            next_text = "Finalizar"
        else:
            next_cmd = lambda: self._show_step(index + 1)
            next_text = "Siguiente"

        btn_next = tb.Button(btn_frame, text=next_text, bootstyle="primary", command=next_cmd, width=10)
        btn_next.pack(side="right")

        btn_prev = tb.Button(
            btn_frame,
            text="Anterior",
            bootstyle="secondary-outline",
            command=lambda: self._show_step(index - 1),
            width=10,
        )
        btn_prev.pack(side="right", padx=(6, 0))
        if index == 0:
            btn_prev.configure(state="disabled")

        # Medir tamaño del contenido sin flecha
        for child in container.pack_slaves():
            child.pack_forget()
        bubble_border.pack(fill="both", expand=True)
        bubble_border.update_idletasks()

        bubble_w = max(220, bubble_border.winfo_width())
        bubble_h = max(140, bubble_border.winfo_height())

        orientation, pos_x, pos_y, total_w, total_h = self._compute_geometry(target_widget, bubble_w, bubble_h)

        self._arrange_layout(container, arrow_label, bubble_border, orientation)

        win.update_idletasks()
        actual_w = max(total_w, win.winfo_width())
        actual_h = max(total_h, win.winfo_height())

        screen_w = self.app.winfo_screenwidth()
        screen_h = self.app.winfo_screenheight()
        pos_x = max(10, min(pos_x, screen_w - actual_w - 10))
        pos_y = max(10, min(pos_y, screen_h - actual_h - 10))
        win.geometry(f"{actual_w}x{actual_h}+{int(pos_x)}+{int(pos_y)}")
        if hasattr(self.app, "reveal_modal"):
            self.app.reveal_modal(win)
        else:
            win.deiconify()
            win.update()
            try:
                win.attributes("-alpha", 1.0)
            except Exception:
                pass
        win.lift(self.app)
        try:
            win.focus_force()
        except Exception:
            pass

        self._window = win

    def _compute_geometry(
        self,
        target_widget: Optional[tk.Widget],
        bubble_w: int,
        bubble_h: int,
    ) -> tuple[Optional[str], int, int, int, int]:
        screen_w = self.app.winfo_screenwidth()
        screen_h = self.app.winfo_screenheight()
        screen_margin = 10
        arrow_size = 48
        offset = 24

        if not target_widget:
            x = max(screen_margin, (screen_w - bubble_w) // 2)
            y = max(screen_margin, (screen_h - bubble_h) // 2)
            return None, x, y, bubble_w, bubble_h

        try:
            self.app.update_idletasks()
            tx = target_widget.winfo_rootx()
            ty = target_widget.winfo_rooty()
            tw = target_widget.winfo_width()
            th = target_widget.winfo_height()
        except Exception:
            x = max(screen_margin, (screen_w - bubble_w) // 2)
            y = max(screen_margin, (screen_h - bubble_h) // 2)
            return None, x, y, bubble_w, bubble_h

        candidates = [
            ("right", bubble_w + arrow_size, bubble_h, tx + tw + offset, ty + (th / 2) - (bubble_h / 2)),
            ("left", bubble_w + arrow_size, bubble_h, tx - (bubble_w + arrow_size) - offset, ty + (th / 2) - (bubble_h / 2)),
            ("bottom", bubble_w, bubble_h + arrow_size, tx + (tw / 2) - (bubble_w / 2), ty + th + offset),
            ("top", bubble_w, bubble_h + arrow_size, tx + (tw / 2) - (bubble_w / 2), ty - (bubble_h + arrow_size) - offset),
        ]

        for orient, total_w, total_h, raw_x, raw_y in candidates:
            x = int(raw_x)
            y = int(raw_y)
            if x < screen_margin or x + total_w > screen_w - screen_margin:
                continue
            if y < screen_margin or y + total_h > screen_h - screen_margin:
                continue
            return orient, x, y, int(total_w), int(total_h)

        orient, total_w, total_h, raw_x, raw_y = candidates[0]
        x = int(max(screen_margin, min(raw_x, screen_w - total_w - screen_margin)))
        y = int(max(screen_margin, min(raw_y, screen_h - total_h - screen_margin)))
        return orient, x, y, int(total_w), int(total_h)

    def _arrange_layout(
        self,
        container: tb.Frame,
        arrow_label: tb.Label,
        bubble_border: tb.Frame,
        orientation: Optional[str],
    ) -> None:
        for child in container.pack_slaves():
            child.pack_forget()

        arrow_label.configure(text="")

        if orientation == "right":
            arrow_label.configure(text="⬅")
            arrow_label.pack(side="left", padx=(0, 8), pady=6)
            bubble_border.pack(side="left", fill="both", expand=True)
        elif orientation == "left":
            bubble_border.pack(side="left", fill="both", expand=True)
            arrow_label.configure(text="➔")
            arrow_label.pack(side="left", padx=(8, 0), pady=6)
        elif orientation == "bottom":
            bubble_border.pack(side="top", fill="both", expand=True)
            arrow_label.configure(text="⬆")
            arrow_label.pack(side="top", pady=(6, 0))
        elif orientation == "top":
            arrow_label.configure(text="⬇")
            arrow_label.pack(side="top", pady=(0, 6))
            bubble_border.pack(side="top", fill="both", expand=True)
        else:
            bubble_border.pack(fill="both", expand=True)

    def _destroy_window(self) -> None:
        window = self._window
        if window and window.winfo_exists():
            try:
                window.destroy()
            except Exception:
                pass
        self._window = None

    def _complete(self) -> None:
        self._destroy_window()
        self._active = False
        self._steps = []
        try:
            self.app.settings_repo.set_setting("onboarding_completed", "1")
        except Exception:
            pass

    def _skip(self) -> None:
        self._complete()
