import math
import matplotlib.pyplot as plt

# ---------------------------------------------
# Helper: Check intersection of two line segments
# ---------------------------------------------

def segment_intersection(p1, p2, p3, p4):
    """
    Returns intersection point (x, y) if segments intersect,
    otherwise returns None
    """

    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denom = (x1 - x2)*(y3 - y4) - (y1 - y2)*(x3 - x4)
    if abs(denom) < 1e-6:
        return None  # parallel lines

    px = ((x1*y2 - y1*x2)*(x3 - x4) - (x1 - x2)*(x3*y4 - y3*x4)) / denom
    py = ((x1*y2 - y1*x2)*(y3 - y4) - (y1 - y2)*(x3*y4 - y3*x4)) / denom

    # Check if intersection lies on both segments
    def on_segment(px, py, a, b):
        return (min(a[0], b[0]) - 0.05 <= px <= max(a[0], b[0]) + 0.05 and
                min(a[1], b[1]) - 0.05 <= py <= max(a[1], b[1]) + 0.05)

    if on_segment(px, py, p1, p2) and on_segment(px, py, p3, p4):
        return (round(px, 3), round(py, 3))

    return None

# ---------------------------------------------
# MAIN LOGIC
# ---------------------------------------------

def find_wall_intersections(walls):
    intersections = set()

    for i in range(len(walls)):
        for j in range(i + 1, len(walls)):
            p1, p2 = walls[i]
            p3, p4 = walls[j]

            point = segment_intersection(p1, p2, p3, p4)
            if point:
                intersections.add(point)

    return list(intersections)

# ---------------------------------------------
# VISUALIZATION
# ---------------------------------------------

def plot_walls_and_intersections(walls, intersections):
    plt.figure(figsize=(8, 6))

    # Plot walls
    for p1, p2 in walls:
        plt.plot([p1[0], p2[0]], [p1[1], p2[1]], 'k-', linewidth=2)

    # Plot intersections
    for x, y in intersections:
        plt.plot(x, y, 'ro')

    plt.title("Wall Intersections")
    plt.axis("equal")
    plt.grid(True)
    plt.show()
