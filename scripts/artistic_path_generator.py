import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import time
import csv

# --- Parameters ---
POND_DIAMETER = 5.0
POND_RADIUS = POND_DIAMETER / 2.0
TOTAL_LENGTH = 15.0
LEDS_PER_METER = 60
TOTAL_POINTS = int(TOTAL_LENGTH * LEDS_PER_METER)

SEGMENT_POINTS_BASE = TOTAL_POINTS // 3
REMAINDER_POINTS = TOTAL_POINTS % 3
SEGMENT_POINTS_LIST = [
    SEGMENT_POINTS_BASE + (1 if i < REMAINDER_POINTS else 0) for i in range(3)
]
SEGMENT_LENGTH = TOTAL_LENGTH / 3.0

class InteractivePathEditor:
    # ... (The __init__, setup_plot, connect_events, create_initial_path, update_display, get_segment_length,
    #      on_press, on_motion, on_release, on_scroll methods are ALL THE SAME as your last working version.
    #      They are omitted here for brevity but should be included in your file.)
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(11, 10))
        plt.subplots_adjust(right=0.75, top=0.95)
        self.pond_center = np.array([0.0, 0.0])
        self.state = "PLACING_ANCHORS"
        self.pull_radius_factor = 0.1
        self.anchor_positions = [
            self.pond_center + np.array([0, POND_RADIUS]),
            self.pond_center + np.array([-POND_RADIUS * np.sin(2*np.pi/3), -POND_RADIUS * np.cos(2*np.pi/3)]),
            self.pond_center + np.array([POND_RADIUS * np.sin(2*np.pi/3), -POND_RADIUS * np.cos(2*np.pi/3)])
        ]
        self.placed_anchor_count = 0
        self.path_vertices = np.zeros((TOTAL_POINTS, 2))
        self.is_dragging = False
        self.drag_info = {}
        self.setup_plot()
        self.connect_events()
        self.create_initial_path()
        self.update_display()
        plt.show()

    def setup_plot(self):
        self.ax.set_aspect('equal', adjustable='box')
        self.ax.set_xlim(-POND_RADIUS - 1, POND_RADIUS + 1)
        self.ax.set_ylim(-POND_RADIUS - 1, POND_RADIUS + 1)
        self.pond = Circle(self.pond_center, POND_RADIUS, facecolor='lightblue', edgecolor='blue', alpha=0.5, zorder=0)
        self.ax.add_patch(self.pond)
        self.line_artist, = self.ax.plot([], [], color='purple', linewidth=2.5, zorder=1)
        self.anchor_artist = self.ax.scatter([], [], color='black', s=120, zorder=5)
        self.info_text = self.fig.text(0.77, 0.9, '', fontsize=10, verticalalignment='top', fontfamily='monospace')
        self.brush_indicator = Circle((0,0), 0.1, facecolor='red', alpha=0.3, zorder=10, visible=False)
        self.ax.add_patch(self.brush_indicator)

    def connect_events(self):
        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)

    def create_initial_path(self):
        p0_idx, p1_idx, p2_idx = 0, SEGMENT_POINTS_LIST[0], SEGMENT_POINTS_LIST[0] + SEGMENT_POINTS_LIST[1]
        p0, p1, p2 = self.anchor_positions
        seg1 = np.linspace(p0, p1, SEGMENT_POINTS_LIST[0])
        seg2 = np.linspace(p1, p2, SEGMENT_POINTS_LIST[1])
        seg3 = np.linspace(p2, self.pond_center, SEGMENT_POINTS_LIST[2])
        self.path_vertices = np.vstack([seg1, seg2, seg3])

    def update_display(self):
        if self.state == "DONE": self.line_artist.set_color('lime')
        else: self.line_artist.set_color('purple')
        self.line_artist.set_data(self.path_vertices[:, 0], self.path_vertices[:, 1])
        anchor_indices = [0, SEGMENT_POINTS_LIST[0], SEGMENT_POINTS_LIST[0] + SEGMENT_POINTS_LIST[1]]
        self.anchor_artist.set_offsets(self.path_vertices[anchor_indices])
        state_titles = {
            "PLACING_ANCHORS": "Click 3 points ON THE EDGE.",
            "EDITING_PATH": "Drag path to shape.\nSCROLL to change brush size.\nPress 'S' to save.",
            "DONE": "SAVED! Final path rendered.\nClose the window."
        }
        s1, s2, s3 = self.get_segment_length(0), self.get_segment_length(1), self.get_segment_length(2)
        info = (f"STATE: {self.state}\n\n"
                f"INSTRUCTIONS:\n{state_titles.get(self.state, '')}\n\n"
                f"BRUSH SIZE: {self.pull_radius_factor*100:.1f}%\n\n"
                f"--- LENGTHS (TARGET: {SEGMENT_LENGTH:.2f}m) ---\n"
                f"Segment 1: {s1:6.4f}m\n"
                f"Segment 2: {s2:6.4f}m\n"
                f"Segment 3: {s3:6.4f}m\n\n"
                f"TOTAL:     {s1+s2+s3:.4f}m")
        self.info_text.set_text(info)
        self.fig.canvas.draw_idle()

    def get_segment_length(self, seg_idx):
        start = sum(SEGMENT_POINTS_LIST[:seg_idx])
        end = sum(SEGMENT_POINTS_LIST[:seg_idx+1])
        points = self.path_vertices[start:end]
        if len(points) < 2: return 0.0
        return np.sum(np.linalg.norm(np.diff(points, axis=0), axis=1))

    def on_press(self, event):
        if event.inaxes != self.ax or self.state == "DONE": return
        pos = np.array([event.xdata, event.ydata])
        if self.state == "PLACING_ANCHORS":
            if self.placed_anchor_count < 3:
                vec = pos - self.pond_center
                self.anchor_positions[self.placed_anchor_count] = self.pond_center + (vec / np.linalg.norm(vec)) * POND_RADIUS
                self.placed_anchor_count += 1
            if self.placed_anchor_count == 3:
                self.state = "EDITING_PATH"
                self.create_initial_path()
            self.update_display()
        elif self.state == "EDITING_PATH":
            self.is_dragging = True
            self.drag_info = {'pos': pos}
            self.brush_indicator.set_visible(True)

    def on_motion(self, event):
        if not self.is_dragging or not event.inaxes: return
        pos = np.array([event.xdata, event.ydata])
        brush_radius = self.pull_radius_factor * POND_RADIUS
        self.brush_indicator.set_center((pos[0], pos[1])); self.brush_indicator.set_radius(brush_radius)
        displacement = pos - self.drag_info['pos']
        distances = np.linalg.norm(self.path_vertices - pos, axis=1)
        sigma = POND_RADIUS * self.pull_radius_factor
        pull_strength = np.exp(-(distances**2) / (2 * sigma**2))
        anchor_indices = [0, SEGMENT_POINTS_LIST[0], SEGMENT_POINTS_LIST[0] + SEGMENT_POINTS_LIST[1]]
        pull_strength[anchor_indices] = 0.0
        self.path_vertices += displacement * pull_strength[:, np.newaxis]
        self.drag_info['pos'] = pos
        self.update_display()

    def on_release(self, event):
        if self.is_dragging:
            self.is_dragging = False
            self.brush_indicator.set_visible(False)
            distances_from_center = np.linalg.norm(self.path_vertices - self.pond_center, axis=1)
            outside_mask = distances_from_center > POND_RADIUS
            if np.any(outside_mask):
                vecs_to_center = self.pond_center - self.path_vertices[outside_mask]
                self.path_vertices[outside_mask] += vecs_to_center * (1 - POND_RADIUS / distances_from_center[outside_mask])[:, np.newaxis]
            self.update_display()

    def on_scroll(self, event):
        if self.state != "EDITING_PATH": return
        if event.button == 'up': self.pull_radius_factor *= 1.2
        elif event.button == 'down': self.pull_radius_factor /= 1.2
        self.pull_radius_factor = np.clip(self.pull_radius_factor, 0.02, 0.5)
        self.update_display()

    def high_precision_resample(self, points, target_num_points, target_length):
        """
        The definitive, high-precision resampling function.
        It preserves the shape while exactly scaling the length.
        """
        # 1. Calculate the exact cumulative length along the current user-drawn shape
        segment_vectors = np.diff(points, axis=0)
        segment_lengths = np.linalg.norm(segment_vectors, axis=1)
        cumulative_lengths = np.insert(np.cumsum(segment_lengths), 0, 0)
        
        # If the path has no length, return a straight line of points
        if cumulative_lengths[-1] < 1e-9:
            return np.linspace(points[0], points[-1], target_num_points)
        
        # 2. Create a set of distances for the new, perfectly-spaced points
        ideal_distances = np.linspace(0, cumulative_lengths[-1], target_num_points)
        
        # 3. Interpolate the original points to find the new, evenly-spaced points
        #    This step ensures we have a high-quality representation of the shape.
        interp_x = np.interp(ideal_distances, cumulative_lengths, points[:, 0])
        interp_y = np.interp(ideal_distances, cumulative_lengths, points[:, 1])
        resampled_points = np.vstack([interp_x, interp_y]).T

        # 4. The resampled path has the correct shape but wrong total length.
        #    Now, we simply scale all vectors from the start point by the required factor.
        scale_factor = target_length / cumulative_lengths[-1]
        start_point = resampled_points[0]
        scaled_points = start_point + (resampled_points - start_point) * scale_factor
        
        return scaled_points

    def on_key_press(self, event):
        if self.state == "EDITING_PATH" and event.key.upper() == 'S':
            print("Performing final high-precision adjustment...")
            self.state = "ADJUSTING"
            self.update_display()
            time.sleep(0.1)

            p0_idx = 0
            p1_idx = SEGMENT_POINTS_LIST[0]
            p2_idx = p1_idx + SEGMENT_POINTS_LIST[1]
            
            # Extract the correct segments
            seg1_shape = self.path_vertices[p0_idx : p1_idx]
            seg2_shape = self.path_vertices[p1_idx : p2_idx]
            seg3_shape = self.path_vertices[p2_idx:]
            
            # Resample each segment with the correct number of points and target length
            seg1_perfect = self.high_precision_resample(seg1_shape, SEGMENT_POINTS_LIST[0], SEGMENT_LENGTH)
            seg2_perfect = self.high_precision_resample(seg2_shape, SEGMENT_POINTS_LIST[1], SEGMENT_LENGTH)
            seg3_perfect = self.high_precision_resample(seg3_shape, SEGMENT_POINTS_LIST[2], SEGMENT_LENGTH)
            
            # Stitch them together
            self.path_vertices = np.vstack([
                seg1_perfect,
                seg2_perfect,
                seg3_perfect
            ])
            
            self.state = "DONE"
            print("Adjustment complete. Final path rendered.")
            self.update_display()
            
            with open('led_positions.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['x', 'y'])
                writer.writerows(self.path_vertices)
            print(f"Path with {len(self.path_vertices)} points saved to 'final_led_positions.csv'")

if __name__ == "__main__":
    print("Starting Interactive Path Builder...")
    editor = InteractivePathEditor()