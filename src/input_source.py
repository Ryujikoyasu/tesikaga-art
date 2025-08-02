import abc
import pygame
import socket
import threading
import numpy as np

# Humanクラスのインポートは不要になる
# from .objects import Human 

# -------------------------------------------------------------
# 1. 共通のインターフェースを定義
# -------------------------------------------------------------
class InputSource(abc.ABC):
    """入力ソースの振る舞いを定義する抽象基底クラス"""
    @abc.abstractmethod
    def get_detected_objects(self) -> np.ndarray:
        """検出されたオブジェクトの生データ（Numpy配列）を返す"""
        pass
    
    def shutdown(self):
        """クリーンアップ処理"""
        pass

# -------------------------------------------------------------
# 2. マウス用の具体的な実装
# -------------------------------------------------------------
class MouseInputSource(InputSource):
    """マウスの動きを [x, y, size] のデータとして提供するクラス"""
    def __init__(self, view_to_model_func):
        self.view_to_model = view_to_model_func

    def get_detected_objects(self) -> np.ndarray:
        mouse_pos_view = pygame.mouse.get_pos()
        if 0 <= mouse_pos_view[0] < 800: # view_width
            model_pos = self.view_to_model(mouse_pos_view)
            # [x, y, size] の形式で返す (sizeはデフォルト値)
            return np.array([[model_pos[0], model_pos[1], 1.0]])
        return np.empty((0, 3)) # 何も検出しなかった場合は空の配列

# -------------------------------------------------------------
# 3. LiDAR(UDP)用の具体的な実装
# -------------------------------------------------------------
class UdpInputSource(InputSource):
    """UDPで受信した [x, y, size] のデータを提供するクラス"""
    def __init__(self, host='0.0.0.0', port=9999):
        self.latest_data = np.empty((0, 3))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        print(f"Listening for OBJECT DATA on UDP port {port}...")

    def _listen(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(2048)
                # 受信データを [x, y, size] のN行3列の配列に変換
                self.latest_data = np.frombuffer(data, dtype=np.float32).reshape(-1, 3)
            except ValueError:
                print("Warning: Received malformed UDP packet. Clearing data.")
                self.latest_data = np.empty((0, 3))
            except socket.error:
                if self.running: break # Shutdown中にエラーが出ることがある

    def get_detected_objects(self) -> np.ndarray:
        return self.latest_data
    
    def shutdown(self):
        self.running = False
        self.sock.close()
        self.thread.join()
        print("UDP Input source shut down.")