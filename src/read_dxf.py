import ezdxf
import math
import matplotlib.pyplot as plt
import os

# =================================================
# STEP 1: LOAD DXF
# =================================================

DXF_PATH = "input_dxf/giraffe360_demo_residential.dxf"

if not os.path.exists(DXF_PATH):
    raise FileNotFoundError(DXF_PATH)

doc = ezdxf.readfile(DXF_PATH)
msp = doc.modelspace()

print("DXF loaded")

# =================================================
# STEP 2: AUTO UNIT DETECTION
# =================================================

def get_scale_to_meters(doc):
    insunits = doc.header.get("$INSUNITS", 0)
    unit_map = {
        0: 1.0,        # unitless → assume meters
        1: 0.0254,     # inches
        2: 0.3048,     # feet
        4: 0.001,      # mm
        5: 0.01,       # cm
        6: 1.0         # meters
    }
    scale = unit_map.get(insunits, 1.0)
    print(f"INSUNITS = {insunits}, scale → meters = {scale}")
    return scale

SCALE = get_scale_to_meters(doc)

# =================================================
# STEP 3: EXTRACT WALL SEGMENTS (CLEAN)
# =================================================

walls = []

def add_wall(p1, p2, eps=1e-6):
    if math.hypot(p2[0]-p1[0], p2[1]-p1[1]) > eps:
        walls.append((p1, p2))

for e in msp.query("LINE"):
    p1 = (e.dxf.start.x * SCALE, e.dxf.start.y * SCALE)
    p2 = (e.dxf.end.x * SCALE, e.dxf.end.y * SCALE)
    add_wall(p1, p2)

for e in msp.query("LWPOLYLINE"):
    pts = e.get_points("xy")
    for i in range(len(pts) - 1):
        p1 = (pts[i][0] * SCALE, pts[i][1] * SCALE)
        p2 = (pts[i+1][0] * SCALE, pts[i+1][1] * SCALE)
        add_wall(p1, p2)

print(f"Walls extracted (clean): {len(walls)}")

# =================================================
# STEP 4: GEOMETRY HELPERS
# =================================================

def direction(p1, p2):
    dx, dy = p2[0]-p1[0], p2[1]-p1[1]
    L = math.hypot(dx, dy)
    return (dx/L, dy/L)

def angle_between(v1, v2):
    dot = max(-1.0, min(1.0, v1[0]*v2[0] + v1[1]*v2[1]))
    return math.degrees(math.acos(dot))

def intersect(p1, p2, p3, p4, tol=0.05):
    x1,y1=p1; x2,y2=p2
    x3,y3=p3; x4,y4=p4

    d = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
    if abs(d) < 1e-9:
        return None

    px = ((x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4))/d
    py = ((x1*y2-y1*x2)*(y3-y4)-(y1-y2)*(x3*y4-y3*x4))/d

    if (min(x1,x2)-tol <= px <= max(x1,x2)+tol and
        min(y1,y2)-tol <= py <= max(y1,y2)+tol and
        min(x3,x4)-tol <= px <= max(x3,x4)+tol and
        min(y3,y4)-tol <= py <= max(y3,y4)+tol):
        return (round(px, 3), round(py, 3))

    return None

def is_endpoint(pt, seg, tol=0.05):
    p1, p2 = seg
    return (
        math.hypot(pt[0]-p1[0], pt[1]-p1[1]) < tol or
        math.hypot(pt[0]-p2[0], pt[1]-p2[1]) < tol
    )

# =================================================
# STEP 5: STRUCTURAL INTERSECTION DETECTION
# =================================================

all_intersections = set()
structural_intersections = set()

for i in range(len(walls)):
    p1, p2 = walls[i]
    v1 = direction(p1, p2)

    for j in range(i + 1, len(walls)):
        p3, p4 = walls[j]
        v2 = direction(p3, p4)

        angle = angle_between(v1, v2)

        # Reject parallel or collinear
        if angle < 20 or angle > 160:
            continue

        # Keep near-perpendicular only
        if abs(angle - 90) > 10:
            continue

        pt = intersect(p1, p2, p3, p4)
        if not pt:
            continue

        all_intersections.add(pt)

        # ❌ Reject endpoint–endpoint coincidence
        if is_endpoint(pt, (p1, p2)) and is_endpoint(pt, (p3, p4)):
            continue

        structural_intersections.add(pt)

print(f"All intersections found: {len(all_intersections)}")
print(f"Structural intersections kept: {len(structural_intersections)}")

# =================================================
# STEP 6: VISUAL DEBUG (IMPORTANT)
# =================================================

plt.figure(figsize=(9, 7))

# Walls
for p1, p2 in walls:
    plt.plot([p1[0], p2[0]], [p1[1], p2[1]], "k-", lw=2)

# All intersections (gray)
for x, y in all_intersections:
    plt.plot(x, y, "o", color="lightgray", markersize=4)

# Structural intersections (red)
for x, y in structural_intersections:
    plt.plot(x, y, "ro")

plt.title("Structural Intersections (Red) vs All (Gray)")
plt.axis("equal")
plt.grid(True)
plt.show()

# =================================================
# STEP 7: SANITY CHECK
# =================================================

lengths = [math.hypot(p2[0]-p1[0], p2[1]-p1[1]) for p1, p2 in walls]
print("Wall length min/max (m):", min(lengths), max(lengths))
