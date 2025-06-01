import socket
import threading
import os
import whisper
import time
import hashlib
import hmac
import base64
import uuid
import requests

# --- 設定 ---
IP = '0.0.0.0'  # 全インターフェースで待機
PORT = 7010
BUFFER_SIZE = 1024
SAVE_DIR = "./received_audio"
os.makedirs(SAVE_DIR, exist_ok=True)

FILE_START = b"FILE_START"
FILE_END = b"FILE_END"
QR_START = b"QR_START"
QR_END = b"QR_END"

# --- SwitchBot API 認証情報 ---
# 環境変数または .env などで安全に設定すること
SWITCHBOT_TOKEN = os.environ['SWITCHBOT_TOKEN']
SWITCHBOT_SECRET = os.environ['SWITCHBOT_SECRET']

# --- デバイス管理（トークンとSwitchBotデバイスIDの対応） ---
QR_TO_DEVICE_ID = {
    "Ventilation1": {
        "device_id": "YOUR_DEVICE_ID_1",
        "commands": ["turnOn", "turnOff"]
    },
    "Shomei1": {
        "device_id": "YOUR_DEVICE_ID_2",
        "commands": ["press"]
    },
}

# --- SwitchBot API ヘッダー生成 ---
def create_header():
    nonce = uuid.uuid4()
    timestamp = int(round(time.time() * 1000))
    string_to_sign = f'{SWITCHBOT_TOKEN}{timestamp}{nonce}'
    signature = base64.b64encode(
        hmac.new(SWITCHBOT_SECRET.encode(), msg=string_to_sign.encode(), digestmod=hashlib.sha256).digest()
    ).decode()
    return {
        'Authorization': SWITCHBOT_TOKEN,
        'Content-Type': 'application/json',
        'charset': 'utf8',
        't': str(timestamp),
        'sign': signature,
        'nonce': str(nonce)
    }

# --- SwitchBot制御コマンド ---
def turn_on(device_id):
    url = f'https://api.switch-bot.com/v1.1/devices/{device_id}/commands'
    payload = {'command': 'turnOn', 'parameter': 'default'}
    return requests.post(url, headers=create_header(), json=payload).json()

def turn_off(device_id):
    url = f'https://api.switch-bot.com/v1.1/devices/{device_id}/commands'
    payload = {'command': 'turnOff', 'parameter': 'default'}
    return requests.post(url, headers=create_header(), json=payload).json()

def press(device_id):
    url = f'https://api.switch-bot.com/v1.1/devices/{device_id}/commands'
    payload = {'command': 'press', 'parameter': 'default'}
    return requests.post(url, headers=create_header(), json=payload).json()

# --- Whisperモデルの読み込み ---
WHISPER_MODEL_NAME = 'large'
WHISPER_DEVICE = 'cuda'  # CPU使用時は 'cpu' に変更
print('Loading Whisper model:', WHISPER_MODEL_NAME, WHISPER_DEVICE)
whisper_model = whisper.load_model(WHISPER_MODEL_NAME, device=WHISPER_DEVICE)
lock = threading.Lock()

def transcribe_audio(file_path):
    """Whisperで音声ファイルを日本語テキストに変換"""
    with lock:
        result = whisper_model.transcribe(file_path, language='ja')
    return result['text']

# --- クライアント接続処理 ---
latest_token = None  # 最後に受信したQRトークン

def handle_client(conn, addr):
    print(f"[接続] {addr} が接続しました")
    buffer = b""
    file_counter = 0
    global latest_token

    while True:
        try:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            buffer += data

            # --- 音声データ処理 ---
            while FILE_START in buffer and FILE_END in buffer:
                start = buffer.index(FILE_START) + len(FILE_START)
                if len(buffer) < start + 4:
                    break
                size_bytes = buffer[start:start+4]
                size = int.from_bytes(size_bytes, 'big')
                file_data_start = start + 4
                file_data_end = file_data_start + size
                if len(buffer) < file_data_end + len(FILE_END):
                    break

                file_data = buffer[file_data_start:file_data_end]
                file_path = os.path.join(SAVE_DIR, f"audio_{file_counter}.wav")
                with open(file_path, "wb") as f:
                    f.write(file_data)
                print(f"[保存] 音声ファイル: {file_path}")
                file_counter += 1
                buffer = buffer[file_data_end + len(FILE_END):]

                # 音声文字起こし（Whisper）
                transcript = transcribe_audio(file_path)
                print(f"[認識] {transcript}")

                # SwitchBot実行判定
                status_msg = ""
                if latest_token in QR_TO_DEVICE_ID:
                    config = QR_TO_DEVICE_ID[latest_token]
                    device_id = config["device_id"]
                    available_cmds = config["commands"]

                    if "turnOn" in available_cmds and "スイッチオン" in transcript:
                        turn_on(device_id)
                        status_msg = f"{latest_token}:on"

                    elif "turnOff" in available_cmds and "スイッチオフ" in transcript:
                        turn_off(device_id)
                        status_msg = f"{latest_token}:off"

                    elif "press" in available_cmds and "スイッチ切り替え" in transcript:
                        press(device_id)
                        status_msg = f"{latest_token}:pressed"

                # クライアントへ応答
                response = transcript
                if status_msg:
                    response += "|" + status_msg
                conn.sendall(response.encode())

            # --- QRコード受信処理 ---
            while QR_START in buffer and QR_END in buffer:
                start = buffer.index(QR_START) + len(QR_START)
                end = buffer.index(QR_END)
                token_bytes = buffer[start:end]
                try:
                    latest_token = token_bytes.decode()
                    print(f"[QR] 受信トークン: {latest_token}")

                    # 状態取得（switchモード対応のみ）
                    if latest_token in QR_TO_DEVICE_ID:
                        config = QR_TO_DEVICE_ID[latest_token]
                        available_cmds = config["commands"]
                        device_id = config["device_id"]

                        if "turnOn" in available_cmds:
                            status_resp = requests.get(
                                f'https://api.switch-bot.com/v1.1/devices/{device_id}/status',
                                headers=create_header()
                            )
                            if status_resp.status_code == 200:
                                device_state = status_resp.json()['body'].get('power', '').lower()
                                conn.sendall(f"{latest_token}:{device_state}".encode())
                        else:
                            conn.sendall(f"{latest_token}:取得不可能".encode())

                except Exception as e:
                    print("[QR処理エラー]", e)
                buffer = buffer[end + len(QR_END):]

        except Exception as e:
            print(f"[例外] 通信中にエラー: {e}")
            break

    conn.close()
    print(f"[切断] {addr} との接続を終了しました")

# --- サーバ起動 ---
def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((IP, PORT))
        server.listen()
        print(f"[起動] {IP}:{PORT} で接続待機中...")
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
            print(f"[スレッド] 新しいクライアント: {addr}")

if __name__ == "__main__":
    start_server()
