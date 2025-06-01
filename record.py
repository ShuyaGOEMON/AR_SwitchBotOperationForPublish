import pyaudio
import numpy as np
import wave
import time
import os
from queue import Queue
from collections import deque
from threading import Thread

class SoundRecorder:
    RATE = 16000              # サンプリング周波数（Hz）
    CHANNELS = 1              # モノラル録音
    WIDTH = 2                 # サンプル幅（バイト）
    CHUNK = 1024              # フレームサイズ
    THRESHOLD = 50            # 音量しきい値（環境により調整が必要）
    SILENCE_CHUNKS = 50       # 無音とみなすまでの連続無音チャンク数
    DEQUE_SIZE = 16           # 録音前バッファ用リングバッファの長さ

    def __init__(self, file_path_queue: Queue):
        self.p = pyaudio.PyAudio()
        self.file_path_queue = file_path_queue
        self.frames: list[bytes] = []
        self.ring_buffer = deque([], maxlen=self.DEQUE_SIZE)
        self.recording = False
        self.silent_chunks = 0
        self.file_number = 0

        self.list_audio_devices()
        # 使用するマイクのインデックス（環境に応じて変更）
        self.input_device_index = 1

    def list_audio_devices(self):
        """利用可能な音声入力デバイスを一覧表示"""
        print("\n--- Audio Input Devices ---")
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                print(f"[{i}] {info['name']} — channels: {info['maxInputChannels']}")
        print("----------------------------\n")

    def audio_callback(self, in_data, frame_count, time_info, status):
        """リアルタイム音声処理（PyAudioのコールバック）"""
        audio_np = np.frombuffer(in_data, dtype=np.int16)
        volume = np.linalg.norm(audio_np) / len(audio_np)

        if volume > self.THRESHOLD:
            if not self.recording:
                print("発話検出 → 録音開始")
                self.frames.extend(self.ring_buffer)
                self.ring_buffer.clear()

            self.recording = True
            self.silent_chunks = 0
            self.frames.append(in_data)

        elif self.recording:
            self.frames.append(in_data)
            self.silent_chunks += 1
            if self.silent_chunks >= self.SILENCE_CHUNKS:
                self.save_recorded_data()
                self.recording = False
                self.frames = []
                self.ring_buffer.clear()
        else:
            self.ring_buffer.append(in_data)

        return (in_data, pyaudio.paContinue)

    def start_recording(self):
        """録音を開始"""
        self.stream = self.p.open(
            rate=self.RATE,
            format=self.p.get_format_from_width(self.WIDTH),
            channels=self.CHANNELS,
            input=True,
            frames_per_buffer=self.CHUNK,
            stream_callback=self.audio_callback,
            input_device_index=self.input_device_index  # Noneにすればデフォルト入力を使用
        )
        print("\n🎙️ 録音ストリーム開始\n")

    def save_recorded_data(self):
        """音声をWAVファイルとして保存し、ファイルパスをキューに送る"""
        duration_sec = len(self.frames) * (self.CHUNK / self.RATE)
        if duration_sec <= 5.0:
            print("🔇 短すぎるため雑音と判断し破棄")
            return

        frames_to_save = list(self.frames)
        current_dir = os.getcwd()
        filename = f"recorded_{int(time.time())}_{self.file_number}.wav"
        file_path = os.path.join(current_dir, filename)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self.p.get_sample_size(self.p.get_format_from_width(self.WIDTH)))
            wf.setframerate(self.RATE)
            wf.writeframes(b"".join(frames_to_save))

        print(f"音声保存完了: {file_path}")
        self.file_path_queue.put(file_path)
        self.file_number += 1

    def run(self):
        """メインループ（例：録音は別スレッドで呼び出し）"""
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("中断されました")
        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()
            print("🎤 終了しました")

# テスト用：このファイル単体で実行可能
if __name__ == "__main__":
    def file_listener(queue):
        while True:
            print("新しいファイル:", queue.get())

    q = Queue()
    Thread(target=file_listener, args=(q,), daemon=True).start()

    recorder = SoundRecorder(q)
    recorder.start_recording()
    recorder.run()
