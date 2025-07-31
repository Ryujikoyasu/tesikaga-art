# This file is a backup of the base bird parameters.
# It is used by audio_sync_generator.py to prevent read errors from a broken config.
def get_base_config():
    return {
        # NOTE: Parameters are redesigned for the 3LED/1Pixel specification.
        # - "base_led_count" is replaced by "base_pixel_count".
        # - "color_structure" is replaced by "color_pattern" and "chirp_color_pattern".
        # - 'b' in patterns denotes base_color, 'a' denotes accent_color.
        
        "ooluri": {
            "name_jp": "オオルリ", 
            "base_color": [20, 100, 240], "accent_color": [240, 240, 255], 
            "base_pixel_count": 4, # 少しだけ大きく
            "size": 1.0, 
            "pixel_personal_space": 5,
            # パターンを[B,A,A,B]に変更し、中心の輝きを強調
            "color_pattern": [['b', 1], ['a', 2], ['b', 1]], 
            "chirp_color_pattern": [['b', 1], ['a', 2], ['b', 1]],
            "movement_speed": 0.2, "approach_speed": 0.1, "curiosity": 0.5, 
            "caution_distance": 1.5, "flee_distance": 1.0, 
            "sound_files": {"default": "assets/sounds/oruri.mp3"}
        },
        "oohakucho": {
            "name_jp": "オオハクチョウ", 
            # 温かみのあるオフホワイトに変更
            "base_color": [255, 250, 240], "accent_color": [255, 220, 0], 
            "base_pixel_count": 6,
            "size": 4.0, 
            "pixel_personal_space": 5,
            "color_pattern": [['b', 2], ['a', 2], ['b', 2]],
            "chirp_color_pattern": [['a', 1], ['b', 4], ['a', 1]],
            "movement_speed": 0.08, "approach_speed": 0.02, "curiosity": 0.1, 
            "caution_distance": 2.2, "flee_distance": 1.8, 
            "sound_files": {"default": "assets/sounds/ohakucho.mp3"}
        },
        "ojirowasi": {
            "name_jp": "オジロワシ", 
            "base_color": [240, 220, 180], "accent_color": [255, 215, 0], 
            "base_pixel_count": 6,
            "size": 5.0, 
            "pixel_personal_space": 5,
            "color_pattern": [['b', 2], ['a', 2], ['b', 2]],
            "chirp_color_pattern": [['a', 3], ['b', 3]],
            "movement_speed": 0.05, "approach_speed": 0.0, "curiosity": 0.0, 
            "caution_distance": 3.0, "flee_distance": 1.2, 
            "sound_files": {"default": "assets/sounds/ojirowasi.mp3"}
        },
        "shimafukuro": {
            "name_jp": "シマフクロウ", 
            "base_color": [70, 130, 180], "accent_color": [255, 255, 100], 
            "base_pixel_count": 5,
            "size": 4.5, 
            "pixel_personal_space": 5,
            "color_pattern": [['b', 2], ['a', 1], ['b', 2]],
            "chirp_color_pattern": [['a', 5]],
            "movement_speed": 0.1, "approach_speed": 0.0, "curiosity": 0.01, 
            "caution_distance": 3.5, "flee_distance": 2.8, 
            "sound_files": {"default": "assets/sounds/simafukuro.mp3"}
        },
        "kumagera": {
            "name_jp": "クマゲラ",
            # 「黒」を「限りなく黒に近い濃紺」に調整し、視認性を確保
            "base_color": [35, 35, 50], "accent_color": [255, 0, 0],
            # 最小ピクセル数を3に
            "base_pixel_count": 3,
            "size": 1.5, 
            "pixel_personal_space": 5,
            # パターンを「黒-赤-黒」のシンメトリーな形に
            "color_pattern": [['b', 1], ['a', 1], ['b', 1]],
            "chirp_color_pattern": [['a', 3]], # 鳴くときは赤一色で点滅
            "movement_speed": 0.3, "approach_speed": 0.1, "curiosity": 0.2, 
            "caution_distance": 1.8, "flee_distance": 1.2, 
            "sound_files": {"call": "assets/sounds/kumagera.mp3", "drumming": "assets/sounds/kumagera_drum.mp3"}
        },
        "tancho": {
            "name_jp": "タンチョウ", 
            # 涼しげな純白に変更
            "base_color": [255, 255, 255], "accent_color": [220, 0, 0], 
            "base_pixel_count": 5,
            "size": 3.5, 
            "pixel_personal_space": 5,
            "color_pattern": [['b', 2], ['a', 1], ['b', 2]],
            "chirp_color_pattern": [['a', 1], ['b', 1], ['a', 1], ['b', 1], ['a', 1]],
            "movement_speed": 0.1, "approach_speed": 0.05, "curiosity": 0.3, 
            "caution_distance": 2.5, "flee_distance": 2.0, 
            "sound_files": {"default": "assets/sounds/tancho.mp3"}
        },
        "nogoma": {
            "name_jp": "ノゴマ", 
            # 「茶色」に少し明るさと赤みを加え、存在感を出す
            "base_color": [140, 115, 90], "accent_color": [255, 10, 10], 
            # 最小ピクセル数を3に
            "base_pixel_count": 3,
            "size": 0.8, 
            "pixel_personal_space": 5,
            # パターンを「茶-赤-茶」のシンメトリーな形に
            "color_pattern": [['b', 1], ['a', 1], ['b', 1]],
            "chirp_color_pattern": [['a', 3]], # 鳴くときは喉の赤だけが光る
            "movement_speed": 0.4, "approach_speed": 0.2, "curiosity": 0.8, 
            "caution_distance": 2.0, "flee_distance": 1.5, 
            "sound_files": {"default": "assets/sounds/nogoma.mp3"}
        },
        "benimashiko": {
            "name_jp": "ベニマシコ", 
            "base_color": [190, 50, 90], "accent_color": [230, 150, 170], 
            # 最小ピクセル数を3に
            "base_pixel_count": 3,
            "size": 0.9, 
            "pixel_personal_space": 5,
            # パターンを「淡赤-濃赤-淡赤」のグラデーションを感じる形に
            "color_pattern": [['a', 1], ['b', 1], ['a', 1]],
            "chirp_color_pattern": [['a', 1], ['b', 2]],
            "movement_speed": 0.35, "approach_speed": 0.15, "curiosity": 0.7, 
            "caution_distance": 2.2, "flee_distance": 2.0, 
            "sound_files": {"default": "assets/sounds/benimasiko.mp3"}
        }
    }