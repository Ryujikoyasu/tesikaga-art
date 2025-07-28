import pygame
import numpy as np
import random
import os
from .config import *
from .config import CHIRP_PROBABILITY_PER_FRAME

class Human:
    """
    Represents the user in the simulation.
    Tracks its position in the model space and how long it has been still.
    """
    def __init__(self):
        self.position = np.array([0.0, 0.0]) # Position in meters
        self.still_timer = 0 # Frames the user has been still
        self.last_position = np.array([0.0, 0.0])

    def update_position(self, model_space_pos):
        # Check if the mouse has moved significantly
        if np.linalg.norm(model_space_pos - self.last_position) < 0.01:
            self.still_timer += 1
        else:
            self.still_timer = 0
        self.last_position = model_space_pos
        self.position = model_space_pos

class Bird:
    """
    Represents a single bird in the simulation.
    Manages its own state, movement, and interaction based on parameters from config.
    """
    def __init__(self, bird_id, params):
        self.id = bird_id
        self.params = params
        
        # Load visual and physical parameters
        self.led_color = np.array(self.params['led_color'])
        self.accent_color = np.array(self.params['accent_color'])
        self.color_ratio = self.params['color_ratio']
        self.speed = self.params['movement_speed'] / 60.0 # Convert m/s to m/frame
        self.approach_speed = self.params['approach_speed'] / 60.0
        self.curiosity = self.params['curiosity']
        self.caution_distance = self.params['caution_distance']
        self.flee_distance = self.params['flee_distance']
        
        # NEW: Now correctly expects a dictionary of named patterns
        self.chirp_patterns = self.params.get('chirp_pattern', {})

        # Initialize state and position
        self.position = self._get_random_position()
        self.velocity = np.array([0.0, 0.0])
        self.target_position = self.position
        
        self.state = "IDLE"
        self.action_timer = random.randint(*IDLE_DURATION_RANGE_FRAMES)
        
        # Playback tracking
        self.chirp_playback_time = 0.0
        self.current_brightness = 0.0
        self.active_pattern_key = None # Tracks which pattern ('default', 'drumming') is playing

        # Load all associated sound files
        self.sounds = {}
        try:
            for key, path in self.params['sound_files'].items():
                abs_path = os.path.join(PROJECT_ROOT, path)
                self.sounds[key] = pygame.mixer.Sound(abs_path)
        except Exception as e:
            print(f"ERROR loading sound for bird {self.id} at '{abs_path}': {e}")

    def _get_random_position(self):
        """Places the bird at a random point within the pond's radius."""
        r = MODEL_RADIUS * np.sqrt(random.random())
        theta = random.random() * 2 * np.pi
        return np.array([r * np.cos(theta), r * np.sin(theta)])
    
    def _apply_boundary_repulsion(self):
        """Applies a soft force pushing the bird away from the pond's edge."""
        dist_from_center = np.linalg.norm(self.position)
        if dist_from_center > MODEL_RADIUS * 0.8:
            repulsion_strength = (dist_from_center - MODEL_RADIUS * 0.8) / (MODEL_RADIUS * 0.2)
            self.velocity += (-self.position / dist_from_center) * repulsion_strength * 0.01

    def update(self, human, all_birds):
        """The main AI and physics update loop for the bird."""
        distance_to_human = np.linalg.norm(self.position - human.position)
        
        # --- 1. State Transitions (Based on external events) ---
        # These transitions can interrupt the current action.
        if self.state not in ["CHIRPING", "FLEEING"]:
            if distance_to_human < self.flee_distance:
                self.state = "FLEEING"
            elif distance_to_human < self.caution_distance:
                self.state = "CAUTION"
            elif human.still_timer > HUMAN_STILLNESS_THRESHOLD_FRAMES and random.random() < self.curiosity:
                self.state = "CURIOUS"
        
        # --- 2. State Logic (Execute behavior based on current state) ---
        self.action_timer -= 1

        if self.state == "IDLE":
            self.velocity *= 0.8 # Come to a gentle stop
            if self.action_timer <= 0:
                # Decide what to do next: explore or forage
                self.state = "FORAGING" if random.random() < 0.7 else "EXPLORING"
                self.action_timer = random.randint(*(FORAGING_DURATION_RANGE_FRAMES if self.state == "FORAGING" else IDLE_DURATION_RANGE_FRAMES))
                if self.state == "EXPLORING":
                    distance = random.uniform(*EXPLORE_DISTANCE_RANGE_METERS)
                    angle = random.uniform(0, 2 * np.pi)
                    self.target_position = self.position + np.array([np.cos(angle), np.sin(angle)]) * distance
        
        elif self.state == "FORAGING":
            # Almost still, with tiny, sudden "pecking" movements
            if random.random() < 0.1: self.velocity += (np.random.rand(2) - 0.5) * 0.02
            else: self.velocity *= 0.7
            if self.action_timer <= 0: self.state = "IDLE"; self.action_timer = random.randint(*IDLE_DURATION_RANGE_FRAMES)

        elif self.state == "EXPLORING":
            direction_vec = self.target_position - self.position
            if np.linalg.norm(direction_vec) < 0.2:
                self.state = "IDLE"; self.action_timer = random.randint(*IDLE_DURATION_RANGE_FRAMES)
            else:
                self.velocity += direction_vec / np.linalg.norm(direction_vec) * self.speed * 0.1
        
        elif self.state == "CURIOUS":
            direction_vec = human.position - self.position; dist = np.linalg.norm(direction_vec)
            if dist < self.caution_distance * 0.8: self.state = "IDLE"; self.action_timer = random.randint(*IDLE_DURATION_RANGE_FRAMES)
            else: self.velocity += direction_vec / dist * self.approach_speed * 0.1
            if human.still_timer == 0: self.state = "CAUTION"

        elif self.state == "FLEEING":
            self.velocity += (self.position - human.position) / distance_to_human * self.speed * 0.3
            if distance_to_human > self.flee_distance * 1.5: self.state = "CAUTION"
        
        elif self.state == "CAUTION":
            self.velocity *= 0.8 # Slow down
            if distance_to_human > self.caution_distance * 1.2: self.state = "IDLE"
        
        elif self.state == "CHIRPING":
            self.velocity *= 0.8 # Stop to perform
            self.chirp_playback_time += 1.0 / 60.0 # Assumes 60 FPS
            self.current_brightness = 0.0
            
            # Use the currently active pattern
            active_pattern = self.chirp_patterns.get(self.active_pattern_key, [])
            for i in range(len(active_pattern) - 1):
                start_time, start_bright = active_pattern[i]
                end_time, end_bright = active_pattern[i+1]
                if start_time <= self.chirp_playback_time < end_time:
                    # Original code might have an error here.
                    # This ensures it doesn't divide by zero if start and end times are identical.
                    time_delta = end_time - start_time
                    progress = (self.chirp_playback_time - start_time) / time_delta if time_delta > 0 else 0
                    self.current_brightness = start_bright + (end_bright - start_bright) * progress
                    break
            
            if self.action_timer <= 0:
                self.state = "IDLE"
                self.current_brightness = 0.0
                self.active_pattern_key = None # Reset the active pattern

        # --- 3. Spontaneous Actions ---
        # Decide if the bird should start a special action (like chirping)
        if self.state in ["IDLE", "FORAGING"] and self.action_timer > 0 and random.random() < CHIRP_PROBABILITY_PER_FRAME:
            # Determine which action to perform
            # For Kumagera, the special action is drumming. For others, it's the default sound.
            self.active_pattern_key = 'drumming' if self.id == 'kumagera' else 'default'
            
            if self.active_pattern_key in self.chirp_patterns:
                self.state = "CHIRPING"
                # Set duration based on the length of the selected light pattern
                self.action_timer = int(self.chirp_patterns[self.active_pattern_key][-1][0] * 60)
                self.chirp_playback_time = 0.0
                
                # Play the corresponding sound
                if self.active_pattern_key in self.sounds:
                    self.sounds[self.active_pattern_key].play()

        # --- 4. Apply Physics and Constraints ---
        self._apply_boundary_repulsion()
        self.position += self.velocity
        self.check_bounds()

    def check_bounds(self):
        """Enforces a hard boundary at the pond's edge."""
        dist = np.linalg.norm(self.position)
        if dist > MODEL_RADIUS:
            self.position = self.position / dist * MODEL_RADIUS
            self.velocity *= -0.5 # Lose energy on impact