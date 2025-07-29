import pygame
import serial
import time
import numpy as np

# --- 設定 ---
SERIAL_PORT = "/dev/tty.usbserial-0001" 
BAUD_RATE = 921600
NUM_PIXELS = 100
HEADER_MAGIC = b'\xAB'
FOOTER_MAGIC = b'\xCD'

def main():
    pygame.init()
    ser = None
    try:
        # --- 1. ESP32に接続 ---
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        time.sleep(2)
        print("Connection Successful! Pygame window is active.")

        # --- 2. Pygameウィンドウのセットアップ ---
        screen = pygame.display.set_mode((600, 400))
        pygame.display.set_caption("Mouse Control: X=Color, Y=Brightness")
        font = pygame.font.SysFont(None, 24) # デフォルトフォント(英語のみ)
        clock = pygame.time.Clock()

        running = True
        while running:
            # --- 3. イベント処理 ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # --- 4. マウス位置から色と明るさを生成 ---
            mouse_x, mouse_y = pygame.mouse.get_pos()
            
            # X座標で色相(Hue)を0-255の範囲で決定 (虹色に変化)
            hue = int((mouse_x / 600) * 255)
            
            # Y座標で明るさ(Brightness)を0.0-1.0の範囲で決定
            brightness = max(0, 1.0 - (mouse_y / 400))
            
            # --- 5. HSV色空間を使ってRGBに変換 ---
            # これにより、マウスを左右に動かすだけで綺麗な虹色スペクトルを表現できる
            color_hsv = pygame.Color(0)
            color_hsv.hsva = (hue * 360 / 255, 100, 100, 100) # (色相, 彩度, 明度, アルファ)
            
            # 最終的な色を計算
            base_color = np.array([color_hsv.r, color_hsv.g, color_hsv.b])
            final_color = base_color * brightness
            led_data = np.full((NUM_PIXELS, 3), final_color)

            # --- 6. データをESP32に送信 ---
            byte_data = np.clip(led_data, 0, 255).astype(np.uint8).tobytes()
            ser.write(HEADER_MAGIC)
            ser.flush()
            time.sleep(0.001) # データ渋滞防止
            ser.write(byte_data)
            ser.write(FOOTER_MAGIC)
            ser.flush()

            # --- 7. ウィンドウに現在の状態を描画 ---
            screen.fill((40, 40, 60))
            info_text = f"Hue: {hue} | Brightness: {brightness:.2f} | RGB: {base_color}"
            text_surface = font.render(info_text, True, (255, 255, 255))
            screen.blit(text_surface, (10, 10))
            pygame.display.flip()
            
            clock.tick(60)

    except KeyboardInterrupt:
        print("\nStopping program.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        # --- 8. 安全な終了処理 ---
        if ser and ser.is_open:
            print("Shutting down... turning off LEDs.")
            shutdown_data = np.zeros((NUM_PIXELS * 3), dtype=np.uint8).tobytes()
            ser.write(HEADER_MAGIC); ser.flush(); time.sleep(0.001)
            ser.write(shutdown_data); ser.write(FOOTER_MAGIC); ser.flush()
            ser.close()
            print("Serial port closed.")
        pygame.quit()

if __name__ == '__main__':
    main()