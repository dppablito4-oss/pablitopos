"""Centralised logging and crash handling utilities."""

from __future__ import annotations

import logging
import os
import sys
from typing import Callable


def setup_error_logging(base_dir: str) -> str:
    """Configure error logging and install a global crash handler.

    Returns the file path used to persist error logs so callers can surface it
    in the UI when something goes wrong.
    """
    log_path = os.path.join(base_dir, "app_errors.log")

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.ERROR)
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)

    sys.excepthook = _build_exception_hook(log_path)
    return log_path


def _build_exception_hook(log_path: str) -> Callable[[type[BaseException], BaseException, object], None]:
    """Return a sys.excepthook compatible callable bound to ``log_path``."""

    def handle_uncaught_exception(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: object) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logging.critical(
            "CRASH NO CONTROLADO:",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

        try:
            # Intentar mostrar un diálogo estilizado con ttkbootstrap si está disponible.
            try:
                from ttkbootstrap.dialogs import Messagebox as TBMessagebox  # type: ignore
                TBMessagebox.show_error(
                    "Error Crítico",
                    (
                        "Ocurrió un error inesperado.\n\n"
                        f"Detalle: {exc_value}\n\n"
                        "Se ha guardado un registro en:\n"
                        f"{log_path}"
                    ),
                )
            except Exception:
                # Caer a tkinter.messagebox como último recurso.
                from tkinter import messagebox

                messagebox.showerror(
                    "Error Crítico",
                    (
                        "Ocurrió un error inesperado.\n\n"
                        f"Detalle: {exc_value}\n\n"
                        "Se ha guardado un registro en:\n"
                        f"{log_path}"
                    ),
                )
        except Exception:
            # Si no es posible mostrar diálogo (por ejemplo, crash antes de crear la UI),
            # dejamos el log registrado y continuamos.
            pass

    return handle_uncaught_exception
