"""Keyboard shortcuts and input helpers extracted from the main window."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

import tkinter as tk
import ttkbootstrap as tb

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app_boletas import App


class HotkeyUI:
    """Centraliza la configuración de atajos y compatibilidad de scroll."""

    def __init__(self, app: "App") -> None:
        self.app = app

    # ------------------------------------------------------------------
    # Hotkey setup
    # ------------------------------------------------------------------
    def setup_hotkeys(self) -> None:
        app = self.app

        # Navegación principal
        app.bind("<Control-Key-1>", lambda _e: app.switch_view("dashboard"))
        app.bind("<Control-Key-2>", lambda _e: app.switch_view("sales"))
        app.bind("<Control-Key-3>", lambda _e: app.switch_view("update"))
        app.bind("<Control-Key-4>", lambda _e: app.switch_view("history"))

        # Ventas
        app.bind("<F3>", self.focus_product_search)
        app.bind("<Control-f>", self.focus_product_search)
        app.bind("<F4>", self.focus_client_search)
        app.bind("<F5>", lambda _e: app.sales_ui.reset_sale_form())
        app.bind("<F10>", lambda _e: app.sales_ui.save_sale_and_generate_pdf())
        app.bind("<Control-Return>", lambda _e: app.sales_ui.save_sale_and_generate_pdf())
        app.bind("<Delete>", self.delete_item_shortcut)
        app.bind("<Control-c>", self.copy_selection)
        app.bind("<Control-C>", self.copy_selection)
        app.bind("<Control-v>", self.paste_into_focus)
        app.bind("<Control-V>", self.paste_into_focus)
        app.bind("<Control-x>", self.cut_selection)
        app.bind("<Control-X>", self.cut_selection)
        app.bind("<Control-z>", self.undo_action)
        app.bind("<Control-Z>", self.undo_action)

        # Sistema
        app.bind("<Escape>", self.on_escape)
        app.bind("<F1>", self.show_shortcuts_help)
        app.bind("<Control-Shift-L>", lambda _e: app.toggle_decoration_mode())
        app.bind("<Control-Shift-l>", lambda _e: app.toggle_decoration_mode())
        app.bind("<Control-Shift-K>", lambda _e: app.cycle_decoration_speed())
        app.bind("<Control-Shift-k>", lambda _e: app.cycle_decoration_speed())

    # ------------------------------------------------------------------
    # Mouse wheel compatibility
    # ------------------------------------------------------------------
    def setup_global_mousewheel_support(self) -> None:
        app = self.app
        if getattr(app, "_mousewheel_bound", False):
            return

        app.bind_all("<MouseWheel>", self._on_global_mousewheel, add="+")
        app.bind_all("<Button-4>", lambda e: self._on_global_mousewheel_linux(e, -1), add="+")
        app.bind_all("<Button-5>", lambda e: self._on_global_mousewheel_linux(e, 1), add="+")
        app._mousewheel_bound = True

    def _on_global_mousewheel(self, event: tk.Event) -> str:
        target = self._locate_scroll_target(event.widget)
        if target:
            delta = -int(event.delta / 120) if event.delta else 0
            if delta:
                try:
                    target.yview_scroll(delta, "units")
                except Exception:
                    pass
        return "break"

    def _on_global_mousewheel_linux(self, event: tk.Event, direction: int) -> str:
        target = self._locate_scroll_target(event.widget)
        if target:
            try:
                target.yview_scroll(direction, "units")
            except Exception:
                pass
        return "break"

    @staticmethod
    def _locate_scroll_target(widget: tk.Misc | None) -> Any:
        current = widget
        while current is not None:
            if hasattr(current, "yview_scroll") and callable(getattr(current, "yview_scroll")):
                return current
            current = getattr(current, "master", None)
        return None

    # ------------------------------------------------------------------
    # Hotkey handlers
    # ------------------------------------------------------------------
    def focus_product_search(self, _event: tk.Event | None = None) -> None:
        app = self.app
        app.switch_view("sales")
        widget = getattr(app, "entry_search_prod", None)
        if widget:
            widget.focus_set()
            widget.select_range(0, tk.END)

    def focus_client_search(self, _event: tk.Event | None = None) -> None:
        app = self.app
        app.switch_view("sales")
        widget = getattr(app, "entry_search_cli", None)
        if widget:
            widget.focus_set()
            widget.select_range(0, tk.END)

    def delete_item_shortcut(self, _event: tk.Event | None = None) -> None:
        app = self.app
        focus_widget = app.focus_get()

        # Si hay un toplevel activo (modal), no borrar ítems con Supr
        try:
            if focus_widget is not None and focus_widget.winfo_toplevel() is not app:
                return
        except Exception:
            pass

        # Evitar borrar ítems cuando se está escribiendo en cualquier Entry/Text
        if focus_widget is not None:
            cls_name = focus_widget.__class__.__name__.lower()
            if isinstance(focus_widget, (tk.Entry, tk.Text, tb.Entry, tb.Text)) or "entry" in cls_name or "text" in cls_name:
                return

        active_view = getattr(app, "_active_view", None)

        # Ventas: eliminar item del carrito
        if active_view == "sales" and getattr(app, "sales_ui", None):
            tree_detail = getattr(app, "tree_detail", None)
            if tree_detail and not (tree_detail.focus() or tree_detail.selection()):
                return
            app.sales_ui.delete_selected_item()
            return

        # Actualizar Info: eliminar cliente o producto según foco/selección
        if active_view == "update":
            tree_cli = getattr(app, "tree_clients", None)
            tree_prod = getattr(app, "tree_products", None)

            # Prioriza el árbol que tiene selección
            if tree_cli:
                focused = tree_cli.focus() or (tree_cli.selection()[0] if tree_cli.selection() else "")
                if focused:
                    if getattr(app, "client_ui", None):
                        values = tree_cli.item(focused, "values") or []
                        if values:
                            app.selected_client_id = values[0]
                        app.client_ui.delete_client_action()
                    return

            if tree_prod:
                focused = tree_prod.focus() or (tree_prod.selection()[0] if tree_prod.selection() else "")
                if focused:
                    if getattr(app, "product_ui", None):
                        values = tree_prod.item(focused, "values") or []
                        if values:
                            app.var_prod_id.set(values[0])
                        app.product_ui.delete_product_action()
                    return

    # --- Clipboard helpers for Treeviews ---
    def _copy_tree_selection(self, tree: tk.Misc | None) -> bool:
        if not tree:
            return False
        focused = tree.focus() or (tree.selection()[0] if tree.selection() else "")
        if not focused:
            return False
        values = tree.item(focused, "values") or []
        if not values:
            return False
        text = "\t".join(str(v) for v in values)
        try:
            self.app.clipboard_clear()
            self.app.clipboard_append(text)
            return True
        except Exception:
            return False

    def copy_selection(self, _event: tk.Event | None = None) -> None:
        app = self.app
        # If focus is Entry/Text, let default behavior work
        focus_widget = app.focus_get()
        if isinstance(focus_widget, (tk.Entry, tk.Text, tb.Entry, tb.Text)):  # type: ignore[attr-defined]
            return

        active_view = getattr(app, "_active_view", None)
        if active_view == "update":
            if self._copy_tree_selection(getattr(app, "tree_clients", None)):
                return
            self._copy_tree_selection(getattr(app, "tree_products", None))

    def cut_selection(self, event: tk.Event | None = None) -> None:
        # Only meaningful in editable entries/text; let default for them
        focus_widget = self.app.focus_get()
        if isinstance(focus_widget, (tk.Entry, tk.Text, tb.Entry, tb.Text)):
            return
        # For trees, treat cut as copy
        self.copy_selection(event)

    def paste_into_focus(self, event: tk.Event | None = None) -> None:
        # Let default paste for text-like widgets; otherwise no-op
        focus_widget = self.app.focus_get()
        if isinstance(focus_widget, (tk.Entry, tk.Text, tb.Entry, tb.Text)):
            return

    def undo_action(self, _event: tk.Event | None = None) -> None:
        app = self.app
        if getattr(app, "_active_view", None) == "update":
            app.undo_last_delete()

    def on_escape(self, _event: tk.Event | None = None) -> None:
        self.app.focus_set()

    def show_shortcuts_help(self, _event: tk.Event | None = None) -> None:
        msg = """ATAJOS DE TECLADO (MODO PRO)

NAVEGACIÓN:
[Ctrl + 1]  Dashboard
[Ctrl + 2]  Ventas / Boletas
[Ctrl + 3]  Actualizar Info
[Ctrl + 4]  Historial

VENTAS:
[F3] o [Ctrl+F]  Buscar Producto
[F4]             Buscar Cliente
[F5]             Nueva Venta (Limpiar)
[F10] o [Ctrl+Enter]  COBRAR (Guardar)
[Supr]           Eliminar Ítem
[Enter]          Agregar Producto / Confirmar

SISTEMA:
[F1]   Esta Ayuda
[ESC]  Cancelar / Quitar Foco
"""
        self.app.show_info("⌨ Atajos de Teclado", msg)
