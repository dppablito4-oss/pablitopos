from repositories.client_repo import ClientRepository


class ClientService:
    def __init__(self, repo: ClientRepository):
        self.repo = repo

    def search_clients(self, text):
        return self.repo.search_clients(text)

    def get_client_by_id(self, client_id):
        return self.repo.get_client_by_id(client_id)

    def create_client(self, dni, full_name, phone, email, address):
        if not full_name.strip():
            raise ValueError("El nombre es obligatorio.")
        if dni and not dni.isdigit():
            raise ValueError("El DNI debe ser numérico.")
        if phone and not phone.isdigit():
            raise ValueError("El celular debe ser numérico.")
        if dni and len(dni) < 6:
            raise ValueError("El DNI parece demasiado corto.")
        return self.repo.create_client(dni, full_name, phone, email, address)

    def update_client(self, client_id, dni, full_name, phone, email, address):
        if not full_name.strip():
            raise ValueError("El nombre es obligatorio.")
        if dni and not dni.isdigit():
            raise ValueError("El DNI debe ser numérico.")
        if phone and not phone.isdigit():
            raise ValueError("El celular debe ser numérico.")
        if dni and len(dni) < 6:
            raise ValueError("El DNI parece demasiado corto.")
        return self.repo.update_client(client_id, dni, full_name, phone, email, address)

    def delete_client(self, client_id):
        return self.repo.delete_client(client_id)
