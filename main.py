import pygame
import numpy as np
import os
import yaml
from src.config import BIRD_PARAMS
from src.objects import Human, Bird
from src.simulation import World

# --- Load all settings from settings.yaml ---
try:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    SETTINGS_PATH = os.path.join(PROJECT_ROOT, "settings.yaml")
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        settings = yaml.safe_load(f)
    
    LED_FILE_NAME = settings['led_layout_file']
    LED_FILE_PATH = os.path.join(PROJECT_ROOT, "assets", "data", LED_FILE_NAME)
    NUM_LEDS = settings['num_leds']
    MODEL_DIAMETER = settings['model_diameter']
    VIEW_WIDTH = settings.get('view_width', 800)
    VIEW_HEIGHT = settings.get('view_height', 800)
    BIRDS_TO_SIMULATE = settings.get('birds_to_simulate', [])
    AI_TUNING = settings.get('ai_tuning', {})
    CHIRP_PROBABILITY_PER_FRAME = AI_TUNING.get('chirp_probability_per_frame', 0.001)
    
    MODEL_RADIUS = MODEL_DIAMETER / 2.0
    SCREEN_WIDTH, SCREEN_HEIGHT = VIEW_WIDTH * 2, VIEW_HEIGHT
    WORLD_RADIUS = 350
    DEBUG_MIN_BIRD_SIZE_PX = 6.0
    
    print("Loaded simulation settings from 'settings.yaml'")

except Exception as e:
    print(f"FATAL: Error loading settings from 'settings.yaml'. Please check the file. Error: {e}")
    exit()

def model_to_view(pos_m):
    return pos_m * (WORLD_RADIUS / MODEL_RADIUS) + np.array([VIEW_WIDTH / 2, VIEW_HEIGHT / 2])
def view_to_model(pos_px):
    return (np.array(pos_px) - np.array([VIEW_WIDTH / 2, VIEW_HEIGHT / 2])) / (WORLD_RADIUS / MODEL_RADIUS)

def main():
    pygame.init(); pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    debug_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    art_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    pygame.display.set_caption("Left: Debug View | Right: Artistic View")
    clock = pygame.time.Clock()

    try:
        led_model_positions = np.loadtxt(LED_FILE_PATH, delimiter=',', skiprows=1)[:NUM_LEDS]
        led_view_positions = np.apply_along_axis(model_to_view, 1, led_model_positions)
    except Exception as e:
        print(f"FATAL: Could not load LED data from '{LED_FILE_PATH}'. Error: {e}"); return
    
    human = Human()
    bird_objects = [Bird(bird_id, BIRD_PARAMS[bird_id], CHIRP_PROBABILITY_PER_FRAME) for bird_id in BIRDS_TO_SIMULATE if bird_id in BIRD_PARAMS]
    world = World(MODEL_RADIUS, human, bird_objects)

    static_background = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    static_background.fill((25, 28, 35))
    pygame.draw.circle(static_background, (20, 40, 80), (VIEW_WIDTH // 2, VIEW_HEIGHT // 2), WORLD_RADIUS)
    for pos_px in led_view_positions:
        pygame.draw.circle(static_background, (50, 50, 50), pos_px, 1)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

        world.human.update_position(view_to_model(pygame.mouse.get_pos()))
        world.update()

        final_led_colors = np.zeros((NUM_LEDS, 3), dtype=int)
        brightness_map = np.zeros(NUM_LEDS, dtype=float)
        winner_map = np.full(NUM_LEDS, -1, dtype=int)
        bird_centers = [np.argmin(np.linalg.norm(led_model_positions - bird.position, axis=1)) for bird in world.birds]

        for i, bird in enumerate(world.birds):
            center_idx = bird_centers[i]
            _, num_pixels = bird.get_current_light_pattern()
            spread = (num_pixels * 3) // 2
            brightness = 0.6
            if bird.state == "CHIRPING": brightness = bird.current_brightness
            elif bird.state == "FLEEING": brightness = 1.0

            for j in range(-spread, spread + 1):
                led_idx = center_idx + j
                if 0 <= led_idx < NUM_LEDS:
                    falloff = (spread - abs(j)) / spread if spread > 0 else 1.0
                    final_brightness = brightness * falloff
                    if final_brightness > brightness_map[led_idx]:
                        brightness_map[led_idx], winner_map[led_idx] = final_brightness, i

        for led_idx in range(NUM_LEDS):
            bird_idx = winner_map[led_idx]
            if bird_idx != -1:
                bird = world.birds[bird_idx]
                pixel_offset = (led_idx - bird_centers[bird_idx]) // 3
                pattern, _ = bird.get_current_light_pattern()
                total_pixels = sum(p[1] for p in pattern)
                if total_pixels > 0:
                    color_type, start_pixel = 'b', -total_pixels // 2
                    for p_type, p_count in pattern:
                        if start_pixel <= pixel_offset < start_pixel + p_count:
                            color_type = p_type; break
                        start_pixel += p_count
                    color = bird.accent_color if color_type == 'a' else bird.base_color
                    final_led_colors[led_idx] = np.clip(color * brightness_map[led_idx], 0, 255)

        debug_surface.blit(static_background, (0, 0))
        for bird in world.birds:
            pos_px = model_to_view(bird.position)
            size_px = max(bird.params['size'] * 2.5, DEBUG_MIN_BIRD_SIZE_PX)
            pygame.draw.circle(debug_surface, bird.base_color, pos_px, size_px)
            pygame.draw.circle(debug_surface, bird.accent_color, pos_px, size_px * 0.4)
        pygame.draw.circle(debug_surface, (255, 255, 255), model_to_view(world.human.position), 10)
        
        art_surface.fill((5, 8, 15))
        pygame.draw.circle(art_surface, (20, 40, 80), (VIEW_WIDTH // 2, VIEW_HEIGHT // 2), WORLD_RADIUS)
        for i, pos_px in enumerate(led_view_positions):
            if np.any(final_led_colors[i] > 5):
                pygame.draw.circle(art_surface, final_led_colors[i], pos_px, 2)

        screen.blit(debug_surface, (0, 0)); screen.blit(art_surface, (VIEW_WIDTH, 0))
        pygame.display.flip()
        clock.tick(60)
        
    pygame.quit()

if __name__ == '__main__':
    main()