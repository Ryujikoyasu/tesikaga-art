# main_hybrid.py
# The ultimate debug tool: Runs the simulation with full graphics AND
# sends the LED data to a real LED strip simultaneously.

import pygame
import serial
import time
import numpy as np

# Import everything from our simulation logic and setup
from src.config import *
from src.objects import Human, Bird

# Import the light calculation logic from the original main.py
# (Ensure main.py is in the same directory or accessible)
from main import calculate_bird_light, model_to_view, view_to_model

# --- Serial Communication Settings ---
SERIAL_PORT = '/dev/ttyACM0'  # Your Arduino's port on Ubuntu
BAUD_RATE = 115200
# We only send data for the first physical strip
NUM_PIXELS_TO_SEND = 100 
MAGIC_BYTE = b'\xAB'          # Must match the Arduino code

def main():
    # --- Pygame Setup ---
    pygame.init()
    pygame.mixer.init() # Needed for Bird sounds
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    debug_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    art_surface = pygame.Surface((VIEW_WIDTH, VIEW_HEIGHT))
    pygame.display.set_caption("HYBRID MODE | Left: Debug | Right: Art Sim | Real LED: SYNCED")
    clock = pygame.time.Clock()
    
    # --- Serial Port Setup ---
    ser = None
    try:
        print(f"Connecting to Arduino on {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1) # Non-blocking timeout
        time.sleep(2) # Wait for Arduino to reset
        print("Arduino connection successful.")
    except serial.SerialException as e:
        print(f"WARNING: Could not connect to Arduino. Running in simulation-only mode. Error: {e}")
        ser = None # Ensure ser is None if connection fails

    # --- Simulation Asset Loading ---
    print("Loading simulation assets...")
    try:
        led_model_positions = np.loadtxt(LED_FILE_PATH, delimiter=',', skiprows=1)
    except Exception as e:
        print(f"FATAL: Could not load LED data from '{LED_FILE_PATH}'. Quitting. Error: {e}")
        return
    
    # We will display all LEDs in simulation, but only send the first segment
    led_view_positions = np.apply_along_axis(model_to_view, 1, led_model_positions)
    num_total_leds = len(led_view_positions)
    
    human = Human()
    birds = [Bird(bird_id, BIRD_PARAMS[bird_id]) for bird_id in BIRDS_TO_SIMULATE if bird_id in BIRD_PARAMS]
    print("Simulation started. Close the window or press Ctrl+C to stop.")

    # --- Main Loop ---
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- Update simulation state ---
        # In this hybrid mode, the mouse still controls the human for easy testing
        human.update_position(view_to_model(pygame.mouse.get_pos()))
        for bird in birds:
            bird.update(human, birds)

        # --- Calculate final LED colors using the "Winner-Takes-All" logic ---
        # This calculation is for ALL LEDs in the simulation for accurate visuals
        led_color_array = np.zeros((num_total_leds, 3), dtype=float)
        led_brightness_buffer = np.zeros(num_total_leds, dtype=float)

        for bird in birds:
            distances_m = np.linalg.norm(led_model_positions - bird.position, axis=1)
            center_led_index = np.argmin(distances_m)
            
            bird_light_colors, bird_light_brightness = calculate_bird_light(bird, center_led_index, num_total_leds)
            
            update_mask = bird_light_brightness > led_brightness_buffer
            led_color_array[update_mask] = bird_light_colors[update_mask]
            led_brightness_buffer[update_mask] = bird_light_brightness[update_mask]
        
        final_led_colors = np.clip(led_color_array, 0, 255).astype('uint8')
        
        # --- Send data to REAL LEDs (if connected) ---
        if ser:
            # Extract only the data for the first strip
            colors_to_send = final_led_colors[:NUM_PIXELS_TO_SEND]
            data_packet = MAGIC_BYTE + colors_to_send.tobytes()
            try:
                ser.write(data_packet)
            except serial.SerialException as e:
                print(f"Error writing to serial port: {e}")
                ser.close()
                ser = None # Stop trying to send data

        # --- Draw simulation on screen ---
        debug_surface.fill((25, 28, 35))
        art_surface.fill((5, 8, 15))
        
        # Draw the pond on both views
        pond_center_px = (VIEW_WIDTH // 2, VIEW_HEIGHT // 2)
        pygame.draw.circle(debug_surface, (20, 40, 80), pond_center_px, WORLD_RADIUS)
        pygame.draw.circle(art_surface, (20, 40, 80), pond_center_px, WORLD_RADIUS)
        
        # Draw debug info (full LED path and birds)
        pygame.draw.lines(debug_surface, (70, 70, 80), False, led_view_positions, 1)
        for bird in birds:
            bird_pos_px = model_to_view(bird.position)
            pygame.draw.circle(debug_surface, bird.led_color, (int(bird_pos_px[0]), int(bird_pos_px[1])), 8)
        human_pos_px = model_to_view(human.position)
        pygame.draw.circle(debug_surface, (255, 255, 255), (int(human_pos_px[0]), int(human_pos_px[1])), 10)

        # Draw artistic view (the calculated light)
        for i, pos_px in enumerate(led_view_positions):
            color = final_led_colors[i]
            if np.any(color > 5): # Only draw if the LED is lit
                pygame.draw.circle(art_surface, color, (int(pos_px[0]), int(pos_px[1])), 2)

        # Blit surfaces to the main screen and update
        screen.blit(debug_surface, (0, 0))
        screen.blit(art_surface, (VIEW_WIDTH, 0))
        pygame.display.flip()
        
        clock.tick(60) # Maintain a consistent frame rate

    # --- Cleanup ---
    print("\nStopping simulation...")
    if ser and ser.is_open:
        # Turn off all LEDs on the physical strip before quitting
        off_colors = np.zeros((NUM_PIXELS_TO_SEND, 3), dtype='uint8')
        ser.write(MAGIC_BYTE + off_colors.tobytes())
        ser.close()
        print("Serial port closed.")
    pygame.quit()

if __name__ == '__main__':
    main()