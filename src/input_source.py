# src/input_source.py
import abc
import pygame
import socket
import threading
import numpy as np
import queue

# -------------------------------------------------------------
# 1. 共通のインターフェース（コンセント）を定義
# -------------------------------------------------------------
class InputSource(abc.ABC):
    """入力ソースの振る舞いを定義する抽象基底クラス（コンセント）"""
    @abc.abstractmethod
    def get_human_positions(self) -> list[np.ndarray]:
        """シミュレーション空間にマッピングされた人間の座標リストを返す"""
        pass
    
    def shutdown(self):
        """クリーンアップ処理（スレッド停止など）"""
        pass

# -------------------------------------------------------------
# 2. マウス用の具体的な実装（マウス用プラグ）
# -------------------------------------------------------------
class MouseInputSource(InputSource):
    """マウスの動きをシミュレーション座標として提供するクラス"""
    def __init__(self, view_to_model_func):
        self.view_to_model = view_to_model_func

    def get_human_positions(self) -> list[np.ndarray]:
        mouse_pos_view = pygame.mouse.get_pos()
        # マウスがデバッグウィンドウ内にある場合のみ座標を返す
        if 0 <= mouse_pos_view[0] < 800: # view_widthをハードコーディング
            model_pos = self.view_to_model(mouse_pos_view)
            return [model_pos]
        return []

# -------------------------------------------------------------
# 3. LiDAR(UDP)用の具体的な実装（LiDAR用プラグ）
#    あなたの指摘通り、座標変換は責務外。受信に徹する。
# -------------------------------------------------------------
class UdpInputSource(InputSource):
    """UDPで受信した座標を提供するクラス"""
    def __init__(self, host='0.0.0.0', port=9999):
        self.latest_positions = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        
        # 受信スレッドを開始
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        print(f"Listening for HUMAN POSITIONS on UDP port {port}...")

    def _listen(self):
        while self.running:
            data, _ = self.sock.recvfrom(1024)
            # 受信したバイト列をfloat32のN行2列の配列に変換
            try:
                positions = np.frombuffer(data, dtype=np.float32).reshape(-1, 2)
                self.latest_positions = list(positions)
            except ValueError:
                print("Warning: Received malformed UDP packet.")
                self.latest_positions = []

    def get_human_positions(self) -> list[np.ndarray]:
        return self.latest_positions
    
    def shutdown(self):
        self.running = False
        self.sock.close()
        print("UDP Input source shut down.")