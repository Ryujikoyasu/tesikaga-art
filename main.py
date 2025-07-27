import pygame
import csv
import numpy as np
from src.config import *
from src.objects import Human, Bird


# --- Choose which birds to simulate here ---
# 全8種類、合計13羽のフルキャスト！
BIRDS_TO_SIMULATE = [
    # --- 主役級・大型の鳥 ---
    "ojirowasi",      # 1羽の孤高の王
    "shimafukuro",    # 1羽の神秘的な賢者
    "tancho",         # 1羽の優雅なつがい
    "oohakucho", "oohakucho", # 2羽の荘厳な家族

    # --- 個性的な中型の鳥 ---
    "ooluri",         # 1羽の美しいシンガー
    "kumagera",       # 1羽の森のドラマー
    
    # --- 賑やかしの小型の鳥 ---
    "nogoma", "nogoma", # 2羽の臆病な探索者
    "benimashiko", "benimashiko", "benimashiko" # 3羽のせわしない群れ
]


def main():
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Interactive Light Art Simulator")
    clock = pygame.time.Clock()

    # Load LED positions
    led_positions = []
    try:
        with open(LED_FILE_PATH, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            for row in reader:
                led_positions.append((float(row[0]), float(row[1])))
    except FileNotFoundError:
        print(f"Error: Cannot find {LED_FILE_PATH}.")
        return
    led_positions = np.array(led_positions)
    
    # --- NEW: Calculate Anchor Point Positions for drawing ---
    # The LEDs are placed at constant intervals. 
    # 0m = 0th LED, 5m = 300th LED, 10m = 600th LED
    anchor_led_indices = [0, 300, 600]
    anchor_pixel_positions = [led_positions[i] for i in anchor_led_indices]


    # Create simulation objects
    human = Human()
    birds = [Bird(bird_id, BIRD_PARAMS[bird_id], WORLD_RADIUS) for bird_id in BIRDS_TO_SIMULATE if bird_id in BIRD_PARAMS]

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- Update ---
        human.update()
        for bird in birds:
            bird.update(human, birds)

        # --- Draw ---
        screen.fill(BLACK)
        pygame.draw.circle(screen, BLUE, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), WORLD_RADIUS)

        led_display_colors = np.full((len(led_positions), 3), 0, dtype=float)
        
        # (Bird light calculation logic is unchanged)
        for bird in birds:
            distances = np.linalg.norm(led_positions - bird.position, axis=1)
            center_led_index = np.argmin(distances)
            spread, brightness = 0, 0.0
            if bird.state == "CHIRPING":
                brightness = bird.current_brightness
                spread = int(bird.params['size'] * 4)
            else:
                if bird.state == "IDLE": spread, brightness = int(bird.params['size'] * 0.5), 0.3
                elif bird.state == "EXPLORING": spread, brightness = int(bird.params['size'] * 2), 0.6
                elif bird.state == "CAUTION": spread, brightness = int(bird.params['size'] * 1.5), 0.7
                elif bird.state == "FLEEING": spread, brightness = int(bird.params['size'] * 3), 1.0
            if spread == 0: continue
            total_leds_in_spread = spread * 2 + 1
            ratio_sum = sum(bird.color_ratio)
            num_accent_leds = int(total_leds_in_spread * (bird.color_ratio[1] / ratio_sum))
            accent_spread = num_accent_leds // 2
            for i in range(-spread, spread + 1):
                idx = center_led_index + i
                if 0 <= idx < len(led_positions):
                    falloff = (spread - abs(i)) / spread
                    final_brightness = brightness * falloff
                    color_to_use = bird.accent_color if -accent_spread <= i <= accent_spread else bird.led_color
                    added_color = color_to_use * final_brightness
                    led_display_colors[idx] += added_color
        
        # Draw the LEDs
        final_led_colors = np.clip(led_display_colors, 0, 255).astype(int)
        for i, pos in enumerate(led_positions):
            pygame.draw.circle(screen, final_led_colors[i], (int(pos[0]), int(pos[1])), 2)
            
        # --- NEW: Draw anchor points on top ---
        for pos in anchor_pixel_positions:
            pygame.draw.circle(screen, (0,0,0), (int(pos[0]), int(pos[1])), 5) # Black circle
            pygame.draw.circle(screen, (255,255,255), (int(pos[0]), int(pos[1])), 5, 1) # White outline

        # Draw objects
        human.draw(screen)
        for bird in birds:
            bird.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == '__main__':
    main()