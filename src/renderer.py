
import pygame
import numpy as np
from src.coordinates import CoordinateSystem

class Renderer:
    """
    Handles all rendering tasks for the simulation, including debug and artistic views.
    """
    def __init__(self, settings, pixel_model_positions, coord_system: CoordinateSystem, lidar_pose_data=None):
        """
        Initializes the Renderer with necessary settings and pre-calculated positions.
        
        Args:
            settings (dict): The main settings dictionary.
            pixel_model_positions (np.array): (N, 2) array of pixel positions in model space.
            coord_system (CoordinateSystem): The coordinate system converter.
        """
        # Settings
        self.view_width = settings.get('view_width', 800)
        self.view_height = settings.get('view_height', 800)
        self.min_brightness_falloff = settings.get('min_brightness_falloff', 0.3)
        self.debug_min_bird_size_px = 6.0
        self.lidar_pose_data = lidar_pose_data # 姿勢データを保存

        # Font for debug text
        pygame.font.init()
        self.font = pygame.font.SysFont('Arial', 16)

        # Coordinate system
        self.coord_system = coord_system
        
        # Pixel data
        self.pixel_model_positions = pixel_model_positions
        self.pixel_view_positions = np.array([self.coord_system.model_to_view(p) for p in self.pixel_model_positions])
        self.num_pixels = len(pixel_model_positions)

        # Surfaces for drawing
        self.debug_surface = pygame.Surface((self.view_width, self.view_height))
        self.art_surface = pygame.Surface((self.view_width, self.view_height))
        
        # Pre-render static backgrounds
        self._create_static_backgrounds()

        # Calculated colors from the last frame, can be fetched for real-time output
        self.final_pixel_colors = np.zeros((self.num_pixels, 3), dtype=int)

    def _create_static_backgrounds(self):
        """Creates the non-changing background elements for both views."""
        # Debug view background
        self.static_debug_bg = pygame.Surface((self.view_width, self.view_height))
        self.static_debug_bg.fill((25, 28, 35))
        pygame.draw.circle(self.static_debug_bg, (20, 40, 80), self.coord_system.view_center, self.coord_system.view_radius)
        for pos_px in self.pixel_view_positions:
            pygame.draw.circle(self.static_debug_bg, (50, 50, 50), pos_px, 2)

        # Artistic view background
        self.static_art_bg = pygame.Surface((self.view_width, self.view_height))
        self.static_art_bg.fill((5, 8, 15))
        pygame.draw.circle(self.static_art_bg, (20, 40, 80), self.coord_system.view_center, self.coord_system.view_radius)

    def calculate_pixel_colors(self, world):
        """
        Calculates the final color for each pixel based on the state of the world.
        This updates the internal `self.final_pixel_colors` attribute.
        """
        brightness_map = np.zeros(self.num_pixels, dtype=float)
        winner_map = np.full(self.num_pixels, -1, dtype=int)
        
        pixel_centers = [np.argmin(np.linalg.norm(self.pixel_model_positions - bird.position, axis=1)) for bird in world.birds]

        for i, bird in enumerate(world.birds):
            center_idx = pixel_centers[i]
            _, num_pixels_pattern = bird.get_current_light_pattern()
            spread = num_pixels_pattern // 2

            # 状態に基づいて基本輝度を決定
            brightness = 0.0 # デフォルトは消灯
            if bird.state == "IDLE":
                brightness = bird.current_brightness # IDLEでも微かに光る
            elif bird.state == "FLEEING":
                brightness = 1.0
            elif bird.state == "CAUTION":
                brightness = 0.4
            elif bird.state == "CURIOUS":
                brightness = 0.6
            elif bird.state == "EXPLORING" or bird.state == "FORAGING":
                brightness = 0.5
            elif bird.state == "CHIRPING":
                # CHIRPING時の輝度計算
                brightness = 0.0 # デフォルトは0
                active_pattern = bird.chirp_patterns.get(bird.active_pattern_key, [])
                if active_pattern:
                    # パターンから現在の輝度を補間して計算
                    for i in range(len(active_pattern) - 1):
                        start_time, start_bright = active_pattern[i]
                        end_time, end_bright = active_pattern[i+1]
                        if start_time <= bird.chirp_playback_time < end_time:
                            time_delta = end_time - start_time
                            progress = (bird.chirp_playback_time - start_time) / time_delta if time_delta > 0 else 0
                            brightness = start_bright + (end_bright - start_bright) * progress
                            break

            for j in range(-spread, spread + 1):
                pixel_idx = center_idx + j
                if 0 <= pixel_idx < self.num_pixels:
                    linear_falloff = (spread - abs(j)) / spread if spread > 0 else 1.0
                    falloff = self.min_brightness_falloff + (1.0 - self.min_brightness_falloff) * linear_falloff
                    final_brightness = brightness * falloff
                    if final_brightness > brightness_map[pixel_idx]:
                        brightness_map[pixel_idx] = final_brightness
                        winner_map[pixel_idx] = i

        # Reset colors and then fill them in
        self.final_pixel_colors.fill(0)
        for pixel_idx in range(self.num_pixels):
            bird_idx = winner_map[pixel_idx]
            if bird_idx != -1 and bird_idx < len(world.birds):
                bird = world.birds[bird_idx]
                pixel_offset = pixel_idx - pixel_centers[bird_idx]
                pattern, _ = bird.get_current_light_pattern()
                total_pixels = sum(p[1] for p in pattern)
                
                if total_pixels > 0:
                    color_type, start_pixel = 'b', -total_pixels // 2
                    for p_type, p_count in pattern:
                        if start_pixel <= pixel_offset < start_pixel + p_count:
                            color_type = p_type
                            break
                        start_pixel += p_count
                    
                    color = bird.accent_color if color_type == 'a' else bird.base_color
                    self.final_pixel_colors[pixel_idx] = np.clip(color * brightness_map[pixel_idx], 0, 255)

    def get_final_colors(self):
        """Returns the latest calculated pixel colors."""
        return self.final_pixel_colors

    def _draw_lidar_pose(self, surface):
        """デバッグ画面にLiDARの姿勢を描画する"""
        if not self.lidar_pose_data:
            return

        # --- 1. LiDARのローカル座標で形状を定義 (前方がX軸プラス方向) ---
        #    - A: 後方左 (-0.1, -0.1)
        #    - B: 後方右 (-0.1, 0.1)
        #    - C: 前方先端 (0.15, 0)
        shape_local = np.array([
            [-0.1, -0.1],
            [-0.1,  0.1],
            [ 0.15, 0.0]
        ])

        # --- 2. 姿勢データを使って、形状をワールド座標に変換 ---
        pos = np.array(self.lidar_pose_data['position_xy'])
        theta_rad = np.deg2rad(self.lidar_pose_data['rotation_z_deg'])
        c, s = np.cos(theta_rad), np.sin(theta_rad)
        rotation_matrix = np.array([[c, -s], [s, c]])

        shape_world = np.array([pos + rotation_matrix @ p for p in shape_local])

        # --- 3. ワールド座標をビュー（ピクセル）座標に変換 ---
        shape_view = np.array([self.coord_system.model_to_view(p) for p in shape_world])

        # --- 4. 描画 ---
        pygame.draw.polygon(surface, (255, 255, 0), shape_view) # 黄色い三角形で描画
        pygame.draw.polygon(surface, (0, 0, 0), shape_view, 2) # 黒い縁取り

    def render(self, screen, world):
        """
        Calculates all colors and draws the full scene to the provided screen.
        """
        # 1. Calculate the light/color values for this frame
        self.calculate_pixel_colors(world)

        # 2. Draw the Debug View
        self.debug_surface.blit(self.static_debug_bg, (0, 0))
        
        # ★LiDARの描画処理をここに追加
        self._draw_lidar_pose(self.debug_surface)

        for bird in world.birds:
            pos_px = self.coord_system.model_to_view(bird.position)
            size_px = max(bird.params['size'] * 2.5, self.debug_min_bird_size_px)
            pygame.draw.circle(self.debug_surface, bird.base_color, pos_px, size_px)
            pygame.draw.circle(self.debug_surface, bird.accent_color, pos_px, size_px * 0.4)
        for human in world.humans:
            pygame.draw.circle(self.debug_surface, (255, 255, 255), self.coord_system.model_to_view(human.position), 10)

            # Display human data as text
            text_lines = [
                f"Pos: ({human.position[0]:.2f}, {human.position[1]:.2f})",
                f"Vel: ({human.velocity[0]:.2f}, {human.velocity[1]:.2f})",
                f"Size: {human.size:.2f}",
                f"Size Change: {human.size_change:.2f}"
            ]
            for i, line in enumerate(text_lines):
                text_surface = self.font.render(line, True, (255, 255, 255))
                self.debug_surface.blit(text_surface, (5, 5 + i * 20)) # 固定位置（左上）に表示

        # 3. Draw the Artistic View
        self.art_surface.blit(self.static_art_bg, (0, 0))
        for i, pos_px in enumerate(self.pixel_view_positions):
            if np.any(self.final_pixel_colors[i] > 5): # Only draw if color is not black
                pygame.draw.circle(self.art_surface, self.final_pixel_colors[i], pos_px, 4)

        # 4. Blit both views to the main screen
        screen.blit(self.debug_surface, (0, 0))
        screen.blit(self.art_surface, (self.view_width, 0))
        
        # 5. Update the display
        pygame.display.flip()
