"""Overlay opcional con copos y siluetas festivas.

Se activa/desactiva sin modificar la interfaz principal.
"""

from __future__ import annotations

import math
import random
import tkinter as tk
from typing import Any, List, Optional


class HolidayOverlay:
    """Capa de nieve/siluetas que se superpone a la ventana principal."""

    def __init__(self, app: tk.Tk, *, flakes: int = 60, use_background: bool = True) -> None:
        self.app = app
        self.target_flakes = flakes
        self.use_background = use_background
        self.overlay: Optional[tk.Toplevel] = None
        self.canvas: Optional[tk.Canvas] = None
        self.flakes: List[dict[str, Any]] = []
        self.after_id: Optional[str] = None
        self._bound = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def is_running(self) -> bool:
        return self.canvas is not None

    def start(self) -> None:
        if self.canvas:
            return

        bg_color = self.app.cget("background") or "#000000"
        prev_children = list(self.app.winfo_children())

        if self.use_background:
            # Canvas pegado a la ventana, colocado al fondo para no bloquear clics.
            self.canvas = tk.Canvas(self.app, bg=bg_color, highlightthickness=0, bd=0, state=tk.DISABLED)
            self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._lower_canvas(prev_children)
            # Por si otros frames aparecen luego, refuerza el z-order tras un breve delay.
            self.app.after(50, lambda: self._lower_canvas(prev_children))
        else:
            # Fallback: Toplevel con alpha suave (puede bloquear si el SO no respeta -disabled).
            self.overlay = tk.Toplevel(self.app)
            self.overlay.withdraw()
            self.overlay.overrideredirect(True)
            self.overlay.attributes("-topmost", True)
            self.overlay.configure(bg=bg_color)
            self.canvas = tk.Canvas(self.overlay, bg=bg_color, highlightthickness=0, bd=0)
            self.canvas.pack(fill="both", expand=True)
            self._apply_transparency()
            try:
                self.overlay.attributes("-disabled", True)
            except tk.TclError:
                pass
            self._sync_geometry()

        self._create_scene()

        if not self._bound:
            self.app.bind("<Configure>", self._on_root_configure, add=True)
            self._bound = True

        if self.overlay:
            self.overlay.deiconify()
        self._tick()

    def _lower_canvas(self, baseline: Optional[list[tk.Misc]] = None) -> None:
        if not self.canvas:
            return
        try:
            self.canvas.lower()
            target = None
            if baseline:
                target = baseline[-1] if baseline else None
            if target:
                self.canvas.lower(target)
        except Exception:
            pass

    def _apply_transparency(self) -> None:
        if not self.overlay:
            return
        try:
            self.overlay.attributes("-alpha", 0.06)
        except tk.TclError:
            pass

    def stop(self) -> None:
        if self.after_id and self.canvas:
            self.canvas.after_cancel(self.after_id)
        self.after_id = None
        self.flakes.clear()
        if self.overlay:
            try:
                self.overlay.destroy()
            except Exception:
                pass
        if self.canvas:
            try:
                self.canvas.destroy()
            except Exception:
                pass
        self.overlay = None
        self.canvas = None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _on_root_configure(self, _event: tk.Event | None = None) -> None:
        if self.use_background:
            return
        if self.overlay:
            self._sync_geometry()

    def _sync_geometry(self) -> None:
        if not self.overlay:
            return
        x = self.app.winfo_rootx()
        y = self.app.winfo_rooty()
        w = self.app.winfo_width()
        h = self.app.winfo_height()
        if w < 50 or h < 50:
            return
        self.overlay.geometry(f"{w}x{h}+{x}+{y}")
        if self.canvas:
            self.canvas.config(width=w, height=h)

    def _is_dark_theme(self) -> bool:
        try:
            bg = self.app.cget("background") or "#101010"
            r, g, b = [c / 65535.0 for c in self.app.winfo_rgb(bg)]
            return (0.299 * r + 0.587 * g + 0.114 * b) < 0.5
        except Exception:
            return True

    def _create_scene(self) -> None:
        if not self.canvas:
            return
        self.canvas.delete("all")
        dark = self._is_dark_theme()
        self._spawn_flakes(dark)

    def _spawn_flakes(self, dark: bool) -> None:
        if not self.canvas:
            return
        w = max(self.canvas.winfo_width(), 400)
        h = max(self.canvas.winfo_height(), 300)
        palette_light = ["#e2e8f0", "#f8fafc", "#cbd5f5", "#9ae6ff"]
        palette_dark = ["#f8fafc", "#e0f2ff", "#bfe1ff", "#a5b4fc"]
        palette = palette_light if dark else palette_dark
        self.flakes = []
        self.canvas.delete("flake")
        for _ in range(self.target_flakes):
            r = random.uniform(2.0, 5.0)
            x = random.uniform(0, w)
            y = random.uniform(0, h)
            speed = random.uniform(0.8, 2.0)
            drift = random.uniform(-0.4, 0.4)
            wobble = random.uniform(0, math.pi * 2)
            color = random.choice(palette)
            flake_id = self.canvas.create_oval(
                x - r,
                y - r,
                x + r,
                y + r,
                fill=color,
                outline="",
                tags=("flake",),
            )
            self.flakes.append(
                {
                    "id": flake_id,
                    "x": x,
                    "y": y,
                    "r": r,
                    "speed": speed,
                    "drift": drift,
                    "wobble": wobble,
                }
            )

    def _tick(self) -> None:
        if not self.canvas:
            return
        w = max(self.canvas.winfo_width(), 1)
        h = max(self.canvas.winfo_height(), 1)

        for flake in self.flakes:
            flake["wobble"] += 0.05
            flake["y"] += flake["speed"]
            flake["x"] += flake["drift"] + math.sin(flake["wobble"]) * 0.3

            if flake["y"] - flake["r"] > h:
                flake["y"] = -flake["r"]
                flake["x"] = random.uniform(0, w)
            if flake["x"] < -10:
                flake["x"] = w + 5
            if flake["x"] > w + 10:
                flake["x"] = -5

            r = flake["r"]
            self.canvas.coords(
                flake["id"],
                flake["x"] - r,
                flake["y"] - r,
                flake["x"] + r,
                flake["y"] + r,
            )

        self.after_id = self.canvas.after(30, self._tick)


__all__ = ["HolidayOverlay"]
