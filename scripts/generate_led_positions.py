import numpy as np
import csv
from scipy.interpolate import splprep, splev

def generate_simple_arc_segment(start_point, end_point, control_point, num_leds):
    """
    This is the definitive, simplified segment generation function.
    It creates a single, predictable, non-intersecting quadratic Bezier-like curve.
    """
    # The control points for a quadratic spline (k=2) define a simple arc.
    curve_points = np.array([start_point, control_point, end_point])
    
    # Create a high-resolution spline that passes through the points.
    tck, u = splprep(curve_points.T, s=0, k=2)
    u_fine = np.linspace(0, 1, 5000)
    x_fine, y_fine = splev(u_fine, tck)
    high_res_path = np.vstack((x_fine, y_fine)).T

    # --- Place LEDs at constant intervals along this final, correctly shaped path ---
    path_segments = np.diff(high_res_path, axis=0)
    segment_lengths = np.linalg.norm(path_segments, axis=1)
    total_path_length = np.sum(segment_lengths)
    
    if total_path_length == 0 or num_leds <= 1:
        return [start_point] * num_leds

    led_interval = total_path_length / (num_leds - 1)
    led_positions = [high_res_path[0]]
    
    cumulative_length = 0.0
    target_dist_for_next_led = led_interval
    current_segment_idx = 0

    while len(led_positions) < num_leds and current_segment_idx < len(segment_lengths):
        segment_len = segment_lengths[current_segment_idx]
        if segment_len <= 0:
            current_segment_idx += 1
            continue
            
        while cumulative_length + segment_len >= target_dist_for_next_led:
            ratio = (target_dist_for_next_led - cumulative_length) / segment_len
            
            p_start = high_res_path[current_segment_idx]
            p_end = high_res_path[current_segment_idx + 1]
            new_led_pos = p_start + ratio * (p_end - p_start)
            
            led_positions.append(new_led_pos)
            
            if len(led_positions) >= num_leds: break
            target_dist_for_next_led += led_interval
        
        cumulative_length += segment_len
        current_segment_idx += 1
        
    return led_positions

def create_final_simple_path(num_leds=900):
    """
    Creates the final path by generating and stitching three independent,
    simple, non-intersecting segments.
    """
    from src.config import SCREEN_WIDTH, SCREEN_HEIGHT, WORLD_RADIUS

    center = np.array([SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2])
    leds_per_segment = num_leds // 3

    # --- 1. Define the three fixed anchor points on the circumference ---
    angle_p0 = np.deg2rad(-90) # Bottom
    angle_p1 = np.deg2rad(30)  # Top-right
    angle_p2 = np.deg2rad(150) # Top-left
    
    p0 = center + WORLD_RADIUS * np.array([np.cos(angle_p0), np.sin(angle_p0)])
    p1 = center + WORLD_RADIUS * np.array([np.cos(angle_p1), np.sin(angle_p1)])
    p2 = center + WORLD_RADIUS * np.array([np.cos(angle_p2), np.sin(angle_p2)])
    
    # --- 2. Define ONE simple control point for each segment to guide its arc ---
    # The control points are pulled towards the center to ensure the arc stays inside.
    # The perpendicular vector logic ensures a nice, tangential curve.
    v1 = (p1 - p0)
    n1 = np.array([-v1[1], v1[0]]) / np.linalg.norm(v1) # Perpendicular vector
    control1 = center + (p0 + p1 - 2*center) * 0.5 + n1 * 150 # Push inwards

    v2 = (p2 - p1)
    n2 = np.array([-v2[1], v2[0]]) / np.linalg.norm(v2)
    control2 = center + (p1 + p2 - 2*center) * 0.5 + n2 * 150

    v3 = (center - p2)
    n3 = np.array([-v3[1], v3[0]]) / np.linalg.norm(v3)
    control3 = center + (p2 + center - 2*center) * 0.5 + n3 * 100

    # --- 3. Generate each segment with its precise number of LEDs ---
    leds1 = generate_simple_arc_segment(p0, p1, control1, leds_per_segment)
    leds2 = generate_simple_arc_segment(p1, p2, control2, leds_per_segment)
    
    remaining_leds = num_leds - 2 * leds_per_segment
    leds3 = generate_simple_arc_segment(p2, center, control3, remaining_leds)

    # --- 4. Concatenate all LEDs into a single, continuous list ---
    final_led_positions = np.vstack([leds1[:-1], leds2[:-1], leds3])
    
    return final_led_positions

if __name__ == "__main__":
    led_positions = create_final_simple_path()

    from src.config import LED_FILE_PATH
    with open(LED_FILE_PATH, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['x', 'y'])
        for pos in led_positions:
            writer.writerow(pos)
    
    print(f"Generated {len(led_positions)} LED positions and saved to {LED_FILE_PATH}.")