import pygame

# Screen and World Dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
WORLD_RADIUS = 350  # Pond radius in pixels

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (20, 40, 80) # Deeper pond blue
GRAY = (50, 50, 50) # Darker LED path

# File Paths (using the new proposed structure)
LED_FILE_PATH = "assets/data/led_positions.csv"

# Simulation settings
LED_GRID_SIZE = 20
CHIRP_PROBABILITY = 0.002 # 休憩中に特別な行動をとる確率

# --- NEW: AI Behavior Tuning ---
IDLE_DURATION_RANGE_FRAMES = (120, 300) # 休憩する時間（フレーム数）。2秒〜5秒。
EXPLORE_DISTANCE_RANGE_PIXELS = (100, 300) # 次の目的地までの距離

# --- Bird Personality Parameters ---
BIRD_PARAMS = {
    "ooluri": {
        "name_jp": "オオルリ",
        "led_color": [20, 100, 240], "accent_color": [240, 240, 255], "color_ratio": [8, 2],
        "size": 1.0, "movement_speed": 1.2, "sociability": 0.1,
        "caution_distance": 120.0, "flee_distance": 80.0,
        "sound_files": { "default": "assets/sounds/oruri.mp3" },
        "chirp_pattern": [(0.2, 1.0), (0.4, 0.8), (1.0, 1.0), (1.2, 0.8), (1.8, 1.0)] # (time, brightness)
    },
    "oohakucho": {
        "name_jp": "オオハクチョウ",
        "led_color": [255, 255, 255], "accent_color": [255, 220, 0], "color_ratio": [9, 1],
        "size": 4.0, "movement_speed": 0.4, "sociability": 0.9,
        "caution_distance": 180.0, "flee_distance": 150.0,
        "sound_files": { "default": "assets/sounds/ohakucho.mp3" },
        "chirp_pattern": [(0.3, 1.0), (0.5, 0.5), (1.2, 1.0), (1.4, 0.5)]
    },
    "ojirowasi": {
        "name_jp": "オジロワシ",
        "led_color": [180, 160, 140], "accent_color": [255, 255, 255], "color_ratio": [7, 3],
        "size": 5.0, "movement_speed": 0.3, "sociability": 0.0,
        "caution_distance": 250.0, "flee_distance": 100.0,
        "sound_files": { "default": "assets/sounds/ojirowasi.mp3" },
        "chirp_pattern": [(0.1, 1.2), (0.2, 0.0)] # A single, bright flash
    },
    "shimafukuro": {
        "name_jp": "シマフクロウ",
        "led_color": [80, 70, 60], "accent_color": [120, 110, 100], "color_ratio": [9, 1],
        "size": 4.5, "movement_speed": 0.6, "sociability": 0.0,
        "caution_distance": 300.0, "flee_distance": 250.0,
        "sound_files": { "default": "assets/sounds/simafukuro.mp3" },
        "chirp_pattern": [(0.5, 0.8), (0.7, 0.0), (1.5, 0.8), (1.7, 0.0)] # Deep, slow double pulse
    },
    "kumagera": {
        "name_jp": "クマゲラ",
        "led_color": [20, 20, 20], "accent_color": [255, 0, 0], "color_ratio": [9, 1],
        "size": 1.5, "movement_speed": 1.8, "sociability": 0.1,
        "caution_distance": 150.0, "flee_distance": 100.0,
        "sound_files": { "call": "assets/sounds/kumagera.mp3", "drumming": "assets/sounds/kumagera_drum.mp3"},
        "chirp_pattern": [(0.1, 1.0), (0.2, 1.0), (0.3, 1.0), (0.4, 1.0), (0.5, 1.0)] # Fast drumming
    },
    "tancho": {
        "name_jp": "タンチョウ",
        "led_color": [255, 255, 255], "accent_color": [220, 0, 0], "color_ratio": [8, 2],
        "size": 3.5, "movement_speed": 0.5, "sociability": 0.7,
        "caution_distance": 200.0, "flee_distance": 160.0,
        "sound_files": { "default": "assets/sounds/tancho.mp3" },
        "chirp_pattern": [(0.4, 1.0), (0.8, 0.0), (1.5, 1.0), (1.9, 0.0)]
    },
    "nogoma": {
        "name_jp": "ノゴマ",
        "led_color": [120, 110, 90], "accent_color": [255, 10, 10], "color_ratio": [9, 1],
        "size": 0.8, "movement_speed": 2.0, "sociability": 0.2,
        "caution_distance": 180.0, "flee_distance": 130.0,
        "sound_files": { "default": "assets/sounds/nogoma.mp3" },
        "chirp_pattern": [(0.1, 1.5), (0.15, 0.0)] # A very brief, sharp flash
    },
    "benimashiko": {
        "name_jp": "ベニマシコ",
        "led_color": [220, 40, 80], "accent_color": [139, 69, 19], "color_ratio": [7, 3],
        "size": 0.9, "movement_speed": 1.9, "sociability": 0.8,
        "caution_distance": 200.0, "flee_distance": 190.0,
        "sound_files": { "default": "assets/sounds/benimasiko.mp3" },
        "chirp_pattern": [(0.2, 0.9), (0.4, 0.0), (0.6, 0.9), (0.8, 0.0)]
    }
}