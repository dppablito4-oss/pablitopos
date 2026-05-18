"""Visual effects and toast notifications extracted from the main application."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING, cast

import tkinter as tk
import ttkbootstrap as tb

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app_boletas import App


class EffectsUI:
    """Centraliza efectos visuales (toasts, animaciones RGB, etc.)."""

    def __init__(self, app: "App") -> None:
        self.app = app
        self._rgb_job: Optional[str] = None

    # ------------------------------------------------------------------
    # Toast notifications
    # ------------------------------------------------------------------
    def show_toast(self, title: str, message: str, level: str = "success", duration: int = 3200) -> None:
        app = self.app
        is_dark = app.is_dark_theme()
        success_bg = "#1DB954" if is_dark else "#2ECC71"
        palette = {
            "success": (success_bg, "#ffffff"),
            "info": (success_bg, "#ffffff"),
            "warning": ("#ffc107", "#212529"),
            "error": ("#dc3545", "#ffffff"),
        }

        bg_color, fg_color = palette.get(level, (success_bg, "#ffffff"))

        try:
            app.update_idletasks()
            toast = tk.Toplevel(app)
            if hasattr(app, "begin_modal_construction"):
                app.begin_modal_construction(toast)
            else:
                try:
                    toast.attributes("-alpha", 0.0)
                except Exception:
                    pass
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            toast.configure(bg=bg_color, highlightthickness=0)

            container = tk.Frame(toast, bg=bg_color, padx=16, pady=12, highlightthickness=0, bd=0)
            container.pack(fill="both", expand=True)

            labels: list[tk.Label] = []
            if title:
                lbl_title = tk.Label(
                    container,
                    text=title,
                    font=("Segoe UI", 10, "bold"),
                    bg=bg_color,
                    fg=fg_color,
                    anchor="w",
                )
                lbl_title.pack(anchor="w")
                labels.append(lbl_title)
            if message:
                lbl_msg = tk.Label(
                    container,
                    text=message,
                    font=("Segoe UI", 9),
                    bg=bg_color,
                    fg=fg_color,
                    justify="left",
                    anchor="w",
                )
                lbl_msg.pack(anchor="w", pady=(4, 0))
                labels.append(lbl_msg)

            def apply_colors() -> None:
                try:
                    toast.configure(bg=bg_color, highlightthickness=0)
                    container.configure(bg=bg_color)
                    for lbl in labels:
                        lbl.configure(bg=bg_color, fg=fg_color)
                except tk.TclError:
                    pass

            apply_colors()
            toast.after_idle(apply_colors)

            toast.update_idletasks()

            parent_x = app.winfo_rootx()
            parent_y = app.winfo_rooty()
            parent_w = max(app.winfo_width(), 1)

            width = toast.winfo_width()
            height = toast.winfo_height()

            x = parent_x + parent_w - width - 24
            y = parent_y + 20

            toast.geometry(f"{width}x{height}+{int(x)}+{int(y)}")
            if hasattr(app, "reveal_modal"):
                app.reveal_modal(toast)
            else:
                toast.deiconify()
                toast.update()
                try:
                    toast.attributes("-alpha", 1.0)
                except Exception:
                    pass

            def close_toast(*_args: object) -> None:
                if toast.winfo_exists():
                    toast.destroy()

            toast.after(duration, close_toast)
            toast.bind("<Button-1>", close_toast)
        except Exception:
            if hasattr(app, "message_ui"):
                app.show_custom_message(title, message, level, level)

    # ------------------------------------------------------------------
    # Animaciones RGB
    # ------------------------------------------------------------------
    def animate_rgb(self, label: tk.Widget, step: int = 0) -> None:
        colors = ["#ff0000", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#ff00ff"]
        app = self.app

        try:
            if not label.winfo_exists():
                return
        except tk.TclError:
            return

        current_color = colors[step % len(colors)]
        label_widget = cast(Any, label)
        try:
            label_widget.configure(foreground=current_color)
        except tk.TclError:
            pass

        app.after(600, lambda: self.animate_rgb(label, step + 1))

    def stop_rgb_animation(self) -> None:
        app = self.app
        if self._rgb_job:
            try:
                app.after_cancel(self._rgb_job)
            except tk.TclError:
                pass
            self._rgb_job = None

    def animate_active_button(self, btn: tb.Button, step: int = 0) -> None:
        colors = [
            "primary",
            "info",
            "success",
            "warning",
            "danger",
            "secondary",
        ]

        try:
            btn.configure(bootstyle=colors[step % len(colors)])
        except tk.TclError:
            return

        self._rgb_job = self.app.after(500, lambda: self.animate_active_button(btn, step + 1))