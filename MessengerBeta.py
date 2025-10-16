# Codigo de inicio de session y de Contactos de Messenger
# Este codigo esta sujeto a cambios y actualizaciones constantes.
# Si lo usas con fines de lucro recuerda que debes mencionar el creador.
# Messenger.py  (Archivo fusionado completo)
import sys
import json
from pathlib import Path
import colorsys
import requests
from io import BytesIO
import os
import subprocess
import threading
import socket
from urllib.parse import urlparse

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QComboBox, QCheckBox,
    QPushButton, QVBoxLayout, QHBoxLayout, QMenuBar, QAction, QMessageBox,
    QTextEdit, QDialog, QFormLayout, QColorDialog, QSpacerItem, QSizePolicy,
    QListWidget, QStackedWidget, QFileDialog, QGridLayout, QTabWidget, QGroupBox,
    QTreeWidget, QTreeWidgetItem, QToolButton, QStyle, QMenu, QInputDialog
)
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QLinearGradient, QColor, QMovie
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QUrl, QTimer, QSize, QByteArray, QRect, QPoint
from PyQt5.QtWebSockets import QWebSocket
from PyQt5.QtNetwork import QSsl, QSslConfiguration, QSslCertificate, QSslKey, QSslSocket, QAbstractSocket

# -------------------------------
# CONFIGURACIÓN GLOBAL
# -------------------------------
CONFIG_DIR = Path.home() / ".config" / "Messenger"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_CHAT_IMAGE = "https://raw.githubusercontent.com/mggons93/Messenger/main/files/user-image.png"

PATH_VERSION_LOCAL = "C:\\MSN\\version.json"
#Aqui se pone el url de version.json donde se va a actualizar el launcher messenger.exe
UPDATE_URL = "https://xxxxxxxx.xxx/files/Messenger/version.json" 

def leer_version_local(path_version):
    """Lee la versión y el canal actual del archivo local version.json"""
    if not os.path.exists(path_version):
        return "v0.0.0", "release"
    try:
        with open(path_version, "r", encoding="utf-8") as f:
            data = json.load(f)

            # Estructura simple
            if "version" in data:
                canal = data.get("channel", "release")
                return data["version"], canal

            # Estructura por canal
            for canal in ("release", "beta", "dev"):
                if canal in data and "version" in data[canal]:
                    return data[canal]["version"], canal

            return "v0.0.0", "release"
    except Exception as e:
        print(f"Error leyendo version.json: {e}")
        return "v0.0.0", "release"


VERSION, CANAL_ACTUAL = leer_version_local(PATH_VERSION_LOCAL)


# -------------------------------
# UTILIDADES (descarga/cache)
# -------------------------------
def ensure_cache_file(url, filename):
    """Descarga un archivo desde url si no está cacheado en ~/.cache/Messenger"""
    home_cache_dir = Path.home() / ".cache" / "Messenger"
    home_cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = home_cache_dir / filename
    if not cache_file.exists():
        try:
            import urllib.request
            urllib.request.urlretrieve(url, cache_file)
        except Exception as e:
            print(f"Error descargando {url}: {e}")
    return str(cache_file)

def cargar_imagen(ruta_o_url):
    parsed = urlparse(ruta_o_url)
    if parsed.scheme in ("http", "https"):
        try:
            response = requests.get(ruta_o_url, timeout=8)
            if response.status_code == 200:
                img_data = BytesIO(response.content)
                pixmap = QPixmap()
                pixmap.loadFromData(img_data.read())
                return pixmap
        except Exception as e:
            print(f"Error cargando imagen desde URL {ruta_o_url}: {e}")
        return QPixmap()
    else:
        return QPixmap(ruta_o_url)

# -------------------------------
# CONFIG: cargar/guardar (unificada)
# -------------------------------
def load_config():
    default = {
        "personal": {
            "display_name": "",
            "personal_message": "",
            "show_song_info": False,
            "show_image": False,
            "status_away_inactive_minutes": 5,
            "status_busy_fullscreen": True,
            "webcam_allowed": True
        },
        "signin": {
            "auto_start": True,
            "allow_automatic_signin": True,
            "multi_location_logoutall": False
        },
        "alerts": {
            "alert_contact_signin": True,
            "alert_message_received": True
        },
        "filetransfer": {
            "received_folder": "",
            "scan_tool_path": "",
            "auto_reject_unsecure": False
        },
        "connection": {
            "connection_status": "No conectado"
        },
        "websocket": {
            "host": "syasoporteglobal.online",
            "port_ws": "8765",
            "port_wss": "8766",
            "use_ssl_wss": True,
            "ssl_key": "",
            "ssl_cert": ""
        },
        "filetransfer": {
            "port_http": "8085",
            "port_https": "8086"
        },
        "app_settings": {
            "chat_name": "Beta Messenger",
            "chat_image": DEFAULT_CHAT_IMAGE,
            "username": "",
            "remember_me": False,
            "remember_config": False,
            "auto_signin": False,
            "primary_color": "#2171b4",
            "use_rgb": False,
            "status": "",
            "menubar_visible": False
        }
    }

    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                #print("DEBUG: Config leído, host =", data.get("websocket", {}).get("host"))  # Añade esto
                # completar claves faltantes recursivamente
                for k, v in default.items():
                    if k not in data:
                        data[k] = v
                    elif isinstance(v, dict):
                        for subk, subv in v.items():
                            if subk not in data[k]:
                                data[k][subk] = subv
                return data
        else:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=4, ensure_ascii=False)
            return default
    except Exception as e:
        print(f"Error loading config: {e}")
        return default
def save_config(config):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")

# -------------------------------
# UTIL: color
# -------------------------------
def is_color_dark(color: QColor) -> bool:
    luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
    return luminance < 128

# -------------------------------
# WEBSOCKET MANAGER (singleton)
# -------------------------------
class WebSocketManager(QObject):
    message_received = pyqtSignal(dict)
    connected = pyqtSignal()
    disconnected = pyqtSignal()

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            super().__init__()
            self._initialized = True
            self.client = WebSocketClient()  # Instanciar directamente si está en el mismo archivo
            self.client.message_received.connect(self.on_message)
            self.client.connected.connect(lambda: self.connected.emit())
            self.client.disconnected.connect(lambda: self.disconnected.emit())

    def connect(self, url):
        if self.ws.state() != QWebSocket.ConnectedState:
            self.ws.open(QUrl(url))

    def disconnect(self):
        if self.ws.state() == QWebSocket.ConnectedState:
            self.ws.close()

    def send(self, message):
        if self.ws.state() == QWebSocket.ConnectedState:
            self.ws.sendTextMessage(json.dumps(message))

    def on_message(self, message):
        try:
            data = json.loads(message)
            self.message_received.emit(data)
        except Exception as e:
            print("Error parseando mensaje WS:", e)

# -------------------------------
# WEBSOCKET CLIENT
# -------------------------------
class WebSocketClient(QObject):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    message_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, url=None, config=None):
        super().__init__()
        self.config = config or load_config()
        self.ws = QWebSocket()

        # Conexiones de señales internas
        self.ws.connected.connect(self.on_connected)
        self.ws.disconnected.connect(self.on_disconnected)
        self.ws.textMessageReceived.connect(self.on_message)

        # QWebSocket.error signal signature depende de PyQt versión
        try:
            self.ws.error.connect(self.on_error)
        except Exception:
            pass

        self.url = QUrl(url) if url else None

    def open(self):
        try:
            print("DEBUG: self.config en WebSocketClient:", self.config)
            cfg_ws = self.config.get("websocket", {})
            print("DEBUG: cfg_ws dict:", cfg_ws)
            cfg_ft = self.config.get("filetransfer", {})

            host = self.config.get("host", "").strip()
            print("DEBUG: Host recibido para conexión:", host)
            if not host:
                self.error_occurred.emit("Host no configurado")
                return

            use_ssl = bool(self.config.get("use_ssl_wss", False))
            port = self.config.get("port_wss" if use_ssl else "port_ws", "8765")
            scheme = "wss" if use_ssl else "ws"

            self.url = QUrl(f"{scheme}://{host}:{port}/ws")
            print(f"🌐 Conectando a {self.url.toString()}")

            if use_ssl:
                ssl_config = QSslConfiguration.defaultConfiguration()

                # Cargar certificado
                cert_file = cfg_ws.get("ssl_cert", "").strip()
                if cert_file:
                    try:
                        with open(cert_file, "rb") as f:
                            cert_data = f.read()
                        cert = QSslCertificate(QByteArray(cert_data))
                        if not cert.isNull():
                            ssl_config.addCaCertificate(cert)
                            print(f"✔ Certificado cargado: {cert_file}")
                    except Exception as e:
                        print(f"⚠ Error cargando certificado: {e}")

                # Cargar clave privada
                key_file = cfg_ws.get("ssl_key", "").strip()
                if key_file:
                    try:
                        with open(key_file, "rb") as f:
                            key_data = f.read()
                        key = QSslKey(QByteArray(key_data), QSslKey.Rsa, QSslKey.Pem, QSslKey.PrivateKey)
                        if not key.isNull():
                            ssl_config.setPrivateKey(key)
                            print(f"✔ Clave privada cargada: {key_file}")
                    except Exception as e:
                        print(f"⚠ Error cargando clave privada: {e}")

                self.ws.setSslConfiguration(ssl_config)

            self.ws.open(self.url)

        except Exception as e:
            self.error_occurred.emit(f"Error al abrir WebSocket: {e}")

    def on_connected(self):
        print("WebSocket conectado.")
        self.connected.emit()

    def on_disconnected(self):
        print("WebSocket desconectado.")
        self.disconnected.emit()

    def on_message(self, msg: str):
        """
        ✅ Este método ahora SOLO reemite el mensaje recibido como señal Qt
        para que la interfaz (LoginWindow) lo procese.
        """
        print(f"Mensaje recibido: {msg}")
        self.message_received.emit(msg)  # ✅ Aquí está la clave

    def on_error(self, error):
        try:
            errstr = self.ws.errorString()
        except Exception:
            errstr = ""
        print(f"Error WebSocket: {error} {errstr}")
        self.error_occurred.emit(f"{error}: {errstr}")

    def send(self, msg):
        if self.ws.state() == QAbstractSocket.ConnectedState:
            self.ws.sendTextMessage(msg)
        else:
            self.error_occurred.emit("No conectado: no se puede enviar mensaje.")

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass

# -------------------------------
# DIALOGS OPCIONES (fusionados)
# -------------------------------
class PruebaConexionDialog(QDialog):
    def __init__(self, parent=None, host="www.google.com", port=80):
        super().__init__(parent)
        self.setWindowTitle("Prueba de conexión")
        self.setFixedSize(370, 170)

        icon_path = ensure_cache_file("https://raw.githubusercontent.com/mggons93/Messenger/main/files/settings.ico", "settings.ico")
        try:
            self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass

        layout = QVBoxLayout(self)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

        hbox = QHBoxLayout()
        self.btnAceptar = QPushButton("Aceptar")
        self.btnAceptar.setEnabled(False)
        self.btnCancelar = QPushButton("Cancelar")
        hbox.addWidget(self.btnAceptar)
        hbox.addWidget(self.btnCancelar)
        layout.addLayout(hbox)

        self.btnAceptar.clicked.connect(self.accept)
        self.btnCancelar.clicked.connect(self.reject)

        self.mensajes = [
            "Resolviendo el nombre del servidor...",
            "Conectando con el servidor...",
            "Conectado, comprobando la disponibilidad para enviar datos ahora...",
            "Puedes conectarte al servicio Messenger."
        ]
        self.index = 0
        self._test_host = host
        self._test_port = port
        self._test_real = None

        self._start_test()

    def _start_test(self):
        self.text.clear()
        self.index = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._show_next)
        self.timer.start(950)

    def _show_next(self):
        if self.index == 1:
            try:
                s = socket.create_connection((self._test_host, self._test_port), timeout=2)
                s.close()
                self._test_real = True
            except Exception:
                self._test_real = False
        if self.index < len(self.mensajes):
            self.text.append(self.mensajes[self.index])
            self.index += 1
        else:
            self.timer.stop()
            self.btnAceptar.setEnabled(True)
            if self._test_real is False:
                self.text.append("No se pudo conectar: Fallo de red o servidor inalcanzable.")

class ConfigAvanzadaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setFixedSize(420, 435)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<b>Configuración de conexión de Internet Explorer</b>"))
        layout.addWidget(QLabel("Haz clic en Probar a continuación para comprobar cada configuración de conexión.<br>Cambia la configuración sólo si sabes cómo resolver el problema de conexión."))

        tcp_line = QHBoxLayout()
        tcp_line.addWidget(QLabel("TCP"))
        tcp_line.addWidget(QLabel("No existe ninguna configuración avanzada para una conexión TCP."))
        tcp_line.addStretch()
        tcp_btn = QPushButton("Probar")
        tcp_line.addWidget(tcp_btn)
        layout.addLayout(tcp_line)

        socks_layout = QHBoxLayout()
        socks_label = QLabel("SOCKS")
        self.socks_host = QLineEdit()
        self.socks_host.setPlaceholderText("Servidor")
        self.socks_port = QLineEdit("1080")
        self.socks_port.setFixedWidth(50)
        socks_btn = QPushButton("Probar")
        socks_layout.addWidget(socks_label)
        socks_layout.addWidget(self.socks_host)
        socks_layout.addWidget(QLabel(":"))
        socks_layout.addWidget(self.socks_port)
        socks_layout.addWidget(socks_btn)
        layout.addLayout(socks_layout)
        socks_layout.addSpacing(10)
        socks_layout.addStretch()

        layout.addLayout(self._userpass_controls("SOCKS"))

        http_layout = QHBoxLayout()
        http_label = QLabel("HTTP")
        self.http_host = QLineEdit()
        self.http_host.setPlaceholderText("Servidor")
        self.http_port = QLineEdit()
        self.http_port.setFixedWidth(50)
        http_btn = QPushButton("Probar")
        http_layout.addWidget(http_label)
        http_layout.addWidget(self.http_host)
        http_layout.addWidget(QLabel(":"))
        http_layout.addWidget(self.http_port)
        http_layout.addWidget(http_btn)
        layout.addLayout(http_layout)
        layout.addSpacing(10)
        layout.addStretch()

        layout.addLayout(self._userpass_controls("HTTP"))

        layout.addWidget(QLabel("<b>Configuración de Messenger</b>"))
        self.log_cb = QCheckBox("Guardar un registro de mis conexiones de servidor para ayudar a solucionar los problemas de conexión.")
        layout.addWidget(self.log_cb)
        layout.addWidget(QLabel("Nota: mediante esta acción se guardará un archivo con información personal en el equipo. Cualquier persona con acceso a este equipo puede ver el archivo."))

        reg_layout = QHBoxLayout()
        ver_btn = QPushButton("Ver registro")
        borrar_btn = QPushButton("Borrar registro")
        reg_layout.addWidget(ver_btn)
        reg_layout.addWidget(borrar_btn)
        reg_layout.addStretch()
        layout.addLayout(reg_layout)

        btns = QHBoxLayout()
        aceptar = QPushButton("Aceptar")
        cancelar = QPushButton("Cancelar")
        ayuda = QPushButton("Ayuda")
        btns.addWidget(aceptar)
        btns.addWidget(cancelar)
        btns.addStretch()
        btns.addWidget(ayuda)
        layout.addLayout(btns)

        cancelar.clicked.connect(self.reject)
        aceptar.clicked.connect(self.accept)
        ayuda.clicked.connect(lambda: QMessageBox.information(self, "Ayuda", "Opciones avanzadas de conexión."))

        tcp_btn.clicked.connect(lambda: PruebaConexionDialog(self, host="www.google.com", port=80).exec_())
        socks_btn.clicked.connect(lambda: PruebaConexionDialog(self, host=self.socks_host.text(), port=int(self.socks_port.text() or "1080")).exec_())
        http_btn.clicked.connect(lambda: PruebaConexionDialog(self, host=self.http_host.text() or "www.google.com", port=int(self.http_port.text() or "80")).exec_())

    def _userpass_controls(self, prefix):
        layout = QHBoxLayout()
        layout.addSpacing(30)
        layout.addWidget(QLabel("Nombre de usuario:"))
        setattr(self, f"{prefix.lower()}_user", QLineEdit())
        layout.addWidget(getattr(self, f"{prefix.lower()}_user"))
        layout.addWidget(QLabel("Contraseña:"))
        setattr(self, f"{prefix.lower()}_pass", QLineEdit())
        getattr(self, f"{prefix.lower()}_pass").setEchoMode(QLineEdit.Password)
        layout.addWidget(getattr(self, f"{prefix.lower()}_pass"))
        return layout

class OpcionesDialog(QDialog):
    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opciones")
        self.setFixedSize(550, 550)

        # usar config pasado o cargar
        self.config = config if isinstance(config, dict) else load_config()

        icon_path = ensure_cache_file("https://raw.githubusercontent.com/mggons93/Messenger/main/files/settings.ico", "settings.ico")
        try:
            self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass

        content_widget = QWidget(self)
        main_layout = QHBoxLayout(content_widget)
        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(145)
        self.sections = ["Personal", "Iniciar sesión", "Alertas", "Transferencia de archivos", "Conexión", "WebSocket/HTTPS"]
        self.list_widget.addItems(self.sections)
        self.list_widget.setCurrentRow(0)
        main_layout.addWidget(self.list_widget, 1)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 4)
        self.pages = {}
        self.pages["Personal"] = self.crear_pagina_personal()
        self.pages["Iniciar sesión"] = self.crear_pagina_iniciar_sesion()
        self.pages["Alertas"] = self.crear_pagina_alertas()
        self.pages["Transferencia de archivos"] = self.crear_pagina_transferencia()
        self.pages["Conexión"] = self.crear_pagina_conexion()
        self.pages["WebSocket/HTTPS"] = self.crear_pagina_websocket()

        for key in self.sections:
            self.stack.addWidget(self.pages[key])

        self.list_widget.currentRowChanged.connect(self.stack.setCurrentIndex)

        buttons_layout = QHBoxLayout()
        self.btn_aceptar = QPushButton("Aceptar")
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_aplicar = QPushButton("Aplicar")
        self.btn_ayuda = QPushButton("Ayuda")

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_aceptar)
        buttons_layout.addWidget(self.btn_cancelar)
        buttons_layout.addWidget(self.btn_aplicar)
        buttons_layout.addWidget(self.btn_ayuda)

        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(content_widget)
        outer_layout.addLayout(buttons_layout)
        self.setLayout(outer_layout)

        self.btn_aceptar.clicked.connect(self.aceptar)
        self.btn_cancelar.clicked.connect(self.cancelar)
        self.btn_aplicar.clicked.connect(self.aplicar)
        self.btn_ayuda.clicked.connect(self.ayuda)

        # cargar valores
        self.cargar_datos()

    # ---------------------------
    # Cargar / Guardar
    # ---------------------------
    def cargar_datos(self):
        c = self.config
        # Personal
        self.personal_nombre_edit.setText(c["personal"].get("display_name", ""))
        self.personal_mensaje_edit.setPlainText(c["personal"].get("personal_message", ""))
        self.personal_cancion_cb.setChecked(c["personal"].get("show_song_info", False))
        self.personal_imagen_cb.setChecked(c["personal"].get("show_image", False))
        self.personal_ausente_spin.setCurrentText(str(c["personal"].get("status_away_inactive_minutes", 5)))
        self.personal_ocupado_cb.setChecked(c["personal"].get("status_busy_fullscreen", True))
        self.personal_webcam_cb.setChecked(c["personal"].get("webcam_allowed", True))

        # Signin
        self.signin_autostart_cb.setChecked(c["signin"].get("auto_start", True))
        self.signin_automatic_cb.setChecked(c["signin"].get("allow_automatic_signin", True))
        self.signin_cerrarestado_cb.setChecked(c["signin"].get("multi_location_logoutall", False))

        # Alerts
        self.alertas_contacto_cb.setChecked(c["alerts"].get("alert_contact_signin", True))
        self.alertas_mensaje_cb.setChecked(c["alerts"].get("alert_message_received", True))

        # Filetransfer
        self.filetransfer_folder_edit.setText(c["filetransfer"].get("received_folder", ""))
        self.filetransfer_scanpath_edit.setText(c["filetransfer"].get("scan_tool_path", ""))
        self.filetransfer_autoreject_cb.setChecked(c["filetransfer"].get("auto_reject_unsecure", False))

        # Connection label
        self.conexion_estado_label.setText(c["connection"].get("connection_status", "No conectado"))

        # WebSocket / HTTPS (cargar datos)
        ws = c.get("websocket", {})
        ft = c.get("filetransfer", {})

        self.websocket_host.setText(ws.get("host", ""))
        self.ws_port_input.setText(ws.get("port_ws", ""))
        self.wss_port_input.setText(ws.get("port_wss", ""))
        self.http_port_input.setText(ft.get("port_http", ""))
        self.https_port_input.setText(ft.get("port_https", ""))
        self.certificados_confianza_cb.setChecked(ws.get("use_ssl_wss", False))
        self.certificados_key.setText(ws.get("ssl_key", ""))
        self.certificados_cert.setText(ws.get("ssl_cert", ""))

    def guardar_datos(self):
        c = self.config
        # Personal
        c["personal"]["display_name"] = self.personal_nombre_edit.text()
        c["personal"]["personal_message"] = self.personal_mensaje_edit.toPlainText()
        c["personal"]["show_song_info"] = self.personal_cancion_cb.isChecked()
        c["personal"]["show_image"] = self.personal_imagen_cb.isChecked()
        c["personal"]["status_away_inactive_minutes"] = int(self.personal_ausente_spin.currentText())
        c["personal"]["status_busy_fullscreen"] = self.personal_ocupado_cb.isChecked()
        c["personal"]["webcam_allowed"] = self.personal_webcam_cb.isChecked()

        # Signin
        c["signin"]["auto_start"] = self.signin_autostart_cb.isChecked()
        c["signin"]["allow_automatic_signin"] = self.signin_automatic_cb.isChecked()
        c["signin"]["multi_location_logoutall"] = self.signin_cerrarestado_cb.isChecked()

        # Alerts
        c["alerts"]["alert_contact_signin"] = self.alertas_contacto_cb.isChecked()
        c["alerts"]["alert_message_received"] = self.alertas_mensaje_cb.isChecked()

        # Filetransfer
        c["filetransfer"]["received_folder"] = self.filetransfer_folder_edit.text()
        c["filetransfer"]["scan_tool_path"] = self.filetransfer_scanpath_edit.text()
        c["filetransfer"]["auto_reject_unsecure"] = self.filetransfer_autoreject_cb.isChecked()


        # WebSocket / HTTPS ajustado sin mTLS (guardar datos)
        self.config["websocket"] = {
            "host": self.websocket_host.text().strip(),
            "port_ws": self.ws_port_input.text().strip(),
            "port_wss": self.wss_port_input.text().strip(),
            "use_ssl_wss": self.certificados_confianza_cb.isChecked(),
            "ssl_key": self.certificados_key.text().strip(),
            "ssl_cert": self.certificados_cert.text().strip()
        }
        self.config["filetransfer"] = {
            "port_http": self.http_port_input.text().strip(),
            "port_https": self.https_port_input.text().strip()
        }


    def aceptar(self):
        self.guardar_datos()
        save_config(self.config)
        # manejar auto start si está en signin_autostart_cb
        try:
            if sys.platform == "win32":
                # usar el valor de la casilla principal
                enable = self.signin_autostart_cb.isChecked()
                set_auto_start(enable=enable)
        except Exception as e:
            print(f"Error manejando autorun: {e}")
        self.accept()

    def aplicar(self):
        self.guardar_datos()
        save_config(self.config)

    def cancelar(self):
        self.reject()

    def ayuda(self):
        QMessageBox.information(self, "Ayuda", "Función de ayuda no implementada.")

    # ---------------------------
    # Páginas creadoras
    # ---------------------------
    def crear_pagina_personal(self):
        pag = QWidget()
        main_layout = QVBoxLayout(pag)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        self.personal_nombre_edit = QLineEdit()
        self.personal_nombre_edit.setPlaceholderText("Escribe tu nombre tal y como deseas que lo vean los demás usuarios")
        form.addRow("Nombre para mostrar", self.personal_nombre_edit)

        self.personal_mensaje_edit = QTextEdit()
        form.addRow("Mensaje personal", self.personal_mensaje_edit)
        main_layout.addLayout(form)

        grid = QGridLayout()
        self.personal_cancion_cb = QCheckBox("Mostrar la información de la canción del Reproductor de Windows\nMedia como mensaje personal")
        self.personal_imagen_cb = QCheckBox("Mostrar mi imagen y permitir que otros la vean")
        grid.addWidget(self.personal_cancion_cb, 0, 0)
        grid.addWidget(self.personal_imagen_cb, 1, 0)
        main_layout.addLayout(grid)

        estado_layout = QHBoxLayout()
        self.personal_ausente_cb = QCheckBox('Mostrarme como "Ausente" si estoy inactivo')
        self.personal_ausente_spin = QComboBox()
        self.personal_ausente_spin.addItems([str(i) for i in range(1, 61)])
        estado_layout.addWidget(self.personal_ausente_cb)
        estado_layout.addWidget(self.personal_ausente_spin)
        estado_layout.addWidget(QLabel("minutos"))
        main_layout.addLayout(estado_layout)

        self.personal_ocupado_cb = QCheckBox('Mostrarme como "Ocupado" y bloquear mis alertas cuando ejecute\nun programa en pantalla completa o si la configuración de\npresentación está activada')
        self.personal_webcam_cb = QCheckBox("Permitir que otros puedan ver que tengo cámara web")
        main_layout.addWidget(self.personal_ocupado_cb)
        main_layout.addWidget(self.personal_webcam_cb)

        main_layout.addStretch()
        return pag

    def crear_pagina_iniciar_sesion(self):
        pag = QWidget()
        lay = QVBoxLayout(pag)

        lay.addWidget(QLabel("<b>General</b>"))

        self.signin_autostart_cb = QCheckBox("Ejecutar Messenger automáticamente cuando inicio sesión\nen Windows")
        lay.addWidget(self.signin_autostart_cb)

        self.signin_automatic_cb = QCheckBox("Permitir el inicio de sesión automático al conectar a Internet")
        lay.addWidget(self.signin_automatic_cb)

        lay.addWidget(QLabel("<hr>"))
        lay.addWidget(QLabel("<b>Iniciar sesión en varias ubicaciones (Debug)</b>"))

        text = ("Puedes iniciar sesión en Messenger en varios lugares y recibir mensajes instantáneos "
                "en todos los lugares en los que has iniciado sesión.\nMás información")
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        self.signin_cerrarestado_cb = QCheckBox("Cerrar la sesión de todas las demás ubicaciones cuando inicie sesión en Messenger")
        self.signin_cerrarestado_cb.setEnabled(False)
        lay.addWidget(self.signin_cerrarestado_cb)

        lay.addStretch()
        return pag

    def crear_pagina_alertas(self):
        pag = QWidget()
        lay = QVBoxLayout(pag)

        self.alertas_contacto_cb = QCheckBox("Mostrar alertas cuando los contactos inicien sesión")
        self.alertas_mensaje_cb = QCheckBox("Mostrar alertas cuando reciba un mensaje")
        lay.addWidget(self.alertas_contacto_cb)
        lay.addWidget(self.alertas_mensaje_cb)

        lay.addStretch()
        return pag

    def crear_pagina_transferencia(self):
        pag = QWidget()
        lay = QVBoxLayout(pag)

        lay.addWidget(QLabel("Opciones de transferencia de archivos"))
        lay.addWidget(QLabel("Guardar los archivos recibidos en esta carpeta:"))
        self.filetransfer_folder_edit = QLineEdit()
        lay.addWidget(self.filetransfer_folder_edit)

        btn_cambiar_folder = QPushButton("Cambiar...")
        lay.addWidget(btn_cambiar_folder)
        btn_cambiar_folder.clicked.connect(self.cambiar_carpeta)

        self.filetransfer_scanpath_edit = QLineEdit()
        lay.addWidget(self.filetransfer_scanpath_edit)

        btn_examinar = QPushButton("Examinar...")
        lay.addWidget(btn_examinar)
        btn_examinar.clicked.connect(self.examinar_archivo)

        self.filetransfer_autoreject_cb = QCheckBox("Rechazar automáticamente la transferencia de archivos para tipos\nconocidos de archivos no seguros")
        lay.addWidget(self.filetransfer_autoreject_cb)

        lay.addStretch()
        return pag

    def crear_pagina_conexion(self):
        pag = QWidget()
        lay = QVBoxLayout(pag)

        img = QLabel()
        img.setPixmap(QPixmap(32, 32))
        lay.addWidget(img)

        self.conexion_estado_label = QLabel("Actualmente no estás conectado a Servicio .NET MESSENGER.")
        lay.addWidget(self.conexion_estado_label)

        leyenda = QLabel(
            "Estás conectado a Internet a través de una conexión de red con cables.\n\n"
            "Solucionador de problemas de conexión realizará una serie de pruebas para intentar determinar la causa "
            "del problema de conexión. Se te preguntará antes de modificar cualquier configuración. Haz clic en "
            "Iniciar para iniciar el solucionador de problemas."
        )
        leyenda.setWordWrap(True)
        lay.addWidget(leyenda)

        btn_actualizar = QPushButton("Actualizar")
        btn_iniciar = QPushButton("Iniciar...")
        btn_config_avanzadas = QPushButton("Configuraciones avanzadas")

        hbtn = QHBoxLayout()
        hbtn.addWidget(btn_actualizar)
        hbtn.addWidget(btn_iniciar)
        lay.addLayout(hbtn)

        btn_config_avanzadas.clicked.connect(self.abrir_config_avanzada)
        lay.addWidget(btn_config_avanzadas)
        lay.addStretch()

        return pag

    def cambiar_carpeta(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de destino")
        if folder:
            self.filetransfer_folder_edit.setText(folder)

    def examinar_archivo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar herramienta de escaneo")
        if file_path:
            self.filetransfer_scanpath_edit.setText(file_path)

    def abrir_config_avanzada(self):
        dlg = ConfigAvanzadaDialog(self)
        dlg.exec_()

    def crear_pagina_websocket(self):
        page = QWidget()
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(8, 8, 8, 8)

        group = QGroupBox("Configuración de conexión segura")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)

        # Checkbox: activar SSL/HTTPS (WSS)
        self.certificados_confianza_cb = QCheckBox("Activar SSL/HTTPS (WSS)")
        form.addRow(self.certificados_confianza_cb)

        # Servidor WebSocket
        self.websocket_host = QLineEdit()
        form.addRow("Servidor WebSocket:", self.websocket_host)

        # Puerto WS (no seguro)
        self.ws_port_input = QLineEdit()
        self.ws_port_input.setMaximumWidth(120)
        form.addRow("Puerto WS:", self.ws_port_input)

        # Puerto WSS (seguro)
        self.wss_port_input = QLineEdit()
        self.wss_port_input.setMaximumWidth(120)
        form.addRow("Puerto WSS:", self.wss_port_input)

        # Puerto HTTP (transferencias no seguras)
        self.http_port_input = QLineEdit()
        self.http_port_input.setMaximumWidth(120)
        form.addRow("Puerto HTTP:", self.http_port_input)

        # Puerto HTTPS (transferencias seguras)
        self.https_port_input = QLineEdit()
        self.https_port_input.setMaximumWidth(120)
        form.addRow("Puerto HTTPS:", self.https_port_input)

        # Certificado del servidor (opcional - solo para servidor)
        cert_layout = QHBoxLayout()
        self.certificados_cert = QLineEdit()
        self.certificados_cert.setPlaceholderText("Ruta del certificado del servidor (.crt / .pem)")
        self.certificados_cert.setReadOnly(False)
        btn_cert = QPushButton("Examinar...")
        btn_cert.clicked.connect(lambda: self._browse_file(self.certificados_cert, "Certificado (*.pem *.crt)"))
        cert_layout.addWidget(self.certificados_cert)
        cert_layout.addWidget(btn_cert)
        form.addRow("Certificado (.crt/.pem):", cert_layout)

        # Clave privada del servidor (opcional)
        key_layout = QHBoxLayout()
        self.certificados_key = QLineEdit()
        self.certificados_key.setPlaceholderText("Ruta de la clave privada (.key)")
        btn_key = QPushButton("Examinar...")
        btn_key.clicked.connect(lambda: self._browse_file(self.certificados_key, "Clave (*.key *.pem)"))
        key_layout.addWidget(self.certificados_key)
        key_layout.addWidget(btn_key)
        form.addRow("Clave privada (.key):", key_layout)

        # Advertencia fija
        warning = QLabel("⚠️ Los archivos .crt y .key son sensibles. No los compartas. Asegúrate de que pertenecen a tu servidor.")
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #d48a00; font-weight: bold;")
        form.addRow(warning)

        group.setLayout(form)
        main_layout.addWidget(group)
        main_layout.addStretch(1)

        # pequeño helper method assumed in dialog: _browse_file(widget, filter)
        # (Si no existe, se añade más abajo la implementación)

        return page

    def _browse_file(self, line_edit_widget, filter_str="Archivos (*)"):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", "", filter_str)
        if path:
            line_edit_widget.setText(path)

# -------------------------------
# Windows autorun helper (set_auto_start)
# -------------------------------
def set_auto_start(enable=True):
    if sys.platform != "win32":
        return
    try:
        import winreg
    except Exception:
        return

    app_name = "Messenger2025"
    # sugerir ruta absoluta a ejecutable; si se está ejecutando con python, usar sys.executable y el script
    try:
        # si hay un exe en C:\MSN\Messenger.exe preferirlo; si no, optar por el ejecutable actual
        exe_path = r'"C:\MSN\Messenger.exe"'
        if not Path(r"C:\MSN\Messenger.exe").exists():
            # construir un comando que ejecute el script con python si procede (no ideal para producción)
            exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
    except Exception:
        exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
    except Exception:
        reg_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)

    try:
        if enable:
            winreg.SetValueEx(reg_key, app_name, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(reg_key, app_name)
            except FileNotFoundError:
                pass
    except Exception as e:
        print(f"Error al actualizar autorun en registro: {e}")
    finally:
        try:
            reg_key.Close()
        except Exception:
            pass

# -------------------------------
# ChatPanel y LoginWindow (Messenger)
# -------------------------------
class ChatPanel(QWidget):
    def __init__(self, ws_client, username):
        super().__init__()
        self.ws_client = ws_client
        self.username = username
        self.setWindowTitle(f"Chat Messenger - {username}")
        self.resize(400, 500)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)

        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("Escribir mensaje...")
        self.input_text.returnPressed.connect(self.send_message)

        layout = QVBoxLayout()
        layout.addWidget(self.chat_display)
        layout.addWidget(self.input_text)
        self.setLayout(layout)

        self.ws_client.message_received.connect(self.receive_message)
        self.ws_client.disconnected.connect(self.on_disconnect)

    def send_message(self):
        text = self.input_text.text().strip()
        if text:
            message_json = json.dumps({
                "type": "chat_message",
                "from": self.username,
                "message": text
            })
            self.ws_client.send(message_json)
            self.chat_display.append(f"[Yo] {text}")
            self.input_text.clear()

    def receive_message(self, msg):
        try:
            data = json.loads(msg)
            if data.get("type") == "chat_message":
                sender = data.get("from", "Desconocido")
                message = data.get("message", "")
                if sender != self.username:
                    self.chat_display.append(f"[{sender}] {message}")
            elif data.get("type") == "auth_response":
                pass
        except Exception:
            self.chat_display.append(msg)

    def on_disconnect(self):
        QMessageBox.warning(self, "Conexión perdida", "La conexión con el servidor se ha perdido.")
        self.close()

class InterfaceSettingsDialog(QDialog):
    # Este diálogo ya estaba en el Messenger original; lo mantenemos (configuración de interfaz simple)
    def __init__(self, parent, config):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Interfaz")

        self.config = config

        layout = QFormLayout(self)

        self.chat_name_edit = QLineEdit()
        self.chat_name_edit.setText(self.config["app_settings"].get("chat_name", "Chat Messenger"))
        layout.addRow("Nombre del chat:", self.chat_name_edit)

        self.logo_mode_combo = QComboBox()
        self.logo_mode_combo.addItems(["URL", "Local"])
        layout.addRow("Logo:", self.logo_mode_combo)

        self.chat_image_edit = QLineEdit()
        self.chat_image_edit.setText(self.config["app_settings"].get("chat_image", ""))
        layout.addRow("", self.chat_image_edit)

        self.logo_search_btn = QPushButton("Buscar...")
        layout.addRow("", self.logo_search_btn)

        self.color_button = QPushButton("Seleccionar color principal")
        self.color_button.clicked.connect(self.select_color)
        layout.addRow("Color principal:", self.color_button)
        self.current_color = self.config["app_settings"].get("primary_color", "#2171b4")
        self.color_button.setStyleSheet(f"background-color: {self.current_color};")

        self.rgb_checkbox = QCheckBox("Activar color RGB dinámico")
        self.rgb_checkbox.setChecked(self.config["app_settings"].get("use_rgb", False))
        layout.addRow(self.rgb_checkbox)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Guardar")
        self.cancel_btn = QPushButton("Cancelar")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.reject)

        # Conexiones
        self.logo_mode_combo.currentIndexChanged.connect(self.toggle_logo_mode)
        self.logo_search_btn.clicked.connect(self.buscar_logo_local)

        self.init_logo_mode()

    def init_logo_mode(self):
        current_path = self.config["app_settings"].get("chat_image", "")
        if current_path.startswith("http") or current_path.startswith("https"):
            self.logo_mode_combo.setCurrentText("URL")
            self.logo_search_btn.setEnabled(False)
            self.chat_image_edit.setReadOnly(False)
            self.chat_image_edit.setText(current_path)
        else:
            self.logo_mode_combo.setCurrentText("Local")
            self.logo_search_btn.setEnabled(True)
            self.chat_image_edit.setReadOnly(True)
            self.chat_image_edit.setText(current_path)

    def toggle_logo_mode(self):
        modo = self.logo_mode_combo.currentText()
        if modo == "URL":
            self.logo_search_btn.setEnabled(False)
            self.chat_image_edit.setReadOnly(False)
            self.chat_image_edit.clear()
        else:
            self.logo_search_btn.setEnabled(True)
            self.chat_image_edit.setReadOnly(True)
            self.chat_image_edit.clear()

    def buscar_logo_local(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar imagen", "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)")
        if ruta:
            self.chat_image_edit.setText(ruta)

    def select_color(self):
        color = QColorDialog.getColor(QColor(self.current_color), self, "Seleccionar color")
        if color.isValid():
            self.current_color = color.name()
            self.color_button.setStyleSheet(f"background-color: {self.current_color};")

    def save_settings(self):
        chat_image_valor = self.chat_image_edit.text().strip()
        if not chat_image_valor:
            chat_image_valor = DEFAULT_CHAT_IMAGE
        self.config["app_settings"]["chat_name"] = self.chat_name_edit.text().strip()
        self.config["app_settings"]["chat_image"] = chat_image_valor
        self.config["app_settings"]["primary_color"] = self.current_color
        self.config["app_settings"]["use_rgb"] = self.rgb_checkbox.isChecked()
        save_config(self.config)
        self.accept()

class MessengerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.ws_manager = WebSocketManager()  # <--- INICIALIZA aquí
        self.setWindowTitle("Messenger - Contactos")
        self.setFixedSize(360, 600)
        self.move(100, 100)  # para posicionar donde quieres

        self.config = load_config()
        personal = self.config.get("personal", {})
        app_settings = self.config.get("app_settings", {})
        visible = app_settings.get("menubar_visible", True)

        self.chat_image = app_settings.get("chat_image", DEFAULT_CHAT_IMAGE)

        display_name = personal.get("display_name", "").strip()
        username = app_settings.get("username", "Usuario")
        self.username_to_show = display_name if display_name else username
        self.personal_message = personal.get("personal_message", "")
        self.current_status = app_settings.get("status", "Disponible")
        self.chat_image = app_settings.get("chat_image", "")

        self.rgb_hue = 0.0
        self.timer_rgb = QTimer(self)
        self.timer_rgb.setInterval(100)
        self.timer_rgb.timeout.connect(self.cambiar_color_rgb)

        self.ws = None  # WebSocket placeholder, si se usa

        self.apply_styles()

        if app_settings.get("use_rgb", False):
            self.timer_rgb.start()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Crear barra de menús ---
        self.menubar = QMenuBar()   # 👈 ahora es atributo
        self.menu_archivo = self.menubar.addMenu("Archivo")
        self.menu_herramientas = self.menubar.addMenu("Herramientas")
        self.menu_estados = self.menubar.addMenu("Estados")
        self.menu_ayuda = self.menubar.addMenu("Ayuda")

        # Agregar acciones
        accion_cerrar_sesion = QAction("Cerrar sesión", self)
        accion_cerrar_sesion.triggered.connect(self.cerrar_sesion)
        self.menu_archivo.addAction(accion_cerrar_sesion)

        accion_salir = QAction("Salir", self)
        accion_salir.triggered.connect(self.close)
        self.menu_archivo.addAction(accion_salir)

        accion_opciones = QAction("Opciones", self)
        accion_opciones.triggered.connect(self.mostrar_opciones)
        self.menu_herramientas.addAction(accion_opciones)

        accion_interfaz = QAction("Interfaz", self)
        accion_interfaz.triggered.connect(self.abrir_config_interfaz)
        self.menu_herramientas.addAction(accion_interfaz)

        accion_version = QAction("Acerca de Messenger", self)
        accion_version.triggered.connect(self.mostrar_version)
        self.menu_ayuda.addAction(accion_version)

        accion_actualizaciones = QAction("Actualizaciones", self)
        accion_actualizaciones.triggered.connect(self.verificar_actualizaciones)
        self.menu_ayuda.addAction(accion_actualizaciones)

        for estado in ["Disponible", "Ocupado", "Ausente", "Invisible", "Desconectado"]:
            accion_estado = QAction(estado, self)
            accion_estado.setCheckable(True)
            accion_estado.setChecked(estado == self.current_status)
            accion_estado.triggered.connect(lambda checked, e=estado: self.cambiar_estado(e))
            self.menu_estados.addAction(accion_estado)

        self.menubar.setVisible(visible)
        main_layout.addWidget(self.menubar)   # 👈 usamos self.menubar

        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(15, 10, 15, 15)

        user_layout = QHBoxLayout()
        user_layout.setSpacing(8)

        self.avatar = QLabel()
        self.avatar.setFixedSize(64, 64)
        self.avatar.setAlignment(Qt.AlignCenter)  # Centrar la imagen
        pixmap = cargar_imagen(self.chat_image)
        if not pixmap.isNull():
            scaled_pix = pixmap.scaled(
                self.avatar.size(),  # tamaño 64x64
                Qt.KeepAspectRatio,  # respetar proporción
                Qt.SmoothTransformation
            )
            self.avatar.setPixmap(scaled_pix)
            self.avatar.setStyleSheet("""
                border-radius: 3px;
                background: #e5f7e8;
                border: 3px solid #55cc88;
            """)
        else:
            self.avatar.clear()

        user_layout.addWidget(self.avatar)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        self.user_label = QLabel(f"<b>{self.username_to_show}</b>")
        self.status_label = QLabel(f"<b>({self.current_status})</b>")
        self.personal_message_label = QLabel(f"<b>{self.personal_message}</b>")

        info_layout.addWidget(self.user_label)
        info_layout.addWidget(self.status_label)
        info_layout.addWidget(self.personal_message_label)

        user_layout.addLayout(info_layout)
        content_layout.addLayout(user_layout)

        search_layout = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar contactos...")
        self.search.setStyleSheet("padding: 5px; font-size: 10pt;")
        search_layout.addWidget(self.search)

        btn_add_contact = QToolButton()
        pixmap_add = cargar_imagen("https://raw.githubusercontent.com/mggons93/Messenger/main/files/agregar-usuario.png")
        btn_add_contact.setIcon(QIcon(pixmap_add))
        btn_add_contact.setIconSize(QSize(24, 24))  
        btn_add_contact.setFixedSize(32, 32)  # Botón un poco más grande que el icono
        btn_add_contact.setStyleSheet("""
            QToolButton {
                border-radius: 16px;  /* Mitad del tamaño para que sea circular */
                background-color: #f0f0f0;
            }
            QToolButton:hover {
                background-color: #d0d0d0;
            }
        """)
        search_layout.addWidget(btn_add_contact)
        btn_add_contact.clicked.connect(self.agregar_usuario)   # <--- conexión funcionalidad nueva

        btn_del_contact = QToolButton()
        pixmap_groups = cargar_imagen("https://raw.githubusercontent.com/mggons93/Messenger/main/files/borrar-usuario.png")
        btn_del_contact.setIcon(QIcon(pixmap_groups))
        btn_del_contact.setIconSize(QSize(24, 24))  
        btn_del_contact.setFixedSize(32, 32)
        btn_del_contact.setStyleSheet("""
            QToolButton {
                border-radius: 16px;
                background-color: #f0f0f0;
            }
            QToolButton:hover {
                background-color: #d0d0d0;
            }
        """)
        search_layout.addWidget(btn_del_contact)
        btn_del_contact.clicked.connect(self.eliminar_usuario)  # <--- conexión funcionalidad nueva

        btn_menu = QToolButton()
        pixmap_menu = cargar_imagen("https://raw.githubusercontent.com/mggons93/Messenger/main/files/menu.png")
        btn_menu.setIcon(QIcon(pixmap_menu))
        btn_menu.setIconSize(QSize(24, 24))  
        btn_menu.setFixedSize(32, 32)
        btn_menu.setStyleSheet("""
            QToolButton {
                border-radius: 16px;
                background-color: #f0f0f0;
            }
            QToolButton:hover {
                background-color: #d0d0d0;
            }
        """)
        search_layout.addWidget(btn_menu)

        menu_popup = QMenu()
        menu_popup.addMenu(self.menu_archivo)
        menu_popup.addMenu(self.menu_herramientas)
        menu_popup.addMenu(self.menu_estados)
        menu_popup.addMenu(self.menu_ayuda)
        show_bar_action = QAction("", self)
        def toggle_bar():
            visible = not self.menubar.isVisible()
            self.menubar.setVisible(visible)
            self.config["app_settings"]["menubar_visible"] = visible
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
            if visible:
                show_bar_action.setText("Ocultar la barra de menús")
            else:
                show_bar_action.setText("Mostrar la barra de menús")
        if visible:
            show_bar_action.setText("Ocultar la barra de menús")
        else:
            show_bar_action.setText("Mostrar la barra de menús")
        show_bar_action.triggered.connect(toggle_bar)
        menu_popup.addAction(show_bar_action)
        btn_menu.setMenu(menu_popup)
        btn_menu.setPopupMode(QToolButton.InstantPopup)
        content_layout.addLayout(search_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet("font-size: 10pt;")

        self.tree.clear()

        estrella_pixmap = QPixmap(16, 16)
        estrella_pixmap.fill(Qt.transparent)
        painter = QPainter(estrella_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#FFD700"))  # Amarillo
        painter.setPen(Qt.NoPen)
        points = [QPoint(8, 0), QPoint(10, 6), QPoint(16, 6), QPoint(11, 10),
                QPoint(13, 16), QPoint(8, 13), QPoint(3, 16), QPoint(5, 10),
                QPoint(0, 6), QPoint(6, 6)]
        painter.drawPolygon(*points)
        painter.end()

        cuadro_verde = QPixmap(12, 12)
        cuadro_verde.fill(QColor("#55cc88"))
        cuadro_gris = QPixmap(12, 12)
        cuadro_gris.fill(QColor("#999999"))

        favoritos = QTreeWidgetItem(self.tree)
        favoritos.setText(0, "Favoritos")
        favoritos.setIcon(0, QIcon(estrella_pixmap))
        online = QTreeWidgetItem(self.tree)
        online.setText(0, "Online")
        online.setIcon(0, QIcon(cuadro_verde))
        offline = QTreeWidgetItem(self.tree)
        offline.setText(0, "Offline")
        offline.setIcon(0, QIcon(cuadro_gris))

        self.tree.expandAll()
        content_layout.addWidget(self.tree)

        url_banner = "https://raw.githubusercontent.com/mggons93/Messenger/main/files/live.png"
        label_banner = QLabel()
        pixmap_banner = cargar_imagen(url_banner)
        if not pixmap_banner.isNull():
            label_banner.setPixmap(pixmap_banner.scaledToWidth(180, Qt.SmoothTransformation))
        content_layout.addWidget(label_banner, alignment=Qt.AlignCenter)

        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)
        self.setLayout(main_layout)
        self.actualizar_imagen_avatar()
        self.cambiar_estado(self.current_status)

        # --- Lista interna de usuarios para gestión local/servidor ---
        self.usuarios = []

    # ---------- NUEVO: FUNCIONES DE GESTIÓN DE CONTACTOS ----------

    def agregar_usuario(self):
        nuevo_usuario, ok = QInputDialog.getText(self, "Agregar usuario", "Ingrese el nombre de usuario:")
        if ok and nuevo_usuario.strip():
            nuevo_usuario = nuevo_usuario.strip()
            if nuevo_usuario not in [u['name'] for u in self.usuarios]:
                self.usuarios.append({"name": nuevo_usuario, "status": "offline"})
                self.sincronizar_usuarios_con_servidor()
                estado = self.consultar_estado_usuario(nuevo_usuario)
                self.actualizar_usuario_en_ui(nuevo_usuario, estado)
            else:
                QMessageBox.warning(self, "Agregar usuario", f"El usuario {nuevo_usuario} ya está en la lista.")
        else:
            QMessageBox.information(self, "Agregar usuario", "No se ingresó ningún nombre válido.")

    def eliminar_usuario(self):
        item = self.tree.currentItem()
        if not item or item.parent() is None:
            QMessageBox.warning(self, "Eliminar usuario", "Seleccione un usuario para eliminar.")
            return
        usuario = item.text(0)
        reply = QMessageBox.question(self, "Eliminar usuario", f"¿Está seguro de eliminar a {usuario}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.usuarios = [u for u in self.usuarios if u["name"] != usuario]
            self.sincronizar_usuarios_con_servidor()
            self.cargar_contactos(self.usuarios)

    def sincronizar_usuarios_con_servidor(self):
        # Implementa aquí la sincronización real contra tu backend (Request, WS, etc)
        pass

    def consultar_estado_usuario(self, usuario):
        # Reemplaza por lógica real de consulta online al servidor
        return "online"  # Mock: todos online

    def actualizar_usuario_en_ui(self, usuario, estado):
        for u in self.usuarios:
            if u["name"] == usuario:
                u["status"] = estado
        self.cargar_contactos(self.usuarios)
        
    # ---------------------------------------------------------

    def actualizar_imagen_avatar(self):
        pixmap = cargar_imagen(self.chat_image)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.avatar.size(),
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation
            )
            self.avatar.setPixmap(scaled)
        else:
            pixmap = cargar_imagen(DEFAULT_CHAT_IMAGE)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.avatar.size(),
                    Qt.IgnoreAspectRatio,
                    Qt.SmoothTransformation
                )
                self.avatar.setPixmap(scaled)
            else:
                self.avatar.clear()

    def cambiar_estado(self, nuevo_estado):
        color_map = {
            "Disponible": "#21df73",
            "Ocupado": "#e01919",
            "Ausente": "#e48a15",
            "Invisible": "#999999",
            "Desconectado": "#666666"
        }
        self.current_status = nuevo_estado
        self.config["app_settings"]["status"] = nuevo_estado
        save_config(self.config)
        self.status_label.setText(f"<b>({nuevo_estado})</b>")
        for accion in self.menu_estados.actions():
            accion.setChecked(accion.text() == nuevo_estado)
        color_borde = color_map.get(nuevo_estado, "#55cc88")
        self.avatar.setStyleSheet(f"""
            border: 6.5px solid {color_borde};
            border-radius: 10px;
            background: #e5f7e8;
        """)

    def apply_styles(self):
        style = """
        QLabel, QCheckBox {
            background: transparent;
        }
        QLineEdit, QComboBox {
            background: #ffffff;
            border: 1px solid #a3bae7;
            border-radius: 4px;
            color: #1e3250;
            padding: 4px;
        }
        QPushButton {
            background-color: #3A9BDC;
            border: 1px solid #1E7CC4;
            border-radius: 5px;
            color: white;
            font-weight: bold;
            padding: 6px 12px;
        }
        QPushButton:hover {
            background-color: #1E7CC4;
        }
        """
        self.setStyleSheet(style)

    def cambiar_color_rgb(self):
        self.rgb_hue += 0.01
        if self.rgb_hue > 1.0:
            self.rgb_hue -= 1.0
        r, g, b = colorsys.hsv_to_rgb(self.rgb_hue, 1.0, 1.0)
        r, g, b = int(r * 255), int(g * 255), int(b * 255)
        self.user_label.setStyleSheet(f"color: rgb({r},{g},{b});")

    def refrescar_display_name(self):
        self.config = load_config()
        personal = self.config.get("personal", {})
        app_settings = self.config.get("app_settings", {})
        display_name = personal.get("display_name", "").strip()
        username = app_settings.get("username", "Usuario")
        self.username_to_show = display_name if display_name else username
        self.user_label.setText(f"<b>{self.username_to_show}</b>")

    def mostrar_opciones(self):
        try:
            proceso = subprocess.Popen(r"C:\MSN\Opciones.exe")
            proceso.wait()
            self.refrescar_display_name()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir las opciones: {e}")

    def cerrar_sesion(self):
        reply = QMessageBox.question(self, "Cerrar sesión",
                                    "¿Desea cerrar sesión?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.ws_manager.disconnected.connect(self.post_cierre_sesion)
                self.ws_manager.disconnect()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo cerrar sesión correctamente: {e}")

    def post_cierre_sesion(self):
        print("[LOG] WebSocket desconectado, cerrando MessengerWindow y mostrando LoginWindow.")
        self.close()
        self.login_window = LoginWindow()
        self.login_window.show()

    def abrir_config_interfaz(self):
        dialog = InterfaceSettingsDialog(self, self.config)
        if dialog.exec_() == QDialog.Accepted:
            self.config = load_config()
            personal = self.config.get("personal", {})
            app_settings = self.config.get("app_settings", {})
            display_name = personal.get("display_name", "").strip()
            username = app_settings.get("username", "Usuario")
            self.username_to_show = display_name if display_name else username
            self.personal_message = personal.get("personal_message", "")
            self.current_status = app_settings.get("status", self.current_status)
            self.chat_image = app_settings.get("chat_image", self.chat_image)
            self.user_label.setText(f"<b>{self.username_to_show}</b>")
            self.personal_message_label.setText(f"<b>{self.personal_message}</b>")
            self.status_label.setText(f"<b>({self.current_status})</b>")
            self.actualizar_imagen_avatar()
            self.cambiar_estado(self.current_status)
            self.apply_styles()

    def mostrar_version(self):
        texto_acerca = (
            f"Messenger\n\n"
            f"Versión 2025 (compilación {VERSION})\n\n"
            f"Canal actual: {CANAL_ACTUAL.capitalize()}\n\n"
            "Copyright © 2025 S&A Network. Reservados todos los derechos.\n\n"
            "Este software está licenciado bajo la licencia MIT.\n\n"
            "Partes de este software están basadas en trabajos independientes y código abierto.\n"
        )
        QMessageBox.information(self, "Acerca de Messenger", texto_acerca)

    def verificar_actualizaciones(self):
        necesita_actualizar, version_remota = self.verificar_version_remota()
        if necesita_actualizar:
            reply = QMessageBox.question(
                self,
                "Actualización disponible",
                f"Hay una nueva versión disponible: {version_remota}\n¿Quieres actualizar ahora?",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.realizar_actualizacion()
        else:
            QMessageBox.information(self, "Actualizaciones", "No hay actualizaciones disponibles.")

    def verificar_version_remota(self, canal=CANAL_ACTUAL):
        """Verifica si hay una nueva versión disponible según el canal (release/beta/dev)."""
        try:
            response = requests.get(UPDATE_URL, timeout=10)
            if response.status_code != 200:
                print("No se pudo obtener la versión remota.")
                return False, VERSION

            data = response.json()

            # Detectar si el canal existe en el JSON remoto
            if canal in data and "version" in data[canal]:
                version_remota = data[canal]["version"]
            else:
                # fallback por si el canal no existe
                version_remota = data.get("version", "v0.0.0")

            hay_update = version_remota != VERSION
            return hay_update, version_remota

        except Exception as e:
            print(f"Error verificando versión remota: {e}")
            return False, VERSION


    def mostrar_mensaje_auto_cerrar(self, titulo, texto, tiempo_ms=3000):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(titulo)
        msg_box.setText(texto)
        msg_box.setStandardButtons(QMessageBox.NoButton)
        msg_box.show()
        timer = QTimer()
        timer.singleShot(tiempo_ms, msg_box.close)
        return msg_box

    def paintEvent(self, event):
        painter = QPainter(self)
        primary_color_str = self.config["app_settings"].get("primary_color", "#6ABF3E")
        primary_color = QColor(primary_color_str)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, primary_color.lighter(110))
        gradient.setColorAt(0.2, primary_color.lighter(130))
        gradient.setColorAt(1.0, QColor("#FFFFFF"))
        painter.fillRect(self.rect(), gradient)

    def cargar_contactos(self, contactos):
        self.tree.clear()
        favoritos = QTreeWidgetItem(self.tree)
        favoritos.setText(0, "Favoritos")
        online = QTreeWidgetItem(self.tree)
        online.setText(0, "Online")
        offline = QTreeWidgetItem(self.tree)
        offline.setText(0, "Offline")

        for c in contactos:
            nombre = c.get("name", "Sin Nombre")
            estado = c.get("status", "offline")
            item = QTreeWidgetItem()
            item.setText(0, nombre)
            if estado == "online":
                online.addChild(item)
            elif estado == "favorito":
                favoritos.addChild(item)
            else:
                offline.addChild(item)
        self.tree.expandAll()


    def init_websocket(self, url):
        self.ws = QWebSocket()
        self.ws.error.connect(self.on_ws_error)
        self.ws.textMessageReceived.connect(self.on_ws_message)
        self.ws.open(QUrl(url))
        self.ws.connected.connect(self.on_ws_connected)

    def on_ws_connected(self):
        print("WebSocket conectado")
        # Al conectarse, sincronizar lista de usuarios con el servidor
        self.enviar_sincronizacion_usuarios()

    def on_ws_error(self, error):
        print("Error WebSocket:", error)

    def on_ws_message(self, message):
        tipo = message.get("type", "")
        if tipo == "synccontacts":
            contactos = message.get("contacts", [])
            self.usuarios = contactos
            self.cargar_contactos(self.usuarios)
        elif tipo == "userstatus":
            usuario = message.get("user")
            estado = message.get("status", "offline")
            for u in self.usuarios:
                if u["name"] == usuario:
                    u["status"] = estado
                    break
            self.cargar_contactos(self.usuarios)

    def enviar_sincronizacion_usuarios(self):
        if self.ws and self.ws.state() == QWebSocket.ConnectedState:
            msg = {
                "type": "synccontacts",
                "contacts": self.usuarios
            }
            self.ws.sendTextMessage(json.dumps(msg))

    def consultar_estado_usuario(self, usuario):
        # Dado que el servidor envía actualizaciones por WebSocket,
        # simplemente devuelve el estado local si lo tiene.
        for u in self.usuarios:
            if u["name"] == usuario:
                return u.get("status", "offline")
        return "offline"

    def sincronizar_usuarios_con_servidor(self):
        # Enviar toda la lista al servidor para sincronización
        self.enviar_sincronizacion_usuarios()

# -------------------------------
# Ventana principal / login
# -------------------------------
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Messenger 2025 Beta")
        self.setFixedSize(340, 530)

        self.config = load_config()
        self.chat_image = self.config["app_settings"].get("chat_image", DEFAULT_CHAT_IMAGE)

        # Obtener la instancia del manager global de WebSocket
        self.ws_manager = WebSocketManager()
        self.ws_manager.message_received.connect(self.on_ws_message)
        self.ws_manager.connected.connect(self.on_ws_connected)
        self.ws_manager.disconnected.connect(self.on_ws_disconnected)

        # En lugar de self.ws, usar ws_manager.ws para referirse a la conexión

        # Icono principal (wlm.ico) cacheado desde GitHub
        icon_url = "https://raw.githubusercontent.com/mggons93/Messenger/main/files/wlm.ico"
        icon_path = ensure_cache_file(icon_url, "wlm.ico")
        try:
            self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass

        # Verificación silenciosa de actualizaciones (no bloqueante)
        QTimer.singleShot(0, self.check_updates_silent)

        # estilos básicos
        self.setStyleSheet("""
            QLabel#logo {
                font-weight: bold;
                font-size: 24px;
                background: transparent;
            }
            QLabel, QCheckBox {
                background: transparent;
            }
            QLineEdit, QComboBox {
                background: #ffffff;
                border: 1px solid #a3bae7;
                border-radius: 4px;
                color: #1e3250;
                padding: 4px;
            }
            QPushButton {
                background-color: #3A9BDC;
                border: 1px solid #1E7CC4;
                border-radius: 5px;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #1E7CC4;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 10, 35, 10)
        main_layout.setSpacing(10)

        menu_bar = QMenuBar(self)
        menu_archivo = menu_bar.addMenu("Archivo")
        menu_herramientas = menu_bar.addMenu("Herramientas")
        menu_ayuda = menu_bar.addMenu("Ayuda")
        main_layout.setMenuBar(menu_bar)

        accion_salir = QAction("Salir", self)
        accion_salir.triggered.connect(self.close)
        menu_archivo.addAction(accion_salir)

        accion_opciones = QAction("Opciones", self)
        accion_opciones.triggered.connect(self.mostrar_opciones)
        menu_herramientas.addAction(accion_opciones)

        accion_interfaz = QAction("Interfaz", self)
        accion_interfaz.triggered.connect(self.abrir_config_interfaz)
        menu_herramientas.addAction(accion_interfaz)

        accion_version = QAction("Acerca de Messenger", self)
        accion_version.triggered.connect(self.mostrar_version)
        menu_ayuda.addAction(accion_version)

        accion_actualizaciones = QAction("Actualizaciones", self)
        accion_actualizaciones.triggered.connect(self.verificar_actualizaciones)
        menu_ayuda.addAction(accion_actualizaciones)

        self.logo = QLabel(self.config["app_settings"].get("chat_name", "Chat Messenger"))
        self.logo.setObjectName("logo")
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setWordWrap(True)
        self.logo.setMaximumHeight(60)
        main_layout.addWidget(self.logo)

        logo_url = self.config["app_settings"].get("chat_image", "")
        pixmap = cargar_imagen(logo_url)
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setFixedSize(120, 120)
        if not pixmap.isNull():
            self.img_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.img_label.setStyleSheet("border: 1.5px solid #bbb; border-radius: 8px; background: #fafcff;")
        main_layout.addWidget(self.img_label, alignment=Qt.AlignHCenter)

        # formulario
        self.form_widget = QWidget()
        self.form_layout = QVBoxLayout(self.form_widget)
        self.username_label = QLabel("Username:")
        self.form_layout.addWidget(self.username_label)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Introduce tu nombre de usuario")
        self.username_edit.setText(self.config["app_settings"].get("username", ""))
        self.form_layout.addWidget(self.username_edit)

        self.status_label = QLabel("Estado:")
        self.form_layout.addWidget(self.status_label)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Disponible", "Ocupado", "Ausente", "Invisible", "Desconectado"])
        # Leer el estado guardado en config y establecerlo
        estado_guardado = self.config["app_settings"].get("status", "Disponible")
        if estado_guardado in ["Disponible", "Ocupado", "Ausente", "Invisible", "Desconectado"]:
            self.status_combo.setCurrentText(estado_guardado)
        else:
            self.status_combo.setCurrentText("Disponible")
        self.form_layout.addWidget(self.status_combo)

        self.remember_me_cb = QCheckBox("Recordarme")
        self.remember_me_cb.setChecked(self.config["app_settings"].get("remember_me", False))
        self.remember_password_cb = QCheckBox("Recordar mi configuración")
        self.remember_password_cb.setChecked(self.config["app_settings"].get("remember_config", False))
        self.auto_signin_cb = QCheckBox("Iniciar sesión automáticamente")
        self.auto_signin_cb.setChecked(self.config["app_settings"].get("auto_signin", False))
        self.form_layout.addWidget(self.remember_me_cb)
        self.form_layout.addWidget(self.remember_password_cb)
        self.form_layout.addWidget(self.auto_signin_cb)

        self.signin_btn = QPushButton("Iniciar sesión")
        self.signin_btn.setFixedHeight(34)
        self.form_layout.addWidget(self.signin_btn, alignment=Qt.AlignHCenter)

        main_layout.addWidget(self.form_widget)

        self.login_status_widget = QWidget()
        self.login_status_layout = QVBoxLayout(self.login_status_widget)
        self.login_status_layout.setAlignment(Qt.AlignHCenter)
        self.login_status_layout.setSpacing(46)

        self.login_status_label = QLabel("Iniciar Sesión..")
        self.login_status_label.setAlignment(Qt.AlignCenter)
        self.login_status_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.login_status_layout.addWidget(self.login_status_label)

        self.login_logo_label = QLabel()
        self.login_logo_label.setAlignment(Qt.AlignCenter)
        self.login_logo_label.setFixedSize(64, 64)
        self.login_status_layout.addWidget(self.login_logo_label, alignment=Qt.AlignHCenter)

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setFixedHeight(34)
        self.login_status_layout.addWidget(self.cancel_btn, alignment=Qt.AlignHCenter)
        self.login_status_widget.hide()
        main_layout.addWidget(self.login_status_widget)

        footer_layout = QHBoxLayout()
        soporte_label = QLabel("S&A Network")
        soporte_label.setStyleSheet("font-size: 8pt; color: gray;")
        footer_layout.addWidget(soporte_label, alignment=Qt.AlignLeft)
        footer_layout.addStretch()
        version_label = QLabel(VERSION)
        version_label.setStyleSheet("font-size: 8pt; color: gray;")
        footer_layout.addWidget(version_label, alignment=Qt.AlignRight)
        main_layout.addLayout(footer_layout)

        # conexiones
        self.signin_btn.clicked.connect(self.try_login)
        self.cancel_btn.clicked.connect(self.on_progress_canceled)

        ws_cfg = self.config.get("websocket", {})
        self.ws_host = ws_cfg.get("host", "0.0.0.0")
        self.ws_port = ws_cfg.get("port", "8765")

        self.timer_rgb = QTimer(self)
        self.timer_rgb.setInterval(100)
        self.timer_rgb.timeout.connect(self.cambiar_color_rgb)
        if self.config["app_settings"].get("use_rgb", False):
            self.timer_rgb.start()
        else:
            self.timer_rgb.stop()
            self.aplicar_color_estatico()

        self._login_canceled = False
        self.ws_client = None
        self.chat_panel = None
        self.rgb_hue = 0.0
        self.login_movie = None

    # color helpers
    def aplicar_color_texto(self):
        if self.config["app_settings"].get("use_rgb", False):
            if not self.timer_rgb.isActive():
                self.timer_rgb.start()
        else:
            if self.timer_rgb.isActive():
                self.timer_rgb.stop()
            self.aplicar_color_estatico()

    def aplicar_color_estatico(self):
        primary_color_str = self.config["app_settings"].get("primary_color", "#2171b4")
        primary_color = QColor(primary_color_str)
        color_texto = "white" if is_color_dark(primary_color) else "#2171b4"
        self.logo.setStyleSheet(f"color: {color_texto};")

    def cambiar_color_rgb(self):
        self.rgb_hue += 0.01
        if self.rgb_hue > 1.0:
            self.rgb_hue -= 1.0
        r, g, b = colorsys.hsv_to_rgb(self.rgb_hue, 1.0, 1.0)
        r, g, b = int(r * 255), int(g * 255), int(b * 255)
        self.logo.setStyleSheet(f"color: rgb({r},{g},{b});")

    # login / websocket flow
    def try_login(self):
        print("[DEBUG] → Iniciando proceso de login...")
        self.config = load_config()
        ws_cfg = self.config.get("websocket", {})
        self.ws_host = ws_cfg.get("host", "0.0.0.0")
        self.ws_port = ws_cfg.get("port", "8765")
        username = self.username_edit.text().strip()
        # Verificar si el usuario cambió respecto al último guardado
        ultimo_usuario = self.config["app_settings"].get("username", "")
        if username and username != ultimo_usuario:
            print("[DEBUG] → Usuario diferente detectado, reseteando estado a 'Disponible'.")
            self.config["app_settings"]["status"] = "Disponible"
            self.status_combo.setCurrentText("Disponible")

        print(f"[DEBUG] → Usuario ingresado: {username}")
        print(f"[DEBUG] → Host: {self.ws_host}, Puerto: {self.ws_port}")

        if not username:
            QMessageBox.warning(self, "Error", "Por favor introduce un nombre de usuario.")
            print("[DEBUG] ❌ No se ingresó usuario, cancelando login.")
            return

        self.config["app_settings"]["username"] = username
        self.config["app_settings"]["remember_me"] = self.remember_me_cb.isChecked()
        self.config["app_settings"]["remember_config"] = self.remember_password_cb.isChecked()
        self.config["app_settings"]["auto_signin"] = self.auto_signin_cb.isChecked()
        self.config["app_settings"]["status"] = self.status_combo.currentText()
        save_config(self.config)
        print("[DEBUG] → Configuración guardada correctamente.")

        self._login_canceled = False
        self.form_widget.hide()
        self.login_status_widget.show()
        print("[DEBUG] → Mostrando animación de espera...")

        # Mostrar GIF de "wait"
        wait_gif_url = "https://raw.githubusercontent.com/mggons93/Messenger/main/files/loading.gif"
        wait_gif_path = ensure_cache_file(wait_gif_url, "wait_icon.gif")
        self.login_movie = QMovie(wait_gif_path)
        self.login_movie.setScaledSize(QSize(40, 40))
        self.login_logo_label.setMovie(self.login_movie)
        self.login_movie.start()
        self.login_logo_label.repaint()

        # Determinar esquema y puerto correctamente según configuración
        if ws_cfg.get("use_ssl_wss"):
            scheme = "wss"
            port = ws_cfg.get("port_wss", "8766")
        else:
            scheme = "ws"
            port = ws_cfg.get("port_ws", "8765")

        ws_url = f"{scheme}://{self.ws_host}:{port}/ws"
        print(f"[DEBUG] → Intentando conectar a WebSocket en: {ws_url}")

        self.ws_client = WebSocketClient(ws_url, ws_cfg)

        # Abrimos primero la conexión real
        self.ws_client.open()

        # Luego conectamos las señales (para evitar perder eventos si cambia URL interna)
        self.ws_client.connected.connect(lambda: self.on_ws_connected(username))
        self.ws_client.error_occurred.connect(self.on_ws_error)
        self.ws_client.disconnected.connect(self.on_ws_disconnected)
        self.ws_client.message_received.connect(self.on_ws_message)
        print("[DEBUG] ✅ Señal message_received conectada correctamente")

    def on_progress_canceled(self):
        print("[DEBUG] → Login cancelado por el usuario o error.")
        self._login_canceled = True
        if self.ws_client:
            self.ws_client.close()
        if self.login_movie:
            self.login_movie.stop()
            self.login_logo_label.clear()
        self.login_status_widget.hide()
        self.form_widget.show()

    def on_ws_connected(self, username):
        print("[DEBUG] ✅ WebSocket conectado correctamente.")
        if self._login_canceled:
            print("[DEBUG] → Login cancelado, abortando autenticación.")
            return

        # Enviar autenticación
        auth_msg = json.dumps({"type": "auth", "username": username})
        self.ws_client.send(auth_msg)
        print(f"[DEBUG] → Mensaje de autenticación enviado: {auth_msg}")

        # Solicitar sincronización de contactos
        sync_msg = json.dumps({"type": "sync_contacts"})
        self.ws_client.send(sync_msg)
        print(f"[DEBUG] → Solicitud de sincronización enviada: {sync_msg}")

    def on_ws_error(self, error_str):
        print(f"[DEBUG] ❌ Error de WebSocket: {error_str}")
        if self.login_movie:
            self.login_movie.stop()
            self.login_logo_label.clear()
        self.login_status_widget.hide()
        self.form_widget.show()
        QMessageBox.critical(self, "Error Conexión", f"No se pudo conectar al servidor:\n{error_str}")

    def on_ws_disconnected(self):
        print("[DEBUG] ⚠ WebSocket desconectado inesperadamente.")
        if self.login_movie:
            self.login_movie.stop()
            self.login_logo_label.clear()
        self.login_status_widget.hide()
        self.form_widget.show()
        if hasattr(self, "chat_panel") and self.chat_panel and self.chat_panel.isVisible():
            QMessageBox.warning(self, "Desconectado", "Se perdió la conexión con el servidor.")
            self.chat_panel.close()

    def on_ws_message(self, msg):
        print(f"[DEBUG] 📩 Mensaje recibido WS: {msg}")
        try:
            data = json.loads(msg)
            tipo = str(data.get("type", "")).strip().lower()
            print(f"[DEBUG] → Tipo normalizado: {repr(tipo)}")

            # 🟦 1️⃣ Guardar contactos cuando llegan (aunque no se haya autenticado todavía)
            if tipo == "sync_contacts":
                contactos = data.get("contacts", [])
                self._last_contacts = contactos  # buffer interno
                print(f"[DEBUG] ✅ Respuesta de sincronización recibida: {len(contactos)} contactos (guardados en buffer)")

            # 🟩 2️⃣ Cuando llega auth_response → abrir la ventana Messenger usando el buffer
            elif tipo == "auth_response":
                print("[DEBUG] 🟢 Entrando a bloque auth_response")
                if not data.get("success", True):
                    print("[DEBUG] ❌ Autenticación fallida")
                    QMessageBox.warning(self, "Error", "Autenticación fallida")
                    self.on_progress_canceled()
                    return

                print("[DEBUG] ✅ Autenticación exitosa.")
                self._auth_ok = True

                # Detener animación de carga
                if self.login_movie:
                    self.login_movie.stop()
                    self.login_logo_label.clear()
                self.login_status_widget.hide()

                # Recuperar contactos del buffer (si existen)
                contactos_final = getattr(self, "_last_contacts", [])
                print(f"[DEBUG] → Programando apertura de MessengerWindow con {len(contactos_final)} contactos...")

                # Apertura diferida para no bloquear el hilo principal
                from PyQt5.QtCore import QTimer
                def abrir_panel():
                    print("[DEBUG] 🚀 Ejecutando apertura diferida de MessengerWindow...")
                    self.messenger_window = MessengerWindow()
                    self.messenger_window.cargar_contactos(contactos_final)

                    #if len(contactos_final) == 0:
                        #QMessageBox.information(self, "Sin contactos",
                        #    "No tienes contactos sincronizados en este momento.")

                    self.messenger_window.show()
                    #self.close()
                    self.hide()

                QTimer.singleShot(0, abrir_panel)

            # 🟨 3️⃣ Cualquier otro mensaje no reconocido
            else:
                print(f"[DEBUG] ⚠ Tipo de mensaje no manejado: {tipo}")

        except Exception as e:
            print(f"[DEBUG] ⚠ Error procesando mensaje WS: {e}")


    def enter_chat_panel(self):
        print("[DEBUG] → Entrando al panel de chat.")
        username = self.username_edit.text().strip()
        self.chat_panel = ChatPanel(self.ws_client, username)
        self.chat_panel.show()
        self.hide()

        chat_name = self.config["app_settings"].get("chat_name", "Chat Messenger")
        self.logo.setText(chat_name)
        self.aplicar_color_texto()

        logo_url = self.config["app_settings"].get("chat_image", "")
        pixmap = cargar_imagen(logo_url)
        if not pixmap.isNull():
            self.img_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    # ---------------------------
    # Opciones: abrir dialog
    # ---------------------------
    def mostrar_opciones(self):
        dlg = OpcionesDialog(load_config(), self)
        dlg.exec_()
        # recargar configuración por si cambió
        self.config = load_config()
        chat_name = self.config["app_settings"].get("chat_name", "Chat Messenger")
        self.logo.setText(chat_name)
        self.aplicar_color_texto()
        logo_url = self.config["app_settings"].get("chat_image", "")
        pixmap = cargar_imagen(logo_url)
        if not pixmap.isNull():
            self.img_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def abrir_config_interfaz(self):
        dialog = InterfaceSettingsDialog(self, self.config)
        if dialog.exec_() == QDialog.Accepted:
            self.config = load_config()
            chat_name = self.config["app_settings"].get("chat_name", "Chat Messenger")
            self.logo.setText(chat_name)
            self.aplicar_color_texto()
            logo_url = self.config["app_settings"].get("chat_image", "")
            pixmap = cargar_imagen(logo_url)
            if not pixmap.isNull():
                self.img_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.update()

    # ---------------------------
    # Actualizaciones
    # ---------------------------
    def mostrar_version(self):
        texto_acerca = (
            f"Messenger\n\n"
            f"Versión 2025 (compilación {VERSION})\n\n"
            f"Canal actual: {CANAL_ACTUAL.capitalize()}\n\n"
            "Copyright © 2025 S&A Network. Reservados todos los derechos.\n\n"
            "Este software está licenciado bajo la licencia MIT.\n\n"
            "Partes de este software están basadas en trabajos independientes y código abierto.\n"
        )
        QMessageBox.information(self, "Acerca de Messenger", texto_acerca)

    def verificar_version_remota(self, canal=CANAL_ACTUAL):
        """Verifica si hay una nueva versión disponible según el canal (release/beta/dev)."""
        try:
            response = requests.get(UPDATE_URL, timeout=10)
            if response.status_code != 200:
                print("⚠ No se pudo obtener la versión remota.")
                return False, VERSION

            data = response.json()

            # Buscar la versión dentro del canal correspondiente
            if canal in data and "version" in data[canal]:
                version_remota = data[canal]["version"]
            elif "version" in data:  # estructura plana (por compatibilidad)
                version_remota = data["version"]
            else:
                version_remota = "v0.0.0"

            hay_update = version_remota != VERSION
            return hay_update, version_remota

        except Exception as e:
            print(f"⚠ Error al verificar actualizaciones: {e}")
            return False, VERSION

    def verificar_actualizaciones(self):
        necesita_actualizar, version_remota = self.verificar_version_remota(canal=CANAL_ACTUAL)
        if necesita_actualizar:
            reply = QMessageBox.question(
                self,
                "Actualización disponible",
                f"Hay una nueva versión disponible en el canal {CANAL_ACTUAL.upper()}:\n\n"
                f"Versión actual: {VERSION}\n"
                f"Versión disponible: {version_remota}\n\n"
                "¿Deseas actualizar ahora?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.realizar_actualizacion()
        else:
            QMessageBox.information(self, "Actualizaciones", "No hay actualizaciones disponibles.")

    def check_updates_silent(self):
        """Verifica en segundo plano si hay una versión más reciente."""
        necesita_actualizar, version_remota = self.verificar_version_remota(canal=CANAL_ACTUAL)

        if necesita_actualizar:
            QMessageBox.information(
                self,
                "Actualización disponible",
                f"Se detectó una nueva versión del canal {CANAL_ACTUAL.upper()}:\n\n"
                f"Versión actual: {VERSION}\n"
                f"Versión disponible: {version_remota}\n\n"
                "Puedes actualizar desde Ayuda → Actualizaciones."
            )

    def realizar_actualizacion(self):
        """Ejecuta el actualizador externo (Update.exe) y cierra la aplicación actual."""
        msg = QMessageBox(self)
        msg.setWindowTitle("Actualizando")
        msg.setText("Iniciando proceso de actualización...")
        msg.setStandardButtons(QMessageBox.NoButton)
        msg.show()

        update_path = r"C:\MSN\Update.exe"
        try:
            subprocess.Popen([update_path])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo iniciar el actualizador:\n{e}")
            return

        QApplication.quit()
        sys.exit(0)

    # ---------------------------
    # painting gradient
    # ---------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        primary_color_str = self.config["app_settings"].get("primary_color", "#2171b4")
        primary_color = QColor(primary_color_str)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, primary_color.lighter(130))
        gradient.setColorAt(0.4, primary_color.lighter(160))
        gradient.setColorAt(1.0, QColor("#FFFFFF"))
        painter.fillRect(self.rect(), gradient)

# -------------------------------
# MAIN
# -------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec_())
