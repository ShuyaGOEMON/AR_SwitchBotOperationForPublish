import os
import socket
import threading
import queue
import time

# Raspiで使用するときは以下をアンコメント
# import sys
# sys.path.append('/home/pi/.local/lib/python3.11/site-packages')

import cv2
from pyzbar.pyzbar import decode, ZBarSymbol
import tkinter as tk

from recordELECOM import SoundRecorder  # 音声録音クラス（ELECOMマイク向けカスタム）

# === サーバ接続設定（IPは環境に応じて変更してください） ===
IP_ADDRESS = 'YOUR_SERVER_IP'
PORT = 7010
BUFFER_SIZE = 1024

# === データマーカー ===
FILE_START = b"FILE_START"
FILE_END = b"FILE_END"
QR_START = b"QR_START"
QR_END = b"QR_END"

# === 通信用キュー ===
record_queue = queue.Queue()
qr_queue = queue.Queue()

# === サーバ接続ソケット ===
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((IP_ADDRESS, PORT))

# === カメラループ：QRコードを1秒おきに読み取り送信 ===
def camera_loop():
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)  # RasPiでは (0, cv2.CAP_V4L2)
    interval = 1.0
    last_token = None

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(interval)
            continue

        for obj in decode(frame, symbols=[ZBarSymbol.QRCODE]):
            token = obj.data.decode()
            if token != last_token:
                last_token = token
                try:
                    s.sendall(QR_START)
                    s.sendall(token.encode())
                    s.sendall(QR_END)
                except Exception:
                    pass  # 通信失敗時は無視
        time.sleep(interval)

# === 音声ファイルを送信 ===
def send_audio():
    if record_queue.empty():
        return
    fn = record_queue.get_nowait()
    try:
        with open(fn, 'rb') as f:
            data = f.read()
        size = os.path.getsize(fn)

        s.sendall(FILE_START)
        s.sendall(size.to_bytes(4, 'big'))
        s.sendall(data)
        s.sendall(FILE_END)
    except Exception as e:
        print("send_audio error:", e)

# === 音声送信ループ（常駐） ===
def send_wav_file():
    while True:
        send_audio()
        time.sleep(0.1)

# === サーバから受信したテキスト／状態メッセージを処理 ===
def text_content():
    try:
        data = s.recv(BUFFER_SIZE).decode()
    except Exception as e:
        print("Receive error:", e)
        return
    if not data:
        return

    # 状態表示（STATUS|token:state）
    if data.startswith("STATUS|"):
        _, ts = data.split("|", 1)
        token, state = ts.split(":")
        root.after(0, tk_update_status, token, state)

    # 状態だけ送られてきた場合
    elif ":" in data and "|" not in data:
        token, state = data.split(":", 1)
        root.after(0, tk_update_status, token, state)

    # 通常のメッセージと状態が両方ある場合（text|token:state）
    else:
        parts = data.split("|")
        transcript = parts[0]
        root.after(0, tk_update_message, transcript)
        if len(parts) > 1:
            token, state = parts[1].split(":")
            root.after(0, tk_update_status, token, state)

# === 受信スレッド ===
def receive_text_file():
    while True:
        text_content()

# === UI: 音声認識結果メッセージを画面に表示 ===
def tk_update_message(msg: str):
    for w in chat_frame.winfo_children():
        w.destroy()

    window_width = root.winfo_width()
    wrap_len = int(window_width * 0.6)  # メッセージの横幅調整

    lbl = tk.Label(
        chat_frame,
        text=msg,
        font=("Arial", 15),
        bg="blue",
        fg="white",
        wraplength=wrap_len,
        justify="left"
    )
    lbl.pack(fill="x", pady=5)

# === UI: デバイスの状態表示（ON/OFF） ===
def tk_update_status(token: str, state: str):
    for w in status_frame.winfo_children():
        w.destroy()
    text = f"{token}: {'ON' if state == 'on' else 'OFF'}"
    lbl = tk.Label(status_frame, text=text,
                   font=("Arial", 20), bg="green", fg="white")
    lbl.pack(fill="x", pady=5)

# === メイン処理（Tkinterウィンドウとスレッド起動） ===
def main():
    global root, chat_frame, status_frame

    root = tk.Tk()
    root.attributes('-fullscreen', True)  # 全画面表示
    root.configure(bg="black")
    root.bind("<Escape>", lambda e: root.destroy())  # Escキーで終了

    chat_frame = tk.Frame(root, bg="blue")
    chat_frame.place(relwidth=0.60, relheight=0.20,
                     relx=0.20, rely=0.75, anchor="nw")

    status_frame = tk.Frame(root, bg="green")
    status_frame.place(relwidth=0.20, relheight=0.10,
                       relx=0.02, rely=0.02, anchor="nw")

    # サーバからの受信スレッド起動
    threading.Thread(target=receive_text_file, daemon=True).start()

    root.mainloop()

# === 起動処理：録音・送信・カメラのスレッドを起動 ===
if __name__ == "__main__":
    recorder = SoundRecorder(record_queue)
    recorder.start_recording()
    threading.Thread(target=recorder.run, daemon=True).start()
    threading.Thread(target=send_wav_file, daemon=True).start()
    threading.Thread(target=camera_loop, daemon=True).start()
    main()
