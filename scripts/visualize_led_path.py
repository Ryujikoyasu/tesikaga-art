import pygame
import csv
import numpy as np
import sys

# プロジェクトのルートディレクトリをパスに追加し、'src'モジュールをインポート可能にする
sys.path.append('.')
from src.config import SCREEN_WIDTH, SCREEN_HEIGHT, WORLD_RADIUS, BLUE, BLACK, GRAY, WHITE, LED_FILE_PATH

def visualize():
    """
    Reads led_positions.csv and provides a clear visualization of the generated path,
    including the crucial anchor points.
    """
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("LED Path Visualizer - Press ESC or close window to exit")
    clock = pygame.time.Clock()

    # --- Load LED positions from the CSV file ---
    led_positions = []
    try:
        with open(LED_FILE_PATH, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header
            for row in reader:
                led_positions.append((float(row[0]), float(row[1])))
    except FileNotFoundError:
        print(f"Error: '{LED_FILE_PATH}' not found.")
        print("Please run the generation script first: python -m scripts.generate_led_positions")
        return

    if not led_positions:
        print("CSV file is empty or could not be read.")
        return

    print(f"Loaded {len(led_positions)} LED positions for visualization.")

    # --- Identify anchor points for special highlighting ---
    # According to the spec: 0m, 5m, 10m correspond to LEDs 0, 300, 600
    anchor_indices = [0, 300, 600]
    anchor_positions = []
    for i in anchor_indices:
        if i < len(led_positions):
            anchor_positions.append(led_positions[i])
    
    print(f"Highlighting anchor points (indices {anchor_indices}). Check if they are on the circumference.")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # --- Drawing ---
        screen.fill(BLACK)
        
        # 1. Draw the pond circumference as a blue reference line
        pygame.draw.circle(screen, BLUE, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), WORLD_RADIUS, 2)

        # 2. Draw the entire LED path as a continuous line to check for intersections
        if len(led_positions) > 1:
            # Use anti-aliasing for a smoother line
            pygame.draw.aalines(screen, GRAY, False, led_positions)

        # 3. Draw prominent anchor points on top
        for pos in anchor_positions:
            # Draw a large, unmistakable red circle for each anchor point
            pygame.draw.circle(screen, (255, 0, 0), (int(pos[0]), int(pos[1])), 8) 
            pygame.draw.circle(screen, WHITE, (int(pos[0]), int(pos[1])), 8, 1)

        pygame.display.flip()
        clock.tick(30) # No need for high FPS for a static view

    pygame.quit()

if __name__ == "__main__":
    visualize()