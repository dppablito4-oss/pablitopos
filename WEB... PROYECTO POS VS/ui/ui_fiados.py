import tkinter as tk
import ttkbootstrap as tb
from typing import Any, List, Optional


class FiadosUIManager:
    """Vista para registrar fiados y gestionar cobros parciales."""

    def __init__(self, app: Any, frame: tb.Frame, fiado_service) -> None:
        self.app = app
        self.frame = frame
        self.fiado_service = fiado_service

        self.entry_client_search: Optional[tb.Entry] = None
        self.list_clients: Optional[tk.Listbox] = None
        self.selected_client_id: Optional[int] = None
        self.label_client_selected: Optional[tb.Label] = None

        self.tree_fiados: Optional[tb.Treeview] = None
        self.items_container: Optional[tb.Frame] = None
        self.items_canvas: Optional[tb.Canvas] = None

        self.new_items: List[dict[str, Any]] = []
        self.new_items_box: Optional[tk.Listbox] = None
        self.entry_desc: Optional[tb.Entry] = None
        self.entry_qty: Optional[tb.Entry] = None
        self.entry_price: Optional[tb.Entry] = None
        self.entry_unit: Optional[tb.Entry] = None
        self.entry_block: Optional[tb.Entry] = None
        self.entry_product_search: Optional[tb.Entry] = None
        self.list_products: Optional[tk.Listbox] = None
        self.selected_product: Optional[dict[str, Any]] = None
        self.current_fiado_id: Optional[int] = None
        self.current_items: list[dict[str, Any]] = []
        self.btn_mark_all_paid: Optional[tb.Button] = None
        self.btn_generate_boleta: Optional[tb.Button] = None

    # ---------------------------- UI BUILD ----------------------------
    def build_ui(self) -> None:
        f = self.frame
        for w in f.winfo_children():
            w.destroy()

        # Estilos propios para dar color al panel
        style = tb.Style()
        style.configure("FiadosLeft.TLabelframe", background="#0f172a", bordercolor="#4f46e5")
        style.configure("FiadosLeft.TLabelframe.Label", foreground="#a5b4fc")
        style.configure("FiadosRight.TLabelframe", background="#111827", bordercolor="#22c55e")
        style.configure("FiadosRight.TLabelframe.Label", foreground="#bbf7d0")
        style.configure("Fiados.Treeview", background="#0b1220", fieldbackground="#0b1220", foreground="#e5e7eb")
        style.configure("Fiados.Treeview.Heading", background="#1f2937", foreground="#d1d5db")

        # --- Buscar y seleccionar cliente ---
        search_lf = tb.Labelframe(f, text="Cliente", padding=10, bootstyle="info")
        search_lf.pack(fill="x", padx=10, pady=(10, 6))

        tb.Label(search_lf, text="DNI / Nombre / Celular:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.entry_client_search = tb.Entry(search_lf)
        self.entry_client_search.grid(row=0, column=1, sticky="we", padx=4, pady=4)
        self.entry_client_search.bind("<KeyRelease>", self._on_client_key)
        search_lf.columnconfigure(1, weight=1)

        tb.Button(
            search_lf,
            text="Buscar",
            bootstyle="success",
            command=self.search_clients,
            width=12,
        ).grid(row=0, column=2, padx=4, pady=4)

        self.list_clients = tk.Listbox(search_lf, height=4)
        self.list_clients.grid(row=1, column=0, columnspan=3, sticky="we", padx=4, pady=4)
        self.list_clients.bind("<<ListboxSelect>>", self.on_client_selected)

        self.label_client_selected = tb.Label(search_lf, text="(ningun cliente seleccionado)", bootstyle="secondary")
        self.label_client_selected.grid(row=2, column=0, columnspan=3, sticky="w", padx=4, pady=(2, 0))

        # --- Zona central: split horizontal ---
        content = tk.PanedWindow(f, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=6)
        content.pack(fill="both", expand=True, padx=10, pady=6)

        left_pane = tb.Frame(content)
        right_pane = tb.Frame(content)
        content.add(left_pane, minsize=360)
        content.add(right_pane, minsize=360)

        # --- Panel de fiados existentes (izquierda) ---
        fiados_lf = tb.Labelframe(left_pane, text="Fiados del cliente", padding=10, bootstyle="secondary", style="FiadosLeft.TLabelframe")
        fiados_lf.pack(fill="both", expand=True)
        fiados_lf.rowconfigure(1, weight=1)
        fiados_lf.columnconfigure(0, weight=1)

        columns = ("code", "status", "pendiente", "pagado")
        self.tree_fiados = tb.Treeview(
            fiados_lf,
            columns=columns,
            show="headings",
            bootstyle="secondary",
            height=6,
            style="Fiados.Treeview",
        )
        style.map("Fiados.Treeview", background=[("selected", "#1d4ed8")], foreground=[("selected", "#e0f2fe")])
        self.tree_fiados.heading("code", text="Vale")
        self.tree_fiados.heading("status", text="Estado")
        self.tree_fiados.heading("pendiente", text="Pendiente")
        self.tree_fiados.heading("pagado", text="Pagado")
        self.tree_fiados.column("code", width=80)
        self.tree_fiados.column("status", width=90)
        self.tree_fiados.column("pendiente", width=90, anchor="e")
        self.tree_fiados.column("pagado", width=90, anchor="e")
        self.tree_fiados.tag_configure("pagado", background="#0f2910", foreground="#c6f6c3")
        self.tree_fiados.tag_configure("pendiente", background="#2a1b1b", foreground="#fcd34d")
        self.tree_fiados.grid(row=0, column=0, sticky="nsew")
        self.tree_fiados.bind("<<TreeviewSelect>>", self.on_fiado_selected)

        scroll = tb.Scrollbar(fiados_lf, orient="vertical", command=self.tree_fiados.yview)
        self.tree_fiados.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")

        # Detalle de items con checkboxes
        items_container_frame = tb.Frame(fiados_lf)
        items_container_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        items_container_frame.rowconfigure(0, weight=1)
        items_container_frame.columnconfigure(0, weight=1)

        self.items_canvas = tk.Canvas(items_container_frame, highlightthickness=0, bd=0)
        self.items_canvas.configure(background="#0b1220")
        items_scroll = tb.Scrollbar(items_container_frame, orient="vertical", command=self.items_canvas.yview)
        self.items_canvas.configure(yscrollcommand=items_scroll.set)
        self.items_canvas.grid(row=0, column=0, sticky="nsew")
        items_scroll.grid(row=0, column=1, sticky="ns")

        # Scroll con rueda dentro del panel de items
        self.items_canvas.bind_all("<MouseWheel>", lambda e: self.items_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.items_canvas.bind_all("<Button-4>", lambda _e: self.items_canvas.yview_scroll(-1, "units"))
        self.items_canvas.bind_all("<Button-5>", lambda _e: self.items_canvas.yview_scroll(1, "units"))

        self.items_container = tb.Frame(self.items_canvas)
        self.items_canvas.create_window((0, 0), window=self.items_container, anchor="nw")
        self.items_container.bind(
            "<Configure>", lambda e: self.items_canvas.configure(scrollregion=self.items_canvas.bbox("all"))
        )

        actions_frame = tb.Frame(fiados_lf)
        actions_frame.grid(row=2, column=0, columnspan=2, sticky="we", pady=(6, 0))
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)
        self.btn_mark_all_paid = tb.Button(actions_frame, text="Marcar todo pagado", bootstyle="success-outline", command=self.mark_all_paid)
        self.btn_mark_all_paid.grid(row=0, column=0, sticky="w", padx=4)
        self.btn_generate_boleta = tb.Button(actions_frame, text="Generar boleta", bootstyle="info", state="disabled", command=self.generate_boleta)
        self.btn_generate_boleta.grid(row=0, column=1, sticky="e", padx=4)
        self.btn_pdf = tb.Button(actions_frame, text="PDF fiado", bootstyle="primary", state="disabled", command=self.generate_fiado_pdf)
        self.btn_pdf.grid(row=0, column=2, sticky="e", padx=4)

        # --- Nuevo fiado (derecha) ---
        new_lf = tb.Labelframe(right_pane, text="Nuevo fiado", padding=10, bootstyle="primary", style="FiadosRight.TLabelframe")
        new_lf.pack(fill="both", expand=True, padx=(8, 0))
        new_lf.columnconfigure(0, weight=1)
        new_lf.columnconfigure(1, weight=1)

        # Buscador de productos (usa base de datos existente)
        prod_search_frame = tb.Frame(new_lf)
        prod_search_frame.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 6))
        prod_search_frame.columnconfigure(1, weight=1)
        tb.Label(prod_search_frame, text="Producto (nombre/código):").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.entry_product_search = tb.Entry(prod_search_frame)
        self.entry_product_search.grid(row=0, column=1, sticky="we", padx=4, pady=2)
        self.entry_product_search.bind("<KeyRelease>", self._on_product_key)
        tb.Button(prod_search_frame, text="Buscar prod", bootstyle="info", width=12, command=self.search_products).grid(row=0, column=2, padx=4, pady=2)

        self.list_products = tk.Listbox(prod_search_frame, height=4)
        self.list_products.grid(row=1, column=0, columnspan=3, sticky="we", padx=4, pady=(0, 6))
        self.list_products.bind("<<ListboxSelect>>", self.on_product_selected)

        form_frame = tb.Frame(new_lf)
        form_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        for c in range(2):
            form_frame.columnconfigure(c, weight=1)

        tb.Label(form_frame, text="Descripcion").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.entry_desc = tb.Entry(form_frame)
        self.entry_desc.grid(row=1, column=0, columnspan=2, sticky="we", padx=4, pady=2)

        tb.Label(form_frame, text="Cantidad").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.entry_qty = tb.Entry(form_frame)
        self.entry_qty.grid(row=3, column=0, sticky="we", padx=4, pady=2)
        self.entry_qty.insert(0, "1")

        tb.Label(form_frame, text="Precio").grid(row=2, column=1, sticky="w", padx=4, pady=4)
        self.entry_price = tb.Entry(form_frame)
        self.entry_price.grid(row=3, column=1, sticky="we", padx=4, pady=2)

        tb.Label(form_frame, text="Unidad").grid(row=4, column=0, sticky="w", padx=4, pady=4)
        self.entry_unit = tb.Entry(form_frame)
        self.entry_unit.grid(row=5, column=0, sticky="we", padx=4, pady=2)

        tb.Label(form_frame, text="Bloque").grid(row=4, column=1, sticky="w", padx=4, pady=4)
        self.entry_block = tb.Entry(form_frame)
        self.entry_block.grid(row=5, column=1, sticky="we", padx=4, pady=2)

        btn_bar = tb.Frame(form_frame)
        btn_bar.grid(row=6, column=0, columnspan=2, sticky="we", pady=(6, 2))
        tb.Button(btn_bar, text="Agregar item", bootstyle="success", command=self.add_new_item).pack(side="left", padx=4)
        tb.Button(btn_bar, text="Limpiar items", bootstyle="secondary", command=self.clear_new_items).pack(side="left", padx=4)

        # Lista de items agregados (estilo detalle ventas)
        list_frame = tb.Frame(new_lf)
        list_frame.grid(row=1, column=1, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=1)
        tb.Label(list_frame, text="Items agregados").grid(row=0, column=0, sticky="w", padx=4, pady=(0, 4))

        columns_items = ("desc", "qty", "price", "sub", "block")
        self.new_items_box = tb.Treeview(list_frame, columns=columns_items, show="headings", height=6, bootstyle="secondary")
        self.new_items_box.heading("desc", text="Descripcion")
        self.new_items_box.heading("qty", text="Cant.")
        self.new_items_box.heading("price", text="P.Unit")
        self.new_items_box.heading("sub", text="Subtotal")
        self.new_items_box.heading("block", text="Bloque")
        self.new_items_box.column("desc", width=160)
        self.new_items_box.column("qty", width=60, anchor="e")
        self.new_items_box.column("price", width=70, anchor="e")
        self.new_items_box.column("sub", width=80, anchor="e")
        self.new_items_box.column("block", width=70, anchor="center")
        self.new_items_box.grid(row=1, column=0, sticky="nsew")

        sb_items = tb.Scrollbar(list_frame, orient="vertical", command=self.new_items_box.yview)
        self.new_items_box.configure(yscrollcommand=sb_items.set)
        sb_items.grid(row=1, column=1, sticky="ns")

        tb.Button(new_lf, text="Guardar vale de fiado", bootstyle="primary", command=self.save_fiado).grid(
            row=2, column=0, columnspan=2, sticky="e", padx=4, pady=(10, 2)
        )

    # ---------------------------- Actions ----------------------------
    def search_clients(self) -> None:
        if not self.entry_client_search:
            return
        text = self.entry_client_search.get().strip()
        if not text:
            self.app.show_warning("Búsqueda", "Ingresa DNI, nombre o celular.")
            return

        rows = self.app.client_service.search_clients(text)
        self.list_clients.delete(0, tk.END)
        for row in rows:
            cid, dni, name, phone = row[0], row[1], row[2], row[3]
            phone_txt = f"📱 {phone}" if phone else ""
            display = " - ".join([p for p in [name or "(Sin nombre)", f"DNI {dni}" if dni else None, phone_txt] if p])
            self.list_clients.insert(tk.END, f"{cid}|{display}")

        if not rows:
            wants_new = self.app.show_question("Cliente no encontrado", "No hay coincidencias. ¿Registrar un nuevo cliente?")
            if wants_new:
                self._prompt_create_client(prefill=text)

    def on_client_selected(self, _event=None) -> None:
        if not self.list_clients:
            return
        sel = self.list_clients.curselection()
        if not sel:
            return
        value = self.list_clients.get(sel[0])
        try:
            cid_str, label = value.split("|", 1)
            self.selected_client_id = int(cid_str)
            if self.label_client_selected:
                self.label_client_selected.configure(text=f"Cliente: {label}", bootstyle="success")
        except Exception:
            self.selected_client_id = None
        self.refresh_fiados()

    # ---------------------------- Productos ----------------------------
    def search_products(self) -> None:
        text = self.entry_product_search.get().strip() if self.entry_product_search else ""
        if len(text) < 1:
            self._clear_product_list()
            return
        rows = self.app.product_service.search_products(text)
        self._fill_product_list(rows)

    def _on_product_key(self, _event=None) -> None:
        text = self.entry_product_search.get().strip() if self.entry_product_search else ""
        if len(text) < 1:
            self._clear_product_list()
            return
        rows = self.app.product_service.search_products(text)
        self._fill_product_list(rows)

    def _fill_product_list(self, rows) -> None:
        if not self.list_products:
            return
        self.list_products.delete(0, tk.END)
        for row in rows:
            pid, code, name, unit, price = row[0], row[1], row[2], row[3], row[4]
            display = f"{name} ({code}) - S/ {price:.2f} [{unit}]"
            self.list_products.insert(tk.END, f"{pid}|{display}|{price}|{unit}|{name}")

    def _clear_product_list(self) -> None:
        if self.list_products:
            self.list_products.delete(0, tk.END)
        self.selected_product = None

    def on_product_selected(self, _event=None) -> None:
        if not self.list_products:
            return
        sel = self.list_products.curselection()
        if not sel:
            return
        value = self.list_products.get(sel[0])
        try:
            pid_str, display, price_str, unit, name = value.split("|", 4)
            self.selected_product = {
                "id": int(pid_str),
                "name": name,
                "unit": unit,
                "price": float(price_str),
            }
            self._populate_product_fields()
        except Exception:
            self.selected_product = None

    def _populate_product_fields(self) -> None:
        if not self.selected_product:
            return
        if self.entry_desc:
            self.entry_desc.delete(0, tk.END)
            self.entry_desc.insert(0, self.selected_product.get("name", ""))
        if self.entry_unit:
            self.entry_unit.delete(0, tk.END)
            self.entry_unit.insert(0, self.selected_product.get("unit", ""))
        if self.entry_price:
            self.entry_price.delete(0, tk.END)
            self.entry_price.insert(0, f"{self.selected_product.get('price', 0):.2f}")
        # Mantener cantidad/bloque como están

    def _on_client_key(self, _event=None) -> None:
        if not self.entry_client_search:
            return
        text = self.entry_client_search.get().strip()
        # Evitar spam con textos muy cortos
        if len(text) < 2:
            self.list_clients.delete(0, tk.END)
            return
        rows = self.app.client_service.search_clients(text)
        self.list_clients.delete(0, tk.END)
        for row in rows:
            cid, dni, name, phone = row[0], row[1], row[2], row[3]
            phone_txt = f"📱 {phone}" if phone else ""
            display = " - ".join([p for p in [name or "(Sin nombre)", f"DNI {dni}" if dni else None, phone_txt] if p])
            self.list_clients.insert(tk.END, f"{cid}|{display}")

    def _select_client(self, client_id: int, label: str) -> None:
        self.selected_client_id = client_id
        if self.label_client_selected:
            self.label_client_selected.configure(text=f"Cliente: {label}", bootstyle="success")
        self.refresh_fiados()

    def _prompt_create_client(self, prefill: str = "") -> None:
        win = tb.Toplevel(self.app)
        win.title("Registrar cliente")
        self.app.set_app_icon(win)
        self.app.begin_modal_construction(win)
        body = tb.Frame(win, padding=12)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        tb.Label(body, text="Nombre*:").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        entry_name = tb.Entry(body)
        entry_name.grid(row=0, column=1, sticky="we", padx=4, pady=4)
        entry_name.insert(0, prefill)

        tb.Label(body, text="DNI:").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        entry_dni = tb.Entry(body)
        entry_dni.grid(row=1, column=1, sticky="we", padx=4, pady=4)

        tb.Label(body, text="Celular*:").grid(row=2, column=0, sticky="e", padx=4, pady=4)
        entry_phone = tb.Entry(body)
        entry_phone.grid(row=2, column=1, sticky="we", padx=4, pady=4)
        entry_phone.insert(0, prefill if prefill.isdigit() else "")

        def on_save():
            name = entry_name.get().strip()
            dni = entry_dni.get().strip()
            phone = entry_phone.get().strip()
            if not name:
                self.app.show_warning("Datos", "El nombre es obligatorio.")
                return
            if not phone:
                self.app.show_warning("Datos", "El celular es obligatorio.")
                return
            try:
                client_id = self.app.client_service.create_client(dni, name, phone, "", "")
                self.app.show_success("Cliente creado", f"{name} registrado para fiados.", use_toast=True)
                label = " - ".join([p for p in [name, f"DNI {dni}" if dni else None, f"📱 {phone}"] if p])
                self._select_client(client_id, label)
                win.destroy()
            except Exception as exc:
                self.app.show_error("Error", str(exc))

        btns = tb.Frame(body)
        btns.grid(row=3, column=0, columnspan=2, sticky="e", pady=(10, 4))
        tb.Button(btns, text="Cancelar", bootstyle="secondary", command=win.destroy).pack(side="right", padx=4)
        tb.Button(btns, text="Guardar", bootstyle="success", command=on_save).pack(side="right", padx=4)

        self.app.reveal_modal(win)

    def refresh_fiados(self) -> None:
        if not self.tree_fiados:
            return
        for row in self.tree_fiados.get_children():
            self.tree_fiados.delete(row)
        if not self.selected_client_id:
            self._clear_items_view()
            return
        rows = self.app.fiado_service.list_by_client(self.selected_client_id)
        for r in rows:
            self.tree_fiados.insert(
                "",
                "end",
                iid=str(r.get("id")),
                values=(
                    r.get("code"),
                    r.get("status"),
                    f"S/ {r.get('total_pendiente', 0):.2f}",
                    f"S/ {r.get('total_pagado', 0):.2f}",
                ),
            )
        self._clear_items_view()

    def on_fiado_selected(self, _event=None) -> None:
        sel = self.tree_fiados.selection() if self.tree_fiados else []
        if not sel:
            self._clear_items_view()
            self.current_fiado_id = None
            self.current_items = []
            self._update_action_buttons(None)
            return
        fiado_id = int(sel[0])
        self.current_fiado_id = fiado_id
        data = self.app.fiado_service.get_fiado_with_items(fiado_id)
        fiado = data.get("fiado", {})
        items = data.get("items", [])
        self.current_items = items
        self._render_items(items, fiado_id)
        self._update_action_buttons(fiado)

    def _render_items(self, items: List[dict[str, Any]], fiado_id: int) -> None:
        self._clear_items_view()
        if not self.items_container:
            return
        for idx, item in enumerate(items):
            status = (item.get("status") or "").lower()
            paid = status == "pagado"
            var = tk.BooleanVar(value=paid)
            boot = "success-round-toggle" if paid else "secondary-round-toggle"
            cb = tb.Checkbutton(
                self.items_container,
                text=self._item_label(item),
                variable=var,
                bootstyle=boot,
                command=lambda iid=item.get("id"), v=var: self._toggle_item(iid, v),
            )
            cb.grid(row=idx, column=0, sticky="w", padx=4, pady=2)

    def _item_label(self, item: dict[str, Any]) -> str:
        desc = item.get("description", "")
        qty = item.get("quantity", 0)
        price = item.get("unit_price", 0)
        block = item.get("block", "")
        return f"[{block or '-'}] {desc} x{qty:g} @ {price:.2f}"

    def _toggle_item(self, item_id: int, var: tk.BooleanVar) -> None:
        try:
            data = self.app.fiado_service.set_item_paid(item_id, var.get())
            fiado = data.get("fiado", {})
            items = data.get("items", [])
            self.current_items = items
            self._update_tree_row(fiado)
            self._render_items(items, fiado.get("id", 0))
            self._update_action_buttons(fiado)
        except Exception as exc:
            self.app.show_error("Error", str(exc))
            var.set(not var.get())
        # Forzar colores de toggles según estado
        for child in self.items_container.winfo_children():
            try:
                text = child.cget("text")
                matched = next((it for it in self.current_items if self._item_label(it) == text), None)
                if matched:
                    status = (matched.get("status") or "").lower()
                    child.configure(bootstyle="success-round-toggle" if status == "pagado" else "secondary-round-toggle")
            except Exception:
                pass

    def _clear_items_view(self) -> None:
        if self.items_container:
            for w in self.items_container.winfo_children():
                w.destroy()
        # Limitar alcance de atajos globales: marcamos el foco de panel
        if hasattr(self.app, "_active_view"):
            self.app._active_view = "fiados"

    def _update_tree_row(self, fiado: dict[str, Any]) -> None:
        if not fiado or not self.tree_fiados:
            return
        fid = fiado.get("id")
        if not fid:
            return
        try:
            tag = (fiado.get("status") or "").lower()
            self.tree_fiados.item(str(fid), tags=(tag,))
            self.tree_fiados.set(str(fid), column="status", value=fiado.get("status"))
            self.tree_fiados.set(str(fid), column="pendiente", value=f"S/ {fiado.get('total_pendiente', 0):.2f}")
            self.tree_fiados.set(str(fid), column="pagado", value=f"S/ {fiado.get('total_pagado', 0):.2f}")
        except Exception:
            pass

    def _update_action_buttons(self, fiado: Optional[dict[str, Any]]) -> None:
        if not fiado:
            if self.btn_mark_all_paid:
                self.btn_mark_all_paid.configure(state="disabled")
            if self.btn_generate_boleta:
                self.btn_generate_boleta.configure(state="disabled")
            if self.btn_pdf:
                self.btn_pdf.configure(state="disabled")
            return
        status = (fiado.get("status") or "").lower()
        has_items = bool(self.current_items)
        any_pending = any((it.get("status") or "").lower() != "pagado" for it in self.current_items)
        if self.btn_mark_all_paid:
            self.btn_mark_all_paid.configure(state="normal" if has_items and any_pending else "disabled")
        if self.btn_generate_boleta:
            already_sale = bool(fiado.get("sale_id"))
            self.btn_generate_boleta.configure(state="normal" if status == "pagado" and not already_sale else "disabled")
        if self.btn_pdf:
            self.btn_pdf.configure(state="normal" if fiado.get("id") else "disabled")

    def mark_all_paid(self) -> None:
        if not self.current_fiado_id or not self.current_items:
            return
        pending_items = [it for it in self.current_items if (it.get("status") or "").lower() != "pagado"]
        if not pending_items:
            self.app.show_info("Fiado", "Todos los items ya estaban pagados.")
            return
        data = None
        for item in pending_items:
            try:
                data = self.app.fiado_service.set_item_paid(item.get("id"), True)
            except Exception as exc:
                self.app.show_error("Error", str(exc))
                return
        if data:
            fiado = data.get("fiado", {})
            items = data.get("items", [])
            self.current_items = items
            self._update_tree_row(fiado)
            self._render_items(items, fiado.get("id", 0))
            self._update_action_buttons(fiado)

    def generate_boleta(self) -> None:
        if not self.current_fiado_id:
            return
        try:
            result = self.app.fiado_service.generate_official_sale(self.current_fiado_id, series=getattr(self.app, "series", "B001"))
            fiado = result.get("fiado", {})
            self._update_tree_row(fiado)
            self._update_action_buttons(fiado)
            pdf_path = result.get("pdf_path", "")
            serie = result.get("series", "")
            number = result.get("number", 0)
            self._show_pdf_notice(pdf_path, title=f"Boleta {serie}-{int(number):06d}")
        except Exception as exc:
            self.app.show_error("Boleta", str(exc))

    def generate_fiado_pdf(self) -> None:
        if not self.current_fiado_id:
            return
        try:
            client = None
            if self.selected_client_id:
                row = self.app.client_service.get_client_by_id(self.selected_client_id)
                if row:
                    client = {
                        "id": row[0],
                        "dni": row[1],
                        "full_name": row[2],
                        "phone": row[3],
                        "email": row[4],
                        "address": row[5],
                    }
            pdf_path = self.app.fiado_service.generate_fiado_pdf(self.current_fiado_id, client=client)
            self._show_pdf_notice(pdf_path)
        except Exception as exc:
            self.app.show_error("PDF", str(exc))

    def _show_pdf_notice(self, pdf_path: str, title: str = "PDF generado") -> None:
        win = tb.Toplevel(self.app)
        win.title(title)
        self.app.set_app_icon(win)
        self.app.begin_modal_construction(win)
        body = tb.Frame(win, padding=12)
        body.pack(fill="both", expand=True)
        tb.Label(body, text=title, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tb.Label(body, text=pdf_path, wraplength=400).pack(anchor="w", pady=(4, 10))

        btns = tb.Frame(body)
        btns.pack(fill="x", pady=(4, 0))
        tb.Button(btns, text="Cerrar", bootstyle="secondary", command=win.destroy).pack(side="right", padx=4)

        def open_pdf():
            try:
                import os as _os
                if _os.name == "nt":
                    _os.startfile(pdf_path)
                else:
                    import subprocess, shlex

                    subprocess.Popen(shlex.split(f"xdg-open '{pdf_path}'"))
            except Exception as exc:
                self.app.show_error("PDF", f"No se pudo abrir el PDF.\n{exc}")
            win.destroy()

        tb.Button(btns, text="Abrir PDF", bootstyle="info", command=open_pdf).pack(side="right", padx=4)

        # Autocierre en 3 segundos si no hay interacción
        win.after(3000, lambda: win.winfo_exists() and win.destroy())
        self.app.reveal_modal(win)

    # ---------------------------- New fiado ----------------------------
    def add_new_item(self) -> None:
        if not all([self.entry_desc, self.entry_qty, self.entry_price, self.entry_unit, self.entry_block]):
            return
        try:
            qty = float(self.entry_qty.get() or 0)
            price = float(self.entry_price.get() or 0)
        except ValueError:
            self.app.show_warning("Campos", "Cantidad y precio deben ser numeros.")
            return
        desc = self.entry_desc.get().strip()
        unit = self.entry_unit.get().strip()
        block = self.entry_block.get().strip()
        subtotal = qty * price
        item = {
            "description": desc,
            "quantity": qty,
            "unit": unit,
            "unit_price": price,
            "subtotal": subtotal,
            "block": block,
            "product_id": self.selected_product.get("id") if self.selected_product else None,
        }
        self.new_items.append(item)
        self._refresh_new_items_box()

    def _refresh_new_items_box(self) -> None:
        if not self.new_items_box:
            return
        for row in self.new_items_box.get_children():
            self.new_items_box.delete(row)
        for it in self.new_items:
            self.new_items_box.insert(
                "",
                "end",
                values=(
                    it["description"],
                    f"{it['quantity']:.2f}",
                    f"S/ {it['unit_price']:.2f}",
                    f"S/ {it['subtotal']:.2f}",
                    it.get("block") or "-",
                ),
            )

    def clear_new_items(self) -> None:
        self.new_items.clear()
        if self.new_items_box:
            for row in self.new_items_box.get_children():
                self.new_items_box.delete(row)

    def save_fiado(self) -> None:
        if not self.selected_client_id:
            self.app.show_warning("Cliente", "Selecciona un cliente primero.")
            return
        if not self.new_items:
            self.app.show_warning("Items", "Agrega al menos un item.")
            return
        try:
            result = self.app.fiado_service.create_fiado(self.selected_client_id, self.new_items)
            self.app.show_success("Vale creado", f"Codigo: {result.get('code')}", use_toast=True)
            self.clear_new_items()
            self.refresh_fiados()
        except Exception as exc:
            self.app.show_error("Error", str(exc))