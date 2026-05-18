import os
import smtplib
import time
import webbrowser
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

try:
    import pyautogui
    import win32clipboard

    WHATSAPP_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    WHATSAPP_AVAILABLE = False


class CommunicationService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def send_email_with_pdf(
        self,
        to_email,
        subject,
        body,
        pdf_path,
        sender_email,
        sender_password,
        company_name=None,
        body_html=None,
        logo_path=None,
    ):
        if not to_email or "@" not in to_email:
            return False, "El correo del destinatario no es válido."

        if not os.path.exists(pdf_path):
            return False, "El archivo PDF no existe en la ruta indicada."

        msg = MIMEMultipart("mixed")

        if company_name:
            msg["From"] = formataddr((company_name, sender_email))
        else:
            msg["From"] = sender_email

        msg["To"] = to_email
        msg["Subject"] = subject

        msg_related = MIMEMultipart("related")
        msg.attach(msg_related)

        if body_html:
            msg_alternative = MIMEMultipart("alternative")
            msg_related.attach(msg_alternative)

            msg_alternative.attach(MIMEText(body, "plain"))
            msg_alternative.attach(MIMEText(body_html, "html"))

            if logo_path and os.path.exists(logo_path):
                try:
                    with open(logo_path, "rb") as f:
                        img_data = f.read()
                    image = MIMEImage(img_data)
                    image.add_header("Content-ID", "<company_logo>")
                    image.add_header("Content-Disposition", "inline")
                    msg_related.attach(image)
                except Exception as exc:  # pragma: no cover - logging elsewhere
                    print(f"Error incrustando logo: {exc}")
        else:
            msg_related.attach(MIMEText(body, "plain"))

        try:
            with open(pdf_path, "rb") as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=os.path.basename(pdf_path),
                )
                msg.attach(part)
        except Exception as exc:
            return False, f"Error al adjuntar el PDF: {exc}"

        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            return True, "Correo enviado exitosamente."
        except smtplib.SMTPAuthenticationError:
            return False, (
                "Error de Acceso: Google rechazó la contraseña. Asegúrate de usar la "
                "'Contraseña de Aplicación' de 16 letras."
            )
        except Exception as exc:
            return False, f"Error de conexión: {exc}"

    def send_whatsapp_pdf(self, phone_number, pdf_path, message="", wait_seconds=5):
        if not WHATSAPP_AVAILABLE:
            return False, "Librerías no disponibles. Instala: pip install pywin32 pyautogui"

        phone_clean = "".join(filter(str.isdigit, phone_number))

        if not phone_clean or len(phone_clean) < 9:
            return False, "Número de teléfono inválido. Debe tener al menos 9 dígitos."

        if len(phone_clean) == 9:
            phone_clean = "51" + phone_clean

        phone_number = phone_clean

        if not os.path.exists(pdf_path):
            return False, f"El archivo PDF no existe: {pdf_path}"

        try:
            wait_cap = max(3, min(int(wait_seconds or 5), 10))
            whatsapp_url = f"whatsapp://send?phone={phone_number}"
            webbrowser.open(whatsapp_url)
            time.sleep(wait_cap)

            if message:
                try:
                    self._copy_text_to_clipboard(message)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(0.6)
                    pyautogui.press("enter")
                    time.sleep(1)
                except Exception:
                    pyautogui.write(message, interval=0.01)
                    time.sleep(0.5)
                    pyautogui.press("enter")
                    time.sleep(1)

            self._copy_file_to_clipboard(pdf_path)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(1.5)
            pyautogui.press("enter")

            return True, f"PDF enviado automáticamente por WhatsApp a {phone_number}"
        except Exception as exc:
            return False, f"Error al enviar por WhatsApp: {exc}"

    def send_whatsapp_message(self, phone_number, message, wait_seconds=5):
        if not WHATSAPP_AVAILABLE:
            return False, "Librerías no disponibles. Instala: pip install pywin32 pyautogui"

        phone_clean = "".join(filter(str.isdigit, phone_number))

        if not phone_clean or len(phone_clean) < 9:
            return False, "Número de teléfono inválido. Debe tener al menos 9 dígitos."

        if len(phone_clean) == 9:
            phone_clean = "51" + phone_clean

        phone_number = phone_clean

        try:
            wait_cap = max(3, min(int(wait_seconds or 5), 10))
            from urllib.parse import quote
            msg_encoded = quote(message)
            whatsapp_url = f"whatsapp://send?phone={phone_number}&text={msg_encoded}"
            webbrowser.open(whatsapp_url)
            time.sleep(wait_cap)
            pyautogui.press("enter")
            return True, f"Mensaje enviado automáticamente por WhatsApp a {phone_number}"
        except Exception as exc:
            return False, f"Error al enviar por WhatsApp: {exc}"

    def _copy_file_to_clipboard(self, file_path):
        import struct
        import win32con

        file_path = os.path.abspath(file_path)

        offset = struct.calcsize("IIIII")
        path_bytes = (file_path + "\0").encode("utf-16-le")
        dropfiles = struct.pack("IIIII", offset, 0, 0, 0, 1)
        data = dropfiles + path_bytes + b"\0\0"

        clipboard_open = False
        attempts = 0
        while not clipboard_open and attempts < 5:
            try:
                win32clipboard.OpenClipboard()
                clipboard_open = True
            except Exception:
                attempts += 1
                time.sleep(0.05)

        if not clipboard_open:
            raise RuntimeError("No se pudo acceder al portapapeles de Windows")

        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_HDROP, data)
        finally:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass

    def _copy_text_to_clipboard(self, text: str) -> None:
        import win32clipboard
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()

    def _is_whatsapp_desktop_available(self) -> bool:
        if os.name != "nt":
            return True

        paths_to_check = []
        try:
            local_app = os.environ.get("LOCALAPPDATA", "")
            prog_files = os.environ.get("ProgramFiles", "")
            prog_files_x86 = os.environ.get("ProgramFiles(x86)", "")
            paths_to_check.extend([
                os.path.join(local_app, "Microsoft", "WindowsApps", "WhatsApp.exe"),
                os.path.join(local_app, "WhatsApp", "WhatsApp.exe"),
                os.path.join(prog_files, "WindowsApps"),
                os.path.join(prog_files_x86, "WindowsApps"),
            ])
        except Exception:
            pass

        for p in paths_to_check:
            if p and os.path.isfile(p):
                return True
            if p and os.path.isdir(p):
                try:
                    for root, _dirs, files in os.walk(p):
                        if any(f.lower() == "whatsapp.exe" for f in files):
                            return True
                except Exception:
                    continue
        return False
