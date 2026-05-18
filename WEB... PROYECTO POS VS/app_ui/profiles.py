"""Profile selection UI helpers extracted from the main application window."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import ttkbootstrap as tb
from PIL import Image, ImageTk

if TYPE_CHECKING:  # pragma: no cover - used only for typing
    from app_boletas import App


class ProfileSelectionUI:
    """Encapsula la pantalla de selección de perfiles y acciones relacionadas."""

    def __init__(self, app: "App") -> None:
        self.app = app

    def _style_tokens(self) -> dict[str, str]:
        """Genera estilos sensibles al tema actual para reutilizarlos en la vista."""
        is_dark = self.app.is_dark_theme()
        return {
            "background": "dark" if is_dark else "light",
            "title": "danger" if is_dark else "primary",
            "subtitle": "light" if is_dark else "secondary",
            "card_border": "info" if is_dark else "secondary",
            "card": "dark" if is_dark else "light",
            "card_text": "inverse-dark" if is_dark else "primary",
            "no_logo": "secondary",
            "enter_button": "primary" if is_dark else "success",
            "hover_border": "success",
        }

    def show_profile_selection(self) -> None:
        app = self.app

        for widget in app.winfo_children():
            widget.destroy()

        app.title("Seleccionar Perfil - PABLITO_POS")

        styles = self._style_tokens()
        app.configure(bg=app._base_background_color())

        bg_frame = tb.Frame(app, padding=24, bootstyle=styles["background"])
        bg_frame.pack(fill="both", expand=True)

        btn_sec = tb.Button(
            bg_frame,
            text="🛡 Seguridad",
            bootstyle="secondary-outline",
            command=app.open_security_dashboard,
        )
        btn_sec.place(relx=0.98, rely=0.02, anchor="ne")

        btn_email = tb.Button(
            bg_frame,
            text="📧 Config Correo",
            bootstyle="secondary-outline",
            command=app.open_email_config_dialog,
        )
        btn_email.place(relx=0.88, rely=0.02, anchor="ne")
        app.add_help_tooltip(btn_email, "Configura el envío de comprobantes por correo electrónico.")

        center_container = tb.Frame(bg_frame)
        center_container.place(relx=0.5, rely=0.5, anchor="center")

        app.title_label = tb.Label(
            center_container,
            text=">> PABLITO_POS SYSTEM <<",
            font=("Segoe UI", 28, "bold"),
            bootstyle=styles["title"],
        )
        app.title_label.pack(pady=(0, 10))

        app.animate_rgb(app.title_label)

        tb.Label(
            center_container,
            text="TOQUE EL PERFIL PARA COMENZAR",
            font=("Segoe UI", 12, "bold"),
            bootstyle=styles["subtitle"],
        ).pack(pady=(0, 40))

        cards_frame = tb.Frame(center_container, bootstyle=styles["background"])
        cards_frame.pack()

        profiles = app.company_service.get_all_profiles()
        if not profiles:
            app.company_service.create_profile("Mi Empresa Default", "20000000001")
            profiles = app.company_service.get_all_profiles()

        columns = 5
        for col in range(columns):
            cards_frame.grid_columnconfigure(col, weight=1)
        for idx, profile in enumerate(profiles):
            row = idx // columns
            col = idx % columns
            self.create_profile_card(cards_frame, profile, row, col, styles)

        backup_frame = tb.Frame(bg_frame, bootstyle=styles["background"])
        backup_frame.place(relx=0.5, rely=0.95, anchor="s")

        btn_backup = tb.Button(
            backup_frame,
            text="💾 Crear Backup",
            bootstyle="info",
            command=app.create_manual_backup,
            width=20,
        )
        btn_backup.pack(side="left", padx=10)
        app.add_help_tooltip(btn_backup, "Genera una copia de seguridad inmediata de la base de datos.")

        btn_restore = tb.Button(
            backup_frame,
            text="📥 Restaurar Backup",
            bootstyle="warning",
            command=app.restore_backup,
            width=20,
        )
        btn_restore.pack(side="left", padx=10)
        app.add_help_tooltip(btn_restore, "Restaurar un respaldo previo desde un archivo .zip.")

    def create_profile_card(
        self,
        parent: tb.Frame,
        profile: dict,
        row: int,
        col: int,
        styles: dict[str, str] | None = None,
    ) -> None:
        app = self.app
        p_id = profile["id"]
        name = profile["name"]
        logo_path = profile["logo_path"]

        styles = styles or self._style_tokens()

        border_frame = tb.Frame(parent, bootstyle=styles["card_border"], padding=2)
        border_frame.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")

        card = tb.Frame(border_frame, bootstyle=styles["card"], padding=15)
        card.pack(fill="both", expand=True)

        def on_enter(_event: object) -> None:
            border_frame.configure(bootstyle=styles["hover_border"])

        def on_leave(_event: object) -> None:
            border_frame.configure(bootstyle=styles["card_border"])

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

        if logo_path and os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                img.thumbnail((120, 120))
                photo = ImageTk.PhotoImage(img)
                lbl_img = tb.Label(card, image=photo, bootstyle=styles["card"])
                setattr(lbl_img, "_photo_ref", photo)
                lbl_img.pack(pady=(0, 15))
                lbl_img.bind("<Enter>", on_enter)
                lbl_img.bind("<Leave>", on_leave)
            except Exception:
                tb.Label(
                    card,
                    text="[NO LOGO]",
                    font=("Courier New", 12, "bold"),
                    bootstyle=styles["no_logo"],
                ).pack(pady=(20, 35))
        else:
            tb.Label(
                card,
                text="[NO LOGO]",
                font=("Courier New", 12, "bold"),
                bootstyle=styles["no_logo"],
            ).pack(pady=(20, 35))

        name_lbl = tb.Label(
            card,
            text=name.upper(),
            font=("Segoe UI", 11, "bold"),
            wraplength=180,
            justify="center",
            bootstyle=styles["card_text"],
        )
        name_lbl.pack(pady=(0, 15))
        name_lbl.bind("<Enter>", on_enter)
        name_lbl.bind("<Leave>", on_leave)

        btn_frame = tb.Frame(card, bootstyle=styles["card"])
        btn_frame.pack(fill="x")

        tb.Button(
            btn_frame,
            text="ENTRAR",
            bootstyle=styles["enter_button"],
            command=lambda: app.select_profile(p_id),
            width=10,
        ).pack(side="top", fill="x", pady=(0, 10))

        action_frame = tb.Frame(btn_frame, bootstyle=styles["card"])
        action_frame.pack(side="top", fill="x")
        action_frame.columnconfigure((0, 1), weight=1)

        tb.Button(
            action_frame,
            text="⚙",
            bootstyle="warning-outline",
            width=4,
            command=lambda: app.edit_profile_dialog(p_id),
        ).grid(row=0, column=0, padx=2, sticky="ew")

        tb.Button(
            action_frame,
            text="🗑",
            bootstyle="danger-outline",
            width=4,
            command=lambda: self.delete_profile_action(p_id),
        ).grid(row=0, column=1, padx=2, sticky="ew")

    def delete_profile_action(self, profile_id: int) -> None:
        app = self.app
        if not app.ask_pin("Eliminar Perfil"):
            return

        confirm = app.show_question(
            "¿Está seguro de eliminar este perfil?\nSe ocultará de la lista pero se mantendrá el historial.",
            "Confirmar Eliminación",
        )
        if confirm:
            app.company_service.delete_profile(profile_id)
            self.show_profile_selection()
