"""Reusable message and dialog helpers extracted from the main window."""

from __future__ import annotations

from typing import Any, Iterable, Optional, TYPE_CHECKING

import ttkbootstrap as tb

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app_boletas import App


class MessageUI:
    """Centraliza diálogos personalizados de la aplicación."""

    def __init__(self, app: "App") -> None:
        self.app = app

    def show_custom_message(
        self,
        title: str,
        message: str,
        icon_name: str = "info",
        bootstyle: str = "info",
        buttons: Optional[Iterable[dict[str, Any]]] = None,
    ) -> None:
        app = self.app
        
        # Determinar la ventana padre correcta para evitar problemas de z-order
        parent = app
        try:
            focus_w = app.focus_get()
            if focus_w:
                toplevel = focus_w.winfo_toplevel()
                if toplevel:
                    parent = toplevel
        except Exception:
            pass

        dialog = tb.Toplevel(master=parent)
        dialog.attributes("-alpha", 0.0)
        dialog.title(title)
        dialog.geometry("420x250")

        try:
            app.set_app_icon(dialog)
        except Exception:
            pass

        main_frame = tb.Frame(dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        header_frame = tb.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 15))

        icons = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "question": "❓",
            "success": "✅",
        }
        icon_char = icons.get(icon_name, "ℹ️")

        tb.Label(
            header_frame,
            text=f"{icon_char}  {title}",
            font=("Helvetica", 14, "bold"),
            bootstyle=bootstyle,
        ).pack(side="left")

        msg_frame = tb.Frame(main_frame)
        msg_frame.pack(fill="both", expand=True)

        tb.Label(
            msg_frame,
            text=message,
            font=("Helvetica", 10),
            wraplength=380,
            justify="left",
        ).pack(pady=10, anchor="w")

        btn_frame = tb.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(15, 0))

        if not buttons:
            def on_ok() -> None:
                dialog.destroy()

            ok_btn = tb.Button(
                btn_frame,
                text="Aceptar",
                bootstyle=bootstyle,
                command=on_ok,
                width=15,
            )
            ok_btn.pack(side="right")
            ok_btn.focus_set()

            dialog.bind("<Return>", lambda _e: on_ok())
            dialog.bind("<Escape>", lambda _e: on_ok())
        else:
            created = []
            for btn in buttons:
                command = btn.get("command", lambda: None)

                def make_cmd(callable_: Any) -> Any:
                    def wrapper() -> None:
                        callable_()
                        dialog.destroy()

                    return wrapper

                b = tb.Button(
                    btn_frame,
                    text=btn.get("text", "Button"),
                    bootstyle=btn.get("style", "secondary"),
                    command=make_cmd(command),
                    width=12,
                )
                b.pack(side="right", padx=5)
                created.append(b)

            if created:
                created[-1].focus_set()
            dialog.bind("<Return>", lambda _e: created[-1].invoke() if created else None)
            dialog.bind("<Escape>", lambda _e: dialog.destroy())

        dialog.update_idletasks()
        app.center_window(dialog, 420, 250)
        dialog.deiconify()
        dialog.update()
        dialog.attributes("-alpha", 1.0)
        app.make_modal(dialog, parent=parent)
        app.wait_window(dialog)

    def show_info(self, title: str, message: str) -> None:
        self.show_custom_message(title, message, "info", "info")

    def show_warning(self, title: str, message: str) -> None:
        self.show_custom_message(title, message, "warning", "warning")

    def show_error(self, title: str, message: str) -> None:
        self.show_custom_message(title, message, "error", "danger")

    def show_success(self, title: str, message: str, use_toast: bool = False, duration: int = 3200) -> None:
        if use_toast:
            self.app.show_toast(title, message, level="success", duration=duration)
        else:
            self.show_custom_message(title, message, "success", "success")

    def show_question(self, title: str, message: str) -> bool:
        result = False

        def on_yes() -> None:
            nonlocal result
            result = True

        def on_no() -> None:
            nonlocal result
            result = False

        buttons = [
            {"text": "No", "command": on_no, "style": "secondary"},
            {"text": "Sí", "command": on_yes, "style": "primary"},
        ]

        self.show_custom_message(title, message, "question", "primary", buttons)
        return result
