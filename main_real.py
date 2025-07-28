### シミュレーションとシリアル通信を行う。
import pygame
import csv
import numpy as np
import serial
import time
from src.config import *
from src.objects import Human, Bird

# --- Serial Communication Settings ---
# シリアルポート名は、お使いの環境に合わせて変更してください。
# Macの場合: "/dev/tty.usbmodemXXXX" や "/dev/tty.usbserial-XXXX" のような名前です。
# Arduino IDEの「ツール > ポート」で確認できる名前と同じものを指定します。
SERIAL_PORT = "/dev/tty.usbmodem14201" # <<< 要変更
BAUD_RATE = 230400
MAGIC_BYTE = b'\xAB'

# LEDテープ1本分のLEDの数を定義 (900個 / 3セグメント)
LEDS_PER_STRIP = 300

class LedController:
    """Handles serial communication with the microcontroller."""
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Successfully connected to {self.port} at {self.baudrate} bps.")
            time.sleep(2) # Wait for ESP32 to reboot
        except serial.SerialException as e:
            print(f"FATAL: Could not open serial port '{self.port}'. Error: {e}")
            print("Please check the port name and ensure the device is connected.")

    def send_colors(self, colors):
        """Sends the color data to the microcontroller."""
        if not self.ser: return
        
        try:
            # Flatten the numpy array and convert to bytes
            byte_data = colors.astype(np.uint8).flatten().tobytes()
            
            # Send the magic byte header + the color data
            self.ser.write(MAGIC_BYTE)
            self.ser.write(byte_data)
            self.ser.flush() # Ensure data is sent immediately
        except serial.SerialException as e:
            print(f"ERROR: Could not write to serial port. {e}")
            self.ser = None # Stop trying to send

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial port closed.")

def main():
    # --- Initialization ---
    led_controller = LedController(SERIAL_PORT, BAUD_RATE)
    if not led_controller.ser: return # Exit if connection failed

    pygame.init()
    screen = pygame.display.set_mode((VIEW_WIDTH, VIEW_HEIGHT)) # Only debug view
    pygame.display.set_caption("Debug View (Real LEDs should be active)")
    clock = pygame.time.Clock()

    try:
        led_model_positions = np.loadtxt(LED_FILE_PATH, delimiter=',', skiprows=1)
    except Exception as e:
        print(f"FATAL: Could not load LED data from '{LED_FILE_PATH}'. Error: {e}"); return
    
    led_view_positions = np.apply_along_axis(model_to_view, 1, led_model_positions)
    num_total_leds = len(led_view_positions)

    human = Human()
    birds = [Bird(bird_id, BIRD_PARAMS[bird_id]) for bird_id in BIRDS_TO_SIMULATE if bird_id in BIRD_PARAMS]

    try:
        running = True
        while running:
            # --- Event & Update Logic (same as main.py) ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False

            human.update_position(view_to_model(pygame.mouse.get_pos()))
            for bird in birds: bird.update(human, birds)

            # --- Calculation Logic (same as main.py) ---
            led_color_array = np.zeros((num_total_leds, 3), dtype=float)
            led_brightness_buffer = np.zeros(num_total_leds, dtype=float)
            for bird in birds:
                distances_m = np.linalg.norm(led_model_positions - bird.position, axis=1)
                center_led_index = np.argmin(distances_m)
                bird_light_colors, bird_light_brightness = calculate_bird_light(bird, center_led_index, num_total_leds)
                update_mask = bird_light_brightness > led_brightness_buffer
                led_color_array[update_mask] = bird_light_colors[update_mask]
                led_brightness_buffer[update_mask] = bird_light_brightness[update_mask]

            final_led_colors = np.clip(led_color_array, 0, 255)
            
            # --- NEW: Send data to physical LEDs ---
            # 最初のセグメント(300個)のデータだけをスライスして送信
            colors_for_strip1 = final_led_colors[:LEDS_PER_STRIP]
            led_controller.send_colors(colors_for_strip1)

            # --- Draw Debug View (Artistic view is now the real world!) ---
            screen.fill((25, 28, 35))
            pygame.draw.circle(screen, (20, 40, 80), (VIEW_WIDTH // 2, VIEW_HEIGHT // 2), WORLD_RADIUS)
            pygame.draw.lines(screen, (70, 70, 80), False, led_view_positions, 1)

            # Highlight the segment being sent to the real LEDs
            pygame.draw.lines(screen, (255, 255, 0), False, led_view_positions[:LEDS_PER_STRIP], 3)
            
            for bird in birds:
                pos_px = model_to_view(bird.position)
                pygame.draw.circle(screen, bird.params['led_color'], (int(pos_px[0]), int(pos_px[1])), 5)
            
            human_pos_px = model_to_view(human.position)
            pygame.draw.circle(screen, (255, 255, 255), (int(human_pos_px[0]), int(human_pos_px[1])), 10)

            pygame.display.flip()
            clock.tick(60)
            
    finally:
        # Ensure the serial port is closed cleanly on exit
        led_controller.close()
        pygame.quit()

if __name__ == '__main__':
    # このスクリプトは他の関数をインポートしているので、
    # main()を直接呼び出す前に、必要な関数が読み込まれていることを確認してください。
    # (この構造なら問題ありません)
    from main import model_to_view, view_to_model, calculate_bird_light # This assumes these functions are still in a main.py
    main()