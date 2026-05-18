import tkinter as tk
import ttkbootstrap as tb

class ClientUIManager:
    def __init__(self, app):
        self.app = app

    # -------------------------------------------------------------------------
    # AUTOCOMPLETADO Y BÚSQUEDA (VENTAS)
    # -------------------------------------------------------------------------

    def setup_client_autocomplete(self):
        """Configurar búsqueda de clientes con autocompletado integrado."""
        # Bind para búsqueda en tiempo real
        self.app.entry_client_search.bind("<KeyRelease>", self.update_client_suggestions)
        # Bind para navegar a la lista con Tab
        self.app.entry_client_search.bind("<Tab>", self.focus_client_list_first)

    def focus_client_list_first(self, event):
        """Enfocar el primer elemento de la lista de clientes al presionar Tab."""
        if hasattr(self.app, 'client_listbox') and self.app.client_listbox.size() > 0:
            self.app.client_listbox.focus_set()
            self.app.client_listbox.selection_clear(0, tk.END)
            self.app.client_listbox.selection_set(0)
            self.app.client_listbox.activate(0)
            return "break" # Evitar comportamiento default de Tab

    def update_client_suggestions(self, event=None):
        """Actualizar lista de sugerencias de clientes."""
        text = self.app.entry_client_search.get().strip()
        
        # Limpiar sugerencias previas
        if hasattr(self.app, 'client_listbox'):
            self.app.client_listbox.delete(0, tk.END)
        
        if len(text) < 1:
            # Si el campo está vacío, ocultar la lista
            if hasattr(self.app, 'client_listbox_frame'):
                self.app.client_listbox_frame.grid_remove()
            return
        
        # Buscar clientes
        results = self.app.client_service.search_clients(text)
        
        if not results:
            # Si no hay resultados, mostrar opción de crear nuevo
            if not hasattr(self.app, 'client_listbox_frame'):
                self.create_client_listbox_frame()
            self.app.client_listbox.delete(0, tk.END)
            self.app.client_listbox.insert(0, f"+ Crear nuevo cliente: {text}")
            self.app.client_listbox_frame.grid()
            
            # Mostrar mensaje "No existe"
            self.app.label_current_client.config(text="No existe coincidencias", bootstyle="danger")
            return
        
        # Hay resultados, limpiar mensaje de error
        self.app.label_current_client.config(text="")
        
        # Mostrar resultados
        if not hasattr(self.app, 'client_listbox_frame'):
            self.create_client_listbox_frame()
        
        self.app.client_listbox.delete(0, tk.END)
        self.app.client_results = {}
        
        for i, client in enumerate(results):
            display_text = f"{client[2]} (DNI: {client[1]})"  # full_name, dni
            self.app.client_listbox.insert(i, display_text)
            self.app.client_results[i] = client
        
        # Agregar opción para crear nuevo
        self.app.client_listbox.insert(tk.END, f"+ Crear nuevo cliente: {text}")
        self.app.client_listbox_frame.grid()

    def create_client_listbox_frame(self):
        """Crear el frame con la listbox de clientes."""
        # Frame para la listbox usando grid
        self.app.client_listbox_frame = tb.Frame(self.app.client_lf)
        # Row 1: Debajo del buscador y encima de mensajes/info
        self.app.client_listbox_frame.grid(row=1, column=0, columnspan=3, sticky="we", padx=5, pady=2)
        self.app.client_listbox_frame.columnconfigure(0, weight=1)
        
        # Listbox con scrollbar
        scrollbar = tb.Scrollbar(self.app.client_listbox_frame)
        self.app.client_listbox = tk.Listbox(
            self.app.client_listbox_frame,
            height=4,
            yscrollcommand=scrollbar.set,
            bg="#2a2a2a",
            fg="#ffffff",
            relief="solid",
            borderwidth=1
        )
        scrollbar.config(command=self.app.client_listbox.yview)
        
        self.app.client_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.app.client_listbox_frame.rowconfigure(0, weight=1)
        
        # Bind para seleccionar
        self.app.client_listbox.bind("<<ListboxSelect>>", self.select_client_from_list)
        self.app.client_listbox.bind("<Return>", self.select_client_from_list) # Seleccionar con Enter

    def select_client_from_list(self, event=None):
        """Seleccionar cliente de la lista."""
        selection = self.app.client_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        text = self.app.client_listbox.get(index)
        
        # Si es crear nuevo cliente
        if text.startswith("+"):
            dni_or_name = self.app.entry_client_search.get().strip()
            self.show_client_form_window(prefill_dni_or_name=dni_or_name)
            self.app.client_listbox_frame.grid_remove()
            return
        
        # Si es cliente existente
        if index in self.app.client_results:
            client = self.app.client_results[index]
            self.app.current_client = {
                "id": client[0],
                "dni": client[1],
                "full_name": client[2],
                "phone": client[3],
                "email": client[4],
                "address": client[5]
            }
            
            # Actualizar UI
            # self.app.label_current_client.config(text=f"Cliente seleccionado: {self.app.current_client['full_name']} (DNI {self.app.current_client['dni']})")
            # Ya no usamos el label para mostrar el seleccionado, sino los campos small
            self.app.label_current_client.config(text="") # Limpiar mensajes
            
            try:
                self.app.var_client_name_small.set(self.app.current_client.get('full_name', '(ninguno)'))
                self.app.var_client_dni.set(self.app.current_client.get('dni', ''))
                self.app.var_client_phone.set(self.app.current_client.get('phone', ''))
            except Exception:
                pass
            
            # Ocultar lista y limpiar buscador
            self.app.client_listbox_frame.grid_remove()
            self.app.entry_client_search.delete(0, tk.END)
            self.app.entry_client_search.insert(0, self.app.current_client['full_name'])
            
            # Enfocar buscador de productos
            self.app.entry_product_catalog_search.focus()

    def search_or_create_client(self):
        """Busca un cliente por DNI o Nombre, o abre formulario para crear."""
        text = self.app.entry_client_search.get().strip()
        if not text:
            self.app.show_warning("Atención", "Ingrese DNI o Nombre para buscar.")
            return

        clients = self.app.client_service.search_clients(text)
        if not clients:
            # No existe -> Crear
            if self.app.show_question("Cliente no encontrado", f"No se encontró '{text}'. ¿Desea registrarlo?"):
                self.show_client_form_window(prefill_dni_or_name=text)
        elif len(clients) == 1:
            # Uno solo -> Seleccionar
            client = clients[0]
            self.app.current_client = {
                "id": client[0],
                "dni": client[1],
                "full_name": client[2],
                "phone": client[3],
                "email": client[4],
                "address": client[5]
            }
            # self.app.label_current_client.config(text=f"Cliente seleccionado: {self.app.current_client['full_name']} (DNI {self.app.current_client['dni']})")
            self.app.label_current_client.config(text="")
            try:
                self.app.var_client_name_small.set(self.app.current_client.get('full_name', '(ninguno)'))
                self.app.var_client_dni.set(self.app.current_client.get('dni', ''))
                self.app.var_client_phone.set(self.app.current_client.get('phone', ''))
            except Exception:
                pass
            
            # Limpiar lista si estaba abierta
            if hasattr(self.app, 'client_listbox_frame'):
                self.app.client_listbox_frame.grid_remove()
                
        else:
            # Varios -> Mostrar lista para elegir
            self.show_client_selection_window(clients)

    def show_client_selection_window(self, clients):
        win = tb.Toplevel(master=self.app)
        self.app.begin_modal_construction(win)
        win.title("Seleccionar Cliente")
        win.geometry("500x300")
        self.app.set_app_icon(win)

        cols = ("id", "dni", "name", "phone")
        tree = tb.Treeview(win, columns=cols, show="headings", bootstyle="info")
        tree.heading("id", text="ID")
        tree.heading("dni", text="DNI/RUC")
        tree.heading("name", text="Nombre")
        tree.heading("phone", text="Teléfono")
        
        tree.column("id", width=40)
        tree.column("dni", width=100)
        tree.column("name", width=250)
        tree.column("phone", width=100)
        
        tree.pack(fill="both", expand=True, padx=5, pady=5)

        SalesUIHelpers.bind_mousewheel(tree)
        try:
            SalesUIHelpers.bind_mousewheel_to_children(win)
        except Exception:
            pass

        for c in clients:
            # c: (id, dni, name, phone, email, address)
            tree.insert("", "end", values=(c[0], c[1], c[2], c[3]))

        def select():
            sel = tree.focus()
            if not sel:
                return
            values = tree.item(sel, "values")
            # Buscar el cliente completo en la lista original por ID
            c_id = int(values[0])
            client = next((x for x in clients if x[0] == c_id), None)
            
            if client:
                self.app.current_client = {
                    "id": client[0],
                    "dni": client[1],
                    "full_name": client[2],
                    "phone": client[3],
                    "email": client[4],
                    "address": client[5]
                }
                # self.app.label_current_client.config(text=f"Cliente seleccionado: {self.app.current_client['full_name']} (DNI {self.app.current_client['dni']})")
                self.app.label_current_client.config(text="")
                try:
                    self.app.var_client_name_small.set(self.app.current_client.get('full_name', '(ninguno)'))
                    self.app.var_client_dni.set(self.app.current_client.get('dni', ''))
                    self.app.var_client_phone.set(self.app.current_client.get('phone', ''))
                except Exception:
                    pass
            win.destroy()

        btn = tb.Button(win, text="Seleccionar", bootstyle="success", command=select)
        btn.pack(pady=5)

        win.update_idletasks()
        self.app.center_window(win, 500, 300)
        self.app.reveal_modal(win)
        self.app.make_modal(win)

    def show_client_form_window(self, prefill_dni_or_name=""):
        win = tb.Toplevel(master=self.app)
        self.app.begin_modal_construction(win)
        win.title("Registrar Cliente")
        win.geometry("400x350")
        self.app.set_app_icon(win)

        lf = tb.Labelframe(win, text="Nuevo Cliente", padding=10, bootstyle="info")
        lf.pack(fill="both", expand=True, padx=10, pady=10)
        lf.columnconfigure(1, weight=1)

        try:
            SalesUIHelpers.bind_mousewheel_to_children(lf)
        except Exception:
            pass

        # Campos
        tb.Label(lf, text="DNI/RUC:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        entry_dni = tb.Entry(lf)
        entry_dni.grid(row=0, column=1, sticky="we", padx=5, pady=5)
        vcmd_dni = (self.app.register(lambda P: self.app.validate_numeric(P, 11)), "%P")
        entry_dni.configure(validate="key", validatecommand=vcmd_dni)

        tb.Label(lf, text="Nombre Completo:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        entry_name = tb.Entry(lf)
        entry_name.grid(row=1, column=1, sticky="we", padx=5, pady=5)

        tb.Label(lf, text="Teléfono:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        entry_phone = tb.Entry(lf)
        entry_phone.grid(row=2, column=1, sticky="we", padx=5, pady=5)
        vcmd_phone = (self.app.register(lambda P: self.app.validate_numeric(P, 11)), "%P")
        entry_phone.configure(validate="key", validatecommand=vcmd_phone)

        tb.Label(lf, text="Email:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        entry_email = tb.Entry(lf)
        entry_email.grid(row=3, column=1, sticky="we", padx=5, pady=5)

        tb.Label(lf, text="Dirección:").grid(row=4, column=0, sticky="e", padx=5, pady=5)
        entry_address = tb.Entry(lf)
        entry_address.grid(row=4, column=1, sticky="we", padx=5, pady=5)

        # Prefill inteligente
        if prefill_dni_or_name:
            if prefill_dni_or_name.isdigit():
                entry_dni.insert(0, prefill_dni_or_name)
            else:
                entry_name.insert(0, prefill_dni_or_name)
        
        # Forzar mayúsculas
        self.app.setup_uppercase_entry(
            entry_name, 
            entry_dni, 
            entry_phone, 
            entry_email, 
            entry_address
        )

        def save_client():
            try:
                client_id = self.app.client_service.create_client(
                    entry_dni.get().strip(),
                    entry_name.get().strip(),
                    entry_phone.get().strip(),
                    entry_email.get().strip(),
                    entry_address.get().strip()
                )
                client = self.app.client_service.get_client_by_id(client_id)
                self.app.current_client = {
                    "id": client[0],
                    "dni": client[1],
                    "full_name": client[2],
                    "phone": client[3],
                    "email": client[4],
                    "address": client[5]
                }
                self.app.label_current_client.config(text="")
                
                # Populate small client info boxes
                try:
                    self.app.var_client_name_small.set(self.app.current_client.get('full_name', '(ninguno)'))
                    self.app.var_client_dni.set(self.app.current_client.get('dni', ''))
                    self.app.var_client_phone.set(self.app.current_client.get('phone', ''))
                except Exception:
                    pass
                
                # Actualizar buscador con el nombre
                self.app.entry_client_search.delete(0, tk.END)
                self.app.entry_client_search.insert(0, self.app.current_client['full_name'])
                
                # ⭐ NUEVO: Actualizar la tabla de Gestión de Clientes
                try:
                    self.filter_clients()
                except Exception:
                    pass  # Si falla, no es crítico
                
                win.destroy()
            except ValueError as e:
                self.app.show_error("Error", str(e))

        btn_save = tb.Button(lf, text="Guardar cliente", bootstyle="success-outline", command=save_client)
        btn_save.grid(row=5, column=0, columnspan=2, pady=10)

        win.update_idletasks()
        self.app.center_window(win, 400, 350)
        self.app.reveal_modal(win)
        self.app.make_modal(win)

    # -------------------------------------------------------------------------
    # GESTIÓN DE CLIENTES (PESTAÑA ACTUALIZAR INFO)
    # -------------------------------------------------------------------------

    def filter_clients(self, event=None):
        """Filtra la tabla de clientes en la pestaña de gestión."""
        search = self.app.entry_search_client.get().strip()
        if search == "Buscar cliente...":
            search = ""
            
        clients = self.app.client_service.search_clients(search)
        
        self.app.tree_clients.delete(*self.app.tree_clients.get_children())
        for c in clients:
            self.app.tree_clients.insert("", "end", values=c)

    def on_client_select(self, event):
        """Carga datos del cliente seleccionado en el formulario de edición."""
        sel = self.app.tree_clients.focus()
        if not sel:
            return
        values = self.app.tree_clients.item(sel, "values")
        # values: (id, dni, name, phone, email, address)
        
        self.app.entry_client_dni.delete(0, tk.END)
        self.app.entry_client_dni.insert(0, values[1])
        
        self.app.entry_client_name.delete(0, tk.END)
        self.app.entry_client_name.insert(0, values[2])
        
        self.app.entry_client_phone.delete(0, tk.END)
        self.app.entry_client_phone.insert(0, values[3])
        
        self.app.entry_client_email.delete(0, tk.END)
        self.app.entry_client_email.insert(0, values[4])
        
        self.app.entry_client_address.delete(0, tk.END)
        self.app.entry_client_address.insert(0, values[5])
        
        self.app.selected_client_id = values[0]

    def clear_client_form(self):
        """Limpia el formulario de gestión de clientes."""
        self.app.entry_client_dni.delete(0, tk.END)
        self.app.entry_client_name.delete(0, tk.END)
        self.app.entry_client_phone.delete(0, tk.END)
        self.app.entry_client_email.delete(0, tk.END)
        self.app.entry_client_address.delete(0, tk.END)
        self.app.selected_client_id = None
        self.app.tree_clients.selection_remove(self.app.tree_clients.selection())

    def save_client_action(self):
        """Guarda (crea o actualiza) un cliente desde la pestaña de gestión."""
        dni = self.app.entry_client_dni.get().strip()
        name = self.app.entry_client_name.get().strip()
        phone = self.app.entry_client_phone.get().strip()
        email = self.app.entry_client_email.get().strip()
        address = self.app.entry_client_address.get().strip()
        
        if not dni or not name:
            self.app.show_warning("Atención", "DNI y Nombre son obligatorios.")
            return

        try:
            if self.app.selected_client_id:
                # Actualizar
                self.app.client_service.update_client(self.app.selected_client_id, dni, name, phone, email, address)
                self.app.show_success("Éxito", "Cliente actualizado correctamente.")
            else:
                # Crear
                self.app.client_service.create_client(dni, name, phone, email, address)
                self.app.show_success("Éxito", "Cliente creado correctamente.")
            
            self.clear_client_form()
            self.filter_clients() # Recargar tabla
            
        except ValueError as e:
            self.app.show_error("Error", str(e))

    def delete_client_action(self):
        """Elimina el cliente seleccionado."""
        if not self.app.selected_client_id:
            self.app.show_warning("Atención", "Seleccione un cliente para eliminar.")
            return

        if not self.app.show_question("Confirmar", "¿Está seguro de eliminar este cliente?"):
            return

        try:
            # Guardar snapshot para deshacer
            sel = self.app.tree_clients.focus() or (self.app.tree_clients.selection()[0] if self.app.tree_clients.selection() else "")
            values = self.app.tree_clients.item(sel, "values") if sel else None
            if values:
                # (id, dni, name, phone, email, addr)
                self.app.undo_last_client = tuple(values)

            self.app.client_service.delete_client(self.app.selected_client_id)
            self.app.show_success("Éxito", "Cliente eliminado.")
            self.clear_client_form()
            self.filter_clients()
        except Exception as e:
            self.app.show_error("Error", f"No se pudo eliminar el cliente: {e}")
