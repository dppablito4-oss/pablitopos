import os
import threading
from datetime import datetime
from typing import Any, List, Optional

import tkinter as tk
import ttkbootstrap as tb

from settings import PDF_DIR
from utils import ensure_country_prefix, normalize_phone_number, build_whatsapp_message


class ToolTip:
	def __init__(self, widget, text):
		self.widget = widget
		self.text = text
		self.tip_window = None
		self.widget.bind("<Enter>", self.show_tip)
		self.widget.bind("<Leave>", self.hide_tip)

	def show_tip(self, event=None):
		if self.tip_window or not self.text:
			return
		x, y, _cx, cy = self.widget.bbox("insert")
		x = x + self.widget.winfo_rootx() + 25
		y = y + cy + self.widget.winfo_rooty() + 25
		self.tip_window = tw = tb.Toplevel(self.widget)
		tw.wm_overrideredirect(True)
		tw.wm_geometry(f"+{x}+{y}")
		
		# Contenedor con borde azul/acento
		container = tb.Frame(tw, bootstyle="primary", padding=1)
		container.pack()
		
		# Etiqueta con fondo oscuro y texto claro
		label = tb.Label(
			container, 
			text=self.text, 
			justify="left",
			background="#0f172a", 
			foreground="#ffffff",
			font=("Segoe UI", 9),
			padding=(8, 4)
		)
		label.pack()

	def hide_tip(self, event=None):
		tw = self.tip_window
		self.tip_window = None
		if tw:
			tw.destroy()


class HistoryUIManager:
	"""Gestiona la vista de historial de comprobantes."""

	def __init__(self, app: Any, frame: tb.Frame) -> None:
		self.app = app
		self.frame = frame
		self.entry_history_search: Optional[tb.Entry] = None
		self.entry_search_boletas: Optional[tb.Entry] = None
		self.combo_boletas: Optional[tb.Combobox] = None
		self.tree_history: Optional[tb.Treeview] = None
		self.scroll_frame: Optional[tb.Frame] = None
		self.scroll_canvas: Optional[tb.Canvas] = None
		self.boleta_list: List = []
		self._search_job = None
		self.history_filter = tk.StringVar(value="boletas")

	def build_ui(self) -> None:
		f = self.frame
		for widget in f.winfo_children():
			widget.destroy()

		# 1. Buscador
		search_lf = tb.Labelframe(
			f,
			text="🔍 Buscar Comprobantes por Cliente",
			padding=10,
			bootstyle="info",
		)
		search_lf.pack(fill="x", padx=10, pady=10)

		tb.Label(search_lf, text="DNI / Nombre:").pack(side="left", padx=5)
		self.entry_history_search = tb.Entry(search_lf)
		self.entry_history_search.pack(side="left", fill="x", expand=True, padx=5)
		self.entry_history_search.bind("<KeyRelease>", self.on_search_keyrelease)

		tb.Button(
			search_lf,
			text="Buscar",
			bootstyle="success",
			command=self.search_sales_history,
		).pack(side="left", padx=5)

		filter_frame = tb.Frame(search_lf)
		filter_frame.pack(side="left", padx=10)
		tb.Radiobutton(
			filter_frame,
			text="Boletas + Proformas",
			variable=self.history_filter,
			value="boletas",
			bootstyle="primary-toolbutton",
			command=self.search_sales_history,
		).pack(side="left", padx=2)
		tb.Radiobutton(
			filter_frame,
			text="Boletines + Adelantos",
			variable=self.history_filter,
			value="boletines",
			bootstyle="warning-toolbutton",
			command=self.search_sales_history,
		).pack(side="left", padx=2)
		tb.Radiobutton(
			filter_frame,
			text="Fiados",
			variable=self.history_filter,
			value="fiados",
			bootstyle="info-toolbutton",
			command=self.search_sales_history,
		).pack(side="left", padx=2)

		# 2. Encabezados de la lista
		headers_frame = tb.Frame(f, bootstyle="secondary")
		headers_frame.pack(fill="x", padx=10, pady=(10, 0))
		
		# Definir columnas con pesos para el grid
		headers_frame.columnconfigure(0, weight=1) # Fecha
		headers_frame.columnconfigure(1, weight=1) # Boleta
		headers_frame.columnconfigure(2, weight=3) # Cliente
		headers_frame.columnconfigure(3, weight=1) # Total
		headers_frame.columnconfigure(4, weight=0) # Acciones (ancho fijo aprox)

		h_font = ("Segoe UI", 9, "bold")
		tb.Label(headers_frame, text="FECHA", font=h_font, bootstyle="inverse-secondary").grid(row=0, column=0, sticky="w", padx=5, pady=5)
		tb.Label(headers_frame, text="DOCUMENTO", font=h_font, bootstyle="inverse-secondary").grid(row=0, column=1, sticky="w", padx=5, pady=5)
		tb.Label(headers_frame, text="CLIENTE", font=h_font, bootstyle="inverse-secondary").grid(row=0, column=2, sticky="w", padx=5, pady=5)
		tb.Label(headers_frame, text="TOTAL", font=h_font, bootstyle="inverse-secondary").grid(row=0, column=3, sticky="e", padx=5, pady=5)
		tb.Label(headers_frame, text="ACCIONES", font=h_font, bootstyle="inverse-secondary").grid(row=0, column=4, padx=20, pady=5)

		# 3. Contenedor Scrollable para filas
		list_container = tb.Frame(f)
		list_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
		
		self.scroll_canvas = tb.Canvas(list_container, highlightthickness=0, bd=0)
		self.scroll_scrollbar = tb.Scrollbar(list_container, orient="vertical", command=self.scroll_canvas.yview)
		self.scroll_frame = tb.Frame(self.scroll_canvas)
		
		self.scroll_frame.bind(
			"<Configure>",
			lambda e: self.scroll_canvas.configure(
				scrollregion=self.scroll_canvas.bbox("all")
			)
		)
		
		self.scroll_canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
		self.scroll_canvas.configure(yscrollcommand=self.scroll_scrollbar.set)
		
		self.scroll_canvas.pack(side="left", fill="both", expand=True)
		self.scroll_scrollbar.pack(side="right", fill="y")
		
		# Ajustar ancho del frame interno al canvas
		def _on_canvas_resize(event):
			self.scroll_canvas.itemconfig(self.scroll_canvas.find_withtag("all")[0], width=event.width)
		self.scroll_canvas.bind("<Configure>", _on_canvas_resize)

		# Bind mousewheel
		self.scroll_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

		try:
			SalesUIHelpers.bind_mousewheel_to_children(self.scroll_frame)
		except Exception:
			pass
		# 4. Botones globales (solo Exportar)
		btn_frame = tb.Frame(f)
		btn_frame.pack(fill="x", padx=10, pady=10)

		tb.Button(
			btn_frame,
			text="📊 Exportar Reporte",
			bootstyle="success",
			command=self.app.open_export_dialog,
		).pack(side="right", padx=10)
		
		self.app.setup_uppercase_entry(self.entry_history_search)
		self.search_sales_history()

	def _on_mousewheel(self, event):
		if self.scroll_canvas.winfo_exists():
			self.scroll_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

	def on_tree_click(self, event) -> None:
		pass

	def refresh_tree(self) -> None:
		self.search_sales_history()

	def on_search_keyrelease(self, event=None) -> None:
		if self._search_job:
			try:
				self.app.after_cancel(self._search_job)
			except Exception:
				pass
			self._search_job = None
		self._search_job = self.app.after(500, self.search_sales_history)

	def _finish_view_pdf(self, pdf_path: str | None, err_msg: str | None) -> None:
		self.app.hide_loading()
		if pdf_path:
			try:
				self.app.open_pdf(pdf_path)
			except Exception as exc:
				self.app.show_error("Error al abrir PDF", f"{exc}\nRuta: {pdf_path}")
		else:
			self.app.show_error("Error", f"No se pudo generar el PDF:\n{err_msg or 'Fallo desconocido'}")

	def view_or_regenerate_pdf(self, sale_id=None) -> None:
		if not sale_id:
			self.app.show_warning("Atención", "No se especificó una boleta.")
			return

		sale, _items = self.app.sale_service.get_sale(sale_id)
		if not sale:
			self.app.show_error("Error", "No se pudo recuperar la venta.")
			return

		sale_map = self.app.sale_service.map_sale_row(sale)
		self.app.show_loading("Generando PDF...")

		def task():
			err_msg = None
			try:
				pdf_path = self.app.pdf_service.generate_sale_pdf(
					sale_id,
					output_dir="temp",
					company_profile=self.app.current_company_data,
				)
				success_path = pdf_path
			except Exception as exc:
				success_path = None
				err_msg = str(exc)
			self.app.after(0, lambda p=success_path, msg=err_msg if success_path is None else None: self._finish_view_pdf(p, msg))

		threading.Thread(target=task, daemon=True).start()

	def view_fiado_pdf(self, fiado_id: int | None) -> None:
		if not fiado_id:
			self.app.show_warning("Fiado", "No se pudo identificar el fiado seleccionado.")
			return
		if not hasattr(self.app, "fiado_service"):
			self.app.show_warning("Fiado", "Servicio de fiados no disponible.")
			return

		self.app.show_loading("Generando PDF de fiado...")

		def task():
			err_msg = None
			try:
				pdf_path = self.app.fiado_service.generate_fiado_pdf(fiado_id, output_dir="temp")
			except Exception as exc:
				pdf_path = None
				err_msg = str(exc)
			self.app.after(0, lambda p=pdf_path, msg=err_msg: self._finish_view_pdf(p, msg))

		threading.Thread(target=task, daemon=True).start()

	def resend_email_from_history(self, sale_id=None) -> None:
		"""Reenvía el PDF por correo (incluye adelantos)."""
		if not sale_id:
			self.app.show_warning("Atención", "No se especificó un comprobante.")
			return

		sender = self.app.settings_service.repo.get_setting("email_sender")
		password = self.app.settings_service.repo.get_setting("email_password")
		if not sender or not password:
			if self.app.show_question("Sin Configuración", "No hay correo configurado. ¿Desea configurarlo ahora?"):
				self.app.open_email_config_dialog()
			return

		sale, _items = self.app.sale_service.get_sale(sale_id)
		if not sale:
			self.app.show_error("Error", "No se pudo recuperar la venta.")
			return

		sale_map = self.app.sale_service.map_sale_row(sale)
		client_id = sale_map.get("client_id")
		client = self.app.client_repo.get_client_by_id(client_id) if client_id else None

		client_email = ""
		if client:
			client_email = client[4] if len(client) > 4 and client[4] else ""

		target_email = self.app.ask_client_email_dialog(client_email or "", parent=self.app)
		if not target_email:
			return

		try:
			pdf_path = self.app.pdf_service.generate_sale_pdf(
				sale_id,
				output_dir="temp",
				company_profile=self.app.current_company_data,
			)
		except Exception as exc:
			self.app.show_error("Error", f"No se pudo generar el PDF para enviar:\n{exc}")
			return
		# Si faltara el archivo en disco, reintentar
		if not pdf_path or not os.path.exists(pdf_path):
			try:
				pdf_path = self.app.pdf_service.generate_sale_pdf(
					sale_id,
					output_dir="temp",
					company_profile=self.app.current_company_data,
				)
			except Exception as exc:
				self.app.show_error("Error", f"No se pudo regenerar el PDF para WhatsApp:\n{exc}")
				return

		payload = self.app.build_email_payload(sale_id, target_email, pdf_path, resend=True)

		self.app.show_loading("Reenviando correo...")

		def finish_email_send(success, msg):
			self.app.hide_loading()
			if success:
				self.app.show_success(
					"Correo Enviado",
					f"Se reenvió el comprobante a:\n{target_email}",
					use_toast=True,
				)
			else:
				self.app.show_error("Error al enviar", msg)

		def email_thread_task():
			try:
				result = self.app.comm_service.send_email_with_pdf(
					target_email,
					payload["subject"],
					payload["body_plain"],
					pdf_path,
					sender,
					password,
					company_name=payload["company_display_name"],
					body_html=payload["body_html"],
					logo_path=payload["logo_path"],
				)
			except Exception as exc:
				result = (False, f"Error inesperado: {exc}")
			self.app.after(0, lambda res=result: finish_email_send(*res))

		threading.Thread(target=email_thread_task, daemon=True).start()
	def edit_adelanto(self, sale_id: int, advance_amount: float, estimated_total: float) -> None:
		"""Permite ajustar montos de un adelanto y regenerar su PDF."""
		# Recuperar subtotales de ítems para sugerir total estimado si viene en 0
		fallback_est = estimated_total
		try:
			sale_row, items = self.app.sale_service.get_sale(sale_id)
			if items:
				subtotal_items = 0.0
				for it in items:
					if len(it) > 6:
						try:
							subtotal_items += float(it[6] or 0)
						except Exception:
							pass
				if fallback_est <= 0 and subtotal_items > 0:
					fallback_est = subtotal_items
		except Exception:
			pass
		estimated_total = fallback_est
		win = tb.Toplevel(self.app)
		self.app.begin_modal_construction(win)
		win.title("Editar adelanto")
		win.geometry("360x220")
		self.app.set_app_icon(win)

		lf = tb.Labelframe(win, text="Adelanto", padding=10)
		lf.pack(fill="both", expand=True, padx=10, pady=10)
		lf.columnconfigure(1, weight=1)

		tb.Label(lf, text="Adelanto recibido:").grid(row=0, column=0, sticky="e", padx=5, pady=6)
		var_adelanto = tk.StringVar(value=f"{advance_amount:.2f}")
		entry_adelanto = tb.Entry(lf, textvariable=var_adelanto)
		entry_adelanto.grid(row=0, column=1, sticky="we", padx=5, pady=6)

		tb.Label(lf, text="Total estimado:").grid(row=1, column=0, sticky="e", padx=5, pady=6)
		var_estimado = tk.StringVar(value=f"{estimated_total:.2f}")
		entry_estimado = tb.Entry(lf, textvariable=var_estimado)
		entry_estimado.grid(row=1, column=1, sticky="we", padx=5, pady=6)

		tb.Label(lf, text="Pago adicional:").grid(row=2, column=0, sticky="e", padx=5, pady=6)
		var_pago_extra = tk.StringVar(value="0.00")
		entry_pago = tb.Entry(lf, textvariable=var_pago_extra)
		entry_pago.grid(row=2, column=1, sticky="we", padx=5, pady=6)

		# Mostrar saldo pendiente estimado en vivo
		var_saldo = tk.StringVar(value=f"S/ {max(estimated_total - advance_amount, 0.0):.2f}")
		saldo_label = tb.Label(lf, textvariable=var_saldo, bootstyle="warning")
		saldo_label.grid(row=3, column=0, columnspan=2, pady=4)

		status_label = tb.Label(lf, text="", bootstyle="secondary")
		status_label.grid(row=4, column=0, columnspan=2, pady=4)

		def _update_saldo(*_args):
			try:
				a = float(var_adelanto.get().replace(",", "") or 0)
				b = float(var_estimado.get().replace(",", "") or 0)
				px = float(var_pago_extra.get().replace(",", "") or 0)
			except Exception:
				var_saldo.set("--")
				return
			nuevo_adelanto = max(0.0, round(a + px, 2))
			saldo = max(b - nuevo_adelanto, 0.0)
			var_saldo.set(f"Saldo pendiente: S/ {saldo:.2f}")

		for v in (var_adelanto, var_estimado, var_pago_extra):
			v.trace_add("write", _update_saldo)
		_update_saldo()

		def save_and_regen():
			try:
				a = float(var_adelanto.get().replace(",", "") or 0)
				b = float(var_estimado.get().replace(",", "") or 0)
				pago_extra = float(var_pago_extra.get().replace(",", "") or 0)
			except Exception:
				self.app.show_warning("Atención", "Revise los montos ingresados.")
				return

			nuevo_adelanto = max(0.0, round(a + pago_extra, 2))
			nuevo_estimado = max(0.0, round(b, 2))
			try:
				self.app.sale_service.update_adelanto_amounts(sale_id, nuevo_adelanto, nuevo_estimado)
				pdf_path = self.app.pdf_service.generate_sale_pdf(sale_id, output_dir="temp", company_profile=self.app.current_company_data)
				self.app.last_pdf_path = pdf_path
				status_label.config(text="Actualizado y PDF generado", bootstyle="success")
				self.app.open_pdf(pdf_path)
				self.search_sales_history()
			except Exception as exc:
				self.app.show_error("Error", f"No se pudo actualizar el adelanto:\n{exc}")
				return
			try:
				self.app.after(1200, win.destroy)
			except Exception:
				pass

		tb.Button(lf, text="Guardar y PDF", bootstyle="success", command=save_and_regen).grid(row=5, column=0, columnspan=2, pady=10)

		win.update_idletasks()
		self.app.center_window(win, 360, 220)
		self.app.reveal_modal(win)
		self.app.make_modal(win)

	def resend_whatsapp_from_history(self, sale_id=None) -> None:
		"""Reenvía PDF por WhatsApp (incluye adelantos con saldo)."""
		if not sale_id:
			self.app.show_warning("Atención", "No se especificó un comprobante.")
			return

		sale, _items = self.app.sale_service.get_sale(sale_id)
		if not sale:
			self.app.show_error("Error", "No se pudo recuperar la venta.")
			return

		sale_map = self.app.sale_service.map_sale_row(sale)
		client_id = sale_map.get("client_id")
		client = self.app.client_repo.get_client_by_id(client_id) if client_id else None

		client_phone = ""
		client_name = "Cliente"
		if client:
			client_name = client[2] if len(client) > 2 and client[2] else "Cliente"
			client_phone = client[3] if len(client) > 3 and client[3] else ""

		phone_clean = normalize_phone_number(client_phone or "")
		phone_number = ""
		if phone_clean and len(phone_clean) >= 9:
			phone_number = ensure_country_prefix(phone_clean)
		else:
			user_input = self.app.ask_whatsapp_number_dialog(phone_clean or "", parent=self.app)
			if not user_input:
				return
			phone_number = ensure_country_prefix(normalize_phone_number(user_input))

		if not phone_number or len(phone_number) < 11:
			self.app.show_warning("Atención", "Ingrese un número válido de 9 dígitos (o con prefijo).")
			return

		try:
			pdf_path = self.app.pdf_service.generate_sale_pdf(
				sale_id,
				output_dir="temp",
				company_profile=self.app.current_company_data,
			)
		except Exception as exc:
			self.app.show_error("Error", f"No se pudo generar el PDF para enviar:\n{exc}")
			return

		company_name = (self.app.current_company_data or {}).get("name", "Nuestra Empresa")
		is_adelanto = bool(sale_map.get("is_adelanto"))
		adv = float(sale_map.get("advance_amount") or 0)
		est = float(sale_map.get("estimated_total") or 0)
		sale_dt_str = sale_map.get("datetime")
		sale_dt = None
		if sale_dt_str:
			try:
				sale_dt = datetime.strptime(sale_dt_str, "%Y-%m-%d %H:%M:%S")
			except Exception:
				sale_dt = None

		mensaje = build_whatsapp_message(
			company_name,
			client_name,
			sale_dt,
			is_adelanto=is_adelanto,
			advance_amount=adv,
			estimated_total=est,
			resend=True,
		)

		# Validar dependencias antes de lanzar hilo
		if not getattr(self.app.comm_service, "WHATSAPP_AVAILABLE", True):
			self.app.show_error(
				"WhatsApp",
				"Faltan dependencias para enviar por WhatsApp. Instala: pip install pyautogui pywin32",
			)
			return

		self.app.show_loading("Enviando WhatsApp...")
		timeout_id = self.app.after(10000, self.app.hide_loading)
		timeout_id = self.app.after(10000, self.app.hide_loading)

		def finish_whatsapp_send(success, msg):
			try:
				if timeout_id:
					self.app.after_cancel(timeout_id)
			except Exception:
				pass
			self.app.hide_loading()
			if success:
				self.app.show_success("WhatsApp", msg, use_toast=True, duration=1400)
			else:
				self.app.show_error("Error al enviar", msg)

		def whatsapp_thread_task():
			try:
				result = self.app.comm_service.send_whatsapp_pdf(
					phone_number,
					pdf_path,
					message=mensaje,
					wait_seconds=7,
				)
			except Exception as exc:
				result = (False, f"Error inesperado: {exc}")
			self.app.after(0, lambda res=result: finish_whatsapp_send(*res))

		threading.Thread(target=whatsapp_thread_task, daemon=True).start()

	def delete_sale_from_history(self, sale_id: int, series_number: str) -> None:
		"""Elimina una boleta tras confirmar con PIN de admin."""
		if not sale_id:
			self.app.show_warning("Atención", "No se especificó una boleta.")
			return

		if not self.app.ask_pin(f"Eliminar boleta {series_number}", allow_recovery=False):
			return

		if not self.app.show_question("Confirmar", f"¿Eliminar la boleta {series_number}? Esta acción no se puede deshacer."):
			return

		try:
			self.app.sale_service.delete_sale(sale_id, product_service=getattr(self.app, "product_service", None))
			self.app.show_success("Boleta eliminada", f"Se eliminó {series_number}.", use_toast=True, duration=1800)
			self.refresh_tree()
		except Exception as exc:
			self.app.show_error("Error", f"No se pudo eliminar la boleta:\n{exc}")

		# Preguntar qué desea enviar
		dialog = tb.Toplevel(self.app)
		dialog.title("Enviar por WhatsApp")
		dialog.geometry("350x180")
		dialog.resizable(False, False)
		self.app.set_app_icon(dialog)
		
		# Centrar en pantalla
		dialog.update_idletasks()
		width = dialog.winfo_width()
		height = dialog.winfo_height()
		x = (dialog.winfo_screenwidth() // 2) - (width // 2)
		y = (dialog.winfo_screenheight() // 2) - (height // 2)
		dialog.geometry(f"+{x}+{y}")

		tb.Label(dialog, text="¿Qué desea enviar?", font=("Segoe UI", 12, "bold")).pack(pady=15)

		action_var = tb.StringVar(value="")

		def set_action(action):
			action_var.set(action)
			dialog.destroy()

		btn_frame = tb.Frame(dialog)
		btn_frame.pack(fill="x", padx=20, pady=10)

		tb.Button(
			btn_frame, 
			text="📄 Boleta (PDF)", 
			bootstyle="success", 
			command=lambda: set_action("pdf")
		).pack(side="left", fill="x", expand=True, padx=5)

		tb.Button(
			btn_frame, 
			text="💬 Mensaje", 
			bootstyle="info", 
			command=lambda: set_action("msg")
		).pack(side="left", fill="x", expand=True, padx=5)

		self.app.wait_window(dialog)
		action = action_var.get()

		if not action:
			return

		sale, _items = self.app.sale_service.get_sale(sale_id)
		if not sale:
			self.app.show_error("Error", "No se pudo recuperar la venta.")
			return

		sale_map = self.app.sale_service.map_sale_row(sale)
		client_id = sale_map.get("client_id")
		client = self.app.client_repo.get_client_by_id(client_id) if client_id else None

		client_phone = ""
		client_name = "Cliente"

		if client:
			client_name = client[2] if client[2] else "Cliente"
			client_phone = client[3] if client[3] else ""

		phone_clean = "".join(filter(str.isdigit, client_phone)) if client_phone else ""

		if not phone_clean or len(phone_clean) < 9:
			phone_number = self.app.ask_whatsapp_number_dialog("", parent=self.app)
			if not phone_number:
				return
		else:
			phone_number = self.app.ask_whatsapp_number_dialog(phone_clean, parent=self.app)
			if not phone_number:
				return

		if not phone_number.startswith("51") and len(phone_number) == 9:
			phone_number = "51" + phone_number

		# Preparar mensaje base
		company_name = (self.app.current_company_data or {}).get("name", "Nuestra Empresa")
		fecha_venta = sale_map.get("datetime") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		is_adelanto = bool(sale_map.get("is_adelanto"))
		adv = float(sale_map.get("advance_amount") or 0)
		est = float(sale_map.get("estimated_total") or 0)
		saldo = max(est - adv, 0.0)
		
		# Lógica según acción
		pdf_path = None
		mensaje = ""

		if action == "pdf":
			try:
				pdf_path = self.app.pdf_service.generate_sale_pdf(
					sale_id,
					output_dir="temp",
					company_profile=self.app.current_company_data,
				)
			except Exception as exc:
				self.app.show_error("Error", f"No se pudo generar el PDF para enviar:\n{exc}")
				return
			
			if is_adelanto:
				mensaje = (
					f"Hola {client_name}, te enviamos el recibo de adelanto del {fecha_venta} en {company_name}. "
					f"Adelanto: S/ {adv:.2f}. Saldo pendiente: S/ {saldo:.2f}. "
					"Podrás pagarlo al recoger tu servicio. Gracias!"
				)
			else:
				mensaje = (
					f"Hola {client_name}, le reenviamos su comprobante de venta digital del día "
					f"{fecha_venta} en {company_name}. Gracias por su preferencia!"
				)
		
		elif action == "msg":
			# Dialogo personalizado para mensaje
			msg_dialog = tb.Toplevel(self.app)
			msg_dialog.title("Mensaje WhatsApp")
			msg_dialog.geometry("400x200")
			msg_dialog.resizable(False, False)
			self.app.set_app_icon(msg_dialog)

			# Centrar
			msg_dialog.update_idletasks()
			dx = (msg_dialog.winfo_screenwidth() // 2) - (msg_dialog.winfo_width() // 2)
			dy = (msg_dialog.winfo_screenheight() // 2) - (msg_dialog.winfo_height() // 2)
			msg_dialog.geometry(f"+{dx}+{dy}")

			tb.Label(msg_dialog, text="Escriba el mensaje a enviar:", font=("Segoe UI", 10)).pack(pady=(20, 10), padx=20, anchor="w")
			
			txt_entry = tb.Entry(msg_dialog)
			txt_entry.pack(fill="x", padx=20, pady=5)
			txt_entry.focus_set()

			msg_var = tb.StringVar(value="")

			def on_confirm():
				msg_var.set(txt_entry.get().strip())
				msg_dialog.destroy()

			def on_cancel():
				msg_dialog.destroy()

			btn_box = tb.Frame(msg_dialog)
			btn_box.pack(fill="x", padx=20, pady=20)

			tb.Button(btn_box, text="Cancelar", bootstyle="secondary", command=on_cancel).pack(side="right", padx=5)
			tb.Button(btn_box, text="Enviar", bootstyle="primary", command=on_confirm).pack(side="right", padx=5)
			
			msg_dialog.bind("<Return>", lambda e: on_confirm())
			msg_dialog.bind("<Escape>", lambda e: on_cancel())

			self.app.wait_window(msg_dialog)
			custom_msg = msg_var.get()

			if not custom_msg:
				return
			mensaje = custom_msg

		self.app.show_loading("Enviando WhatsApp...")

		def finish_whatsapp_send(success, msg):
			try:
				if timeout_id:
					self.app.after_cancel(timeout_id)
			except Exception:
				pass
			self.app.hide_loading()
			if success:
				self.app.show_success("WhatsApp", msg, use_toast=True, duration=1400)
			else:
				self.app.show_error("Error al enviar", msg)

		def whatsapp_thread_task():
			try:
				if action == "msg":
					# Usar método específico para mensajes si existe, o el genérico
					if hasattr(self.app.comm_service, "send_whatsapp_message"):
						result = self.app.comm_service.send_whatsapp_message(
							phone_number,
							mensaje,
							wait_seconds=7
						)
					else:
						# Fallback si no existe el método específico, intentamos pasar path vacío si la librería lo soporta
						# Ojo: El error indica que send_whatsapp_pdf falla con None.
						# Si no hay PDF, no deberíamos llamar a send_whatsapp_pdf.
						# Asumiremos que existe send_whatsapp_message o lo implementaremos.
						# Por seguridad, si no existe, lanzamos error o usamos un path dummy si es absolutamente necesario (no recomendado).
						result = (False, "Método de envío de mensajes no disponible.")
				else:
					result = self.app.comm_service.send_whatsapp_pdf(
						phone_number,
						pdf_path,
						message=mensaje,
						wait_seconds=7,
					)
			except Exception as exc:
				result = (False, f"Error inesperado: {exc}")
			self.app.after(0, lambda res=result: finish_whatsapp_send(*res))

		threading.Thread(target=whatsapp_thread_task, daemon=True).start()

	def search_sales_history(self, event=None) -> None:
		if self._search_job:
			self._search_job = None

		if not self.scroll_frame:
			return

		# Limpiar lista actual
		for widget in self.scroll_frame.winfo_children():
			widget.destroy()

		text = self.entry_history_search.get().strip() if self.entry_history_search else ""
		mode = self.history_filter.get() if hasattr(self, "history_filter") else "boletas"

		if mode == "fiados":
			fiado_rows = []
			if hasattr(self.app, "fiado_service"):
				fiado_rows = self.app.fiado_service.search_fiados(text)
			else:
				self.app.show_warning("Fiados", "Servicio de fiados no disponible.")

			display_rows = fiado_rows[:50]
			if not display_rows:
				tb.Label(self.scroll_frame, text="No se encontraron fiados", bootstyle="secondary").pack(pady=20)
				return

			for i, fiado in enumerate(display_rows):
				status = (fiado.get("status") or "").lower()
				is_paid = status == "pagado"
				if i % 2 == 0:
					row_style = ""
					lbl_style = ""
				else:
					row_style = "secondary"
					lbl_style = "inverse-secondary"

				row_frame = tb.Frame(self.scroll_frame, bootstyle=row_style)
				row_frame.pack(fill="x", pady=1)
				row_frame.columnconfigure(0, weight=1)
				row_frame.columnconfigure(1, weight=1)
				row_frame.columnconfigure(2, weight=3)
				row_frame.columnconfigure(3, weight=1)
				row_frame.columnconfigure(4, weight=0)

				dt_str = fiado.get("created_at") or ""
				tb.Label(row_frame, text=dt_str, bootstyle=lbl_style).grid(row=0, column=0, sticky="w", padx=5, pady=8)
				series_style = "success" if is_paid else "warning"
				badge_text = "FIADO PAGADO" if is_paid else "FIADO"
				doc_label = f"{badge_text}: {fiado.get('code') or '---'}"
				tb.Label(row_frame, text=doc_label, font=("Segoe UI", 9, "bold"), bootstyle=series_style).grid(row=0, column=1, sticky="w", padx=5, pady=8)

				full_name = fiado.get("full_name") or ""
				dni = fiado.get("dni") or ""
				client_info = f"{full_name}\n{dni}" if dni else full_name
				tb.Label(row_frame, text=client_info, bootstyle=lbl_style).grid(row=0, column=2, sticky="w", padx=5, pady=8)

				total_value = float(fiado.get("total_pendiente") or 0.0)
				if is_paid:
					total_value = float(fiado.get("total_bruto") or 0.0)
				tb.Label(row_frame, text=f"S/ {total_value:.2f}", font=("Segoe UI", 10, "bold"), bootstyle=lbl_style).grid(row=0, column=3, sticky="e", padx=5, pady=8)

				actions_frame = tb.Frame(row_frame, bootstyle=row_style)
				actions_frame.grid(row=0, column=4, sticky="e", padx=5, pady=4)

				btn_pdf = tb.Button(
					actions_frame,
					text="📄",
					bootstyle="danger",
					width=3,
					command=lambda fid=fiado.get("id"): self.view_fiado_pdf(fid),
				)
				btn_pdf.pack(side="left", padx=2)
				ToolTip(btn_pdf, "Ver fiado en PDF")

				sale_id = fiado.get("sale_id")
				if sale_id:
					btn_sale = tb.Button(
						actions_frame,
						text="🧾",
						bootstyle="primary",
						width=3,
						command=lambda sid=sale_id: self.view_or_regenerate_pdf(sid),
					)
					btn_sale.pack(side="left", padx=2)
					ToolTip(btn_sale, "Abrir boleta oficial")

			return

		rows = self.app.sale_service.search_sales_by_client_with_adelantos(text)
		filtered_rows = []
		for r in rows:
			sale_id, series, number, _dt_str, _total, _full_name, _dni, is_proforma_db, is_boletin_db, is_adelanto_db, _adv, _est = r
			is_proforma = bool(is_proforma_db) or str(series).upper().startswith("PF")
			is_boletin = bool(is_boletin_db) or (not is_proforma and str(series).upper().startswith("BL"))
			is_adelanto = bool(is_adelanto_db)
			if mode == "boletas" and not is_boletin and not is_adelanto:
				filtered_rows.append(r)
			elif mode == "boletines" and (is_boletin or is_adelanto):
				filtered_rows.append(r)

		display_rows = filtered_rows[:50]

		if not display_rows:
			tb.Label(self.scroll_frame, text="No se encontraron resultados", bootstyle="secondary").pack(pady=20)
			return

		for i, r in enumerate(display_rows):
			sale_id, series, number, dt_str, total, full_name, dni, is_proforma_db, is_boletin_db, is_adelanto_db, advance_amount, estimated_total = r
			series_number = f"{series}-{int(number):06d}"
			is_proforma = bool(is_proforma_db) or str(series).upper().startswith("PF")
			is_boletin = bool(is_boletin_db) or (not is_proforma and str(series).upper().startswith("BL"))
			is_adelanto = bool(is_adelanto_db)
			
			if i % 2 == 0:
				row_style = ""
				lbl_style = ""
			else:
				row_style = "secondary"
				lbl_style = "inverse-secondary"

			row_frame = tb.Frame(self.scroll_frame, bootstyle=row_style)
			row_frame.pack(fill="x", pady=1)
			
			row_frame.columnconfigure(0, weight=1)
			row_frame.columnconfigure(1, weight=1)
			row_frame.columnconfigure(2, weight=3)
			row_frame.columnconfigure(3, weight=1)
			row_frame.columnconfigure(4, weight=0)

			tb.Label(row_frame, text=dt_str, bootstyle=lbl_style).grid(row=0, column=0, sticky="w", padx=5, pady=8)
			series_style = "warning" if is_adelanto else ("secondary" if is_boletin else ("info" if is_proforma else lbl_style))
			badge_text = "ADELANTO" if is_adelanto else ("BOLETIN" if is_boletin else ("PROFORMA" if is_proforma else "BOLETA"))
			doc_label = f"{badge_text}: {series_number}"
			tb.Label(row_frame, text=doc_label, font=("Segoe UI", 9, "bold"), bootstyle=series_style).grid(row=0, column=1, sticky="w", padx=5, pady=8)
			
			client_info = f"{full_name}\n{dni}" if dni else full_name
			tb.Label(row_frame, text=client_info, bootstyle=lbl_style).grid(row=0, column=2, sticky="w", padx=5, pady=8)
			
			tb.Label(row_frame, text=f"S/ {total:.2f}", font=("Segoe UI", 10, "bold"), bootstyle=lbl_style).grid(row=0, column=3, sticky="e", padx=5, pady=8)

			actions_frame = tb.Frame(row_frame, bootstyle=row_style)
			actions_frame.grid(row=0, column=4, sticky="e", padx=5, pady=4)

			btn_pdf = tb.Button(
				actions_frame,
				text="📄",
				bootstyle="danger",
				width=3,
				command=lambda sid=sale_id: self.view_or_regenerate_pdf(sid)
			)
			btn_pdf.pack(side="left", padx=2)
			ToolTip(btn_pdf, "Ver PDF")

			btn_wsp = tb.Button(
				actions_frame,
				text="📱",
				bootstyle="success",
				width=3,
				command=lambda sid=sale_id: self.resend_whatsapp_from_history(sid)
			)
			btn_wsp.pack(side="left", padx=2)
			ToolTip(btn_wsp, "Enviar por WhatsApp")

			btn_email = tb.Button(
				actions_frame,
				text="📧",
				bootstyle="info",
				width=3,
				command=lambda sid=sale_id: self.resend_email_from_history(sid)
			)
			btn_email.pack(side="left", padx=2)
			ToolTip(btn_email, "Enviar por Correo")

			btn_delete = tb.Button(
				actions_frame,
				text="🗑",
				bootstyle="danger",
				width=3,
				command=lambda sid=sale_id, sn=series_number: self.delete_sale_from_history(sid, sn),
			)
			btn_delete.pack(side="left", padx=2)
			ToolTip(btn_delete, "Eliminar boleta (pide PIN)")

			if is_adelanto:
				btn_edit_adelanto = tb.Button(
					actions_frame,
					text="✏",
					bootstyle="warning-outline",
					width=3,
					command=lambda sid=sale_id, aa=advance_amount, et=estimated_total: self.edit_adelanto(sid, aa, et),
				)
				btn_edit_adelanto.pack(side="left", padx=2)
				ToolTip(btn_edit_adelanto, "Editar adelanto y regenerar PDF")

			row_frame.sale_meta = {
				"sale_id": sale_id,
				"advance_amount": advance_amount,
				"estimated_total": estimated_total,
				"is_adelanto": is_adelanto,
			}

	def search_boletas_list(self) -> None:
		if not self.entry_search_boletas or not self.combo_boletas:
			self.app.show_warning("Atención", "El buscador rápido no está disponible en este momento.")
			return

		text = self.entry_search_boletas.get().strip()
		if not text:
			self.app.show_warning("Atención", "Ingrese DNI o nombre del cliente.")
			return

		rows = self.app.sale_service.search_sales_by_client(text)
		self.boleta_list = rows
		display_list = []
		for r in rows:
			sale_id, series, number, dt_str, total, full_name, dni = r
			display_list.append(f"{series}-{int(number):06d} | {full_name} ({dni}) | {total:.2f}")
		self.combo_boletas["values"] = display_list
		if display_list:
			self.combo_boletas.current(0)
		else:
			self.combo_boletas.set("")

	def open_searched_boleta_pdf(self) -> None:
		if not self.combo_boletas:
			self.app.show_warning("Atención", "Seleccione una boleta desde el historial.")
			return

		boletas = self.boleta_list or []
		idx = self.combo_boletas.current()
		if idx < 0 or idx >= len(boletas):
			self.app.show_warning("Atención", "Seleccione una boleta del listado.")
			return

		sale_id = boletas[idx][0]
		try:
			sale, _items = self.app.sale_service.get_sale(sale_id)
			if not sale:
				self.app.show_error("Error", "Boleta no encontrada en la base de datos.")
				return
			sale_map = self.app.sale_service.map_sale_row(sale)
			self.app.show_info("Generando PDF", "Se generará un PDF temporal para visualizar.")
			new_pdf_path = self.app.pdf_service.generate_sale_pdf(
				sale_id,
				output_dir="temp",
				company_profile=self.app.current_company_data,
			)
			self.app.open_pdf(new_pdf_path)
		except Exception as exc:
			self.app.show_error("Error", f"Error al obtener boleta:\n{exc}")
