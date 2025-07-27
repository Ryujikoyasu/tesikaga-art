# This file is a backup of the base bird parameters.
# It is used by audio_sync_generator.py to prevent read errors from a broken config.
def get_base_config():
    return {
        "ooluri": {"name_jp": "オオルリ", "led_color": [20, 100, 240], "accent_color": [240, 240, 255], "color_ratio": [8, 2], "size": 1.0, "movement_speed": 0.2, "approach_speed": 0.1, "curiosity": 0.5, "caution_distance": 1.5, "flee_distance": 1.0, "sound_files": {"default": "assets/sounds/oruri.mp3"}},
        "oohakucho": {"name_jp": "オオハクチョウ", "led_color": [255, 255, 255], "accent_color": [255, 220, 0], "color_ratio": [9, 1], "size": 4.0, "movement_speed": 0.08, "approach_speed": 0.02, "curiosity": 0.1, "caution_distance": 2.2, "flee_distance": 1.8, "sound_files": {"default": "assets/sounds/ohakucho.mp3"}},
        "ojirowasi": {"name_jp": "オジロワシ", "led_color": [180, 160, 140], "accent_color": [255, 255, 255], "color_ratio": [7, 3], "size": 5.0, "movement_speed": 0.05, "approach_speed": 0.0, "curiosity": 0.0, "caution_distance": 3.0, "flee_distance": 1.2, "sound_files": {"default": "assets/sounds/ojirowasi.mp3"}},
        "shimafukuro": {"name_jp": "シマフクロウ", "led_color": [80, 70, 60], "accent_color": [120, 110, 100], "color_ratio": [9, 1], "size": 4.5, "movement_speed": 0.1, "approach_speed": 0.0, "curiosity": 0.01, "caution_distance": 3.5, "flee_distance": 2.8, "sound_files": {"default": "assets/sounds/simafukuro.mp3"}},
        "kumagera": {"name_jp": "クマゲラ", "led_color": [20, 20, 20], "accent_color": [255, 0, 0], "color_ratio": [9, 1], "size": 1.5, "movement_speed": 0.3, "approach_speed": 0.1, "curiosity": 0.2, "caution_distance": 1.8, "flee_distance": 1.2, "sound_files": {"call": "assets/sounds/kumagera.mp3", "drumming": "assets/sounds/kumagera_drum.mp3"}},
        "tancho": {"name_jp": "タンチョウ", "led_color": [255, 255, 255], "accent_color": [220, 0, 0], "color_ratio": [8, 2], "size": 3.5, "movement_speed": 0.1, "approach_speed": 0.05, "curiosity": 0.3, "caution_distance": 2.5, "flee_distance": 2.0, "sound_files": {"default": "assets/sounds/tancho.mp3"}},
        "nogoma": {"name_jp": "ノゴマ", "led_color": [120, 110, 90], "accent_color": [255, 10, 10], "color_ratio": [9, 1], "size": 0.8, "movement_speed": 0.4, "approach_speed": 0.2, "curiosity": 0.8, "caution_distance": 2.0, "flee_distance": 1.5, "sound_files": {"default": "assets/sounds/nogoma.mp3"}},
        "benimashiko": {"name_jp": "ベニマシコ", "led_color": [220, 40, 80], "accent_color": [139, 69, 19], "color_ratio": [7, 3], "size": 0.9, "movement_speed": 0.35, "approach_speed": 0.15, "curiosity": 0.7, "caution_distance": 2.2, "flee_distance": 2.0, "sound_files": {"default": "assets/sounds/benimasiko.mp3"}}
    }

def get_simulation_cast():
    return ["ojirowasi", "shimafukuro", "tancho", "oohakucho", "oohakucho", "ooluri", "kumagera", "nogoma", "nogoma", "benimashiko", "benimashiko", "benimashiko"]
