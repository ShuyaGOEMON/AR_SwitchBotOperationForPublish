## English description is following this chapter.
# ARグラス×音声認識によるSwitchBot遠隔操作システム
（このREADMEはGPT-4oを用いて作成されました。内容はShuyaGOEMONが確認済みです。）


## 🔧 概要

本プロジェクトは、**ARグラスを用いたハンズフリー環境操作**を実現するためのクライアント・サーバシステムです。  
**音声認識エンジンWhisper**と、**SwitchBot API**を組み合わせ、QRコードで識別されたデバイスに対して音声で指示を出すことができます。

## 🏗️ システム構成

```
+----------------+          TCP通信          +------------------+         HTTPS         +-----------------+
|  クライアント（AR側）  |  <================>  |     サーバ（PC/RasPi）   |  <===========>  |  SwitchBotクラウド |
| - QR読み取り           |                      | - 音声受信・Whisper変換   |                 | - デバイス制御API   |
| - 音声録音・送信       |                      | - QR対応デバイス状態管理 |                 |                   |
+----------------+                          +------------------+                         +-----------------+
```

## 🖥️ 使用技術

- Python 3.11
- Whisper (OpenAI) for speech-to-text
- OpenCV + Pyzbar for QRコード認識
- PyAudio for 音声録音
- SwitchBot API v1.1
- Tkinter for UI表示

## 📁 ディレクトリ構成

```
.
├── client.py               # クライアント（カメラ・録音・UI送信）
├── record.py               # 音声録音（PyAudio + 音声検知）
├── server.py               # サーバ（音声受信・Whisper認識・SwitchBot制御）
├── .env                    # SwitchBot APIトークン（公開しないでください）
├── received_audio/         # 音声保存用ディレクトリ
```

## 🔑 .envファイル（必須）

以下の内容を `.env` に記述し、`python-dotenv` などで読み込んでください。

```env
SWITCHBOT_TOKEN=your_token_here
SWITCHBOT_SECRET=your_secret_here
```

`.env` は `.gitignore` に必ず追加してください。

## 🚀 実行方法

### 1. サーバ起動

```bash
python server.py
```

### 2. クライアント起動

```bash
python client.py
```

（必要に応じて `input_device_index` を `record.py` 内で調整）

## 🔈 音声コマンド例

- 「スイッチオン」 → `turnOn` 実行
- 「スイッチオフ」 → `turnOff` 実行
- 「スイッチ切り替え」 → `press` 実行（ワンプッシュ型）

## ⚠️ 注意点

- Whisperモデル（`large`）はGPU推奨（`cuda`）。CPU利用時は `server.py` の `WHISPER_DEVICE = 'cpu'` に変更。
- カメラデバイスやマイクデバイスのIDは環境依存です。`VideoCapture(0)` や `input_device_index` を調整してください。
- SwitchBotの物理スイッチに機能が対応しているかをご確認ください。

## 📜 ライセンス

MIT License

## ✨ 今後の展望

- WebベースのUI追加
- 英語音声認識対応
- BLE経由のローカルSwitchBot制御

# Remote SwitchBot Control System with AR Glasses and Speech Recognition

## 🔧 Overview

This project implements a **hands-free control system** using AR glasses, speech recognition, and the SwitchBot API.  
By combining **OpenAI's Whisper** for speech-to-text and **QR-based device identification**, users can remotely control SwitchBot devices via voice commands.

## 🏗️ System Architecture

```
+----------------+          TCP Communication         +------------------+         HTTPS         +-----------------+
|  Client (AR side)  |  <=============================>  |     Server (PC/RasPi)   |  <===========>  |  SwitchBot Cloud |
| - QR recognition     |                                | - Audio reception & STT  |                 | - Device Control API |
| - Audio recording     |                                | - QR device management   |                 |                     |
+----------------+                                +------------------+                             +-----------------+
```

## 🖥️ Technologies Used

- Python 3.11
- Whisper (OpenAI) for speech-to-text
- OpenCV + Pyzbar for QR code recognition
- PyAudio for audio recording
- SwitchBot API v1.1
- Tkinter for UI display

## 📁 Directory Structure

```
.
├── client.py               # Client: camera, recording, UI, and transmission
├── record.py               # Audio recorder (PyAudio + detection)
├── server.py               # Server: audio reception, Whisper, SwitchBot control
├── .env                    # SwitchBot API tokens (not for public)
├── received_audio/         # Directory to store recorded audio
```

## 🔑 .env File (Required)

Prepare a `.env` file containing your SwitchBot credentials:

```env
SWITCHBOT_TOKEN=your_token_here
SWITCHBOT_SECRET=your_secret_here
```

**Note:** Make sure to add `.env` to `.gitignore` to prevent accidental exposure.

## 🚀 How to Run

### 1. Start the server

```bash
python server.py
```

### 2. Start the client

```bash
python client.py
```

(Adjust `input_device_index` in `record.py` depending on your microphone setup.)

## 🔈 Example Voice Commands (Japanese)

- "スイッチオン" → Executes `turnOn`
- "スイッチオフ" → Executes `turnOff`
- "スイッチ切り替え" → Executes `press` (toggle)

## ⚠️ Notes

- Whisper `large` model is GPU-friendly. For CPU, set `WHISPER_DEVICE = 'cpu'` in `server.py`.
- Camera and microphone device IDs may vary by system. Update `VideoCapture(0)` and `input_device_index` accordingly.
- Make sure your SwitchBot devices support the required control mode.

## 📜 License

MIT License

## ✨ Future Improvements

- Add Web-based UI
- Add English voice command support
- Enable local BLE control of SwitchBot devices
