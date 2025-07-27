import pygame
import numpy as np
import random
# The dot '.' indicates a relative import from the same package
from .config import *

def noise(x, y):
    """A simple pseudo-random noise function for wandering"""
    n = np.sin(x * 12.9898 + y * 78.233) * 43758.5453
    return np.sin(n)

class Human:
    """Represents the user, controlled by the mouse."""
    def __init__(self):
        self.position = np.array(pygame.mouse.get_pos())

    def update(self):
        self.position = np.array(pygame.mouse.get_pos())

    def draw(self, screen):
        pygame.draw.circle(screen, WHITE, self.position, 10)

class Bird:
    """Represents a single bird with enhanced AI for more natural movement."""
    def __init__(self, bird_id, params, world_radius):
        self.id = bird_id
        self.params = params
        self.world_radius = world_radius
        
        # Load parameters
        self.name_jp = self.params['name_jp']
        self.led_color = np.array(self.params['led_color'])
        self.accent_color = np.array(self.params['accent_color'])
        self.color_ratio = self.params['color_ratio']
        self.speed = self.params['movement_speed']
        self.caution_distance = self.params['caution_distance']
        self.flee_distance = self.params['flee_distance']
        self.chirp_pattern = self.params.get('chirp_pattern', [(0.1, 1.0), (0.3, 0.0)])

        self.position = self._get_random_position_in_pond()
        self.velocity = np.array([0.0, 0.0])
        self.target_position = self.position

        self.state = "IDLE"
        self.action_timer = random.randint(*IDLE_DURATION_RANGE_FRAMES)
        
        self.chirp_playback_time = 0.0
        self.current_brightness = 0.0

        self.sounds = {}
        try:
            for key, path in self.params['sound_files'].items():
                self.sounds[key] = pygame.mixer.Sound(path)
        except pygame.error as e:
            print(f"Could not load sound for bird {self.id} at {path}: {e}")

    def _get_random_position_in_pond(self):
        r = self.world_radius * np.sqrt(random.random())
        theta = random.random() * 2 * np.pi
        center = np.array([SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2])
        return center + np.array([r * np.cos(theta), r * np.sin(theta)])

    def _apply_boundary_repulsion(self):
        """NEW: Adds a force pushing the bird away from the edge."""
        center = np.array([SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2])
        dist_from_center = np.linalg.norm(self.position - center)
        
        # Start applying repulsion force when the bird is in the outer 20% of the radius
        repulsion_zone_start = self.world_radius * 0.8
        
        if dist_from_center > repulsion_zone_start:
            # The force gets stronger as the bird gets closer to the edge
            repulsion_strength = (dist_from_center - repulsion_zone_start) / (self.world_radius - repulsion_zone_start)
            force_direction = (center - self.position) / dist_from_center
            
            # Apply the force to the velocity
            self.velocity += force_direction * repulsion_strength * 0.5 # 0.5 is a damping factor
    
    def update(self, human, all_birds):
        distance_to_human = np.linalg.norm(self.position - human.position)
        
        if self.state != "CHIRPING":
            if distance_to_human < self.flee_distance: self.state = "FLEEING"
            elif distance_to_human < self.caution_distance and self.state != "FLEEING": self.state = "CAUTION"

        self.action_timer -= 1

        # State logic...
        if self.state == "IDLE":
            self.velocity *= 0.8
            if self.action_timer <= 0:
                self.state = "EXPLORING"
                distance = random.uniform(*EXPLORE_DISTANCE_RANGE_PIXELS)
                angle = random.uniform(0, 2 * np.pi)
                self.target_position = self.position + np.array([np.cos(angle), np.sin(angle)]) * distance
        # ... (other state logic is the same)
        elif self.state == "EXPLORING":
            direction = self.target_position - self.position
            if np.linalg.norm(direction) < 10:
                self.state = "IDLE"
                self.action_timer = random.randint(*IDLE_DURATION_RANGE_FRAMES)
            else:
                self.velocity = direction / np.linalg.norm(direction) * self.speed
        elif self.state == "FLEEING":
            flee_vector = self.position - human.position
            if np.linalg.norm(flee_vector) > 0:
                self.velocity = flee_vector / np.linalg.norm(flee_vector) * self.speed * 2
            if distance_to_human > self.flee_distance * 1.2:
                self.state = "CAUTION"
                self.action_timer = 60
        elif self.state == "CAUTION":
            self.velocity *= 0.9
            if distance_to_human > self.caution_distance:
                self.state = "IDLE"
                self.action_timer = random.randint(*IDLE_DURATION_RANGE_FRAMES) // 2
        elif self.state == "CHIRPING":
            # ... (chirp logic is the same)
            self.velocity = np.array([0.0, 0.0])
            self.chirp_playback_time += 1.0 / 60.0
            self.current_brightness = 0.0
            for i in range(len(self.chirp_pattern) - 1):
                start_time, start_bright = self.chirp_pattern[i]
                end_time, end_bright = self.chirp_pattern[i+1]
                if start_time <= self.chirp_playback_time < end_time:
                    progress = (self.chirp_playback_time - start_time) / (end_time - start_time)
                    self.current_brightness = start_bright + (end_bright - start_bright) * progress
                    break
            if self.action_timer <= 0:
                self.state = "IDLE"
                self.action_timer = random.randint(*IDLE_DURATION_RANGE_FRAMES)
                self.current_brightness = 0.0
        
        # Special action decision
        if self.state == "IDLE" and self.action_timer > 0 and random.random() < CHIRP_PROBABILITY:
            # ... (chirp decision is the same)
            self.state = "CHIRPING"
            self.action_timer = int(self.chirp_pattern[-1][0] * 60)
            self.chirp_playback_time = 0.0
            sound_to_play = 'drumming' if self.id == 'kumagera' else 'default'
            if sound_to_play in self.sounds: self.sounds[sound_to_play].play()
            elif 'call' in self.sounds: self.sounds['call'].play()

        # --- APPLY FORCES and UPDATE POSITION ---
        self._apply_boundary_repulsion() # Call the new function
        self.position += self.velocity
        self.check_bounds() # Final check to prevent any escape

    def check_bounds(self):
        center = np.array([SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2])
        dist_from_center = np.linalg.norm(self.position - center)
        if dist_from_center > self.world_radius:
            normal = (self.position - center) / dist_from_center
            self.position = center + normal * self.world_radius
            self.velocity *= -0.5 # Lose energy on hard impact

    def draw(self, screen):
        pygame.draw.circle(screen, self.led_color.tolist(), (int(self.position[0]), int(self.position[1])), 5)