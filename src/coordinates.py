# src/coordinates.py
import numpy as np

class CoordinateSystem:
    """
    シミュレーション空間（モデル）と表示空間（ビュー）の間の座標変換を責務として持つ。
    楕円形の池に対応。
    """
    def __init__(self, view_size, model_size):
        self.view_width, self.view_height = view_size
        self.model_width, self.model_height = model_size

        self.view_center = np.array([self.view_width / 2, self.view_height / 2])
        
        # モデルの半径（X軸、Y軸）
        self.model_radius_x = self.model_width / 2.0
        self.model_radius_y = self.model_height / 2.0

        # ビュー空間における池の半径（X軸、Y軸）
        # ウィンドウの端との間に少し余白(padding)を持たせる
        padding = 0.9  # 90%のサイズにする
        self.view_radius_x = (self.view_width / 2.0) * padding
        self.view_radius_y = (self.view_height / 2.0) * padding

        # スケールファクター（X軸、Y軸）
        self.scale_factor_x = self.view_radius_x / self.model_radius_x if self.model_radius_x != 0 else 0
        self.scale_factor_y = self.view_radius_y / self.model_radius_y if self.model_radius_y != 0 else 0

    def model_to_view(self, pos_m: np.ndarray) -> np.ndarray:
        """モデル空間の座標をビュー空間のピクセル座標に変換する"""
        scaled_pos = np.array([
            pos_m[0] * self.scale_factor_x,
            pos_m[1] * self.scale_factor_y
        ])
        return scaled_pos + self.view_center

    def view_to_model(self, pos_px: np.ndarray) -> np.ndarray:
        """ビュー空間のピクセル座標をモデル空間の座標に変換する"""
        relative_pos = np.array(pos_px) - self.view_center
        model_pos = np.array([
            relative_pos[0] / self.scale_factor_x if self.scale_factor_x != 0 else 0,
            relative_pos[1] / self.scale_factor_y if self.scale_factor_y != 0 else 0
        ])
        return model_pos

    def get_model_bounds(self):
        """モデル空間の境界（左、右、下、上）を返す"""
        return -self.model_radius_x, self.model_radius_x, -self.model_radius_y, self.model_radius_y
