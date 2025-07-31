
import pygame
import numpy as np

class Renderer:
    """
    Handles all rendering tasks for the simulation, including debug and artistic views.
    """
    def __init__(self, settings, pixel_model_positions, pixel_view_positions):
        """
        Initializes the Renderer with necessary settings and pre-calculated positions.
        
        Args:
            settings (dict): The main settings dictionary.
            pixel_model_positions (np.array): (N, 2) array of pixel positions in model space.
            pixel_view_positions (np.array): (N, 2) array of pixel positions in Pygame view space.
        """
        # Settings
        self.view_width = settings.get('view_width', 800)
        self.view_height = settings.get('view_height', 800)
        self.world_radius = 350 # This is a view-space constant
        self.model_radius = settings['model_diameter'] / 2.0
        self.min_brightness_falloff = settings.get('min_brightness_falloff', 0.3)
        self.debug_min_bird_size_px = 6.0

        # Pixel data
        self.pixel_model_positions = pixel_model_positions
        self.pixel_view_positions = pixel_view_positions
        self.num_pixels = len(pixel_model_positions)

        # Surfaces for drawing
        self.debug_surface = pygame.Surface((self.view_width, self.view_height))
        self.art_surface = pygame.Surface((self.view_width, self.view_height))
        
        # Pre-render static backgrounds
        self._create_static_backgrounds()

        # Calculated colors from the last frame, can be fetched for real-time output
        self.final_pixel_colors = np.zeros((self.num_pixels, 3), dtype=int)

    def _model_to_view(self, pos_m):
        """Converts a position from model space to view (pixel) space."""
        return pos_m * (self.world_radius / self.model_radius) + np.array([self.view_width / 2, self.view_height / 2])

    def _create_static_backgrounds(self):
        """Creates the non-changing background elements for both views."""
        # Debug view background
        self.static_debug_bg = pygame.Surface((self.view_width, self.view_height))
        self.static_debug_bg.fill((25, 28, 35))
        pygame.draw.circle(self.static_debug_bg, (20, 40, 80), (self.view_width // 2, self.view_height // 2), self.world_radius)
        for pos_px in self.pixel_view_positions:
            pygame.draw.circle(self.static_debug_bg, (50, 50, 50), pos_px, 2)

        # Artistic view background
        self.static_art_bg = pygame.Surface((self.view_width, self.view_height))
        self.static_art_bg.fill((5, 8, 15))
        pygame.draw.circle(self.static_art_bg, (20, 40, 80), (self.view_width // 2, self.view_height // 2), self.world_radius)

    def calculate_pixel_colors(self, world):
        """
        Calculates the final color for each pixel based on the state of the world.
        This updates the internal `self.final_pixel_colors` attribute.
        """
        brightness_map = np.zeros(self.num_pixels, dtype=float)
        winner_map = np.full(self.num_pixels, -1, dtype=int)
        
        pixel_centers = [np.argmin(np.linalg.norm(self.pixel_model_positions - bird.position, axis=1)) for bird in world.birds]

        for i, bird in enumerate(world.birds):
            center_idx = pixel_centers[i]
            _, num_pixels_pattern = bird.get_current_light_pattern()
            spread = num_pixels_pattern // 2
            
            brightness = 0.6
            if bird.state == "CHIRPING": brightness = bird.current_brightness
            elif bird.state == "FLEEING": brightness = 1.0

            for j in range(-spread, spread + 1):
                pixel_idx = center_idx + j
                if 0 <= pixel_idx < self.num_pixels:
                    linear_falloff = (spread - abs(j)) / spread if spread > 0 else 1.0
                    falloff = self.min_brightness_falloff + (1.0 - self.min_brightness_falloff) * linear_falloff
                    final_brightness = brightness * falloff
                    if final_brightness > brightness_map[pixel_idx]:
                        brightness_map[pixel_idx] = final_brightness
                        winner_map[pixel_idx] = i

        # Reset colors and then fill them in
        self.final_pixel_colors.fill(0)
        for pixel_idx in range(self.num_pixels):
            bird_idx = winner_map[pixel_idx]
            if bird_idx != -1:
                bird = world.birds[bird_idx]
                pixel_offset = pixel_idx - pixel_centers[bird_idx]
                pattern, _ = bird.get_current_light_pattern()
                total_pixels = sum(p[1] for p in pattern)
                
                if total_pixels > 0:
                    color_type, start_pixel = 'b', -total_pixels // 2
                    for p_type, p_count in pattern:
                        if start_pixel <= pixel_offset < start_pixel + p_count:
                            color_type = p_type
                            break
                        start_pixel += p_count
                    
                    color = bird.accent_color if color_type == 'a' else bird.base_color
                    self.final_pixel_colors[pixel_idx] = np.clip(color * brightness_map[pixel_idx], 0, 255)

    def get_final_colors(self):
        """Returns the latest calculated pixel colors."""
        return self.final_pixel_colors

    def render(self, screen, world):
        """
        Calculates all colors and draws the full scene to the provided screen.
        """
        # 1. Calculate the light/color values for this frame
        self.calculate_pixel_colors(world)

        # 2. Draw the Debug View
        self.debug_surface.blit(self.static_debug_bg, (0, 0))
        for bird in world.birds:
            pos_px = self._model_to_view(bird.position)
            size_px = max(bird.params['size'] * 2.5, self.debug_min_bird_size_px)
            pygame.draw.circle(self.debug_surface, bird.base_color, pos_px, size_px)
            pygame.draw.circle(self.debug_surface, bird.accent_color, pos_px, size_px * 0.4)
        for human in world.humans:
            pygame.draw.circle(self.debug_surface, (255, 255, 255), self._model_to_view(human.position), 10)

        # 3. Draw the Artistic View
        self.art_surface.blit(self.static_art_bg, (0, 0))
        for i, pos_px in enumerate(self.pixel_view_positions):
            if np.any(self.final_pixel_colors[i] > 5): # Only draw if color is not black
                pygame.draw.circle(self.art_surface, self.final_pixel_colors[i], pos_px, 4)

        # 4. Blit both views to the main screen
        screen.blit(self.debug_surface, (0, 0))
        screen.blit(self.art_surface, (self.view_width, 0))
        
        # 5. Update the display
        pygame.display.flip()
