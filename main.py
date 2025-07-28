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

# ==============================================================================
# ▼▼▼ THIS IS THE ONLY FUNCTION THAT IS MODIFIED ▼▼▼
# ==============================================================================

def calculate_bird_light(bird, center_idx, num_leds):
    """
    Calculates the light contribution of a single bird based on its defined color structure.
    Returns: (light_color_array, light_brightness_array)
    """
    light_colors = np.zeros((num_leds, 3), dtype=float)
    light_brightness = np.zeros(num_leds, dtype=float)

    # 1. Determine the spread (number of LEDs to light) and brightness based on state
    base_spread = bird.params['base_led_count'] // 2
    brightness_factor = 0.0
    dynamic_spread_factor = 1.0

    if bird.state == "CHIRPING":
        brightness_factor = bird.current_brightness
        dynamic_spread_factor = 1.0 + (bird.params['size'] / 2.0) # Chirping makes the light much larger
    elif bird.state == "FLEEING":
        brightness_factor = 1.0
        dynamic_spread_factor = 1.2 # Fleeing makes light slightly larger
    elif bird.state == "CAUTION":
        brightness_factor = 0.7
        dynamic_spread_factor = 1.0
    elif bird.state == "CURIOUS":
        brightness_factor = 0.5
        dynamic_spread_factor = 0.9 # Curious is a bit smaller
    else: # IDLE, EXPLORING, FORAGING
        brightness_factor = 0.6
        dynamic_spread_factor = 1.0

    # Final spread is the base count scaled by the dynamic factor
    spread = int(base_spread * dynamic_spread_factor)
    spread = int(spread * LED_SPREAD_MULTIPLIER) # Apply global multiplier
    
    if spread == 0 or brightness_factor <= 0:
        return light_colors, light_brightness

    # 2. Get the bird's specific color structure
    structure = bird.params['color_structure']
    num_accent = structure.get('accent', 0)
    
    # The accent color will be placed in the very center of the light spread
    accent_spread = num_accent // 2

    # 3. Apply colors and brightness to the LED arrays
    for i in range(-spread, spread + 1):
        idx = center_idx + i
        if 0 <= idx < num_leds:
            falloff = (spread - abs(i)) / spread if spread > 0 else 1.0
            final_brightness = brightness_factor * falloff

            # Determine color based on the physical structure
            # The innermost LEDs get the accent color
            if -accent_spread <= i <= accent_spread:
                color_to_use = bird.accent_color
            else:
                color_to_use = bird.led_color
            
            # Store the final calculated values
            light_colors[idx] = color_to_use * final_brightness
            light_brightness[idx] = final_brightness
            
    return light_colors, light_brightness

# ==============================================================================
# ▲▲▲ END OF MODIFIED SECTION ▲▲▲
# ==============================================================================


def main():
    pygame.init(); pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    debug_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    art_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    pygame.display.set_caption("Left: Debug View | Right: Artistic View")
    clock = pygame.time.Clock()

    try:
        led_model_positions = np.loadtxt(LED_FILE_PATH, delimiter=',', skiprows=1)
    except Exception as e:
        print(f"FATAL: Could not load LED data from '{LED_FILE_PATH}'. Error: {e}"); return
    
    led_view_positions = np.apply_along_axis(model_to_view, 1, led_model_positions)
    num_leds = len(led_view_positions)
    leds_per_segment = num_leds // 3
    anchor_indices = [i for i in [0, leds_per_segment, leds_per_segment * 2] if i < num_leds]
    anchor_pixel_positions = [led_view_positions[i] for i in anchor_indices]
    
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

        pygame.draw.lines(debug_surface, (70, 70, 80), False, led_view_positions, 1)
        for pos_px in anchor_pixel_positions:
            pygame.draw.circle(debug_surface, (255, 255, 0), (int(pos_px[0]), int(pos_px[1])), 8, 2)
        
        for bird in birds:
            bird_pos_px = model_to_view(bird.position)
            final_draw_size_px = max(bird.params['size'] * 2.5, DEBUG_MIN_BIRD_SIZE_PX)
            pygame.draw.circle(debug_surface, bird.params['led_color'], (int(bird_pos_px[0]), int(bird_pos_px[1])), int(final_draw_size_px))
            pygame.draw.circle(debug_surface, bird.params['accent_color'], (int(bird_pos_px[0]), int(bird_pos_px[1])), int(final_draw_size_px * 0.4))
        
        human_pos_px = model_to_view(human.position)
        pygame.draw.circle(debug_surface, (255, 255, 255), (int(human_pos_px[0]), int(human_pos_px[1])), 10)
        
        # This "Winner-Takes-All" logic remains unchanged and works with the new light calculation
        led_color_array = np.zeros((num_leds, 3), dtype=float)
        led_brightness_buffer = np.zeros(num_leds, dtype=float)

        for bird in birds:
            distances_m = np.linalg.norm(led_model_positions - bird.position, axis=1)
            center_led_index = np.argmin(distances_m)
            
            # The new function is called here, but the surrounding logic doesn't need to change
            bird_light_colors, bird_light_brightness = calculate_bird_light(bird, center_led_index, num_leds)
            
            update_mask = bird_light_brightness > led_brightness_buffer
            led_color_array[update_mask] = bird_light_colors[update_mask]
            led_brightness_buffer[update_mask] = bird_light_brightness[update_mask]
        
        final_led_colors = np.clip(led_color_array, 0, 255).astype(int)
        for i, pos_px in enumerate(led_view_positions):
            if np.any(final_led_colors[i] > 5):
                pygame.draw.circle(art_surface, final_led_colors[i], (int(pos_px[0]), int(pos_px[1])), 2)

        screen.blit(debug_surface, (0, 0)); screen.blit(art_surface, (VIEW_WIDTH, 0))
        pygame.display.flip()
        clock.tick(60)
        
    pygame.quit()

if __name__ == '__main__':
    main()