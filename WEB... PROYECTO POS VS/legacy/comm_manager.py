import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

class CommunicationService:
    def __init__(self):
        # CONFIGURACIÓN PARA GMAIL (La que funciona)
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def send_email_with_pdf(self, to_email, subject, body, pdf_path, sender_email, sender_password):
        """
        Envía un correo electrónico usando GMAIL con un archivo PDF adjunto.
        """
        if not to_email or "@" not in to_email:
            return False, "El correo del destinatario no es válido."

        if not os.path.exists(pdf_path):
            return False, "El archivo PDF no existe en la ruta indicada."

        # Configurar el mensaje MIME
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject

        # Cuerpo del mensaje
        msg.attach(MIMEText(body, 'plain'))

        # Adjuntar PDF
        try:
            with open(pdf_path, "rb") as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
                part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
                msg.attach(part)
        except Exception as e:
            return False, f"Error al adjuntar el PDF: {str(e)}"

        # Conexión con el Servidor
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Encriptación segura
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            return True, "Correo enviado exitosamente."
        except smtplib.SMTPAuthenticationError:
            return False, "Error de Acceso: Google rechazó la contraseña. Asegúrate de usar la 'Contraseña de Aplicación' de 16 letras."
        except Exception as e:
            return False, f"Error de conexión: {str(e)}"