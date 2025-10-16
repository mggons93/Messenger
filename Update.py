import os
import sys
import requests
import threading
import time
import tempfile
import psutil
import subprocess
import json
# Codigo de Actualizaciones de Messenger
# Este codigo esta sujeto a cambios y actualizaciones constantes.
# Si lo usas con fines de lucro recuerda que debes mencionar el creador.
import datetime
import urllib.request
import shutil
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation
from PyQt5.QtGui import QPixmap, QFont, QIcon


# -----------------------
# Configuraci贸n
# -----------------------
SERVIDORES_FALLBACK = [
    "https://syasoporteglobal.online/files/Messenger/version.json",
    "https://raw.githubusercontent.com/mggons93/MessengerUpdates/main/version.json",
    "https://mirror.syasoporte.net/files/Messenger/version.json"
]

SEVEN_ZIP_URL = "https://www.7-zip.org/a/7zr.exe"
INSTALL_DIR = r"C:\MSN"
os.makedirs(INSTALL_DIR, exist_ok=True)
TEMP_DIR = tempfile.gettempdir()
SEVEN_ZIP_EXE = os.path.join(TEMP_DIR, "7zr.exe")
UPDATE_FILE = os.path.join(INSTALL_DIR, "update.7z")
MESSENGER_EXE = os.path.join(INSTALL_DIR, "Messenger.exe")
LOCAL_VERSION_FILE = os.path.join(INSTALL_DIR, "version.json")
LOG_FILE = os.path.join(INSTALL_DIR, "update.log")

# 馃敼 Auto-copia de Update.exe a C:\MSN si no est谩 ejecut谩ndose desde all铆
CURRENT_PATH = os.path.abspath(sys.argv[0])
UPDATE_EXE = os.path.join(INSTALL_DIR, "Update.exe")

if not os.path.exists(INSTALL_DIR):
    os.makedirs(INSTALL_DIR, exist_ok=True)

if os.path.normcase(CURRENT_PATH) != os.path.normcase(UPDATE_EXE):
    try:
        print(f"馃搨 Copiando Update.exe a {INSTALL_DIR}...")
        if os.path.exists(UPDATE_EXE):
            os.remove(UPDATE_EXE)
        shutil.copy2(CURRENT_PATH, UPDATE_EXE)
        subprocess.Popen([UPDATE_EXE], shell=True)
        sys.exit(0)
    except Exception as e:
        print(f"鈿狅笍 Error al copiar Update.exe: {e}")
        sys.exit(1)


# 脥cono cacheado en el usuario
ICON_URL = "https://raw.githubusercontent.com/mggons93/Messenger/refs/heads/main/files/update.ico"
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "Messenger")
os.makedirs(CACHE_DIR, exist_ok=True)
ICON_PATH = os.path.join(CACHE_DIR, "update.ico")

if not os.path.exists(ICON_PATH):
    try:
        urllib.request.urlretrieve(ICON_URL, ICON_PATH)
    except Exception as e:
        print(f"No se pudo descargar el 铆cono: {e}")

HTTP_TIMEOUT = 10


# -----------------------
# Logging
# -----------------------
def write_log(msg: str):
    os.makedirs(INSTALL_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)


# -----------------------
# Splash principal
# -----------------------
class SplashWithProgress(QWidget):
    def __init__(self, pixmap: QPixmap, channel="release", width=560, height=300):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(width, height)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 14px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(12)

        # 脥cono principal
        self.label_img = QLabel()
        self.label_img.setPixmap(pixmap.scaled(width // 2, height // 2, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.label_img.setAlignment(Qt.AlignCenter)
        self.label_img.setStyleSheet("border: none; background: white;")
        layout.addWidget(self.label_img)

        # Canal (Release / Beta / Dev)
        self.label_channel = QLabel(self.get_channel_text(channel))
        self.label_channel.setAlignment(Qt.AlignCenter)
        self.label_channel.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.label_channel.setStyleSheet(self.get_channel_style(channel) + "border: none; background: white;")
        layout.addWidget(self.label_channel)

        # Mensaje de estado
        self.label_text = QLabel("Cargando actualizador...")
        self.label_text.setAlignment(Qt.AlignCenter)
        self.label_text.setWordWrap(True)
        self.label_text.setFont(QFont("Segoe UI", 11))
        self.label_text.setStyleSheet("color: black; border: none; background: white;")
        layout.addWidget(self.label_text)

        # Centrar ventana
        screen_geometry = QApplication.primaryScreen().geometry()
        self.move(
            (screen_geometry.width() - self.width()) // 2,
            (screen_geometry.height() - self.height()) // 2
        )

        # Efecto de aparici贸n suave
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.anim = QPropertyAnimation(self.effect, b"opacity")
        self.anim.setDuration(800)
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.start()

    def get_channel_text(self, channel):
        c = channel.lower()
        if c == "dev":
            return "Canal: Desarrollador (Dev)"
        elif c == "beta":
            return "Canal: Beta"
        return "Canal: Release"

    def get_channel_style(self, channel):
        c = channel.lower()
        colors = {
            "release": "color: #2ecc71;",  # verde
            "beta": "color: #3498db;",     # azul
            "dev": "color: #e74c3c;"       # rojo
        }
        return colors.get(c, "color: gray;")

    def update_message(self, text, progress=None):
        msg = text
        if progress is not None:
            msg += f" ({progress}%)"
        self.label_text.setText(msg)
        QApplication.processEvents()


# -----------------------
# Funci贸n principal de actualizaci贸n
# -----------------------
def run_update(splash: SplashWithProgress):
    try:
        version_local = "v0.0.0"
        server_from_local = None
        channel = "release"

        if os.path.exists(LOCAL_VERSION_FILE):
            try:
                with open(LOCAL_VERSION_FILE, "r", encoding="utf-8") as f:
                    loc = json.load(f)
                    version_local = loc.get("version", "v0.0.0")
                    server_from_local = loc.get("server")
                    channel = loc.get("channel", "release")
            except:
                pass

        splash.update_message("Obteniendo informaci贸n remota...")
        data_remote = None
        for src in SERVIDORES_FALLBACK:
            try:
                r = requests.get(src, timeout=HTTP_TIMEOUT)
                if r.status_code == 200:
                    data_remote = r.json()
                    break
            except:
                continue

        if not data_remote:
            splash.update_message("鉂?No se pudo obtener version.json remoto")
            time.sleep(3)
            QTimer.singleShot(0, splash.close)
            return

        chan_info = data_remote.get(channel)
        if not chan_info:
            splash.update_message(f"鉂?Canal {channel} no existe")
            time.sleep(3)
            QTimer.singleShot(0, splash.close)
            return

        version_remote = chan_info.get("version")
        url_rel = chan_info.get("url")
        server_remote = chan_info.get("server") or server_from_local or ""

        splash.update_message(f"Ver. local: {version_local} | Remota: {version_remote}")
        time.sleep(1)

        if version_remote == version_local:
            splash.update_message("鉁?Ya tienes la 煤ltima versi贸n")
            time.sleep(5)
            QTimer.singleShot(0, splash.close)
            return

        if not os.path.exists(SEVEN_ZIP_EXE):
            splash.update_message("Descargando motor 7zr.exe...")
            descargar(SEVEN_ZIP_URL, SEVEN_ZIP_EXE, splash)

        if url_rel.startswith("http"):
            update_full_url = url_rel
        else:
            update_full_url = f"{server_remote.rstrip('/')}/{url_rel.lstrip('/')}"

        splash.update_message("Descargando actualizaci贸n...", 0)
        descargar(update_full_url, UPDATE_FILE, splash)

        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and proc.info['name'].lower() == 'messenger.exe':
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except:
                    proc.kill()

        splash.update_message("Extrayendo actualizaci贸n...", 0)
        extraer_7z(UPDATE_FILE, INSTALL_DIR, splash)

        try:
            os.remove(UPDATE_FILE)
        except:
            pass

        with open(LOCAL_VERSION_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "version": version_remote,
                "url": url_rel,
                "server": server_remote,
                "channel": channel
            }, f, indent=2)

        splash.update_message("鉁?Actualizaci贸n completada")
        time.sleep(1)

        if os.path.exists(MESSENGER_EXE):
            subprocess.Popen([MESSENGER_EXE], cwd=INSTALL_DIR)

        time.sleep(2)
        QTimer.singleShot(0, splash.close)

    except Exception as e:
        write_log(f"Error en actualizaci贸n: {e}")
        splash.update_message(f"鉂?Error: {e}")
        time.sleep(4)
        QTimer.singleShot(0, splash.close)


# -----------------------
# Helpers
# -----------------------
def descargar(url, path, splash: SplashWithProgress):
    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        total = r.headers.get('content-length')
        with open(path, "wb") as f:
            if total is None:
                f.write(r.content)
            else:
                dl = 0
                total = int(total)
                for chunk in r.iter_content(chunk_size=4096):
                    if not chunk:
                        continue
                    f.write(chunk)
                    dl += len(chunk)
                    progress = int(dl * 100 / total)
                    splash.update_message(f"Descargando...", progress)
    except Exception as e:
        write_log(f"Error descargando {url}: {e}")
        splash.update_message(f"鉂?Fall贸 descarga: {url}")
        time.sleep(3)


def extraer_7z(file_path, out_dir, splash: SplashWithProgress):
    try:
        cmd = [SEVEN_ZIP_EXE, 'x', file_path, f'-o{out_dir}', '-y']
        CREATE_NO_WINDOW = 0x08000000
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        while True:
            line = proc.stdout.readline()
            if line == b"" and proc.poll() is not None:
                break
            if line:
                s = line.decode('utf-8', errors='ignore').strip()
                if "%" in s:
                    num = ''.join(c for c in s.split('%')[0] if c.isdigit())
                    if num:
                        #splash.update_message(f"Aplicando Actualizacion...", int(num))
                        splash.update_message(f"Aplicando Actualizacion...")
        proc.wait()
    except Exception as e:
        write_log(f"Error extrayendo {file_path}: {e}")


# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    # Leer canal actual
    channel = "release"
    if os.path.exists(LOCAL_VERSION_FILE):
        try:
            with open(LOCAL_VERSION_FILE, "r", encoding="utf-8") as f:
                loc = json.load(f)
                channel = loc.get("channel", "release")
        except:
            pass

    splash_pix = QPixmap(ICON_PATH) if os.path.exists(ICON_PATH) else QPixmap(520, 160)
    splash = SplashWithProgress(splash_pix, channel)
    splash.show()

    threading.Thread(target=run_update, args=(splash,), daemon=True).start()
    sys.exit(app.exec_())
