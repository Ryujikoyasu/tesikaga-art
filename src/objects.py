import pygame
import numpy as np
import random
import os

class Human:
    """Represents the user in the simulation. An "actor" in the world."""
    def __init__(self):
        self.position = np.array([0.0, 0.0])
        self.still_timer = 0
        self.last_position = np.array([0.0, 0.0])

    def update_position(self, model_space_pos):
        if np.linalg.norm(model_space_pos - self.last_position) < 0.01:
            self.still_timer += 1
        else:
            self.still_timer = 0
        self.last_position = model_space_pos
        self.position = model_space_pos

class Bird:
    """
    Represents a single bird as an AI agent. An "actor" in the world.
    It is only responsible for its own behavior and intentions.
    """
    def __init__(self, bird_id, params, chirp_probability):
        self.id = bird_id
        self.params = params
        self.chirp_probability = chirp_probability

        # Visual and personality parameters
        self.base_color = np.array(self.params['base_color'])
        self.accent_color = np.array(self.params['accent_color'])
        self.base_pixel_count = self.params['base_pixel_count']
        self.color_pattern = self.params['color_pattern']
        self.chirp_color_pattern = self.params.get('chirp_color_pattern', self.color_pattern)
        self.speed = self.params['movement_speed'] / 60.0
        self.approach_speed = self.params['approach_speed'] / 60.0
        self.curiosity = self.params['curiosity']
        self.caution_distance = self.params['caution_distance']
        self.flee_distance = self.params['flee_distance']
        self.chirp_patterns = self.params.get('chirp_pattern', {})

        # State initialization
        self.position = np.array([0.0, 0.0])
        self.velocity = np.array([0.0, 0.0])
        self.target_position = self.position
        self.state = "IDLE"
        self.action_timer = random.randint(180, 400)
        
        # Playback tracking
        self.chirp_playback_time = 0.0
        self.current_brightness = 0.0
        self.active_pattern_key = None 

        # Load sounds
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sounds = {}
        try:
            for key, path in self.params.get('sound_files', {}).items():
                abs_path = os.path.join(project_root, path)
                self.sounds[key] = pygame.mixer.Sound(abs_path)
        except Exception as e:
            print(f"ERROR loading sound for {self.id} at '{abs_path}': {e}")

    def get_current_light_pattern(self):
        """Returns the appropriate light pattern and pixel count based on the current state."""
        if self.state == "CHIRPING":
            dynamic_pixel_count = int(self.base_pixel_count * (1 + self.current_brightness * self.params['size'] * 0.5))
            return self.chirp_color_pattern, dynamic_pixel_count
        return self.color_pattern, self.base_pixel_count

    def update(self, human, all_birds):
        """Updates the bird's internal state and intended velocity."""
        distance_to_human = np.linalg.norm(self.position - human.position)
        
        if self.state not in ["CHIRPING", "FLEEING"]:
            if distance_to_human < self.flee_distance: self.state = "FLEEING"
            elif distance_to_human < self.caution_distance: self.state = "CAUTION"
            elif human.still_timer > 180 and random.random() < self.curiosity: self.state = "CURIOUS"
        
        self.action_timer -= 1

        if self.state == "IDLE":
            self.velocity *= 0.8
            if self.action_timer <= 0:
                self.state = "FORAGING" if random.random() < 0.7 else "EXPLORING"
                self.action_timer = random.randint(120, 300) if self.state == "FORAGING" else random.randint(180, 400)
                if self.state == "EXPLORING":
                    distance = random.uniform(1.5, 4.0)
                    angle = random.uniform(0, 2 * np.pi)
                    self.target_position = self.position + np.array([np.cos(angle), np.sin(angle)]) * distance
        elif self.state == "FORAGING":
            if random.random() < 0.1: self.velocity += (np.random.rand(2) - 0.5) * 0.02
            else: self.velocity *= 0.7
            if self.action_timer <= 0: self.state = "IDLE"; self.action_timer = random.randint(180, 400)
        elif self.state == "EXPLORING":
            direction_vec = self.target_position - self.position
            if np.linalg.norm(direction_vec) < 0.2: self.state = "IDLE"; self.action_timer = random.randint(180, 400)
            else: self.velocity += direction_vec / np.linalg.norm(direction_vec) * self.speed * 0.1
        elif self.state == "CURIOUS":
            direction_vec = human.position - self.position; dist = np.linalg.norm(direction_vec)
            if dist < self.caution_distance * 0.8: self.state = "IDLE"; self.action_timer = random.randint(180, 400)
            else: self.velocity += direction_vec / dist * self.approach_speed * 0.1
            if human.still_timer == 0: self.state = "CAUTION"
        elif self.state == "FLEEING":
            self.velocity += (self.position - human.position) / distance_to_human * self.speed * 0.3
            if distance_to_human > self.flee_distance * 1.5: self.state = "CAUTION"
        elif self.state == "CAUTION":
            self.velocity *= 0.8
            if distance_to_human > self.caution_distance * 1.2: self.state = "IDLE"
        elif self.state == "CHIRPING":
            self.velocity *= 0.8
            self.chirp_playback_time += 1.0 / 60.0
            self.current_brightness = 0.0
            active_pattern = self.chirp_patterns.get(self.active_pattern_key, [])
            for i in range(len(active_pattern) - 1):
                start_time, start_bright = active_pattern[i]; end_time, end_bright = active_pattern[i+1]
                if start_time <= self.chirp_playback_time < end_time:
                    time_delta = end_time - start_time
                    progress = (self.chirp_playback_time - start_time) / time_delta if time_delta > 0 else 0
                    self.current_brightness = start_bright + (end_bright - start_bright) * progress
                    break
            if self.action_timer <= 0: self.state = "IDLE"; self.current_brightness = 0.0; self.active_pattern_key = None

        if self.state in ["IDLE", "FORAGING"] and self.action_timer > 0 and random.random() < self.chirp_probability:
            self.active_pattern_key = 'drumming' if self.id == 'kumagera' else 'default'
            if self.active_pattern_key in self.chirp_patterns:
                self.state = "CHIRPING"
                self.action_timer = int(self.chirp_patterns[self.active_pattern_key][-1][0] * 60)
                self.chirp_playback_time = 0.0
                if self.active_pattern_key in self.sounds: self.sounds[self.active_pattern_key].play()