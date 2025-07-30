# main_real.py
# This script runs the simulation, displays it, and sends the results to an Arduino.
# Optimized for performance with non-blocking, threaded serial communication.

import pygame
import numpy as np
import serial
import time
import os
import yaml
import threading
import queue
from src.config import *
from src.objects import Human, Bird

# --- settings.yaml からハードウェア設定を読み込む ---
try:
    SETTINGS_PATH = os.path.join(PROJECT_ROOT, "settings.yaml")
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        settings = yaml.safe_load(f)
    
    SERIAL_PORT = settings['serial_port']
    BAUD_RATE = settings['baud_rate']
    print(f"Loaded hardware settings from '{os.path.basename(SETTINGS_PATH)}'")
    print(f"  - Serial Port: {SERIAL_PORT}")
    print(f"  - Baud Rate:   {BAUD_RATE}")

except FileNotFoundError:
    print(f"FATAL: Settings file not found at '{SETTINGS_PATH}'")
    exit()
except KeyError as e:
    print(f"FATAL: Missing required key in '{os.path.basename(SETTINGS_PATH)}': {e}")
    exit()
except Exception as e:
    print(f"FATAL: Error reading or parsing settings.yaml: {e}")
    exit()

MAGIC_BYTE = 0x7E
DEBUG_MIN_BIRD_SIZE_PX = 6.0

class SerialWriterThread(threading.Thread):
    """Manages serial communication in a separate, non-blocking thread."""
    def __init__(self, port, baudrate):
        super().__init__(daemon=True)
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.queue = queue.Queue(maxsize=2)
        self.running = False

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1, write_timeout=1)
            print(f"Successfully connected to Arduino on {self.port}")
            time.sleep(2)
            return True
        except serial.SerialException as e:
            print(f"FATAL: Could not connect to Arduino on {self.port}. Error: {e}")
            return False

    def run(self):
        """The main loop for the serial writing thread."""
        self.running = True
        if not self.connect():
            self.running = False
            return
            
        while self.running:
            try:
                colors_to_send = self.queue.get(timeout=1)
                
                data_bytes = colors_to_send.astype(np.uint8).tobytes()
                packet = bytearray([MAGIC_BYTE]) + data_bytes
                
                if self.ser and self.ser.is_open:
                    self.ser.write(packet)
                    self.ser.flush()
            except queue.Empty:
                continue
            except serial.SerialException as e:
                print(f"Error during serial write: {e}")
                self.running = False
            except Exception as e:
                print(f"An unexpected error occurred in SerialWriterThread: {e}")
                self.running = False

        if self.ser and self.ser.is_open:
            self.ser.close()
        print("Serial thread stopped.")

    def send(self, data):
        """Puts data into the queue for the thread to send."""
        if not self.running: return
        if self.queue.full():
            try: self.queue.get_nowait()
            except queue.Empty: pass
        self.queue.put(data)

    def close(self):
        """Safely stops the thread."""
        print("Stopping serial thread...")
        self.running = False

def model_to_view(pos_m):
    scale = WORLD_RADIUS / MODEL_RADIUS
    view_center = np.array([VIEW_WIDTH / 2, VIEW_HEIGHT / 2])
    return pos_m * scale + view_center

def view_to_model(pos_px):
    scale = WORLD_RADIUS / MODEL_RADIUS
    view_center = np.array([VIEW_WIDTH / 2, VIEW_HEIGHT / 2])
    return (np.array(pos_px) - view_center) / scale

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
        all_led_model_positions = np.loadtxt(LED_FILE_PATH, delimiter=',', skiprows=1)
    except Exception as e:
        print(f"FATAL: Could not load LED data from '{LED_FILE_PATH}'. Error: {e}"); serial_thread.close(); return
    
    num_active_leds = NUM_TEST_STRIP_LEDS if ENABLE_TEST_MODE else NUM_LEDS
    led_model_positions = all_led_model_positions[:num_active_leds]
    led_view_positions = np.apply_along_axis(model_to_view, 1, led_model_positions)
    
    human = Human()
    birds = [Bird(bird_id, BIRD_PARAMS[bird_id]) for bird_id in BIRDS_TO_SIMULATE if bird_id in BIRD_PARAMS]
    
    static_background_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    static_background_surface.fill((25, 28, 35))
    pond_center_px = (VIEW_WIDTH // 2, VIEW_HEIGHT // 2)
    pygame.draw.circle(static_background_surface, (20, 40, 80), pond_center_px, WORLD_RADIUS)
    for led_pos_px in led_view_positions:
        pygame.draw.circle(static_background_surface, (50, 50, 50), (int(led_pos_px[0]), int(led_pos_px[1])), 1)

    print("Starting real-time simulation and LED output...")
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
        
        mouse_pos = pygame.mouse.get_pos()
        if 0 <= mouse_pos[0] < VIEW_WIDTH and 0 <= mouse_pos[1] < VIEW_HEIGHT:
            human.update_position(view_to_model(mouse_pos))
        
        for bird in birds: bird.update(human, birds)

        final_led_colors_view = np.zeros((num_active_leds, 3), dtype=int)
        brightness_map = np.zeros(num_active_leds, dtype=float)
        winner_map = np.full(num_active_leds, -1, dtype=int)
        
        bird_centers = [np.argmin(np.linalg.norm(led_model_positions - bird.position, axis=1)) for bird in birds]

        for i, bird in enumerate(birds):
            center_led_index = bird_centers[i]
            current_pattern, num_pixels = bird.get_current_light_pattern()
            num_physical_leds = num_pixels * 3
            spread = num_physical_leds // 2

            brightness = 0.6
            if bird.state == "CHIRPING": brightness = bird.current_brightness
            elif bird.state == "FLEEING": brightness = 1.0

            for j in range(-spread, spread + 1):
                led_idx = center_led_index + j
                if 0 <= led_idx < num_active_leds:
                    falloff = (spread - abs(j)) / spread if spread > 0 else 1.0
                    final_brightness = brightness * falloff
                    
                    if final_brightness > brightness_map[led_idx]:
                        brightness_map[led_idx] = final_brightness
                        winner_map[led_idx] = i

        for led_idx in range(num_active_leds):
            bird_idx = winner_map[led_idx]
            if bird_idx != -1:
                bird = birds[bird_idx]
                brightness = brightness_map[led_idx]
                center_led_index = bird_centers[bird_idx]
                physical_offset = led_idx - center_led_index
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

        debug_surface.blit(static_background_surface, (0, 0))
        for bird in birds:
            bird_pos_px = model_to_view(bird.position)
            size_px = max(bird.params['size'] * 2.5, DEBUG_MIN_BIRD_SIZE_PX)
            pygame.draw.circle(debug_surface, bird.base_color, (int(bird_pos_px[0]), int(bird_pos_px[1])), int(size_px))
            pygame.draw.circle(debug_surface, bird.accent_color, (int(bird_pos_px[0]), int(bird_pos_px[1])), int(size_px * 0.4))
        
        human_pos_px = model_to_view(human.position)
        pygame.draw.circle(debug_surface, (255, 255, 255), (int(human_pos_px[0]), int(human_pos_px[1])), 10)
        
        art_surface.fill((5, 8, 15))
        pygame.draw.circle(art_surface, (20, 40, 80), pond_center_px, WORLD_RADIUS)
        for i, pos_px in enumerate(led_view_positions):
            if np.any(final_led_colors_view[i] > 5):
                pygame.draw.circle(art_surface, final_led_colors_view[i], (int(pos_px[0]), int(pos_px[1])), 2)

        pixels_to_send = final_led_colors_view[::3]
        target_pixel_count = NUM_TEST_STRIP_PIXELS if ENABLE_TEST_MODE else NUM_PIXELS

        if len(pixels_to_send) > target_pixel_count:
            pixels_to_send = pixels_to_send[:target_pixel_count]
        elif len(pixels_to_send) < target_pixel_count:
            padding = np.zeros((target_pixel_count - len(pixels_to_send), 3), dtype=int)
            pixels_to_send = np.vstack([pixels_to_send, padding])

        serial_thread.send(pixels_to_send)
        
        screen.blit(debug_surface, (0, 0)); screen.blit(art_surface, (VIEW_WIDTH, 0))
        pygame.display.flip()
        clock.tick(60)

    serial_thread.close()
    serial_thread.join()
    pygame.quit()
    print("Simulation finished.")

if __name__ == '__main__':
    main_realtime()