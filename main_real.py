import pygame
import numpy as np
import serial
import time
import os
import yaml
import threading
import queue
import random
from src.config import BIRD_PARAMS
from src.objects import Human, Bird
from src.simulation import World

# --- Load all settings from settings.yaml ---
try:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    SETTINGS_PATH = os.path.join(PROJECT_ROOT, "settings.yaml")
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        settings = yaml.safe_load(f)
    
    SERIAL_PORT = settings['serial_port']
    BAUD_RATE = settings['baud_rate']
    LED_FILE_NAME = settings['led_layout_file']
    LED_FILE_PATH = os.path.join(PROJECT_ROOT, "assets", "data", LED_FILE_NAME)
    NUM_LEDS = settings['num_leds']
    MODEL_DIAMETER = settings['model_diameter']
    ENABLE_TEST_MODE = settings.get('enable_test_mode', False)
    NUM_TEST_STRIP_LEDS = settings.get('test_strip_led_count', 100)
    VIEW_WIDTH = settings.get('view_width', 800)
    VIEW_HEIGHT = settings.get('view_height', 800)
    BIRDS_TO_SIMULATE = settings.get('birds_to_simulate', [])
    AI_TUNING = settings.get('ai_tuning', {})
    CHIRP_PROBABILITY_PER_FRAME = AI_TUNING.get('chirp_probability_per_frame', 0.001)

    # ▼▼▼【変更点 1/6】LED数からピクセル数を計算。テストモードも考慮 ▼▼▼
    # アクティブなLED数とピクセル数を決定
    NUM_ACTIVE_LEDS = NUM_TEST_STRIP_LEDS if ENABLE_TEST_MODE else NUM_LEDS
    NUM_ACTIVE_PIXELS = NUM_ACTIVE_LEDS // 3
    
    MODEL_RADIUS = MODEL_DIAMETER / 2.0
    SCREEN_WIDTH, SCREEN_HEIGHT = VIEW_WIDTH * 2, VIEW_HEIGHT
    WORLD_RADIUS = 350
    DEBUG_MIN_BIRD_SIZE_PX = 6.0
    MAGIC_BYTE = 0x7E
    
    print("Loaded runtime settings from 'settings.yaml'")
    if ENABLE_TEST_MODE:
        print(f"--- RUNNING IN TEST MODE ---")
        print(f"Using {NUM_TEST_STRIP_LEDS} LEDs = {NUM_ACTIVE_PIXELS} Pixels.")


except Exception as e:
    print(f"FATAL: Error loading settings from 'settings.yaml'. Error: {e}")
    exit()

class SerialWriterThread(threading.Thread):
    def __init__(self, port, baudrate):
        super().__init__(daemon=True)
        self.port, self.baudrate = port, baudrate
        self.ser, self.queue, self.running = None, queue.Queue(maxsize=2), False

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1, write_timeout=1)
            print(f"Successfully connected to Arduino on {self.port}")
            time.sleep(2)
            return True
        except serial.SerialException as e:
            print(f"FATAL: Could not connect to Arduino: {e}"); return False

    def run(self):
        self.running = True
        if not self.connect(): self.running = False; return
        while self.running:
            try:
                colors = self.queue.get(timeout=1)
                packet = bytearray([MAGIC_BYTE]) + colors.astype(np.uint8).tobytes()
                if self.ser and self.ser.is_open: self.ser.write(packet); self.ser.flush()
            except queue.Empty: continue
            except Exception as e: print(f"Serial thread error: {e}"); self.running = False
        if self.ser and self.ser.is_open: self.ser.close()
        print("Serial thread stopped.")

    def send(self, data):
        if not self.running: return
        if self.queue.full():
            try: self.queue.get_nowait()
            except queue.Empty: pass
        self.queue.put(data)

    def close(self):
        print("Stopping serial thread..."); self.running = False

def model_to_view(pos_m):
    return pos_m * (WORLD_RADIUS / MODEL_RADIUS) + np.array([VIEW_WIDTH / 2, VIEW_HEIGHT / 2])
def view_to_model(pos_px):
    return (np.array(pos_px) - np.array([VIEW_WIDTH / 2, VIEW_HEIGHT / 2])) / (WORLD_RADIUS / MODEL_RADIUS)

def main_realtime():
    pygame.init(); pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    debug_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    art_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    pygame.display.set_caption("Left: Debug View | Right: Artistic View (Synced to Physical Pixels)")
    clock = pygame.time.Clock()
    
    serial_thread = SerialWriterThread(SERIAL_PORT, BAUD_RATE)
    serial_thread.start()

    try:
        # ▼▼▼【変更点 2/6】LED座標をピクセル座標に変換する処理を追加 ▼▼▼
        all_led_positions = np.loadtxt(LED_FILE_PATH, delimiter=',', skiprows=1)
        # アクティブなピクセル数だけ座標を生成
        pixel_model_positions = np.array([np.mean(all_led_positions[i*3:(i+1)*3], axis=0) for i in range(NUM_ACTIVE_PIXELS)])
        pixel_view_positions = np.apply_along_axis(model_to_view, 1, pixel_model_positions)

    except Exception as e:
        print(f"FATAL: Could not load LED data from '{LED_FILE_PATH}'. Error: {e}"); serial_thread.close(); return
    
    human = Human()
    bird_objects = [Bird(bird_id, BIRD_PARAMS[bird_id], CHIRP_PROBABILITY_PER_FRAME) for bird_id in BIRDS_TO_SIMULATE if bird_id in BIRD_PARAMS]
    world = World(MODEL_RADIUS, human, bird_objects)
    
    static_background = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    static_background.fill((25, 28, 35))
    pygame.draw.circle(static_background, (20, 40, 80), (VIEW_WIDTH // 2, VIEW_HEIGHT // 2), WORLD_RADIUS)
    for pos_px in pixel_view_positions:
        pygame.draw.circle(static_background, (50, 50, 50), pos_px, 2)
        
    print("Starting real-time simulation and LED output...")
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
        
        mouse_pos = pygame.mouse.get_pos()
        if 0 <= mouse_pos[0] < VIEW_WIDTH:
            world.human.update_position(view_to_model(mouse_pos))
        
        world.update()

        # ▼▼▼【変更点 3/6】全ての配列をピクセル数(NUM_ACTIVE_PIXELS)で初期化 ▼▼▼
        final_pixel_colors = np.zeros((NUM_ACTIVE_PIXELS, 3), dtype=int)
        brightness_map = np.zeros(NUM_ACTIVE_PIXELS, dtype=float)
        winner_map = np.full(NUM_ACTIVE_PIXELS, -1, dtype=int)
        
        # 鳥の最近傍ピクセルのインデックスを計算
        pixel_centers = [np.argmin(np.linalg.norm(pixel_model_positions - bird.position, axis=1)) for bird in world.birds]

        for i, bird in enumerate(world.birds):
            center_idx = pixel_centers[i]
            _, num_pixels_pattern = bird.get_current_light_pattern()
            spread = num_pixels_pattern // 2
            brightness = 0.6
            if bird.state == "CHIRPING": brightness = bird.current_brightness
            elif bird.state == "FLEEING": brightness = 1.0

            for j in range(-spread, spread + 1):
                pixel_idx = center_idx + j
                if 0 <= pixel_idx < NUM_ACTIVE_PIXELS:
                    falloff = (spread - abs(j)) / spread if spread > 0 else 1.0
                    final_brightness = brightness * falloff
                    if final_brightness > brightness_map[pixel_idx]:
                        brightness_map[pixel_idx], winner_map[pixel_idx] = final_brightness, i

        for pixel_idx in range(NUM_ACTIVE_PIXELS):
            bird_idx = winner_map[pixel_idx]
            if bird_idx != -1:
                bird = world.birds[bird_idx]
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

        # ▼▼▼【変更点 4/6】シリアル送信ロジックの簡略化 ▼▼▼
        # `final_pixel_colors`は既に正しいピクセル数のデータなので、そのまま送信する
        # [::3]スライスは完全に不要になった
        serial_thread.send(final_pixel_colors)
        
        # デバッグビューの描画 (変更なし)
        debug_surface.blit(static_background, (0, 0))
        for bird in world.birds:
            pos_px = model_to_view(bird.position)
            size_px = max(bird.params['size'] * 2.5, DEBUG_MIN_BIRD_SIZE_PX)
            pygame.draw.circle(debug_surface, bird.base_color, pos_px, size_px)
            pygame.draw.circle(debug_surface, bird.accent_color, pos_px, size_px * 0.4)
        pygame.draw.circle(debug_surface, (255, 255, 255), model_to_view(world.human.position), 10)
        
        # ▼▼▼【変更点 5/6】アーティスティックビューを物理的な見た目に合わせる ▼▼▼
        art_surface.fill((5, 8, 15))
        pygame.draw.circle(art_surface, (20, 40, 80), (VIEW_WIDTH // 2, VIEW_HEIGHT // 2), WORLD_RADIUS)
        for i, pos_px in enumerate(pixel_view_positions):
            # `final_pixel_colors`を参照するように変更
            if np.any(final_pixel_colors[i] > 5):
                # 円を大きく(radius=4)描画
                pygame.draw.circle(art_surface, final_pixel_colors[i], pos_px, 4)
        
        # ▼▼▼【変更点 6/6】両方のビューを正しく描画するように修正 (元のコードの軽微なバグ修正) ▼▼▼
        screen.blit(debug_surface, (0, 0))
        screen.blit(art_surface, (VIEW_WIDTH, 0))
        
        pygame.display.flip()
        clock.tick(60)

    serial_thread.close(); serial_thread.join(); pygame.quit()
    print("Simulation finished.")

if __name__ == '__main__':
    main_realtime()