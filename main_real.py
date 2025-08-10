
import pygame
import numpy as np
import os
import yaml
from src.config import BIRD_PARAMS
from src.objects import Bird
from src.simulation import World
from src.renderer import Renderer
from src.input_source import MouseInputSource, UdpInputSource
from src.serial_handler import SerialWriterThread
from src.coordinates import CoordinateSystem

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

def main_realtime():
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Left: Debug View | Right: Artistic View (Synced to Physical Pixels)")
    clock = pygame.time.Clock()
    
    serial_thread = SerialWriterThread(SERIAL_PORT, BAUD_RATE, MAGIC_BYTE, NUM_ACTIVE_PIXELS)
    serial_thread.start()

    # --- Coordinate System ---
    coord_system = CoordinateSystem(view_size=(VIEW_WIDTH, VIEW_HEIGHT), model_radius=MODEL_RADIUS)

    # --- Data and Object Initialization ---
    try:
        all_led_positions = np.loadtxt(LED_FILE_PATH, delimiter=',', skiprows=1)
        pixel_model_positions = np.array([np.mean(all_led_positions[i*3:(i+1)*3], axis=0) for i in range(NUM_ACTIVE_PIXELS)])

    except Exception as e:
        print(f"FATAL: Could not load LED data from '{LED_FILE_PATH}'. Error: {e}")
        serial_thread.close()
        return
    
    if INPUT_SOURCE_TYPE == 'udp':
        input_source = UdpInputSource(host=UDP_SETTINGS.get('host', '0.0.0.0'), port=UDP_SETTINGS.get('port', 9999))
    elif INPUT_SOURCE_TYPE == 'mouse':
        input_source = MouseInputSource(coord_system.view_to_model)
    else:
        print(f"FATAL: Unknown input_source_type '{INPUT_SOURCE_TYPE}' in settings.yaml. Exiting.")
        return

    bird_objects = [Bird(bird_id, BIRD_PARAMS[bird_id], CHIRP_PROBABILITY_PER_FRAME) for bird_id in BIRDS_TO_SIMULATE if bird_id in BIRD_PARAMS]
    world = World(MODEL_RADIUS, bird_objects)
    
    # --- ★LiDARの姿勢情報を読み込む ---
    lidar_pose_data = None
    transform_matrix_path = settings.get('transform_matrix_path')
    if transform_matrix_path:
        try:
            # settings.yamlからのパスが相対パスの場合も考慮し、プロジェクトルートからの絶対パスに変換
            TRANSFORM_PATH = os.path.join(PROJECT_ROOT, transform_matrix_path)
            with open(TRANSFORM_PATH, 'r') as f:
                transform_data = yaml.safe_load(f)
                if 'lidar_pose' in transform_data:
                    lidar_pose_data = transform_data['lidar_pose']
                    print(f"Loaded LiDAR pose data for visualization from '{TRANSFORM_PATH}'.")
        except Exception as e:
            print(f"Warning: Could not load LiDAR pose data from '{TRANSFORM_PATH}'. Visualization will be skipped. Error: {e}")
    else:
        print("Info: 'transform_matrix_path' not found in settings.yaml. Skipping LiDAR pose visualization.")

    # Rendererの初期化時に、読み込んだ姿勢データを渡す
    renderer = Renderer(settings, pixel_model_positions, coord_system, lidar_pose_data)
    
    print("Starting real-time simulation and LED output...")
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Get raw detected objects from the selected input source
        detected_objects = input_source.get_detected_objects()

        # Update the world with the raw data, which will handle object tracking
        world.update_humans(detected_objects)
        
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
