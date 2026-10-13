import ezdxf
import math
import matplotlib.pyplot as plt
from enum import Enum

# ============================================================
# GLOBAL TOLERANCE POLICY (CRITICAL FOR PRODUCTION)
# ============================================================

BASE_TOL = 0.05            # 5 cm
ENDPOINT_TOL = 0.10
MERGE_TOL = 0.30
ANGLE_TOL = 10.0
MIN_STUB_LENGTH = 1.20    # meters (windows / doors usually smaller)

# ============================================================
# DATA MODELS
# ============================================================

class DXFType(Enum):
    DRAFTING_ONLY = "drafting_only"
    SEMANTIC_BIM = "semantic_bim"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class Wall:
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2
        self.length = math.hypot(p2[0]-p1[0], p2[1]-p1[1])


class Node:
    def __init__(self, pt):
        self.pt = pt


# ============================================================
# GEOMETRY HELPERS
# ============================================================

def direction(p1, p2):
    dx, dy = p2[0]-p1[0], p2[1]-p1[1]
    L = math.hypot(dx, dy)
    return (dx/L, dy/L)


def angle_between(v1, v2):
    dot = max(-1, min(1, v1[0]*v2[0] + v1[1]*v2[1]))
    return math.degrees(math.acos(dot))


def is_collinear(v1, v2):
    return abs(angle_between(v1, v2) - 180) < ANGLE_TOL


def intersect(p1, p2, p3, p4):
    x1,y1=p1; x2,y2=p2
    x3,y3=p3; x4,y4=p4

    d = (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4)
    if abs(d) < 1e-9:
        return None

    px = ((x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4))/d
    py = ((x1*y2-y1*x2)*(y3-y4)-(y1-y2)*(x3*y4-y3*x4))/d

    if (min(x1,x2)-BASE_TOL <= px <= max(x1,x2)+BASE_TOL and
        min(y1,y2)-BASE_TOL <= py <= max(y1,y2)+BASE_TOL and
        min(x3,x4)-BASE_TOL <= px <= max(x3,x4)+BASE_TOL and
        min(y3,y4)-BASE_TOL <= py <= max(y3,y4)+BASE_TOL):
        return (round(px,3), round(py,3))
    return None


def is_endpoint(pt, wall):
    return (
        math.hypot(pt[0]-wall.p1[0], pt[1]-wall.p1[1]) < ENDPOINT_TOL or
        math.hypot(pt[0]-wall.p2[0], pt[1]-wall.p2[1]) < ENDPOINT_TOL
    )

# ============================================================
# NODE MERGING
# ============================================================

def merge_close_points(points):
    merged = []
    for p in points:
        for i, q in enumerate(merged):
            if math.hypot(p[0]-q[0], p[1]-q[1]) < MERGE_TOL:
                merged[i] = ((p[0]+q[0])/2, (p[1]+q[1])/2)
                break
        else:
            merged.append(p)
    return merged

# ============================================================
# STRUCTURAL NODE VALIDATION
# ============================================================

def is_false_junction(pt, walls):
    touching = [w for w in walls if is_endpoint(pt, w)]
    if len(touching) < 3:
        return False

    dirs = [(w, direction(w.p1, w.p2)) for w in touching]

    for w1, d1 in dirs:
        for w2, d2 in dirs:
            if w1 is w2:
                continue
            if is_collinear(d1, d2):
                for w3, d3 in dirs:
                    if w3 not in (w1, w2):
                        if abs(angle_between(d1, d3) - 90) < ANGLE_TOL:
                            if w3.length < MIN_STUB_LENGTH:
                                return True
    return False


def is_real_structural_node(pt, walls):
    touching = [w for w in walls if is_endpoint(pt, w)]
    if len(touching) < 2:
        return False

    dirs = []
    for w in touching:
        d = direction(w.p1, w.p2)
        if not any(angle_between(d, e) < ANGLE_TOL for e in dirs):
            dirs.append(d)

    return len(dirs) >= 2

# ============================================================
# MAIN PIPELINE
# ============================================================

def process_dxf(path):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()

    insunits = doc.header.get("$INSUNITS", 0)
    scale = {
        0: 1.0, 1: 0.0254, 2: 0.3048,
        4: 0.001, 5: 0.01, 6: 1.0
    }.get(insunits, 1.0)

    walls = []

    def add_wall(p1, p2):
        if math.hypot(p2[0]-p1[0], p2[1]-p1[1]) > BASE_TOL:
            walls.append(Wall(p1, p2))

    for e in msp.query("LINE"):
        p1 = (e.dxf.start.x*scale, e.dxf.start.y*scale)
        p2 = (e.dxf.end.x*scale, e.dxf.end.y*scale)
        add_wall(p1, p2)

    for e in msp.query("LWPOLYLINE"):
        pts = e.get_points("xy")
        for i in range(len(pts)-1):
            p1 = (pts[i][0]*scale, pts[i][1]*scale)
            p2 = (pts[i+1][0]*scale, pts[i+1][1]*scale)
            add_wall(p1, p2)

    raw_points = []

    for i in range(len(walls)):
        for j in range(i+1, len(walls)):
            v1 = direction(walls[i].p1, walls[i].p2)
            v2 = direction(walls[j].p1, walls[j].p2)

            if abs(angle_between(v1, v2) - 90) > ANGLE_TOL:
                continue

            pt = intersect(walls[i].p1, walls[i].p2,
                           walls[j].p1, walls[j].p2)

            if pt and not (is_endpoint(pt, walls[i]) and is_endpoint(pt, walls[j])):
                raw_points.append(pt)

    merged = merge_close_points(raw_points)

    nodes = []
    for pt in merged:
        if is_real_structural_node(pt, walls) and not is_false_junction(pt, walls):
            nodes.append(Node(pt))

    return walls, nodes

# ============================================================
# VISUALIZATION
# ============================================================

def visualize(walls, nodes):
    plt.figure(figsize=(9,7))
    for w in walls:
        plt.plot([w.p1[0], w.p2[0]], [w.p1[1], w.p2[1]], "k-", lw=1)
    for n in nodes:
        plt.plot(n.pt[0], n.pt[1], "ro")
    plt.axis("equal")
    plt.grid(True)
    plt.show()

# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    walls, nodes = process_dxf("input_dxf/demo.dxf")
    print("Walls:", len(walls))
    print("Structural Nodes:", len(nodes))
    visualize(walls, nodes)
