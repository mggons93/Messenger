# Messenger 2025 - Cliente y Actualizador

![Messenger Logo](https://raw.githubusercontent.com/mggons93/Messenger/refs/heads/main/files/update.ico)

## 📌 Descripción

**Messenger 2025** es un proyecto de mensajería instantánea inspirado en Windows Live Messenger (WLM), escrito en **Python con PyQt5**.  
El proyecto incluye:

- **Cliente de mensajería** (`Messenger.py`) con:
  - Lista de contactos.
  - Mensajes en tiempo real vía **WebSocket**.
  - Presencia de usuarios (Disponible, Ocupado, etc.).
  - Botones de llamadas de voz/video (prototipo WebRTC).

- **Actualizador automático** (`Update.py`) que:
  - Verifica nuevas versiones del cliente desde GitHub.
  - Descarga archivos de actualización y los aplica.
  - Soporta descarga de dependencias como `7zip` y controladores SSD/NVMe opcionales.
  - Muestra splash screen moderno durante la actualización.

---

## 🛠 Tecnologías

- **Python 3.13+**
- **PyQt5** para la interfaz gráfica
- **WebSockets** para mensajería y señalización
- **aiortc** para llamadas de voz/video (WebRTC)
- **JSON** para configuración y persistencia de datos
- **Opcionales:** `ffmpeg`, `7zr` para medios y compresión de archivos

---

## ⚡ Capturas de Pantalla

![Messenger](https://raw.githubusercontent.com/mggons93/Messenger/refs/heads/main/files/messenger_screenshot.png)  
*Interfaz principal del cliente Messenger 2025.*

![Update](https://raw.githubusercontent.com/mggons93/Messenger/refs/heads/main/files/update_screenshot.png)  
*Actualizador automático con splash screen.*

> Nota: Puedes agregar más capturas en la carpeta `/files` y actualizar los links.

---

