### シミュレーションのみ。
### シリアル通信するのはmain_real.py

import pygame
import csv
import numpy as np
from src.config import *
from src.objects import Human, Bird

# A parameter for minimum bird size on the debug view
DEBUG_MIN_BIRD_SIZE_PX = 6.0

def model_to_view(pos_m):
    """Converts model meters (simulation space) to view pixels (drawing space)."""
    scale = WORLD_RADIUS / MODEL_RADIUS
    view_center = np.array([VIEW_WIDTH / 2, VIEW_HEIGHT / 2])
    return pos_m * scale + view_center

def view_to_model(pos_px):
    """Converts view pixels to model meters. Assumes mouse is over the left view."""
    scale = WORLD_RADIUS / MODEL_RADIUS
    view_center = np.array([VIEW_WIDTH / 2, VIEW_HEIGHT / 2])
    return (np.array(pos_px) - view_center) / scale

def main():
    pygame.init(); pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    debug_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    art_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    pygame.display.set_caption("Left: Debug View | Right: Artistic View")
    clock = pygame.time.Clock()

    try:
        all_led_model_positions = np.loadtxt(LED_FILE_PATH, delimiter=',', skiprows=1)
    except Exception as e:
        print(f"FATAL: Could not load LED data from '{LED_FILE_PATH}'. Error: {e}"); return
    
    led_model_positions = all_led_model_positions[:NUM_LEDS]
    led_view_positions = np.apply_along_axis(model_to_view, 1, led_model_positions)
    
    human = Human()
    birds = [Bird(bird_id, BIRD_PARAMS[bird_id]) for bird_id in BIRDS_TO_SIMULATE if bird_id in BIRD_PARAMS]

    # --- 静的な背景を一度だけ描画（パフォーマンス改善） ---
    static_background_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    static_background_surface.fill((25, 28, 35))
    pond_center_px = (VIEW_WIDTH // 2, VIEW_HEIGHT // 2)
    pygame.draw.circle(static_background_surface, (20, 40, 80), pond_center_px, WORLD_RADIUS)
    # 全てのLEDの物理的なレイアウトを描画
    for led_pos_px in led_view_positions:
        pygame.draw.circle(static_background_surface, (50, 50, 50), (int(led_pos_px[0]), int(led_pos_px[1])), 1)
    # --- ここまでが事前描画 ---

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

        human.update_position(view_to_model(pygame.mouse.get_pos()))
        for bird in birds: bird.update(human, birds)

        # --- デバッグビューの描画 ---
        # 1. 事前描画した静的な背景を貼り付け
        debug_surface.blit(static_background_surface, (0, 0))
        
        # 2. 動的な要素（鳥と人）のみを描画
        for bird in birds:
            bird_pos_px = model_to_view(bird.position)
            final_draw_size_px = max(bird.params['size'] * 2.5, DEBUG_MIN_BIRD_SIZE_PX)
            pygame.draw.circle(debug_surface, bird.base_color, (int(bird_pos_px[0]), int(bird_pos_px[1])), int(final_draw_size_px))
            pygame.draw.circle(debug_surface, bird.accent_color, (int(bird_pos_px[0]), int(bird_pos_px[1])), int(final_draw_size_px * 0.4))
        
        human_pos_px = model_to_view(human.position)
        pygame.draw.circle(debug_surface, (255, 255, 255), (int(human_pos_px[0]), int(human_pos_px[1])), 10)
                # --- LEDの色の計算（統合・効率化版） ---
        final_led_colors_view = np.zeros((NUM_LEDS, 3), dtype=int)
        brightness_map = np.zeros(NUM_LEDS, dtype=float)
        winner_map = np.full(NUM_LEDS, -1, dtype=int)

        # 1. Winner-Takes-All: どのLEDをどの鳥が担当するか決定
        for i, bird in enumerate(birds):
            distances_m = np.linalg.norm(led_model_positions - bird.position, axis=1)
            center_led_index = np.argmin(distances_m)
            
            _, num_pixels = bird.get_current_light_pattern()
            num_physical_leds = num_pixels * 3
            spread = num_physical_leds // 2

            brightness = 0.6
            if bird.state == "CHIRPING": brightness = bird.current_brightness
            elif bird.state == "FLEEING": brightness = 1.0

            for j in range(-spread, spread + 1):
                led_idx = center_led_index + j
                if 0 <= led_idx < NUM_LEDS:
                    falloff = (spread - abs(j)) / spread if spread > 0 else 1.0
                    final_brightness = brightness * falloff
                    
                    if final_brightness > brightness_map[led_idx]:
                        brightness_map[led_idx] = final_brightness
                        winner_map[led_idx] = i
        
        # 2. 色を決定して描画配列を生成
        for led_idx in range(NUM_LEDS):
            bird_idx = winner_map[led_idx]
            if bird_idx != -1:
                bird = birds[bird_idx]
                brightness = brightness_map[led_idx]
                
                # 鳥の中心からの物理的なオフセットを再計算（これは一度きりでOK）
                distances_m = np.linalg.norm(led_model_positions - bird.position, axis=1)
                center_led_index = np.argmin(distances_m)
                physical_offset = led_idx - center_led_index
                
                # 正確なピクセルオフセット計算
                pixel_offset = physical_offset // 3

                current_pattern, _ = bird.get_current_light_pattern()
                total_pattern_pixels = sum(p[1] for p in current_pattern)
                
                if total_pattern_pixels > 0:
                    color_type = 'b'
                    start_pixel = -total_pattern_pixels // 2
                    
                    for p_type, p_count in current_pattern:
                        if start_pixel <= pixel_offset < start_pixel + p_count:
                            color_type = p_type; break
                        start_pixel += p_count

                    color = bird.accent_color if color_type == 'a' else bird.base_color
                    final_led_colors_view[led_idx] = np.clip(color * brightness, 0, 255)
                    
        # 3. アートビューに計算されたLEDの色を描画
        art_surface.fill((5, 8, 15))
        pygame.draw.circle(art_surface, (20, 40, 80), pond_center_px, WORLD_RADIUS)
        for i, pos_px in enumerate(led_view_positions):
            if np.any(final_led_colors_view[i] > 5):
                pygame.draw.circle(art_surface, final_led_colors_view[i], (int(pos_px[0]), int(pos_px[1])), 2)

        # 画面を更新
        screen.blit(debug_surface, (0, 0)); screen.blit(art_surface, (VIEW_WIDTH, 0))
        pygame.display.flip()
        clock.tick(60)
        
    pygame.quit()

if __name__ == '__main__':
    main()