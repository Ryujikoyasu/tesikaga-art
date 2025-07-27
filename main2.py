# --- main.py ---
# This is the main entry point for the Teshikaga Interactive Art simulation.
# It handles rendering, the main loop, and orchestrates all other modules.

import pygame
import csv
import numpy as np
import sys
import os

# Ensure the 'src' directory is in the Python path
# This allows us to use `from src.module import ...`
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import *
from src.objects import Human, Bird
from src.serial_controller import SerialController

# A parameter for minimum bird size on the debug view
DEBUG_MIN_BIRD_SIZE_PX = 6.0

# --- User Configuration ---
# IMPORTANT: Replace this with the actual port your ESP32 is connected to.
# - On macOS, it's likely '/dev/tty.usbserial-XXXXXXXX'
# - On Linux, it might be '/dev/ttyUSB0' or '/dev/ttyACM0'
# - On Windows, it will be 'COM3', 'COM4', etc.
SERIAL_PORT = '/dev/tty.usbserial-XXXXXXXX'  # <--- CHANGE THIS!
SERIAL_BAUDRATE = 921600 # Must match the microcontroller code


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

def calculate_bird_light(bird, center_idx, num_leds):
    """
    Calculates the light contribution of a single bird.
    Returns two separate arrays: one for color and one for brightness.
    This enables the "Winner-Takes-All" blending mode.
    """
    light_colors = np.zeros((num_leds, 3), dtype=float)
    light_brightness = np.zeros(num_leds, dtype=float)
    spread, brightness_factor = 0, 0.0

    # Determine base brightness and spread from the bird's current state
    if bird.state == "CHIRPING":
        brightness_factor, spread = bird.current_brightness, int(bird.params['size'] * 4)
    elif bird.state == "FORAGING":
        spread, brightness_factor = int(bird.params['size'] * 0.8), 0.4
    elif bird.state == "IDLE":
        spread, brightness_factor = int(bird.params['size'] * 0.5), 0.3
    elif bird.state == "EXPLORING":
        spread, brightness_factor = int(bird.params['size'] * 2), 0.6
    elif bird.state == "CAUTION":
        spread, brightness_factor = int(bird.params['size'] * 1.5), 0.7
    elif bird.state == "FLEEING":
        spread, brightness_factor = int(bird.params['size'] * 3), 1.0
    elif bird.state == "CURIOUS":
        spread, brightness_factor = int(bird.params['size'] * 1.0), 0.5
    
    spread = int(spread * LED_SPREAD_MULTIPLIER)
    if spread == 0 or brightness_factor <= 0:
        return light_colors, light_brightness

    # Pre-calculate color distribution based on the bird's color_ratio
    total_leds_in_spread = spread * 2 + 1
    ratio_sum = sum(bird.color_ratio)
    if ratio_sum == 0: ratio_sum = 1 # Avoid division by zero
    num_accent_leds = int(total_leds_in_spread * (bird.color_ratio[1] / ratio_sum))
    accent_spread = num_accent_leds // 2
    
    for i in range(-spread, spread + 1):
        idx = center_idx + i
        if 0 <= idx < num_leds:
            # Calculate brightness falloff from the center
            falloff = (spread - abs(i)) / spread
            final_brightness = brightness_factor * falloff
            
            # Determine the color for this specific LED
            color_to_use = bird.accent_color if -accent_spread <= i <= accent_spread else bird.led_color
            
            # Store the final calculated color and brightness in our temporary arrays
            light_colors[idx] = color_to_use * final_brightness
            light_brightness[idx] = final_brightness
            
    return light_colors, light_brightness

def main():
    """The main execution function of the program."""
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    debug_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    art_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    pygame.display.set_caption("Teshikaga Art Simulator | Left: Debug View | Right: Artistic View")
    clock = pygame.time.Clock()

    # --- Initialization ---
    led_controller = SerialController(port=SERIAL_PORT, baudrate=SERIAL_BAUDRATE)

    try:
        led_model_positions = np.loadtxt(LED_FILE_PATH, delimiter=',', skiprows=1)
    except Exception as e:
        print(f"FATAL: Could not load LED data from '{LED_FILE_PATH}'. Error: {e}")
        print("Please run 'artistic_path_generator.py' first to create the file.")
        return
    
    led_view_positions = np.apply_along_axis(model_to_view, 1, led_model_positions)
    num_leds = len(led_view_positions)
    leds_per_segment = num_leds // 3
    anchor_indices = [i for i in [0, leds_per_segment, leds_per_segment * 2] if i < num_leds]
    anchor_pixel_positions = [led_view_positions[i] for i in anchor_indices]
    
    human = Human()
    birds = [Bird(bird_id, BIRD_PARAMS[bird_id]) for bird_id in BIRDS_TO_SIMULATE if bird_id in BIRD_PARAMS]
    print(f"Simulation started with {len(birds)} birds.")

    # --- Main Loop ---
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- Update ---
        human.update_position(view_to_model(pygame.mouse.get_pos()))
        for bird in birds:
            bird.update(human, birds)

        # --- Draw Debug View ---
        debug_surface.fill((25, 28, 35))
        pond_center_px = (VIEW_WIDTH // 2, VIEW_HEIGHT // 2)
        pygame.draw.circle(debug_surface, (20, 40, 80), pond_center_px, WORLD_RADIUS, 1) # Pond outline
        pygame.draw.lines(debug_surface, (70, 70, 80), False, led_view_positions, 1) # LED path outline
        for pos_px in anchor_pixel_positions:
            pygame.draw.circle(debug_surface, (255, 255, 0), (int(pos_px[0]), int(pos_px[1])), 8, 2)
        
        for bird in birds:
            bird_pos_px = model_to_view(bird.position)
            final_draw_size_px = max(bird.params['size'] * 2.5, DEBUG_MIN_BIRD_SIZE_PX)
            pygame.draw.circle(debug_surface, bird.params['led_color'], (int(bird_pos_px[0]), int(bird_pos_px[1])), int(final_draw_size_px))
            pygame.draw.circle(debug_surface, bird.params['accent_color'], (int(bird_pos_px[0]), int(bird_pos_px[1])), int(final_draw_size_px * 0.4), 2)
        
        human_pos_px = model_to_view(human.position)
        pygame.draw.circle(debug_surface, (255, 255, 255), (int(human_pos_px[0]), int(human_pos_px[1])), 10)
        
        # --- Light Calculation (Winner-Takes-All) ---
        final_led_colors_float = np.zeros((num_leds, 3), dtype=float)
        led_brightness_buffer = np.zeros(num_leds, dtype=float)

        for bird in birds:
            distances_m = np.linalg.norm(led_model_positions - bird.position, axis=1)
            center_led_index = np.argmin(distances_m)
            bird_light_colors, bird_light_brightness = calculate_bird_light(bird, center_led_index, num_leds)
            
            update_mask = bird_light_brightness > led_brightness_buffer
            
            final_led_colors_float[update_mask] = bird_light_colors[update_mask]
            led_brightness_buffer[update_mask] = bird_light_brightness[update_mask]
        
        final_led_colors_int = np.clip(final_led_colors_float, 0, 255).astype(int)

        # --- Send data to hardware ---
        if led_controller.is_connected():
            led_controller.send_led_data(final_led_colors_int)

        # --- Draw Artistic View ---
        art_surface.fill((5, 8, 15))
        for i, pos_px in enumerate(led_view_positions):
            if np.any(final_led_colors_int[i] > 5): # Only draw if the color is not black
                pygame.draw.circle(art_surface, final_led_colors_int[i], (int(pos_px[0]), int(pos_px[1])), 2)

        # --- Final Blit & Update ---
        screen.blit(debug_surface, (0, 0))
        screen.blit(art_surface, (VIEW_WIDTH, 0))
        pygame.display.flip()
        clock.tick(60)
        
    # --- Cleanup ---
    print("Shutting down...")
    led_controller.close()
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()