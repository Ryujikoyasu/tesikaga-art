import numpy as np
import random
from src.objects import Human

class World:
    """
    Manages all simulation objects, tracks them over time, and enforces world rules.
    This is the "environment" or "stage" where the actors live.
    """
    def __init__(self, model_radius, birds):
        self.model_radius = model_radius
        self.birds = birds
        self.humans = []
        
        # For tracking objects over time
        self.previous_humans = {} # Stores {id: Human} from the last frame
        self.next_human_id = 0

        # The World is responsible for setting the initial positions of the actors.
        for bird in self.birds:
            bird.position = self._get_random_position()
            bird.target_position = bird.position

    def update_humans(self, detected_objects: np.ndarray):
        
        current_humans_by_id = {}
        matched_ids = set()

        # 1. 前フレームのHumanと、現在の検出物体をマッチング
        for obj_data in detected_objects:
            current_pos = obj_data[0:2]
            current_size = obj_data[2]
            
            best_match_id = None
            min_dist = 0.5 # マッチングする最大距離

            for human_id, human in self.previous_humans.items():
                if human_id in matched_ids: continue
                
                dist = np.linalg.norm(current_pos - human.position)
                if dist < min_dist:
                    min_dist = dist
                    best_match_id = human_id
            
            # 2. マッチしたら、情報更新 & 速度などを計算
            if best_match_id is not None:
                matched_ids.add(best_match_id)
                last_human = self.previous_humans[best_match_id]

                # 速度とサイズの変化を計算 (60.0はフレームレート)
                velocity = (current_pos - last_human.position) * 60.0
                size_change = current_size - last_human.size

                # 前フレームの滑らかな速度を使って、新しい速度を平滑化する
                last_smooth_velocity = last_human.smooth_velocity
                smooth_vel = last_smooth_velocity * 0.9 + velocity * 0.1 # 90%は過去を維持、10%だけ新しい情報を反映
                
                # 新しいHumanオブジェクトを作成
                new_human = Human(current_pos, smooth_vel, current_size, size_change)
                # 計算したばかりの生の速度も保持しておく（次回の平滑化計算のため）
                new_human.smooth_velocity = smooth_vel

                current_humans_by_id[best_match_id] = new_human

            # 3. マッチしなかったら、新規Humanとして登録
            else:
                # 新規オブジェクトの速度は0, size_changeも0
                new_human = Human(current_pos, np.array([0.0, 0.0]), current_size, 0.0)
                current_humans_by_id[self.next_human_id] = new_human
                self.next_human_id += 1

        # 4. self.humansリストを更新し、前フレーム情報を保存
        self.humans = list(current_humans_by_id.values())
        self.previous_humans = current_humans_by_id

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
        
        # 2. Update position based on velocity, but only if the bird is not chirping.
        if bird.state != "CHIRPING":
            bird.position += bird.velocity

        # 3. Apply hard boundary enforcement
        dist_from_center_after_move = np.linalg.norm(bird.position)
        if dist_from_center_after_move > self.model_radius:
            bird.position = bird.position / dist_from_center_after_move * self.model_radius
            bird.velocity *= -0.5 # Lose energy on impact

    def update(self, pixel_model_positions):
        """The main update loop for the entire simulation."""
        pixel_centers = [np.argmin(np.linalg.norm(pixel_model_positions - bird.position, axis=1)) for bird in self.birds]

        # 1. First, update the AI of all birds to determine their intentions.
        for i, bird in enumerate(self.birds):
            bird.update(self.humans, self.birds, i, pixel_centers)
        
        # 2. Then, apply the world's physics and rules to each bird.
        for bird in self.birds:
            self._apply_physics_and_constraints(bird)