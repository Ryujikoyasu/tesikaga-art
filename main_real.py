# main_real.py
# This script runs the simulation and sends the results to an Arduino via serial.

import pygame
import numpy as np
import serial
import time
from src.config import *
from src.objects import Human, Bird

# --- Serial Port Settings ---
SERIAL_PORT = '/dev/ttyACM0'  # Adjust for your environment (e.g., COM3 on Windows)
BAUD_RATE = 115200
MAGIC_BYTE = 0x7E

class SerialController:
    """Manages serial communication with the Arduino."""
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Successfully connected to Arduino on {self.port}")
            time.sleep(2) # Wait for Arduino to reset
        except serial.SerialException as e:
            print(f"FATAL: Could not connect to Arduino on {self.port}. Error: {e}")
            print("Please check the port, permissions, and physical connection.")

    def send_colors(self, colors_to_send):
        """Sends an array of color data to the Arduino."""
        if not self.ser or not self.ser.is_open:
            return

        data_bytes = colors_to_send.astype(np.uint8).tobytes()
        packet = bytearray([MAGIC_BYTE]) + data_bytes
        
        try:
            self.ser.write(packet)
            self.ser.flush()
        except serial.SerialException as e:
            print(f"Error writing to serial port: {e}")
            self.close()

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"Disconnected from {self.port}")

def view_to_model(pos_px):
    """Converts view pixels to model meters."""
    scale = WORLD_RADIUS / MODEL_RADIUS
    view_center = np.array([VIEW_WIDTH / 2, VIEW_HEIGHT / 2])
    return (np.array(pos_px) - view_center) / scale

def main_realtime():
    pygame.init(); pygame.mixer.init()
    clock = pygame.time.Clock()

    serial_controller = SerialController(SERIAL_PORT, BAUD_RATE)
    if not serial_controller.ser: return

    try:
        all_led_model_positions = np.loadtxt(LED_FILE_PATH, delimiter=',', skiprows=1)
    except Exception as e:
        print(f"FATAL: Could not load LED data from '{LED_FILE_PATH}'. Error: {e}"); serial_controller.close(); return
    
    # Use the number of LEDs specified in the config, truncating if the CSV is larger.
    led_model_positions = all_led_model_positions[:NUM_LEDS]
    human = Human()
    birds = [Bird(bird_id, BIRD_PARAMS[bird_id]) for bird_id in BIRDS_TO_SIMULATE if bird_id in BIRD_PARAMS]
    
    print("Starting real-time simulation and LED output...")
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
        
        # In a real scenario, this would be updated from a LiDAR sensor
        # For now, we use the mouse position for simulation
        mouse_pos = pygame.mouse.get_pos()
        # A simple way to check if the mouse is on the debug view (left side)
        if 0 <= mouse_pos[0] < VIEW_WIDTH and 0 <= mouse_pos[1] < VIEW_HEIGHT:
            human.update_position(view_to_model(mouse_pos))
        
        for bird in birds: bird.update(human, birds)
            
        # --- New LED Color Calculation (same as main.py) ---
        final_led_colors_view = np.zeros((NUM_LEDS, 3), dtype=int) 
        winner_map = np.full(NUM_LEDS, -1, dtype=int)
        brightness_map = np.zeros(NUM_LEDS, dtype=float)

        # 1. Winner-Takes-All based on brightness
        for i, bird in enumerate(birds):
            distances_m = np.linalg.norm(led_model_positions - bird.position, axis=1)
            center_led_index = np.argmin(distances_m)
            
            current_pattern, num_pixels = bird.get_current_light_pattern()
            total_pattern_pixels = sum(p[1] for p in current_pattern)
            if total_pattern_pixels == 0: continue

            brightness = 0.6 # Default brightness
            if bird.state == "CHIRPING": brightness = bird.current_brightness
            elif bird.state == "FLEEING": brightness = 1.0

            num_physical_leds = num_pixels * 3
            spread = num_physical_leds // 2

            for j in range(-spread, spread + 1):
                led_idx = center_led_index + j
                if 0 <= led_idx < NUM_LEDS:
                    falloff = (spread - abs(j)) / spread if spread > 0 else 1.0
                    final_brightness = brightness * falloff
                    
                    if final_brightness > brightness_map[led_idx]:
                        brightness_map[led_idx] = final_brightness
                        winner_map[led_idx] = i

        # 2. Render LED colors based on the winner map and patterns
        for led_idx in range(NUM_LEDS):
            bird_idx = winner_map[led_idx]
            if bird_idx != -1:
                bird = birds[bird_idx]
                brightness = brightness_map[led_idx]
                
                distances_m = np.linalg.norm(led_model_positions - bird.position, axis=1)
                center_led_index = np.argmin(distances_m)
                
                physical_offset = led_idx - center_led_index
                pixel_offset = (physical_offset + 1) // 3

                current_pattern, num_pixels = bird.get_current_light_pattern()
                total_pattern_pixels = sum(p[1] for p in current_pattern)
                
                if total_pattern_pixels > 0:
                    pixel_cursor = 0
                    color_type = 'b'
                    start_pixel = -total_pattern_pixels // 2
                    
                    for p_type, p_count in current_pattern:
                        if start_pixel <= pixel_offset < start_pixel + p_count:
                            color_type = p_type
                            break
                        start_pixel += p_count

                    color = bird.accent_color if color_type == 'a' else bird.base_color
                    final_led_colors_view[led_idx] = np.clip(color * brightness, 0, 255)

        # --- Data Sampling for Arduino ---
        pixels_to_send = final_led_colors_view[::3]
        
        # Ensure the data has the exact size expected by Arduino
        if len(pixels_to_send) > NUM_PIXELS:
            pixels_to_send = pixels_to_send[:NUM_PIXELS]
        elif len(pixels_to_send) < NUM_PIXELS:
            padding = np.zeros((NUM_PIXELS - len(pixels_to_send), 3), dtype=int)
            pixels_to_send = np.vstack([pixels_to_send, padding])

        serial_controller.send_colors(pixels_to_send)

        clock.tick(30)

    serial_controller.close()
    pygame.quit()
    print("Simulation finished.")

if __name__ == '__main__':
    main_realtime()