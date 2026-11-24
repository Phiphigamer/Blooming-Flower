"""HopeBloom patient unit, rev D ("everything hides in the base").

Low weighted base (Ø120) holds the main PCB (ESP32-C3), the MG90S servo and the touch-ring LEDs.
A slim stem carries a pushrod up to the flower head: five translucent petals hinged at the cup rim,
pushed open by thin links. The 12-LED ring PCB sits in the cup as the glowing light core.

Units mm. Origin = centre of the base underside, Z up. Section plane A-A = XZ (y = 0).
HB_STATE=1 -> petals open, 0 -> closed bud.
"""
import math, os
import cadquery as cq

P = dict(
    base_r=60, base_h=32, base_wall=3, base_floor=3, cap_t=3,
    weight_r=48, weight_t=4,
    pcb_r=54, pcb_t=1.6, pcb_z=24.9, pcb_hole_r=5.2,
    ring_ri=22, ring_ro=28, ring_led_r=25, n_ring_leds=8,
    servo_cz=14.0, servo_sx=-12.0, arm_l=12,
    stem_ro=4.0, stem_ri=3.0, stem_z0=20.0, stem_z1=210.0,
    cup_ro=20, cup_wall=1.2, cup_h=27, cup_bot=2, cup_open_r=8,
    board_r=18.5, board_t=1.6,
    n_petals=5, petal_l=60, petal_w=30, petal_t=2, open_deg=62, closed_deg=12, hinge_off=1.7,
    rod_r=1.5, head_r=6.5, link_at=10,
)
CZ0 = P['stem_z1']                       # 210 cup bottom
CZ1 = CZ0 + P['cup_h']                   # 237 rim / hinge height
CR = P['cup_ro']
HX = CR + P['hinge_off']             # hinge axis radius, just outside the cup wall
BOARD_Z = CZ0 + P['cup_bot']             # 212


def link_len():
    a = math.radians(P['open_deg'])
    return math.hypot(CR + P['link_at'] * math.sin(a) - 6, 0) if False else None


# link length chosen so the head sits 21.4 mm above the cup bottom when open (as in rev B)
HEAD_OPEN = CZ0 + 21.4
a_open, a_cl = math.radians(P['open_deg']), math.radians(P['closed_deg'])
HEAD_AR = 6.0                           # link anchor radius on the pushrod head


def anchor(a):
    """Link anchor on the petal's inner face, 'link_at' mm from the hinge, petal at angle a."""
    return (HX - 1.5 * math.cos(a) + P['link_at'] * math.sin(a), CZ1 + 1.5 * math.sin(a) + P['link_at'] * math.cos(a))


_ox, _oz = anchor(a_open)
LINK = math.hypot(_ox - HEAD_AR, _oz - HEAD_OPEN)
_cx, _cz = anchor(a_cl)
HEAD_CLOSED = _cz - math.sqrt(LINK ** 2 - (_cx - HEAD_AR) ** 2)
TRAVEL = HEAD_OPEN - HEAD_CLOSED

STATE = float(os.environ.get("HB_STATE", "1"))
ANG = P['closed_deg'] + (P['open_deg'] - P['closed_deg']) * STATE
HEAD_Z = HEAD_CLOSED + TRAVEL * STATE
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_d")
os.makedirs(OUT, exist_ok=True)


def revolve(profile):
    return cq.Workplane("XZ").polyline(profile).close().revolve(360, (0, 0, 0), (0, 1, 0))


def cyl(r, p0, p1):
    v = cq.Vector(*p1) - cq.Vector(*p0)
    return cq.Workplane().add(cq.Solid.makeCylinder(r, v.Length, cq.Vector(*p0), v.normalized()))


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane().box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def rotz(s, deg):
    return s.rotate((0, 0, 0), (0, 0, 1), deg)


# ------------------------------------------------------------------ base
BR, BH, W, F = P['base_r'], P['base_h'], P['base_wall'], P['base_floor']
cap_z = BH - P['cap_t']                                                    # 29
base = revolve([(0, 0), (BR - 2, 0), (BR, 2), (BR, cap_z), (BR - W, cap_z), (BR - W, F), (0, F)])
usb_open = box(-6.0, 6.0, BR - W - 1, BR + 1, 20.8, 25.6)                  # USB-C at the back (+y)
base = base.cut(usb_open)
for k in range(4):                                                         # cap screw bosses
    base = base.union(rotz(cyl(3.5, (BR - W - 3, 0, F), (BR - W - 3, 0, P['pcb_z'] - 0.1)), 45 + 90 * k)
                      .cut(rotz(cyl(1.2, (BR - W - 3, 0, F), (BR - W - 3, 0, P['pcb_z'])), 45 + 90 * k)))
for k in range(3):                                                         # rubber feet pockets
    base = base.cut(rotz(cyl(5.2, (44, 0, -0.1), (44, 0, 1.0)), 90 + 120 * k))

cap = revolve([(P['stem_ro'] + 0.05, cap_z), (BR, cap_z), (BR, BH - 1.5), (BR - 1.5, BH), (P['stem_ro'] + 0.05, BH)])
cap = cap.cut(revolve([(P['ring_ri'], cap_z - 1), (P['ring_ro'], cap_z - 1), (P['ring_ro'], BH + 1), (P['ring_ri'], BH + 1)]))
cap = cap.union(revolve([(P['stem_ro'] + 0.05, cap_z - 2.3), (P['stem_ro'] + 2.5, cap_z - 2.3),
                         (P['stem_ro'] + 2.5, cap_z), (P['stem_ro'] + 0.05, cap_z)]))     # stem socket boss
lz = P['pcb_z'] + P['pcb_t'] + 1.6 + 0.1                                   # 28.2 underside of ring
touch_ring = revolve([(P['ring_ri'] - 1, lz), (P['ring_ro'] + 1, lz), (P['ring_ro'] + 1, cap_z), (P['ring_ro'] - 0.1, cap_z),
                      (P['ring_ro'] - 0.1, BH), (P['ring_ri'] + 0.1, BH), (P['ring_ri'] + 0.1, cap_z), (P['ring_ri'] - 1, cap_z)])

weight = (cq.Workplane().circle(P['weight_r']).extrude(P['weight_t']).translate((0, 0, F))
          .cut(cyl(5, (0, 0, 0), (0, 0, 10))))

# ------------------------------------------------------------------ main PCB (round, under the cap)
pz = P['pcb_z']
pcb = (cq.Workplane().circle(P['pcb_r']).circle(P['pcb_hole_r']).extrude(P['pcb_t']).translate((0, 0, pz)))
for k in range(4):
    pcb = pcb.cut(rotz(cyl(1.2, (BR - W - 3, 0, pz - 1), (BR - W - 3, 0, pz + 3)), 45 + 90 * k))
ring_leds = [rotz(box(-2.5, 2.5, -2.5, 2.5, pz + P['pcb_t'], pz + P['pcb_t'] + 1.6).translate((P['ring_led_r'], 0, 0)),
                  360 * k / P['n_ring_leds'] + 22.5) for k in range(P['n_ring_leds'])]
esp = box(22.0, 35.2, -8.3, 8.3, pz - 2.4, pz)                             # ESP32-C3-MINI-1 (underside)
usb = box(-4.47, 4.47, 50.5, 57.85, pz - 3.2, pz)                          # USB-C receptacle (underside, back edge)
ttp = box(12, 15, 18, 21, pz - 1.2, pz)                                    # TTP223 touch IC
mainboard = pcb.union(esp).union(usb).union(ttp)
for s in ring_leds:
    mainboard = mainboard.union(s)

# ------------------------------------------------------------------ servo + frame + pushrod
sz, sx = P['servo_cz'], P['servo_sx']
servo = (box(-28.9, -6.1, 4.5, 27, sz - 6.1, sz + 6.1)
         .union(box(-33.75, -1.25, 9, 11.5, sz - 6.1, sz + 6.1))
         .union(cyl(5.5, (sx, 4.5, sz), (sx, 1.5, sz)))
         .union(cyl(2.4, (sx, 1.5, sz), (sx, -1.0, sz))))
arm = box(sx - 1.5, 3.5, -1.0, 0.5, sz - 2, sz + 2).cut(cyl(1.6, (0, 0, sz - 5), (0, 0, sz + 5)))
servo = servo.union(arm)
frame = (box(-37, -1.6, 11.5, 14.5, F + P['weight_t'], sz + 8)
         .cut(box(-29.0, -6.0, 11.0, 15.0, sz - 6.2, sz + 6.2))
         .union(box(-37, -1.6, 11.5, 30, F + P['weight_t'], F + P['weight_t'] + 0.8).cut(box(-29.5, -5.5, 11.0, 28, 0, 20))))
screws = [cyl(1.0, (x, 8.0, sz), (x, 16.0, sz)) for x in (-31.3, -3.7)]
rod_z0 = sz - 3 + TRAVEL * STATE
rod = cyl(P['rod_r'], (0, 0, rod_z0), (0, 0, HEAD_Z - 1))

stem = cyl(P['stem_ro'], (0, 0, P['stem_z0']), (0, 0, P['stem_z1'])).cut(
    cyl(P['stem_ri'], (0, 0, P['stem_z0'] - 1), (0, 0, P['stem_z1'] + 1)))

# decorative leaf clipped to the stem
leaf_pts = [(0, 0), (8, 5), (20, 7), (32, 4), (40, 0), (32, -3), (20, -5), (8, -4)]
leaf = (cq.Workplane("XY").polyline(leaf_pts).close().extrude(1.6).translate((0, 0, -0.8))
        .rotate((0, 0, 0), (0, 1, 0), -25).translate((P['stem_ro'] + 1.2, 0, 92)))
leaf = leaf.union(cyl(P['stem_ro'] + 1.6, (0, 0, 88), (0, 0, 96)).cut(cyl(P['stem_ro'] + 0.05, (0, 0, 80), (0, 0, 100))))
leaf = rotz(leaf, 150)

# ------------------------------------------------------------------ flower head
cup = revolve([(P['cup_open_r'], CZ0), (CR, CZ0), (CR, CZ1), (CR - P['cup_wall'], CZ1),
               (CR - P['cup_wall'], CZ0 + P['cup_bot']), (P['cup_open_r'], CZ0 + P['cup_bot'])])
cup = cup.union(revolve([(P['stem_ro'] + 0.05, CZ0 - 6), (P['stem_ro'] + 2, CZ0 - 6), (P['stem_ro'] + 2, CZ0),
                         (P['stem_ro'] + 0.05, CZ0)]))
for k in range(P['n_petals']):
    lug = box(CR - 1, HX + 1.6, -5, -3, CZ1 - 4, CZ1 + 1.6).union(box(CR - 1, HX + 1.6, 3, 5, CZ1 - 4, CZ1 + 1.6))
    lug = lug.cut(cyl(0.8, (HX, -6, CZ1), (HX, 6, CZ1)))
    cup = cup.union(rotz(lug, 360 * k / P['n_petals']))

board = cq.Workplane().circle(P['board_r']).circle(3).extrude(P['board_t']).translate((0, 0, BOARD_Z))
for k in range(12):
    board = board.union(rotz(box(10.5, 15.5, -2.5, 2.5, BOARD_Z + P['board_t'], BOARD_Z + P['board_t'] + 1.6), -30 * k))
head = cyl(P['head_r'], (0, 0, HEAD_Z - 1), (0, 0, HEAD_Z + 1))


def petal_solid():
    # teardrop outline, cupped across, slight flare toward the tip, thinner edges
    L, Wh = P['petal_l'], P['petal_w'] / 2
    Rc, Rl = 24.0, 230.0                  # cupping radius across, flare radius along
    t0, te = 2.0, 1.2                     # thickness at the midrib / at the edges
    s0 = 3.5                              # straight narrow neck above the hinge (clears the lugs)

    def half_w(s):
        if s <= s0:
            return 2.8
        x = (s - s0) / (L - s0)
        g = math.sin(math.pi * x ** 1.3) ** 0.6
        return 2.8 * (1 - x) + Wh * g

    def mid_x(s, u):
        flare = Rl - math.sqrt(Rl * Rl - s * s)
        cup = Rc - math.sqrt(Rc * Rc - u * u)
        return HX + flare - cup

    stations = [0, 1.5, s0, 6, 9, 13, 18, 24, 30, 36, 42, 47, 51, 54.5, 57, 58.6, 59.5]
    n = 12
    wires = []
    for s in stations:
        w = half_w(s)
        us = [-w * math.cos(math.pi * i / n) for i in range(n + 1)]
        outer, inner = [], []
        for u in us:
            th = t0 - (t0 - te) * (u / w) ** 2 if w > 0 else te
            xm = mid_x(s, u)
            outer.append(cq.Vector(xm + th / 2, u, CZ1 + s))
            inner.append(cq.Vector(xm - th / 2, u, CZ1 + s))
        wires.append(cq.Wire.makePolygon(outer + inner[::-1], close=True))
    blade = cq.Workplane().add(cq.Solid.makeLoft(wires, ruled=False))
    blade = blade.cut(cyl(0.8, (HX, -20, CZ1), (HX, 20, CZ1)))
    knuckle = cyl(1.6, (HX, -2.8, CZ1), (HX, 2.8, CZ1)).cut(cyl(0.8, (HX, -4, CZ1), (HX, 4, CZ1)))
    return blade.union(knuckle)


petal0 = petal_solid()
petals, pins, links = [], [], []
for k in range(P['n_petals']):
    b = 360 * k / P['n_petals']
    petals.append(rotz(petal0.rotate((HX, 0, CZ1), (HX, 1, CZ1), ANG), b))
    pins.append(rotz(cyl(0.75, (HX, -4.5, CZ1), (HX, 4.5, CZ1)), b))
    a = math.radians(ANG)
    px, pzz = anchor(a)
    br = math.radians(b)
    p0 = (HEAD_AR * math.cos(br), HEAD_AR * math.sin(br), HEAD_Z)
    p1 = (px * math.cos(br), px * math.sin(br), pzz)
    links.append(cyl(0.5, p0, p1))

parts = {
    "01_petal": (petals, (0.99, 0.96, 0.92)), "02_hinge_pin": (pins, (0.55, 0.55, 0.55)),
    "03_petal_link": (links, (0.55, 0.55, 0.55)), "04_cup": ([cup], (0.97, 0.97, 0.95)),
    "05_led_core_pcb": ([board], (0.95, 0.55, 0.15)), "06_pushrod_head": ([head], (0.97, 0.97, 0.95)),
    "07_stem_tube": ([stem], (0.82, 0.82, 0.80)), "08_pushrod": ([rod], (0.55, 0.55, 0.55)),
    "09_leaf": ([leaf], (0.85, 0.85, 0.83)), "10_touch_ring": ([touch_ring], (0.98, 0.70, 0.40)),
    "11_top_cap": ([cap], (0.96, 0.96, 0.95)), "12_main_pcb": ([mainboard], (0.10, 0.30, 0.15)),
    "13_servo_MG90S": ([servo], (0.20, 0.30, 0.55)), "14_servo_frame": ([frame], (0.85, 0.85, 0.82)),
    "15_steel_weight": ([weight], (0.45, 0.45, 0.48)), "16_base": ([base], (0.93, 0.93, 0.92)),
    "17_screws_M2": (screws, (0.4, 0.4, 0.4)),
}
printable = ["01_petal", "04_cup", "06_pushrod_head", "09_leaf", "10_touch_ring", "11_top_cap", "14_servo_frame", "16_base"]

if __name__ == "__main__":
    tag = "open" if STATE > 0.5 else "closed"
    asm = cq.Assembly(name=f"HopeBloom_revD_{tag}")
    for name, (shapes, rgb) in parts.items():
        for i, s in enumerate(shapes):
            asm.add(s, name=f"{name}_{i + 1}" if len(shapes) > 1 else name, color=cq.Color(*rgb))
    asm.export(os.path.join(OUT, f"HopeBloom_revD_assembly_{tag}.step"))
    if tag == "open":
        for d in ("step", "stl"):
            os.makedirs(os.path.join(OUT, d), exist_ok=True)
        for name, (shapes, _) in parts.items():
            s = shapes[0]
            for extra in shapes[1:]:
                s = s.union(extra)
            cq.exporters.export(s, os.path.join(OUT, "step", f"{name}.step"))
        for name in printable:
            src = petal0 if name == "01_petal" else parts[name][0][0]
            cq.exporters.export(src, os.path.join(OUT, "stl", f"{name}.stl"), tolerance=0.05, angularTolerance=0.1)
    print(tag, "travel", round(TRAVEL, 2), "head", round(HEAD_Z, 2), "link", round(LINK, 2),
          "valid", all(parts[n][0][0].val().isValid() for n in printable))
