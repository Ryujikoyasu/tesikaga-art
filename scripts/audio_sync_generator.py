import os
import sys
import numpy as np
import librosa
import yaml

# ----------------------------------------------------------------------
# 1. プロジェクトのルートディレクトリを特定し、Pythonのパスに追加
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
# ----------------------------------------------------------------------

from src.config_structure import get_base_config

# --- 定数 ---
CONFIG_PATH = os.path.join(PROJECT_ROOT, "src", "config.py")
SETTINGS_PATH = os.path.join(PROJECT_ROOT, "settings.yaml")


# --- ヘルパー関数 ---

def analyze_chirp(file_path):
    """
    音声ファイルを解析し、エネルギーの高いイベント（鳴き声）のタイミングを検出して、
    (時刻, 明るさ) のタプルのリストを返します。
    """
    try:
        y, sr = librosa.load(file_path)
        onset_frames = librosa.onset.onset_detect(
            y=y, sr=sr, units='frames', hop_length=512, backtrack=True, energy=y**2
        )
        onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=512)
        
        if not onset_times.any():
            return [(0.0, 0.0), (librosa.get_duration(y=y, sr=sr), 0.0)]
            
        events = [(0.0, 0.0)]
        last_time = 0.0
        
        for t in onset_times:
            if t > last_time + 0.05:
                events.append((np.float64(last_time), 0.0))
                events.append((np.float64(t), 1.2))
                last_time = t + 0.075
        
        events.append((np.float64(last_time), 0.0))
        final_duration = librosa.get_duration(y=y, sr=sr)
        if final_duration > last_time:
            events.append((final_duration, 0.0))
            
        return events
        
    except Exception as e:
        print(f"  [ERROR] 音声ファイルの処理中にエラーが発生しました {os.path.basename(file_path)}: {e}")
        return [(0, 0)]

def format_python_code(obj, indent=0):
    """
    Pythonオブジェクトを整形されたコード文字列に再帰的に変換します。
    """
    margin = ' ' * indent
    if isinstance(obj, dict):
        items = [f"{margin}    '{k}': {format_python_code(v, indent + 4)}" for k, v in obj.items()]
        return f"{{\n" + ",\n".join(items) + f"\n{margin}}}"
    if isinstance(obj, list):
        if not obj: return "[]"
        if isinstance(obj[0], (tuple, list)):
            items = [f"{margin}    {repr(tuple(i))}" for i in obj]
            return f"[\n" + ",\n".join(items) + f"\n{margin}]"
        else:
            items = [f"{margin}    {repr(i)}" for i in obj]
            return f"[\n" + ",\n".join(items) + f"\n{margin}]"
    
    return repr(obj)

# --- メインロジック ---

def main():
    print("--- 音声同期パターンの生成を開始します ---")

    # 1. settings.yamlからユーザー設定を読み込む
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            settings = yaml.safe_load(f)
        print(f"'{os.path.basename(SETTINGS_PATH)}' から設定を正常に読み込みました。")
    except FileNotFoundError:
        print(f"FATAL: 設定ファイル '{SETTINGS_PATH}' が見つかりません。")
        sys.exit(1)
    except Exception as e:
        print(f"FATAL: '{SETTINGS_PATH}' の読み込みまたは解析中にエラーが発生しました。Error: {e}")
        sys.exit(1)

    # 2. settings.yamlに必須キーが存在するかチェック
    required_keys = ['led_layout_file', 'num_leds', 'serial_port', 'baud_rate', 'model_diameter']
    missing_keys = [key for key in required_keys if key not in settings]
    if missing_keys:
        print(f"FATAL: 設定ファイル '{os.path.basename(SETTINGS_PATH)}' に必須の設定項目がありません。")
        for key in missing_keys:
            print(f"  - '{key}' を追加してください。")
        sys.exit(1)

    # 3. config_structure.pyから鳥の基本設定を取得
    bird_params = get_base_config()

    # 4. 音声ファイルを処理し、鳴き声の同期パターンを生成
    for bird_id, params in bird_params.items():
        print(f"鳥を処理中: {bird_id.capitalize()}")
        chirp_patterns = {}
        sound_files = params.get('sound_files', {})
        
        for sound_name, sound_path in sound_files.items():
            full_path = os.path.join(PROJECT_ROOT, sound_path)
            if os.path.exists(full_path):
                print(f"  -> 解析中: '{sound_name}' ({sound_path})...")
                chirp_patterns[sound_name] = analyze_chirp(full_path)
            else:
                print(f"  [WARNING] 音声ファイルが見つかりません: {bird_id} ('{sound_name}') at {full_path}")
        
        params['chirp_pattern'] = chirp_patterns
    
    # 5. 最終的なconfig.pyのコンテンツを生成
    print("\n--- 新しい 'src/config.py' を生成中... ---")

    # settings.yamlからテスト設定を読み込む
    enable_test_mode = settings.get('enable_test_mode', False)
    test_strip_leds = settings.get('test_strip_led_count', 100)

    
    output_content = f"""# このファイルは audio_sync_generator.py によって自動生成されました。手動で編集しないでください。
import pygame
import os
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- 画面とワールドのスケール設定 (settings.yamlより) ---
VIEW_WIDTH = {settings.get('view_width', 800)}
VIEW_HEIGHT = {settings.get('view_height', 800)}
SCREEN_WIDTH = VIEW_WIDTH * 2
SCREEN_HEIGHT = VIEW_HEIGHT
WORLD_RADIUS = 350  # 描画用の半径（固定）
MODEL_DIAMETER = {settings['model_diameter']}
MODEL_RADIUS = MODEL_DIAMETER / 2.0

# --- ファイルパス (settings.yamlより) ---
LED_FILE_NAME = "{settings['led_layout_file']}"
LED_FILE_PATH = os.path.join(PROJECT_ROOT, "assets", "data", LED_FILE_NAME)

# --- LEDストリップ設定 (settings.yamlより) ---
NUM_LEDS = {settings['num_leds']}
NUM_PIXELS = NUM_LEDS // 3 # アドレス指定可能なピクセル数 (WS2811の場合、1ピクセル = 3 LED)

# --- ハードウェアテストモード設定 (settings.yamlより) ---
ENABLE_TEST_MODE = {enable_test_mode}
NUM_TEST_STRIP_LEDS = {test_strip_leds}
NUM_TEST_STRIP_PIXELS = NUM_TEST_STRIP_LEDS // 3

# --- AIと見た目の調整（現在は固定値。必要ならsettings.yamlに移動可能） ---
LED_SPREAD_MULTIPLIER = 1.5
IDLE_DURATION_RANGE_FRAMES = (180, 400)
FORAGING_DURATION_RANGE_FRAMES = (120, 300)
EXPLORE_DISTANCE_RANGE_METERS = (1.5, 4.0)
HUMAN_STILLNESS_THRESHOLD_FRAMES = 180
CHIRP_PROBABILITY_PER_FRAME = 0.001

# --- 鳥の性格パラメータ（自動生成された同期パターンを含む） ---
BIRD_PARAMS = {format_python_code(bird_params, 4)}

# --- シミュレーションに登場する鳥 (settings.yamlより) ---
BIRDS_TO_SIMULATE = {format_python_code(settings.get('birds_to_simulate', []), 4)}
"""
    
    # 6. コンテンツをconfig.pyに書き込む
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            f.write(output_content)
        print(f"新しい設定を '{CONFIG_PATH}' に正常に書き込みました。")
    except Exception as e:
        print(f"FATAL: '{CONFIG_PATH}' への書き込みに失敗しました。Error: {e}")
        sys.exit(1)
        
    print("\n--- 全ての処理が完了しました ---")

if __name__ == '__main__':
    main()