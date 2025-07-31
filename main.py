import pygame
import numpy as np
import os
import yaml
from src.config import BIRD_PARAMS
from src.objects import Human, Bird
from src.simulation import World

# --- Load all settings from settings.yaml ---
try:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    SETTINGS_PATH = os.path.join(PROJECT_ROOT, "settings.yaml")
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        settings = yaml.safe_load(f)
    
    LED_FILE_NAME = settings['led_layout_file']
    LED_FILE_PATH = os.path.join(PROJECT_ROOT, "assets", "data", LED_FILE_NAME)
    NUM_LEDS = settings['num_leds']
    MODEL_DIAMETER = settings['model_diameter']
    VIEW_WIDTH = settings.get('view_width', 800)
    VIEW_HEIGHT = settings.get('view_height', 800)
    BIRDS_TO_SIMULATE = settings.get('birds_to_simulate', [])
    AI_TUNING = settings.get('ai_tuning', {})
    CHIRP_PROBABILITY_PER_FRAME = AI_TUNING.get('chirp_probability_per_frame', 0.001)
    
    # 光の減衰の最低光量を定義
    MIN_BRIGHTNESS_FALLOFF = 0.3 # 30%の明るさを保証

    # ▼▼▼【変更点 1/5】LED数からピクセル数を計算する変数を追加 ▼▼▼
    NUM_PIXELS = NUM_LEDS // 3
    
    MODEL_RADIUS = MODEL_DIAMETER / 2.0
    SCREEN_WIDTH, SCREEN_HEIGHT = VIEW_WIDTH * 2, VIEW_HEIGHT
    WORLD_RADIUS = 350
    DEBUG_MIN_BIRD_SIZE_PX = 6.0
    
    print("Loaded simulation settings from 'settings.yaml'")

except Exception as e:
    print(f"FATAL: Error loading settings from 'settings.yaml'. Please check the file. Error: {e}")
    exit()

def model_to_view(pos_m):
    return pos_m * (WORLD_RADIUS / MODEL_RADIUS) + np.array([VIEW_WIDTH / 2, VIEW_HEIGHT / 2])
def view_to_model(pos_px):
    return (np.array(pos_px) - np.array([VIEW_WIDTH / 2, VIEW_HEIGHT / 2])) / (WORLD_RADIUS / MODEL_RADIUS)

def main():
    pygame.init(); pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    debug_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    art_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    pygame.display.set_caption("Left: Debug View | Right: Artistic View (Synced to Physical Pixels)")
    clock = pygame.time.Clock()

    try:
        # ▼▼▼【変更点 2/5】LED座標をピクセル座標に変換する処理を追加 ▼▼▼
        # まずは全ての物理LEDの座標を読み込む
        all_led_positions = np.loadtxt(LED_FILE_PATH, delimiter=',', skiprows=1)[:NUM_LEDS]
        # 3個ずつのLED座標の平均値を計算し、ピクセルの座標とする
        pixel_model_positions = np.array([np.mean(all_led_positions[i*3:(i+1)*3], axis=0) for i in range(NUM_PIXELS)])
        # 描画用のピクセル座標を計算
        pixel_view_positions = np.apply_along_axis(model_to_view, 1, pixel_model_positions)

    except Exception as e:
        print(f"FATAL: Could not load LED data from '{LED_FILE_PATH}'. Error: {e}"); return
    
    human = Human()
    bird_objects = [Bird(bird_id, BIRD_PARAMS[bird_id], CHIRP_PROBABILITY_PER_FRAME) for bird_id in BIRDS_TO_SIMULATE if bird_id in BIRD_PARAMS]
    world = World(MODEL_RADIUS, human, bird_objects)

    static_background = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    static_background.fill((25, 28, 35))
    pygame.draw.circle(static_background, (20, 40, 80), (VIEW_WIDTH // 2, VIEW_HEIGHT // 2), WORLD_RADIUS)
    # 背景の静的な光もピクセル単位で描画
    for pos_px in pixel_view_positions:
        pygame.draw.circle(static_background, (50, 50, 50), pos_px, 2) # ピクセルなので少し大きく

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

        world.human.update_position(view_to_model(pygame.mouse.get_pos()))
        world.update(pixel_model_positions)

        # ▼▼▼【変更点 3/5】全ての配列をピクセル数(NUM_PIXELS)で初期化する ▼▼▼
        final_pixel_colors = np.zeros((NUM_PIXELS, 3), dtype=int)
        brightness_map = np.zeros(NUM_PIXELS, dtype=float)
        winner_map = np.full(NUM_PIXELS, -1, dtype=int)
        
        # 鳥の最近傍ピクセルのインデックスを計算
        pixel_centers = [np.argmin(np.linalg.norm(pixel_model_positions - bird.position, axis=1)) for bird in world.birds]

        for i, bird in enumerate(world.birds):
            center_idx = pixel_centers[i]
            _, num_pixels_pattern = bird.get_current_light_pattern()
            spread = num_pixels_pattern // 2 # ピクセル単位なのでスプレッドもシンプルに
            brightness = 0.6
            if bird.state == "CHIRPING": brightness = bird.current_brightness
            elif bird.state == "FLEEING": brightness = 1.0

            for j in range(-spread, spread + 1):
                pixel_idx = center_idx + j
                if 0 <= pixel_idx < NUM_PIXELS:
                    # 線形減衰率を計算
                    linear_falloff = (spread - abs(j)) / spread if spread > 0 else 1.0
                    # 最低光量を保証するようにスケーリング
                    falloff = MIN_BRIGHTNESS_FALLOFF + (1.0 - MIN_BRIGHTNESS_FALLOFF) * linear_falloff
                    final_brightness = brightness * falloff
                    if final_brightness > brightness_map[pixel_idx]:
                        brightness_map[pixel_idx], winner_map[pixel_idx] = final_brightness, i

        for pixel_idx in range(NUM_PIXELS):
            bird_idx = winner_map[pixel_idx]
            if bird_idx != -1:
                bird = world.birds[bird_idx]
                # ピクセル単位でのオフセットを計算
                pixel_offset = pixel_idx - pixel_centers[bird_idx]
                pattern, _ = bird.get_current_light_pattern()
                total_pixels = sum(p[1] for p in pattern)
                if total_pixels > 0:
                    color_type, start_pixel = 'b', -total_pixels // 2
                    for p_type, p_count in pattern:
                        if start_pixel <= pixel_offset < start_pixel + p_count:
                            color_type = p_type; break
                        start_pixel += p_count
                    color = bird.accent_color if color_type == 'a' else bird.base_color
                    final_pixel_colors[pixel_idx] = np.clip(color * brightness_map[pixel_idx], 0, 255)

        # デバッグビューの描画 (変更なし)
        debug_surface.blit(static_background, (0, 0))
        for bird in world.birds:
            pos_px = model_to_view(bird.position)
            size_px = max(bird.params['size'] * 2.5, DEBUG_MIN_BIRD_SIZE_PX)
            pygame.draw.circle(debug_surface, bird.base_color, pos_px, size_px)
            pygame.draw.circle(debug_surface, bird.accent_color, pos_px, size_px * 0.4)
        pygame.draw.circle(debug_surface, (255, 255, 255), model_to_view(world.human.position), 10)
        
        # ▼▼▼【変更点 4/5】アーティスティックビューを物理的な見た目に合わせる ▼▼▼
        art_surface.fill((5, 8, 15))
        pygame.draw.circle(art_surface, (20, 40, 80), (VIEW_WIDTH // 2, VIEW_HEIGHT // 2), WORLD_RADIUS)
        # ピクセル座標(pixel_view_positions)を使い、円を大きく(radius=4)描画する
        for i, pos_px in enumerate(pixel_view_positions):
            if np.any(final_pixel_colors[i] > 5):
                pygame.draw.circle(art_surface, final_pixel_colors[i], pos_px, 4)

        # ▼▼▼【変更点 5/5】変数名が分かりやすいように修正（おまけ）▼▼▼
        # 変数名がfinal_led_colorsからfinal_pixel_colorsに変わったので、描画部分も合わせる
        screen.blit(debug_surface, (0, 0)); screen.blit(art_surface, (VIEW_WIDTH, 0))
        pygame.display.flip()
        clock.tick(60)
        
    pygame.quit()

if __name__ == '__main__':
    main()