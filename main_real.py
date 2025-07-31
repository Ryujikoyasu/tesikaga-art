
import pygame
import numpy as np
import serial
import time
import os
import yaml
import threading
import queue
from src.config import BIRD_PARAMS
from src.objects import Human, Bird
from src.simulation import World
from src.renderer import Renderer
from src.input_source import MouseInputSource, UdpInputSource

# --- Load all settings from settings.yaml ---
try:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    SETTINGS_PATH = os.path.join(PROJECT_ROOT, "settings.yaml")
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        settings = yaml.safe_load(f)
    
    # Hardware and layout
    SERIAL_PORT = settings['serial_port']
    BAUD_RATE = settings['baud_rate']
    LED_FILE_NAME = settings['led_layout_file']
    LED_FILE_PATH = os.path.join(PROJECT_ROOT, "assets", "data", LED_FILE_NAME)
    NUM_LEDS = settings['num_leds']
    MODEL_DIAMETER = settings['model_diameter']
    MODEL_RADIUS = MODEL_DIAMETER / 2.0

    # Test mode settings
    ENABLE_TEST_MODE = settings.get('enable_test_mode', False)
    NUM_TEST_STRIP_LEDS = settings.get('test_strip_led_count', 100)
    NUM_ACTIVE_LEDS = NUM_TEST_STRIP_LEDS if ENABLE_TEST_MODE else NUM_LEDS
    NUM_ACTIVE_PIXELS = NUM_ACTIVE_LEDS // 3

    # Simulation and AI
    BIRDS_TO_SIMULATE = settings.get('birds_to_simulate', [])
    AI_TUNING = settings.get('ai_tuning', {})
    CHIRP_PROBABILITY_PER_FRAME = AI_TUNING.get('chirp_probability_per_frame', 0.001)

    # Visuals
    VIEW_WIDTH = settings.get('view_width', 800)
    VIEW_HEIGHT = settings.get('view_height', 800)
    SCREEN_WIDTH, SCREEN_HEIGHT = VIEW_WIDTH * 2, VIEW_HEIGHT

    # Protocol
    MAGIC_BYTE = 0x7E
    
    # Input Source
    INPUT_SOURCE_TYPE = settings.get('input_source_type', 'mouse')
    UDP_SETTINGS = settings.get('udp_settings', {})
    
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

# --- Helper Functions (Coordinate Conversion) ---
def model_to_view(pos_m, world_radius, model_radius, view_size):
    return pos_m * (world_radius / model_radius) + np.array([view_size[0] / 2, view_size[1] / 2])

def view_to_model(pos_px, world_radius, model_radius, view_size):
    return (np.array(pos_px) - np.array([view_size[0] / 2, view_size[1] / 2])) / (world_radius / model_radius)

def main_realtime():
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Left: Debug View | Right: Artistic View (Synced to Physical Pixels)")
    clock = pygame.time.Clock()
    
    serial_thread = SerialWriterThread(SERIAL_PORT, BAUD_RATE)
    serial_thread.start()

    # --- Data and Object Initialization ---
    try:
        all_led_positions = np.loadtxt(LED_FILE_PATH, delimiter=',', skiprows=1)
        pixel_model_positions = np.array([np.mean(all_led_positions[i*3:(i+1)*3], axis=0) for i in range(NUM_ACTIVE_PIXELS)])
        pixel_view_positions = np.array([model_to_view(p, 350, MODEL_RADIUS, (VIEW_WIDTH, VIEW_HEIGHT)) for p in pixel_model_positions])

    except Exception as e:
        print(f"FATAL: Could not load LED data from '{LED_FILE_PATH}'. Error: {e}")
        serial_thread.close()
        return
    
    if INPUT_SOURCE_TYPE == 'udp':
        input_source = UdpInputSource(host=UDP_SETTINGS.get('host', '0.0.0.0'), port=UDP_SETTINGS.get('port', 9999))
    elif INPUT_SOURCE_TYPE == 'mouse':
        input_source = MouseInputSource(lambda pos: view_to_model(pos, 350, MODEL_RADIUS, (VIEW_WIDTH, VIEW_HEIGHT)))
    else:
        print(f"FATAL: Unknown input_source_type '{INPUT_SOURCE_TYPE}' in settings.yaml. Exiting.")
        return

    bird_objects = [Bird(bird_id, BIRD_PARAMS[bird_id], CHIRP_PROBABILITY_PER_FRAME) for bird_id in BIRDS_TO_SIMULATE if bird_id in BIRD_PARAMS]
    world = World(MODEL_RADIUS, bird_objects)
    
    renderer = Renderer(settings, pixel_model_positions, pixel_view_positions)
    
    print("Starting real-time simulation and LED output...")
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Get human positions from the selected input source
        human_positions = input_source.get_human_positions()

        # Update the world with the list of humans
        world.update_humans(human_positions)
        
        # Update the main world simulation
        world.update(pixel_model_positions)

        # Render the views
        renderer.render(screen, world)

        # Send the latest colors to the hardware
        final_colors = renderer.get_final_colors()
        serial_thread.send(final_colors)
        
        clock.tick(60)

    input_source.shutdown()
    serial_thread.close()
    serial_thread.join()
    pygame.quit()
    print("Simulation finished.")

if __name__ == '__main__':
    main_realtime()
