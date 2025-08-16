import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Circle
import time
import csv

class InteractivePathEditor:
    def __init__(self, num_segments=3):
        # --- Core Parameters ---
        self.num_segments = num_segments
        self.num_total_anchors = self.num_segments + 1

        # --- Constants ---
        self.POND_WIDTH = 6.3
        self.POND_HEIGHT = 5.3
        self.POND_RADIUS_X = self.POND_WIDTH / 2.0
        self.POND_RADIUS_Y = self.POND_HEIGHT / 2.0
        self.SEGMENT_LENGTH = 5.0
        self.LEDS_PER_METER = 60
        self.TOTAL_LENGTH = self.num_segments * self.SEGMENT_LENGTH
        self.TOTAL_POINTS = int(self.TOTAL_LENGTH * self.LEDS_PER_METER)

        # --- Distribute points evenly among segments ---
        segment_points_base = self.TOTAL_POINTS // self.num_segments
        remainder_points = self.TOTAL_POINTS % self.num_segments
        self.segment_points_list = [
            segment_points_base + (1 if i < remainder_points else 0) for i in range(self.num_segments)
        ]

        # --- State Initialization ---
        self.fig, self.ax = plt.subplots(figsize=(11, 10))
        plt.subplots_adjust(right=0.75, top=0.95)
        self.pond_center = np.array([0.0, 0.0])
        self.state = "PLACING_ANCHORS"
        self.pull_radius_factor = 0.1

        # --- Anchor and Path Data ---
        self.anchor_positions = [np.zeros(2) for _ in range(self.num_total_anchors)]
        self.placed_anchor_count = 0
        self.path_vertices = np.zeros((self.TOTAL_POINTS, 2))
        self.anchor_indices = []

        # --- UI State ---
        self.is_dragging = False
        self.drag_info = {}

        # --- Setup ---
        self.setup_plot()
        self.connect_events()
        self.update_display()
        plt.show()

    def setup_plot(self):
        self.ax.set_aspect('equal', adjustable='box')
        self.ax.set_xlim(-self.POND_RADIUS_X - 1, self.POND_RADIUS_X + 1)
        self.ax.set_ylim(-self.POND_RADIUS_Y - 1, self.POND_RADIUS_Y + 1)
        self.pond = Ellipse(self.pond_center, self.POND_WIDTH, self.POND_HEIGHT, 
                              facecolor='lightblue', edgecolor='blue', alpha=0.5, zorder=0)
        self.ax.add_patch(self.pond)
        self.line_artist, = self.ax.plot([], [], color='purple', linewidth=2.5, zorder=1)
        self.anchor_artist = self.ax.scatter([], [], color='black', s=120, zorder=5)
        self.info_text = self.fig.text(0.77, 0.9, '', fontsize=9, verticalalignment='top', fontfamily='monospace')
        self.brush_indicator = Circle((0,0), 0.1, facecolor='red', alpha=0.3, zorder=10, visible=False)
        self.ax.add_patch(self.brush_indicator)

    def connect_events(self):
        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)

    def create_initial_path(self):
        """Generates the initial straight-line path between all anchor points."""
        segments = []
        for i in range(self.num_segments):
            p_start = self.anchor_positions[i]
            p_end = self.anchor_positions[i+1]
            num_points = self.segment_points_list[i]
            segments.append(np.linspace(p_start, p_end, max(2, num_points)))
        
        self.path_vertices = np.vstack(segments)
        
        self.anchor_indices = list(np.cumsum([0] + self.segment_points_list[:-1]))
        self.anchor_indices.append(self.TOTAL_POINTS - 1)

    def update_display(self):
        """Updates all visual elements in the plot."""
        if self.state == "DONE":
            self.line_artist.set_color('lime')
        else:
            self.line_artist.set_color('purple')

        if self.path_vertices.ndim == 2 and self.path_vertices.shape[0] > 1:
            self.line_artist.set_data(self.path_vertices[:, 0], self.path_vertices[:, 1])

        if self.anchor_indices:
            anchor_coords = self.path_vertices[self.anchor_indices]
            self.anchor_artist.set_offsets(anchor_coords)
        else:
            if self.placed_anchor_count > 0:
                offsets = np.array(self.anchor_positions[:self.placed_anchor_count])
                self.anchor_artist.set_offsets(offsets)
            else:
                self.anchor_artist.set_offsets(np.empty((0, 2)))

        # --- Generate dynamic instructions for placing anchors ---
        placing_instruction = ""
        if self.state == "PLACING_ANCHORS":
            # The first N points (0 to N-1) go on the edge
            if self.placed_anchor_count < self.num_segments:
                placing_instruction = f"Click {self.num_segments - self.placed_anchor_count} more point(s) ON THE EDGE."
            else: # The last point (N+1)
                placing_instruction = "Click the final anchor point.\n(Can be inside the pond)."
        
        state_titles = {
            "PLACING_ANCHORS": placing_instruction,
            "EDITING_PATH": "Drag path to shape.\nSCROLL to change brush size.\nPress 'S' to save.",
            "ADJUSTING": "Finalizing path, please wait...",
            "DONE": "SAVED! Final path rendered.\nClose the window."
        }
        
        s_lengths = [self.get_segment_length(i) for i in range(self.num_segments)]
        total_len = sum(s_lengths)
        
        length_info_lines = [f"Segment {i+1}: {s_lengths[i]:6.4f}m" for i in range(self.num_segments)]
        length_info = "\n".join(length_info_lines)

        info = (f"STATE: {self.state}\n\n"
                f"INSTRUCTIONS:\n{state_titles.get(self.state, '')}\n\n"
                f"BRUSH SIZE: {self.pull_radius_factor*100:.1f}%\n\n"
                f"--- LENGTHS (TARGET: {self.SEGMENT_LENGTH:.2f}m) ---\n"
                f"{length_info}\n"
                f"-------------------------------------\n"
                f"TOTAL:     {total_len:.4f}m")
        self.info_text.set_text(info)
        self.fig.canvas.draw_idle()

    def get_segment_length(self, seg_idx):
        """Calculates the geometric length of a single path segment."""
        if self.state == "PLACING_ANCHORS": return 0.0
        
        start_idx = sum(self.segment_points_list[:seg_idx])
        end_idx = start_idx + self.segment_points_list[seg_idx]
        points = self.path_vertices[start_idx:end_idx]
        
        if len(points) < 2: return 0.0
        return np.sum(np.linalg.norm(np.diff(points, axis=0), axis=1))

    def on_press(self, event):
        if event.inaxes != self.ax or self.state == "DONE": return
        
        if self.state == "PLACING_ANCHORS":
            if self.placed_anchor_count < self.num_total_anchors:
                pos = np.array([event.xdata, event.ydata])
                is_last_anchor = (self.placed_anchor_count == self.num_segments)

                if not is_last_anchor:
                    vec = pos - self.pond_center
                    if np.linalg.norm(vec) < 1e-6:
                        self.anchor_positions[self.placed_anchor_count] = self.pond_center + np.array([self.POND_RADIUS_X, 0])
                    else:
                        # Snap to ellipse boundary by finding the intersection of the line from center to point
                        # with the ellipse.
                        angle = np.arctan2(vec[1], vec[0])
                        a = self.POND_RADIUS_X
                        b = self.POND_RADIUS_Y
                        
                        # Parametric equation for ellipse: x = a*cos(t), y = b*sin(t)
                        # Relation between angle from center (theta) and parameter t:
                        # tan(theta) = (b*sin(t)) / (a*cos(t)) => tan(t) = (a/b)*tan(theta)
                        if abs(np.cos(angle)) < 1e-9: # Vertical line
                            t = np.pi / 2 if vec[1] > 0 else -np.pi / 2
                        else:
                            t = np.arctan((a/b) * np.tan(angle))
                        
                        # We need to be in the correct quadrant
                        if np.cos(angle) < 0: t += np.pi

                        x_on_ellipse = a * np.cos(t)
                        y_on_ellipse = b * np.sin(t)

                        self.anchor_positions[self.placed_anchor_count] = self.pond_center + np.array([x_on_ellipse, y_on_ellipse])
                else:
                    self.anchor_positions[self.placed_anchor_count] = pos
                
                self.placed_anchor_count += 1

            if self.placed_anchor_count == self.num_total_anchors:
                print("All anchors placed. Entering editing mode.")
                self.state = "EDITING_PATH"
                self.create_initial_path()
            
            self.update_display()

        elif self.state == "EDITING_PATH":
            pos = np.array([event.xdata, event.ydata])
            self.is_dragging = True
            self.drag_info = {'pos': pos}
            self.brush_indicator.set_visible(True)
            self.on_motion(event)

    def on_motion(self, event):
        if not self.is_dragging or not event.inaxes: return
        
        pos = np.array([event.xdata, event.ydata])
        avg_radius = (self.POND_RADIUS_X + self.POND_RADIUS_Y) / 2.0
        brush_radius = self.pull_radius_factor * avg_radius
        self.brush_indicator.set_center((pos[0], pos[1]))
        self.brush_indicator.set_radius(brush_radius)
        
        displacement = pos - self.drag_info['pos']
        distances = np.linalg.norm(self.path_vertices - pos, axis=1)
        
        sigma = avg_radius * self.pull_radius_factor
        pull_strength = np.exp(-(distances**2) / (2 * sigma**2))
        
        if self.anchor_indices:
            pull_strength[self.anchor_indices] = 0.0
            
        self.path_vertices += displacement * pull_strength[:, np.newaxis]
        self.drag_info['pos'] = pos
        self.update_display()

    def on_release(self, event):
        if self.is_dragging:
            self.is_dragging = False
            self.brush_indicator.set_visible(False)
            
            # Check for points outside the ellipse
            relative_coords = self.path_vertices - self.pond_center
            # Add epsilon to avoid division by zero
            check = (relative_coords[:, 0] / (self.POND_RADIUS_X + 1e-9))**2 + (relative_coords[:, 1] / (self.POND_RADIUS_Y + 1e-9))**2
            outside_mask = check > 1.0

            if np.any(outside_mask):
                # Scale points back onto the ellipse boundary
                scale_factors = np.sqrt(check[outside_mask])
                self.path_vertices[outside_mask] = self.pond_center + relative_coords[outside_mask] / scale_factors[:, np.newaxis]
            
            self.update_display()

    def on_scroll(self, event):
        if self.state != "EDITING_PATH": return
        if event.button == 'up':
            self.pull_radius_factor *= 1.2
        elif event.button == 'down':
            self.pull_radius_factor /= 1.2
        self.pull_radius_factor = np.clip(self.pull_radius_factor, 0.02, 0.5)
        self.update_display()

    def high_precision_resample(self, points, target_num_points, target_length):
        """
        Resamples a sequence of points to a specific length and number of points,
        while preserving its geometric shape.
        """
        segment_vectors = np.diff(points, axis=0)
        segment_lengths = np.linalg.norm(segment_vectors, axis=1)
        cumulative_lengths = np.insert(np.cumsum(segment_lengths), 0, 0)
        
        current_total_length = cumulative_lengths[-1]
        
        if current_total_length < 1e-9:
            return np.linspace(points[0], points[-1], target_num_points)
        
        ideal_distances = np.linspace(0, current_total_length, target_num_points)
        
        interp_x = np.interp(ideal_distances, cumulative_lengths, points[:, 0])
        interp_y = np.interp(ideal_distances, cumulative_lengths, points[:, 1])
        resampled_points = np.vstack([interp_x, interp_y]).T

        scale_factor = target_length / current_total_length
        start_point = resampled_points[0]
        scaled_points = start_point + (resampled_points - start_point) * scale_factor
        
        return scaled_points

    def on_key_press(self, event):
        if self.state == "EDITING_PATH" and event.key.upper() == 'S':
            print("Performing final high-precision adjustment...")
            self.state = "ADJUSTING"
            self.update_display()
            self.fig.canvas.flush_events()
            time.sleep(0.1)

            perfect_segments = []
            current_start_idx = 0
            
            for i in range(self.num_segments):
                num_points = self.segment_points_list[i]
                current_end_idx = current_start_idx + num_points
                
                segment_shape = self.path_vertices[current_start_idx:current_end_idx]
                
                segment_perfect = self.high_precision_resample(
                    segment_shape, num_points, self.SEGMENT_LENGTH
                )
                perfect_segments.append(segment_perfect)
                
                current_start_idx = current_end_idx

            self.path_vertices = np.vstack(perfect_segments)
            
            self.state = "DONE"
            print("Adjustment complete. Final path rendered.")
            self.anchor_indices = list(np.cumsum([0] + self.segment_points_list[:-1]))
            self.anchor_indices.append(self.TOTAL_POINTS - 1)
            self.update_display()
            
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                output_dir = os.path.join(project_root, "assets", "data")
                os.makedirs(output_dir, exist_ok=True)
                
                # ファイル名にセグメント数を含める
                output_file_name = f"led_positions_{self.num_segments}_segments.csv"
                full_path = os.path.join(output_dir, output_file_name)

                with open(full_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['x', 'y'])
                    writer.writerows(self.path_vertices)
                print(f"Successfully saved path to: {full_path}")

            except Exception as e:
                print(f"Error saving file: {e}")

if __name__ == "__main__":
    # --- User Configuration ---
    # Set the desired number of line segments.
    NUM_SEGMENTS = 4  # <-- CHANGE THIS VALUE (e.g., 3, 4, 5, etc.)
    # --------------------------

    print("--- Interactive Path Builder ---")
    print(f"You will define {NUM_SEGMENTS} segments by clicking {NUM_SEGMENTS + 1} anchor points.")
    print(f"The first {NUM_SEGMENTS} points must be on the edge of the pond.")
    print("The final point can be placed anywhere.")
    
    try:
        editor = InteractivePathEditor(num_segments=NUM_SEGMENTS)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure you have a graphical environment and matplotlib is installed correctly.")