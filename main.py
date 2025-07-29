### シミュレーションのみ。
### シリアル通信するのはmain2.py

import pygame
import csv
import numpy as np
from src.config import *
from src.objects import Human, Bird

# A parameter for minimum bird size on the debug view
DEBUG_MIN_BIRD_SIZE_PX = 6.0

def model_to_view(pos_m):
    """Converts model meters (simulation space) to view pixels (drawing space)."""
    scale = WORLD_RADIUS / MODEL_RADIUS
    view_center = np.array([VIEW_WIDTH / 2, VIEW_HEIGHT / 2])
    return pos_m * scale + view_center

def view_to_model(pos_px):
    """Converts view pixels to model meters. Assumes mouse is over the left view."""
    scale = WORLD_RADIUS / MODEL_RADIUS
    view_center = np.array([VIEW_WIDTH / 2, VIEW_HEIGHT / 2])
    return (np.array(pos_px) - view_center) / scale



def main():
    pygame.init(); pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    debug_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    art_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    pygame.display.set_caption("Left: Debug View | Right: Artistic View")
    clock = pygame.time.Clock()

    try:
        all_led_model_positions = np.loadtxt(LED_FILE_PATH, delimiter=',', skiprows=1)
    except Exception as e:
        print(f"FATAL: Could not load LED data from '{LED_FILE_PATH}'. Error: {e}"); return
    
    # Use the number of LEDs specified in the config, truncating if the CSV is larger.
    led_model_positions = all_led_model_positions[:NUM_LEDS]
    led_view_positions = np.apply_along_axis(model_to_view, 1, led_model_positions)
    # num_leds is now defined in config.py
    # num_leds = len(led_view_positions)
    
    human = Human()
    birds = [Bird(bird_id, BIRD_PARAMS[bird_id]) for bird_id in BIRDS_TO_SIMULATE if bird_id in BIRD_PARAMS]

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

        human.update_position(view_to_model(pygame.mouse.get_pos()))
        for bird in birds: bird.update(human, birds)

        debug_surface.fill((25, 28, 35)); art_surface.fill((5, 8, 15))
        pond_center_px = (VIEW_WIDTH // 2, VIEW_HEIGHT // 2)
        pygame.draw.circle(debug_surface, (20, 40, 80), pond_center_px, WORLD_RADIUS)
        pygame.draw.circle(art_surface, (20, 40, 80), pond_center_px, WORLD_RADIUS)

        for bird in birds:
            bird_pos_px = model_to_view(bird.position)
            final_draw_size_px = max(bird.params['size'] * 2.5, DEBUG_MIN_BIRD_SIZE_PX)
            pygame.draw.circle(debug_surface, bird.base_color, (int(bird_pos_px[0]), int(bird_pos_px[1])), int(final_draw_size_px))
            pygame.draw.circle(debug_surface, bird.accent_color, (int(bird_pos_px[0]), int(bird_pos_px[1])), int(final_draw_size_px * 0.4))
        
        human_pos_px = model_to_view(human.position)
        pygame.draw.circle(debug_surface, (255, 255, 255), (int(human_pos_px[0]), int(human_pos_px[1])), 10)
        
        # --- New Drawing Logic ---
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

            # Simplified brightness calculation for now
            brightness = 0.6
            if bird.state == "CHIRPING":
                brightness = bird.current_brightness
            elif bird.state == "FLEEING":
                brightness = 1.0

            # Spread brightness across LEDs
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

        # 2. Render LEDs based on the winner map and color patterns
        for led_idx in range(NUM_LEDS):
            bird_idx = winner_map[led_idx]
            if bird_idx != -1:
                bird = birds[bird_idx]
                brightness = brightness_map[led_idx]
                
                distances_m = np.linalg.norm(led_model_positions - bird.position, axis=1)
                center_led_index = np.argmin(distances_m)
                
                # Determine the pixel offset from the bird's center
                physical_offset = led_idx - center_led_index
                pixel_offset = (physical_offset + 1) // 3 

                current_pattern, num_pixels = bird.get_current_light_pattern()
                total_pattern_pixels = sum(p[1] for p in current_pattern)
                
                if total_pattern_pixels > 0:
                    # Find which part of the pattern this pixel falls into
                    pixel_cursor = 0
                    color_type = 'b' # Default to base
                    
                    # Center the pattern
                    start_pixel = -total_pattern_pixels // 2
                    
                    for p_type, p_count in current_pattern:
                        if start_pixel <= pixel_offset < start_pixel + p_count:
                            color_type = p_type
                            break
                        start_pixel += p_count

                    color = bird.accent_color if color_type == 'a' else bird.base_color
                    final_led_colors_view[led_idx] = np.clip(color * brightness, 0, 255)

        # 3. Draw the final computed LED colors
        for i, pos_px in enumerate(led_view_positions):
            if np.any(final_led_colors_view[i] > 5):
                pygame.draw.circle(art_surface, final_led_colors_view[i], (int(pos_px[0]), int(pos_px[1])), 2)

        screen.blit(debug_surface, (0, 0)); screen.blit(art_surface, (VIEW_WIDTH, 0))
        pygame.display.flip()
        clock.tick(60)
        
    pygame.quit()

if __name__ == '__main__':
    main()