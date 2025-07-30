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

    NUM_PIXELS = NUM_LEDS // 3
    NUM_TEST_STRIP_PIXELS = NUM_TEST_STRIP_LEDS // 3
    MODEL_RADIUS = MODEL_DIAMETER / 2.0
    SCREEN_WIDTH, SCREEN_HEIGHT = VIEW_WIDTH * 2, VIEW_HEIGHT
    WORLD_RADIUS = 350
    DEBUG_MIN_BIRD_SIZE_PX = 6.0
    MAGIC_BYTE = 0x7E
    
    print("Loaded runtime settings from 'settings.yaml'")

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
    pygame.display.set_caption("Left: Debug View | Right: Artistic View (Real-time to Arduino)")
    clock = pygame.time.Clock()
    
    serial_thread = SerialWriterThread(SERIAL_PORT, BAUD_RATE)
    serial_thread.start()

    try:
        all_led_positions = np.loadtxt(LED_FILE_PATH, delimiter=',', skiprows=1)
    except Exception as e:
        print(f"FATAL: Could not load LED data from '{LED_FILE_PATH}'. Error: {e}"); serial_thread.close(); return

    num_active_leds = NUM_TEST_STRIP_LEDS if ENABLE_TEST_MODE else NUM_LEDS
    led_model_positions = all_led_positions[:num_active_leds]
    led_view_positions = np.apply_along_axis(model_to_view, 1, led_model_positions)
    
    human = Human()
    bird_objects = [Bird(bird_id, BIRD_PARAMS[bird_id], CHIRP_PROBABILITY_PER_FRAME) for bird_id in BIRDS_TO_SIMULATE if bird_id in BIRD_PARAMS]
    world = World(MODEL_RADIUS, human, bird_objects)
    
    static_background = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    static_background.fill((25, 28, 35))
    pygame.draw.circle(static_background, (20, 40, 80), (VIEW_WIDTH // 2, VIEW_HEIGHT // 2), WORLD_RADIUS)
    for pos_px in led_view_positions:
        pygame.draw.circle(static_background, (50, 50, 50), pos_px, 1)
        
    print("Starting real-time simulation and LED output...")
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
        
        mouse_pos = pygame.mouse.get_pos()
        if 0 <= mouse_pos[0] < VIEW_WIDTH:
            world.human.update_position(view_to_model(mouse_pos))
        
        world.update()

        final_led_colors = np.zeros((num_active_leds, 3), dtype=int)
        brightness_map = np.zeros(num_active_leds, dtype=float)
        winner_map = np.full(num_active_leds, -1, dtype=int)
        bird_centers = [np.argmin(np.linalg.norm(led_model_positions - bird.position, axis=1)) for bird in world.birds]

        for i, bird in enumerate(world.birds):
            center_idx = bird_centers[i]
            _, num_pixels = bird.get_current_light_pattern()
            spread = (num_pixels * 3) // 2
            brightness = 0.6
            if bird.state == "CHIRPING": brightness = bird.current_brightness
            elif bird.state == "FLEEING": brightness = 1.0

            for j in range(-spread, spread + 1):
                led_idx = center_idx + j
                if 0 <= led_idx < num_active_leds:
                    falloff = (spread - abs(j)) / spread if spread > 0 else 1.0
                    final_brightness = brightness * falloff
                    if final_brightness > brightness_map[led_idx]:
                        brightness_map[led_idx], winner_map[led_idx] = final_brightness, i

        for led_idx in range(num_active_leds):
            bird_idx = winner_map[led_idx]
            if bird_idx != -1:
                bird = world.birds[bird_idx]
                pixel_offset = (led_idx - bird_centers[bird_idx]) // 3
                pattern, _ = bird.get_current_light_pattern()
                total_pixels = sum(p[1] for p in pattern)
                if total_pixels > 0:
                    color_type, start_pixel = 'b', -total_pixels // 2
                    for p_type, p_count in pattern:
                        if start_pixel <= pixel_offset < start_pixel + p_count:
                            color_type = p_type; break
                        start_pixel += p_count
                    color = bird.accent_color if color_type == 'a' else bird.base_color
                    final_led_colors[led_idx] = np.clip(color * brightness_map[led_idx], 0, 255)

        pixels_to_send = final_led_colors[::3]
        target_pixel_count = NUM_TEST_STRIP_PIXELS if ENABLE_TEST_MODE else NUM_PIXELS
        if len(pixels_to_send) != target_pixel_count:
            current_len = len(pixels_to_send)
            if current_len > target_pixel_count:
                pixels_to_send = pixels_to_send[:target_pixel_count]
            else:
                padding = np.zeros((target_pixel_count - current_len, 3), dtype=int)
                pixels_to_send = np.vstack([pixels_to_send, padding]) if current_len > 0 else padding
        serial_thread.send(pixels_to_send)
        
        debug_surface.blit(static_background, (0, 0))
        for bird in world.birds:
            pos_px = model_to_view(bird.position)
            size_px = max(bird.params['size'] * 2.5, DEBUG_MIN_BIRD_SIZE_PX)
            pygame.draw.circle(debug_surface, bird.base_color, pos_px, size_px)
            pygame.draw.circle(debug_surface, bird.accent_color, pos_px, size_px * 0.4)
        pygame.draw.circle(debug_surface, (255, 255, 255), model_to_view(world.human.position), 10)
        
        art_surface.fill((5, 8, 15))
        pygame.draw.circle(art_surface, (20, 40, 80), (VIEW_WIDTH // 2, VIEW_HEIGHT // 2), WORLD_RADIUS)
        for i, pos_px in enumerate(led_view_positions):
            if np.any(final_led_colors[i] > 5):
                pygame.draw.circle(art_surface, final_led_colors[i], pos_px, 2)
        
        # ▼▼▼【修正】両方のビューを正しく描画するように修正 ▼▼▼
        screen.blit(debug_surface, (0, 0))
        screen.blit(art_surface, (VIEW_WIDTH, 0))
        # ▲▲▲
        
        pygame.display.flip()
        clock.tick(60)

    serial_thread.close(); serial_thread.join(); pygame.quit()
    print("Simulation finished.")

if __name__ == '__main__':
    main_realtime()