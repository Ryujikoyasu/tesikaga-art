# src/coordinates.py
import numpy as np

class CoordinateSystem:
    """
    シミュレーション空間（モデル）と表示空間（ビュー）の間の座標変換を責務として持つ。
    """
    def __init__(self, view_size, model_radius):
        self.view_width, self.view_height = view_size
        self.view_center = np.array([self.view_width / 2, self.view_height / 2])
        
        # view_radiusは、ビュー空間における池の半径ピクセル数 (固定値)
        # これを基準にモデル空間とのスケールを決定する
        self.view_radius = min(self.view_width, self.view_height) * 0.45 # e.g., 360
        self.model_radius = model_radius
        self.scale_factor = self.view_radius / self.model_radius

    def model_to_view(self, pos_m: np.ndarray) -> np.ndarray:
        """モデル空間の座標をビュー空間のピクセル座標に変換する"""
        return pos_m * self.scale_factor + self.view_center

    def view_to_model(self, pos_px: np.ndarray) -> np.ndarray:
        """ビュー空間のピクセル座標をモデル空間の座標に変換する"""
        return (np.array(pos_px) - self.view_center) / self.scale_factor