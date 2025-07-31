import numpy as np
import random

class World:
    """
    Manages all simulation objects and enforces world rules like boundaries.
    This is the "environment" or "stage" where the actors live.
    """
    def __init__(self, model_radius, human, birds):
        self.model_radius = model_radius
        self.human = human
        self.birds = birds
        # The World is responsible for setting the initial positions of the actors.
        for bird in self.birds:
            bird.position = self._get_random_position()
            bird.target_position = bird.position

    def _get_random_position(self):
        """Returns a random position within the world's radius."""
        r = self.model_radius * np.sqrt(random.random())
        theta = random.random() * 2 * np.pi
        return np.array([r * np.cos(theta), r * np.sin(theta)])

    def _apply_physics_and_constraints(self, bird):
        """Applies world rules (boundaries, physics) to a single bird."""
        # 1. Apply soft boundary repulsion
        dist_from_center = np.linalg.norm(bird.position)
        if dist_from_center > self.model_radius * 0.8:
            repulsion_strength = (dist_from_center - self.model_radius * 0.8) / (self.model_radius * 0.2)
            bird.velocity += (-bird.position / dist_from_center) * repulsion_strength * 0.01
        
        # 2. Update position based on velocity
        bird.position += bird.velocity

        # 3. Apply hard boundary enforcement
        dist_from_center_after_move = np.linalg.norm(bird.position)
        if dist_from_center_after_move > self.model_radius:
            bird.position = bird.position / dist_from_center_after_move * self.model_radius
            bird.velocity *= -0.5 # Lose energy on impact

    def update(self, pixel_model_positions): # ★引数を追加
        """The main update loop for the entire simulation."""
        # 毎フレーム、全鳥の物理ピクセル位置を計算
        pixel_centers = [np.argmin(np.linalg.norm(pixel_model_positions - bird.position, axis=1)) for bird in self.birds]

        # 1. First, update the AI of all birds to determine their intentions.
        # 鳥のAIに、物理世界の情報を渡して更新
        for i, bird in enumerate(self.birds):
            bird.update(self.human, self.birds, i, pixel_centers) # ★引数を追加
        
        # 2. Then, apply the world's physics and rules to each bird.
        for bird in self.birds:
            self._apply_physics_and_constraints(bird)