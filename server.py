#!/usr/bin/env python3
"""
Remote Control Server
Запуск: python server.py
Потім відкрий браузер на http://localhost:8765
"""

import asyncio
import websockets
import json
import base64
import io
import threading
import time
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

try:
    import pyautogui
    import PIL.ImageGrab as ImageGrab
except ImportError:
    print("Встановлюю залежності...")
    os.system(f"{sys.executable} -m pip install pyautogui pillow websockets")
    import pyautogui
    import PIL.ImageGrab as ImageGrab

pyautogui.FAILSAFE = False

# --- HTTP сервер для клієнта ---
class SilentHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(os.path.dirname(__file__), "static"), **kwargs)
    def log_message(self, format, *args):
        pass

def start_http():
    server = HTTPServer(("0.0.0.0", 8080), SilentHandler)
    print("Веб-клієнт: http://localhost:8080")
    server.serve_forever()

# --- WebSocket сервер ---
clients = set()

async def capture_screen():
    """Захоплення екрану і відправка клієнтам"""
    global clients
    while True:
        if clients:
            try:
                img = ImageGrab.grab()
                img.thumbnail((1280, 720))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=50)
                b64 = base64.b64encode(buf.getvalue()).decode()
                msg = json.dumps({"type": "screen", "data": b64})
                dead = set()
                for ws in clients.copy():
                    try:
                        await ws.send(msg)
                    except:
                        dead.add(ws)
                clients -= dead
            except Exception as e:
                print(f"Помилка екрану: {e}")
        await asyncio.sleep(0.05)  # ~20 fps

async def handle_client(websocket):
    global clients
    clients.add(websocket)
    print(f"Клієнт підключився ({len(clients)} всього)")
    # Відправити розмір екрану
    w, h = pyautogui.size()
    await websocket.send(json.dumps({"type": "screen_size", "w": w, "h": h}))
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                t = data.get("type")

                if t == "mouse_move":
                    pyautogui.moveTo(int(data["x"]), int(data["y"]))

                elif t == "mouse_click":
                    btn = data.get("button", "left")
                    pyautogui.click(int(data["x"]), int(data["y"]), button=btn)

                elif t == "mouse_dblclick":
                    pyautogui.doubleClick(int(data["x"]), int(data["y"]))

                elif t == "mouse_down":
                    pyautogui.mouseDown(int(data["x"]), int(data["y"]), button=data.get("button","left"))

                elif t == "mouse_up":
                    pyautogui.mouseUp(int(data["x"]), int(data["y"]), button=data.get("button","left"))

                elif t == "scroll":
                    pyautogui.scroll(int(data.get("dy", 0)), x=int(data["x"]), y=int(data["y"]))

                elif t == "key_press":
                    key = data.get("key", "")
                    if key:
                        pyautogui.press(key)

                elif t == "key_down":
                    key = data.get("key", "")
                    if key:
                        pyautogui.keyDown(key)

                elif t == "key_up":
                    key = data.get("key", "")
                    if key:
                        pyautogui.keyUp(key)

                elif t == "type_text":
                    text = data.get("text", "")
                    if text:
                        pyautogui.typewrite(text, interval=0.02)

                elif t == "hotkey":
                    keys = data.get("keys", [])
                    if keys:
                        pyautogui.hotkey(*keys)

            except Exception as e:
                print(f"Помилка команди: {e}")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.discard(websocket)
        print(f"Клієнт відключився ({len(clients)} всього)")

async def main():
    print("=" * 50)
    print("  Remote Control Server")
    print("=" * 50)
    
    # Запуск HTTP сервера в окремому потоці
    t = threading.Thread(target=start_http, daemon=True)
    t.start()

    # Запуск WebSocket сервера
    print("WebSocket: ws://localhost:8765")
    print("-" * 50)
    print("Натисни Ctrl+C щоб зупинити")
    print("=" * 50)

    async with websockets.serve(handle_client, "0.0.0.0", 8765):
        await asyncio.gather(
            capture_screen(),
            asyncio.Future()  # тримає сервер
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nСервер зупинено.")
