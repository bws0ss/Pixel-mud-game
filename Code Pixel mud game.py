import json
import math
import os
import random
import pygame

pygame.init()
VW, VH, SCALE = 320, 180, 3            # рисуем в 320x180 и увеличиваем в 3 раза -> пиксельный стиль
W, H = VW * SCALE, VH * SCALE
FLAGS = getattr(pygame, "SCALED", 0) | getattr(pygame, "RESIZABLE", 0)
screen = pygame.display.set_mode((W, H), FLAGS)
pygame.display.set_caption("Mud Pixel Runner")
clock = pygame.time.Clock()
low = pygame.Surface((VW, VH))
wsurf = pygame.Surface((VW, VH), pygame.SRCALPHA)
font = pygame.font.SysFont("couriernew", 20, bold=True)
big = pygame.font.SysFont("couriernew", 44, bold=True)
title_font = pygame.font.SysFont("couriernew", 56, bold=True)
mid = pygame.font.SysFont("couriernew", 24, bold=True)
small = pygame.font.SysFont("couriernew", 16, bold=True)
ov = pygame.Surface((W, H), pygame.SRCALPHA)
gsurf = pygame.Surface((VW, VH), pygame.SRCALPHA)   # слой для призрака

# ======================= константы физики =======================
N = 2500                 # длина уровня (колонок земли)
GOAL_X = 2420
G = 240.0                # гравитация
DT = 1 / 60
SUB = 4                  # подшагов физики за кадр
K0, CD = 420.0, 22.0     # жёсткость и демпфирование контакта с землёй
KS = 12.0                # жёсткость проскальзывания шины
MU0 = 1.15               # сцепление на сухой земле
R_W, I_W = 6.0, 9.0      # радиус и инерция колеса
BRAKE_T = 450.0
DW, BF = 0.35, 1.1       # сопротивление воды и выталкивающая сила
DIG = 0.06               # скорость вырывания колеи
GHOST_STEP = 3           # призрак записывается раз в 3 кадра
GHOST_ALPHA = 120


# ======================= уровни =======================
# ctrl  - опорные точки рельефа (x, y), y вниз; ponds - (центр, полуширина, глубина)
# mud   - (от, до, влажность); rock - (от, до); trees - якоря лебёдки; cps - чекпоинты
LEVELS = [
    dict(name="Muddy Trail", diff=1, n=2500, goal=2420,
         desc=("Mud fields, a ford and one steep", "mud hill. A good place to learn."),
         theme=((118, 178, 230), (150, 205, 240), (96, 150, 120)),
         ctrl=[(0, 130), (300, 127), (380, 132), (650, 134), (720, 129), (880, 129), (930, 127),
               (1075, 86), (1230, 112), (1290, 128), (1320, 130), (1660, 134), (1700, 132),
               (1790, 114), (1870, 94), (1935, 90), (1990, 128), (2060, 130), (2260, 130),
               (2340, 124), (2500, 124)],
         ponds=[(790, 70, 17), (1440, 45, 9), (2160, 100, 26)],
         mud=[(380, 650, 0.75), (1300, 1660, 0.85), (1700, 1960, 0.92)],
         rock=[(930, 1230)],
         trees=[300, 700, 1000, 1290, 1650, 1950, 2000, 2350],
         cps=[460, 1250, 1700, 2000]),
    dict(name="Black Swamp", diff=2, n=2800, goal=2720,
         desc=("Wet ground everywhere and many ponds.", "Two deep ones will flood your engine."),
         theme=((140, 165, 150), (165, 185, 170), (70, 100, 80)),
         ctrl=[(0, 130), (250, 130), (420, 134), (700, 132), (900, 136), (1150, 132), (1400, 128),
               (1650, 134), (1900, 132), (2150, 136), (2400, 130), (2650, 128), (2800, 128)],
         ponds=[(560, 45, 10), (850, 60, 14), (1250, 70, 19), (1700, 55, 12), (2050, 80, 20),
                (2500, 50, 12)],
         mud=[(300, 900, 0.7), (900, 1000, 0.85), (1100, 1900, 0.85), (1900, 2400, 0.9),
              (2400, 2650, 0.75)],
         rock=[],
         trees=[250, 460, 700, 1000, 1100, 1400, 1580, 1830, 1900, 2220, 2390, 2620],
         cps=[420, 1000, 1500, 2200]),
    dict(name="Rocky Pass", diff=3, n=2700, goal=2620,
         desc=("A long climb over rock with two steep", "mud slopes and a lake on the summit."),
         theme=((150, 175, 215), (185, 205, 235), (125, 135, 155)),
         ctrl=[(0, 150), (250, 148), (400, 140), (600, 120), (750, 118), (900, 102), (1050, 98),
               (1200, 72), (1350, 68), (1500, 82), (1600, 88), (1760, 52), (1830, 44),
               (1990, 46), (2120, 74), (2250, 104), (2400, 112), (2550, 114), (2700, 114)],
         ponds=[(700, 40, 12), (1910, 50, 14), (2400, 50, 12)],
         mud=[(1050, 1210, 0.92), (1600, 1780, 0.97)],
         rock=[(400, 1050), (1210, 1600), (1780, 2250)],
         trees=[320, 600, 800, 1000, 1215, 1360, 1500, 1580, 1800, 2010, 2250, 2300, 2520],
         cps=[520, 1260, 1560, 2040]),
    dict(name="Flood Plains", diff=4, n=3050, goal=2990,
         desc=("A storm has flooded the valley.", "Deep mud, a wide river, no mercy."),
         theme=((92, 108, 138), (115, 128, 155), (62, 86, 92)),
         ctrl=[(0, 132), (300, 130), (500, 136), (800, 132), (1000, 128), (1180, 92), (1320, 88),
               (1450, 98), (1600, 126), (1800, 134), (2100, 132), (2300, 118), (2450, 100),
               (2600, 102), (2750, 128), (3050, 130)],
         ponds=[(450, 40, 10), (700, 55, 19), (1950, 100, 27), (2850, 45, 14)],
         mud=[(300, 1000, 0.85), (1000, 1350, 0.95), (1600, 1780, 0.85), (2100, 2700, 0.9)],
         rock=[(1350, 1500)],
         trees=[240, 360, 560, 820, 1090, 1340, 1500, 1700, 1780, 2110, 2350, 2600, 2760, 2950],
         cps=[560, 900, 1400, 2160, 2700]),
    dict(name="Canyon River", diff=4, n=3600, goal=3520,
         desc=("Four river crossings, one of them so deep", "that even a snorkel will not save you."),
         theme=((200, 160, 120), (228, 190, 150), (118, 102, 120)),
         ctrl=[(0, 140), (300, 138), (500, 142), (900, 138), (1100, 120), (1300, 118), (1500, 132),
               (1900, 134), (2050, 100), (2250, 84), (2450, 86), (2700, 120), (3000, 124),
               (3300, 122), (3600, 118)],
         ponds=[(700, 70, 22), (1700, 90, 34), (2850, 70, 30), (3350, 50, 18)],
         mud=[(500, 1000, 0.8), (1000, 1300, 0.92), (2000, 2300, 0.95)],
         rock=[(1300, 1560), (2300, 2700), (3000, 3250)],
         trees=(220,),
         cps=[540, 1450, 1950, 2400, 3100]),
    dict(name="Mud Marathon", diff=5, n=4200, goal=4120,
         desc=("A very long trip through deep wet mud.", "Ruts pile up. Mind the throttle."),
         theme=((170, 160, 125), (200, 190, 150), (120, 108, 80)),
         ctrl=[(x, int(120 + (y - 120) * 1.3)) for x, y in
               [(0, 130), (300, 128), (500, 118), (700, 132), (900, 112), (1100, 134), (1300, 104),
                (1450, 98), (1600, 128), (1800, 136), (2000, 110), (2200, 92), (2350, 96),
                (2500, 130), (2700, 134), (2900, 108), (3100, 84), (3250, 86), (3400, 120),
                (3600, 134), (3800, 126), (4000, 128), (4200, 128)]],
         ponds=[(1700, 50, 12), (2600, 45, 10), (3700, 50, 14), (3900, 60, 24)],
         mud=[(200, 1000, 0.92), (1000, 2000, 0.96), (2000, 3000, 0.98), (3000, 4000, 0.96)],
         rock=[(1300, 1450), (2200, 2350), (3100, 3250)],
         trees=(190,),
         cps=[480, 1060, 1580, 2100, 2480, 3000, 3570]),
    dict(name="Storm Delta", diff=5, n=4600, goal=4520,
         desc=("The longest and wettest trip. Eight deep", "ponds, flooded mud, winch all the way."),
         theme=((78, 92, 118), (100, 112, 138), (52, 74, 82)),
         ctrl=[(0, 130), (400, 128), (700, 134), (1000, 126), (1300, 120), (1600, 130),
               (1900, 134), (2200, 126), (2500, 118), (2800, 128), (3100, 134), (3400, 126),
               (3700, 112), (4000, 120), (4300, 132), (4600, 130)],
         ponds=[(550, 60, 30), (1150, 80, 32), (1750, 90, 34), (2350, 70, 28), (2950, 90, 36),
                (3250, 60, 24), (3850, 80, 32), (4350, 50, 16)],
         mud=[(300, 1500, 0.8), (1500, 3000, 0.88), (3000, 4400, 0.85)],
         rock=[(3500, 3730)],
         trees=(220,),
         cps=[400, 900, 1450, 2100, 2650, 3100, 3500, 4100]),
]


def make_trees(lv):
    """Кортеж (шаг,) -> деревья через равные промежутки и по берегам всех прудов."""
    t = lv["trees"]
    if isinstance(t, tuple):
        xs = list(range(150, lv["n"] - 30, t[0]))
        for c, hw, d in lv["ponds"]:
            xs += [int(c - 1.5 * hw - 14), int(c + 1.5 * hw + 14),       # у берегов
                   int(c - 1.5 * hw - 140), int(c + 1.5 * hw + 140)]     # подальше, чтобы вытянуть на берег
        return sorted(set(xs))
    return list(t)


def apply_level(lv):
    """Подставляет данные уровня в глобальные переменные (одновременно играем один уровень)."""
    global N, GOAL_X, CTRL, PONDS, MUD, ROCK, SAND, TREES, CPS, THEME
    N, GOAL_X = lv["n"], lv["goal"]
    CTRL, PONDS, MUD, ROCK = lv["ctrl"], lv["ponds"], lv["mud"], lv["rock"]
    SAND = lv.get("sand", [])
    TREES, CPS, THEME = make_trees(lv), list(lv["cps"]), lv["theme"]


# ======================= vehicles & customization =======================
COLORS = [("RED", (200, 52, 42)), ("ORANGE", (228, 126, 36)), ("YELLOW", (232, 204, 50)),
          ("GREEN", (58, 160, 72)), ("BLUE", (56, 104, 212)), ("WHITE", (226, 226, 232)),
          ("BLACK", (52, 52, 60)), ("PURPLE", (142, 72, 192))]

# Local vehicle coordinates: x forward, y down, origin at the body centre.
# wheels = (x, y, radius); extras = other contact points (belly, bumpers, roof); the first
# `wheels` are driven. bed = (x0, x1, floor y) of the cargo bed; capacity = cargo units.
VEHICLES = [
    dict(name="PICKUP 4x4", role="LIGHT TRUCK",
         info=("All-rounder: quick, light, fine in mud.", "Small cargo bed (3 units)."),
         mass=1.0, inertia=260.0, torque=450.0, wmax=20.0, grip=1.0, mud_bias=0.0, rr=0.0,
         tank=100.0, fuel=1.0, dig=1.0, buoy=1.0, drag=1.0, winch=(300.0, 40.0, 280.0),
         hook=(22, 3), intake=(19, -2), snorkel=(12, -15),
         wheels=[(-14, 6, 6), (14, 6, 6)],
         extras=[(0, 6, 3), (-22, 3, 2), (22, 3, 2), (-9, -12, 3), (8, -12, 3)],
         bed=(-22, -6, -6), capacity=3,
         shapes=[("poly", "dark", [(-22, -3), (22, -3), (23, 5), (-23, 5)]),
                 ("poly", "bed", [(-22, -6), (-6, -6), (-6, -3), (-22, -3)]),
                 ("poly", "body", [(-4, -3), (-2, -11), (10, -11), (14, -3)]),
                 ("poly", "glass", [(-1, -4), (0, -9), (8, -9), (11, -4)])],
         lights=[(0, -11), (5, -11)], pipe=[(12, -4), (12, -15), (15, -15)],
         bar=[(22, -2), (26, -2), (26, 5), (22, 5)], headlight=(22, -1)),
    dict(name="DUNE BUGGY", role="",
         info=("Very light and fast. Great on dry ground,", "but weak in water and thick mud."),
         mass=0.62, inertia=120.0, torque=340.0, wmax=27.0, grip=1.06, mud_bias=0.05, rr=0.0,
         tank=70.0, fuel=0.8, dig=0.7, buoy=1.5, drag=0.8, winch=(190.0, 35.0, 240.0),
         hook=(19, 2), intake=(14, -1), snorkel=(10, -12),
         wheels=[(-13, 6, 6), (13, 6, 6)],
         extras=[(0, 5, 3), (-19, 2, 2), (19, 2, 2), (-8, -11, 3), (6, -11, 3)],
         bed=None, capacity=0,
         shapes=[("poly", "dark", [(-18, 0), (18, 0), (20, 5), (-20, 5)]),
                 ("poly", "body", [(8, 0), (14, -3), (19, 0)]),
                 ("poly", "body", [(-8, 0), (-6, -4), (1, -4), (3, 0)]),
                 ("line", "cage", [(-9, 0), (-7, -11), (5, -11), (7, 0)], 1)],
         lights=[(-3, -11), (1, -11)], pipe=[(10, -2), (10, -12), (13, -12)],
         bar=[(19, -1), (23, -1), (23, 5), (19, 5)], headlight=(19, -2)),
    dict(name="ROCK CRAWLER", role="",
         info=("Huge tires and low gearing: climbs and", "crawls through mud. Slow and thirsty."),
         mass=1.35, inertia=310.0, torque=900.0, wmax=11.0, grip=1.0, mud_bias=-0.10, rr=0.003,
         tank=80.0, fuel=1.15, dig=0.9, buoy=0.9, drag=1.1, winch=(480.0, 45.0, 300.0),
         hook=(18, -1), intake=(14, -6), snorkel=(8, -16),
         wheels=[(-12, 4, 9), (12, 4, 9)],
         extras=[(0, 0, 3), (-18, -2, 2), (18, -2, 2), (-6, -14, 3), (6, -14, 3)],
         bed=None, capacity=0,
         shapes=[("poly", "dark", [(-18, -6), (18, -6), (18, 0), (-18, 0)]),
                 ("poly", "body", [(-8, -6), (-7, -13), (7, -13), (10, -6)]),
                 ("poly", "body", [(10, -6), (18, -6), (18, -3), (10, -3)]),
                 ("poly", "glass", [(-6, -7), (-5, -12), (6, -12), (8, -7)]),
                 ("line", "cage", [(-8, -14), (8, -14)], 1)],
         lights=[(-5, -14), (2, -14)], pipe=[(9, -6), (9, -16), (12, -16)],
         bar=[(18, -4), (22, -4), (22, 2), (18, 2)], headlight=(18, -4)),
    dict(name="HEAVY TRUCK 6x6", role="HEAVY-DUTY",
         info=("Massive 6x6 hauler: huge bed (8 units),", "strong winch, high intake. Heavy and slow."),
         mass=2.4, inertia=1100.0, torque=1100.0, wmax=12.0, grip=1.0, mud_bias=-0.04, rr=0.002,
         tank=160.0, fuel=1.5, dig=1.2, buoy=0.8, drag=1.3, winch=(700.0, 50.0, 340.0),
         hook=(31, 3), intake=(27, -9), snorkel=(28, -20),
         wheels=[(22, 5, 8), (-10, 5, 8), (-26, 5, 8)],
         extras=[(0, 7, 3), (-33, 3, 2), (32, 3, 2), (14, -17, 3), (23, -17, 3)],
         bed=(-31, 8, -6), capacity=8,
         shapes=[("poly", "dark", [(-31, -2), (31, -2), (32, 6), (-32, 6)]),
                 ("poly", "bed", [(-31, -6), (8, -6), (8, -2), (-31, -2)]),
                 ("poly", "body", [(11, -2), (11, -16), (24, -16), (29, -8), (29, -2)]),
                 ("poly", "glass", [(14, -14), (23, -14), (26, -9), (14, -9)]),
                 ("line", "cage", [(10, -16), (10, -23)], 2)],
         lights=[(14, -16), (19, -16)], pipe=[(27, -9), (27, -20), (30, -20)],
         bar=[(29, -3), (33, -3), (33, 5), (29, 5)], headlight=(29, -4)),
]
VEHICLES[0]["role"] = "LIGHT TRUCK"
for _v in VEHICLES:                                   # contact points: wheels first
    _v["pts"] = [(a, b, c, True) for a, b, c in _v["wheels"]] + [(a, b, c, False) for a, b, c in _v["extras"]]
HAULERS = [0, 3]                                      # vehicles that can carry cargo: light and heavy

TIRES = [
    dict(name="ROAD", cost=0, grip=1.12, mudk=0.92, rr=0.0,
         info=("Best on rock and dry dirt.", "Hopeless in mud.")),
    dict(name="ALL-TERRAIN", cost=1, grip=1.0, mudk=0.85, rr=0.004,
         info=("Balanced tires for every surface.", "Average in mud.")),
    dict(name="MUD", cost=2, grip=0.9, mudk=0.66, rr=0.012,
         info=("Knobby tires: much better grip in mud,", "but weaker on dry ground and heavier to roll.")),
]
ENGINES = [
    dict(name="STOCK", cost=0, tq=1.0, wk=1.0, fuel=1.0, info=("Standard engine.", "")),
    dict(name="TUNED", cost=2, tq=1.25, wk=1.075, fuel=1.25,
         info=("+25% power, higher top speed.", "Burns 25% more fuel. Costs 2 points.")),
    dict(name="RACING", cost=3, tq=1.5, wk=1.15, fuel=1.6,
         info=("+50% power, much higher top speed.", "Burns 60% more fuel. Costs 3 points.")),
]
WINCHES = [
    dict(name="STOCK", cost=0, pull=1.0, speed=1.0, range=1.0, info=("Standard winch for this vehicle.", "")),
    dict(name="HEAVY", cost=1, pull=1.4, speed=1.25, range=1.2,
         info=("+40% pull, faster reel, longer cable.", "Costs 1 point.")),
    dict(name="PRO", cost=2, pull=1.87, speed=1.6, range=1.43,
         info=("+87% pull, much faster reel, long cable.", "Costs 2 points.")),
]
SNORKEL_COST = 2
BUDGET = 7
SNORKEL_INFO = {0: ("No snorkel: the engine floods as soon as", "water reaches the stock air intake."),
                1: ("Raised air intake: the engine floods only", "in much deeper water. Costs 2 points.")}
GARAGE_ROWS = [("VEHICLE", "vehicle", len(VEHICLES)), ("COLOR", "color", len(COLORS)),
               ("TIRES", "tires", len(TIRES)), ("ENGINE", "engine", len(ENGINES)),
               ("WINCH", "winch", len(WINCHES)), ("SNORKEL", "snorkel", 2),
               ("ROOF LIGHTS", "lights", 2), ("BULL BAR", "bar", 2)]
DEFAULT_TRUCK = dict(vehicle=0, color=0, tires=1, engine=0, winch=0, snorkel=0, lights=0, bar=0)
TRUCK = dict(DEFAULT_TRUCK)


def truck_cost(cfg):
    return (TIRES[cfg["tires"]]["cost"] + ENGINES[cfg["engine"]]["cost"]
            + WINCHES[cfg["winch"]]["cost"] + SNORKEL_COST * cfg["snorkel"])


def truck_stats(vi=None):
    """Final numbers for a vehicle = vehicle spec combined with the garage upgrades."""
    v = VEHICLES[TRUCK["vehicle"] if vi is None else vi]
    t, e, w = TIRES[TRUCK["tires"]], ENGINES[TRUCK["engine"]], WINCHES[TRUCK["winch"]]
    return dict(veh=v, pts=v["pts"], grip=t["grip"] * v["grip"],
                mudk=min(0.97, max(0.3, t["mudk"] + v["mud_bias"])), rr=t["rr"] + v["rr"],
                torque=v["torque"] * e["tq"], wmax=v["wmax"] * e["wk"], fuel=v["fuel"] * e["fuel"],
                tank=v["tank"], w_max=v["winch"][0] * w["pull"], w_speed=v["winch"][1] * w["speed"],
                w_range=v["winch"][2] * w["range"],
                intake=v["snorkel"] if TRUCK["snorkel"] else v["intake"])


def wading_depth(st):
    """Water depth (px) at which the engine floods."""
    return max(ly + r for lx, ly, r in st["veh"]["wheels"]) - st["intake"][1]


def option_name(key, v):
    if key == "vehicle":
        return VEHICLES[v]["name"]
    if key == "color":
        return COLORS[v][0]
    if key == "tires":
        return TIRES[v]["name"]
    if key == "engine":
        return ENGINES[v]["name"]
    if key == "winch":
        return WINCHES[v]["name"]
    return "ON" if v else "OFF"


def option_cost(key, v):
    if key == "tires":
        return TIRES[v]["cost"]
    if key == "engine":
        return ENGINES[v]["cost"]
    if key == "winch":
        return WINCHES[v]["cost"]
    if key == "snorkel":
        return SNORKEL_COST * v
    return 0


def option_info(key, v):
    if key == "vehicle":
        return VEHICLES[v]["info"]
    if key == "tires":
        return TIRES[v]["info"]
    if key == "engine":
        return ENGINES[v]["info"]
    if key == "winch":
        return WINCHES[v]["info"]
    if key == "snorkel":
        return SNORKEL_INFO[v]
    return {"color": ("Paint job.", "Cosmetic only."), "lights": ("Roof lights.", "Cosmetic only."),
            "bar": ("Bull bar.", "Cosmetic only.")}[key]


def rec_key(idx, vi):
    """Key of a level record. The pickup keeps the old key so old records still work."""
    return str(idx) if vi == 0 else f"{idx}:{vi}"


# settings, records, ghosts and career are saved next to the script
BEST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mud_runner_best.json")
DEFAULT_PREFS = dict(fullscreen=False, ghost=True)
DEFAULT_CAREER = dict(money=300.0, jobs=0, units=0, hauler=0)


def load_save():
    try:
        with open(BEST_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    best = data.get("best", data if "truck" not in data else {})
    cfg = dict(DEFAULT_TRUCK)
    saved = data.get("truck", {})
    for label, key, count in GARAGE_ROWS:
        v = saved.get(key)
        if isinstance(v, int) and not isinstance(v, bool) and 0 <= v < count:
            cfg[key] = v
    if truck_cost(cfg) > BUDGET:
        cfg = dict(DEFAULT_TRUCK)
    ghosts = {}
    for k, v in (data.get("ghosts") or {}).items():
        if (isinstance(v, dict) and isinstance(v.get("t"), (int, float)) and isinstance(v.get("s"), list)
                and len(v["s"]) >= 8 and len(v["s"]) % 4 == 0
                and all(isinstance(i, int) for i in v["s"])):
            ghosts[k] = v
    prefs = dict(DEFAULT_PREFS)
    for k, v in (data.get("prefs") or {}).items():
        if k in prefs and isinstance(v, bool):
            prefs[k] = v
    career = dict(DEFAULT_CAREER)
    sc = data.get("career") or {}
    if isinstance(sc.get("money"), (int, float)) and sc["money"] >= 0:
        career["money"] = float(sc["money"])
    for k in ("jobs", "units"):
        if isinstance(sc.get(k), int) and sc[k] >= 0:
            career[k] = sc[k]
    if sc.get("hauler") in (0, 1):
        career["hauler"] = sc["hauler"]
    return ({k: v for k, v in best.items() if isinstance(v, (int, float))}, cfg, ghosts, prefs, career)


def save_all():
    try:
        with open(BEST_FILE, "w", encoding="utf-8") as f:
            json.dump({"best": BEST, "truck": TRUCK, "ghosts": GHOSTS, "prefs": PREFS, "career": CAREER},
                      f, separators=(",", ":"))
    except OSError:
        pass


BEST, _cfg, GHOSTS, PREFS, CAREER = load_save()
TRUCK.update(_cfg)
apply_level(LEVELS[0])




def build_level():
    g = [0.0] * N
    j = 0
    for x in range(N):
        while j < len(CTRL) - 2 and x > CTRL[j + 1][0]:
            j += 1
        x0, y0 = CTRL[j]
        x1, y1 = CTRL[j + 1]
        t = min(1.0, max(0.0, (x - x0) / (x1 - x0)))
        t = (1 - math.cos(t * math.pi)) / 2
        g[x] = y0 + (y1 - y0) * t
    for c, hw, d in PONDS:                       # dig the basins
        for x in range(max(0, c - 3 * hw), min(N, c + 3 * hw)):
            g[x] += d / (1 + (abs(x - c) / hw) ** 6)
    water = [0.0] * N
    for c, hw, d in PONDS:                       # fill them with water up to the bank level
        a, b = int(c - 1.6 * hw), int(c + 1.6 * hw)
        level = max(g[a], g[b]) + 1.0
        for x in range(a, b + 1):
            if g[x] > level:
                water[x] = g[x] - level
    base = [0.06] * N
    rock = [False] * N
    sand = [False] * N
    for a, b, wv in MUD:
        for x in range(a, b):
            base[x] = wv
    for a, b in ROCK:
        for x in range(a, b):
            rock[x] = True
            base[x] = 0.0
    for a, b in SAND:
        for x in range(a, b):
            if not rock[x]:
                sand[x] = True
                base[x] = max(base[x], 0.5)
    bed = [g[x] + (0 if rock[x] else (18 if sand[x] else 14)) for x in range(N)]   # bedrock: no digging below
    TREES[:] = [x for x in TREES if 0 <= x < N and water[x] <= 0.3]   # no trees in water
    return g, water, base[:], base, rock, bed, g[:], sand


# ======================= cargo hauling: the big map =======================
CARGO_TYPES = {
    "logs": dict(name="LOGS", mass=0.15, pay=22, color=(130, 90, 50)),
    "cement": dict(name="CEMENT", mass=0.18, pay=30, color=(168, 172, 190)),
    "bricks": dict(name="BRICKS", mass=0.25, pay=40, color=(192, 82, 56)),
}
LOCATIONS = [
    dict(name="Depot", x=300, role="depot"),
    dict(name="Sawmill", x=1500, role="source", cargo="logs"),
    dict(name="Cabin Site", x=2800, role="site"),
    dict(name="Marsh Camp", x=3620, role="site"),
    dict(name="Cement Plant", x=4300, role="source", cargo="cement"),
    dict(name="Quarry Camp", x=5100, role="site"),
    dict(name="Brick Works", x=6800, role="source", cargo="bricks"),
    dict(name="Mountain Lodge", x=10100, role="site"),
    dict(name="Dam Project", x=10950, role="site"),
    dict(name="Lumber Camp", x=11300, role="source", cargo="logs"),
    dict(name="Brick Yard", x=13250, role="source", cargo="bricks"),
    dict(name="Harbor", x=13500, role="site"),
]
STATIONS = [300, 2250, 3200, 4000, 5800, 6650, 7630, 8900, 10230, 11100, 12300, 13650]
CARGO_MAP = dict(
    name="Cargo Map", n=14000, goal=10 ** 9,
    theme=((128, 188, 235), (160, 210, 242), (92, 148, 118)),
    ctrl=[(0, 132), (300, 130), (600, 134), (900, 128),                                   # meadow
          (1100, 118), (1300, 122), (1440, 112), (1560, 112), (1700, 120), (1900, 108),   # pine hills
          (2100, 116), (2300, 126),
          (2500, 132), (2700, 134), (2760, 133), (2840, 133), (3100, 134), (3300, 132),   # marsh
          (3500, 134), (3700, 132), (4000, 130),
          (4250, 126), (4350, 126), (4500, 118), (4650, 100), (4800, 92), (5000, 88),     # rocky ridge
          (5200, 88), (5400, 90), (5600, 112), (5800, 130),
          (6000, 134), (6200, 134), (6400, 132), (6600, 134), (6740, 133), (6860, 133),   # river valley
          (7000, 130),
          (7200, 112), (7400, 128), (7560, 108), (7700, 108), (7800, 126), (8000, 104), (8200, 120),   # desert dunes
          (8400, 100), (8600, 118), (8800, 126), (9000, 128),
          (9200, 120), (9300, 118), (9500, 96), (9650, 66), (9800, 56), (10000, 54),      # mountain pass
          (10200, 56), (10400, 72), (10600, 100), (10800, 124),
          (10950, 130), (11200, 132), (11400, 130), (11600, 134), (11800, 132),           # dam valley
          (12000, 134), (12200, 132),
          (12400, 134), (12600, 132), (12800, 134), (13000, 132), (13200, 134),           # final marsh
          (13440, 133), (13560, 133), (13700, 134), (14000, 134)],
    ponds=[(2600, 50, 12), (3000, 70, 18), (3400, 75, 24), (3800, 50, 14), (6000, 85, 28),
           (6400, 80, 30), (11800, 150, 32), (12700, 75, 22), (13000, 80, 26)],
    mud=[(1900, 2300, 0.7), (2300, 4100, 0.85), (5600, 5900, 0.8), (5900, 6700, 0.9),
         (9250, 9500, 0.92), (10420, 10800, 0.85), (10800, 12300, 0.8), (12300, 13900, 0.88)],
    rock=[(4450, 5350), (9500, 10420)],
    sand=[(7000, 9000)],
    trees=(200,), cps=[])


def lerp(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def text(s, x, y, color=(255, 255, 255), f=font, center=False):
    img = f.render(s, False, color)
    shadow = f.render(s, False, (0, 0, 0))
    r = img.get_rect()
    if center:
        r.center = (x, y)
    else:
        r.topleft = (x, y)
    screen.blit(shadow, r.move(2, 2))
    screen.blit(img, r)


def fmt_time(t):
    t = int(t)
    return f"{t // 60:02d}:{t % 60:02d}"


class GhostRun:
    """Recording of a best run: a sample every GHOST_STEP frames, interpolated between samples."""

    def __init__(self, data):
        sm = data["s"]
        self.t = data["t"]
        v = data.get("v", 0)
        self.v = v if isinstance(v, int) and 0 <= v < len(VEHICLES) else 0
        self.xs, self.ys, self.rs, self.fl = sm[0::4], sm[1::4], sm[2::4], sm[3::4]
        self.n = len(self.xs)

    def pose(self, frames):
        f = frames / GHOST_STEP
        i = int(f)
        if i >= self.n - 1:
            return None                                    # the ghost has finished
        a = f - i
        x0, y0, r0 = self.xs[i] / 10, self.ys[i] / 10, self.rs[i] / 1000
        face = -1 if self.fl[i] & 2 else 1                 # bit 1 = facing left
        if self.fl[i + 1] & 1:                             # bit 0 = teleport (respawn): no interpolation
            return x0, y0, r0, face
        x1, y1, r1 = self.xs[i + 1] / 10, self.ys[i + 1] / 10, self.rs[i + 1] / 1000
        return x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, r0 + (r1 - r0) * a, face


class GhostObj:
    """Minimal object with the fields draw_truck needs."""

    def __init__(self, x, y, ang, face=1, vi=0):
        self.x, self.y, self.ang, self.dirt = x, y, ang, 0.0
        self.facing = face
        self.veh = VEHICLES[vi]
        self.cargo = None
        self.wheels = [[0.0, x / w[2]] for w in self.veh["wheels"]]   # rolling without slip


class Game:
    fuel_scale = 1.0

    def __init__(self, idx=0, veh=None, level=None):
        self.idx = idx
        self.cargo_mode = level is not None
        self.lv = level if level is not None else LEVELS[idx]
        apply_level(self.lv)
        self.set_vehicle(TRUCK["vehicle"] if veh is None else veh)
        (self.ground, self.water, self.wet, self.base, self.rock,
         self.bedrock, self.orig, self.sand) = build_level()
        self.parts = []
        self.t = 0.0
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.cp = 60
        self.fuel = self.tank
        self.time = 0.0
        self.won = False
        self.new_best = False
        self.frames = 0
        self.rec = []
        self.rec_flag = 0
        self.ghost = None
        if not self.cargo_mode:
            gd = GHOSTS.get(rec_key(idx, self.vi))
            self.ghost = GhostRun(gd) if gd else None
        self.dirt = 0.0
        self.msg, self.msg_t = "", 0.0
        self.slip_max = 0.0
        self.grounded = True
        self.was_grounded = True
        self.vy_before = 0.0
        self.hand = self.reel = False
        self.lean = 0
        self.spawn(self.cp)
        self.cam_x = max(0, self.x - 120)

    def set_vehicle(self, vi):
        self.vi = vi
        self.facing = 1                                    # 1 = nose to the right, -1 = turned around
        self.st = truck_stats(vi)
        self.veh = self.st["veh"]
        self.pts = self.st["pts"]
        self.m0 = self.veh["mass"]
        self.m = self.m0
        self.tank = self.st["tank"]
        self.bottom = max(ly + r for lx, ly, r in self.veh["wheels"])
        self.wheels = [[0.0, 0.0] for _ in self.veh["wheels"]]     # [angular speed, angle]
        self.cargo = None

    # ---------------- spawn / respawn ----------------
    def spawn(self, x):
        self.x = float(x)
        self.y = self.ground[int(x)] - self.bottom - 12
        self.ang = 0.0
        self.vx = self.vy = self.om = 0.0
        self.wheels = [[0.0, 0.0] for _ in self.veh["wheels"]]
        self.winch = None
        self.flood_t = 0.0
        self.flooded = False
        self.restart_t = 0.0
        self.flip_t = 0.0
        self.engine_on = self.fuel > 0
        self.throttle = 0.0

    def say(self, s, t=3.0):
        self.msg, self.msg_t = s, t

    # ---------------- terrain: digging ruts ----------------
    def dig(self, wx, d):
        ix = int(wx)
        for k in range(-4, 5):
            i = ix + k
            if 0 <= i < N:
                self.ground[i] = min(self.bedrock[i], self.ground[i] + d * max(0.0, 1 - abs(k) / 5))
        for k in (-8, -7, 7, 8):                       # displaced mud piles up as small berms
            i = ix + k
            if 0 <= i < N and not self.rock[i]:
                self.ground[i] = max(self.orig[i] - 3.0, self.ground[i] - d * 0.1)

    def burst(self, x, y, vx, vy, color):
        if len(self.parts) < 300:
            self.parts.append([x, y, vx + random.uniform(-25, 25), vy + random.uniform(-40, 0),
                               random.uniform(0.4, 1.0), color])

    # ---------------- physics step ----------------
    def drive_torque(self, w, th, r):
        k = self.m0 * (r / 6.0) ** 2                       # wheel inertia scale
        if th != 0 and th * w < 0 and abs(w) > 1.0:
            return -math.copysign(BRAKE_T * self.m0 * (r / 6.0), w)    # brake with the engine
        if th == 0:
            return -w * (1.5 if self.engine_on else 0.3) * k
        lim = max(0.0, 1 - abs(w) / self.st["wmax"])
        tq = self.st["torque"]
        return th * (tq if th * self.facing > 0 else tq * 0.7) * lim      # reversing is weaker

    def physics(self, dt):
        veh, st = self.veh, self.st
        c, s = math.cos(self.ang), math.sin(self.ang)
        x, y, vx, vy, om = self.x, self.y, self.vx, self.vy, self.om
        m0, m = self.m0, self.m
        fx = fy = tq = 0.0
        grounded = False
        ground, water, wetarr, sand = self.ground, self.water, self.wet, self.sand
        bsc = m0 * 7.0 / len(self.pts)
        drag_k, buoy_k = DW * bsc * veh["drag"], BF * bsc * veh["buoy"]
        th = self.throttle
        face = self.facing

        for ki, (lx, ly, r, is_wheel) in enumerate(self.pts):
            lx = lx * face
            rx = c * lx - s * ly
            ry = s * lx + c * ly
            wx, wy = x + rx, y + ry
            pvx, pvy = vx - om * ry, vy + om * rx
            ix = max(1, min(N - 2, int(wx)))
            gy = ground[ix]

            # --- water: buoyancy and drag
            sub = 0.0
            wd = water[ix]
            if wd > 0.3:
                sub = wy - (gy - wd)
                if sub > 0:
                    sub = min(sub, 14.0)
                    f = min(sub / 8, 1.0)
                    wfx = -drag_k * pvx * f
                    wfy = -buoy_k * sub - drag_k * pvy * f
                    fx += wfx
                    fy += wfy
                    tq += rx * wfy - ry * wfx
                else:
                    sub = 0.0

            pen = wy + r - gy
            wh = self.wheels[ki] if is_wheel else None
            if pen > 0:
                grounded = True
                sl = (ground[ix + 1] - ground[ix - 1]) * 0.5
                nl = math.sqrt(1 + sl * sl)
                tx, ty = 1 / nl, sl / nl
                nx, ny = sl / nl, -1 / nl
                pen_n = min(pen / nl, 12.0)
                vn = pvx * nx + pvy * ny
                wet = wetarr[ix]
                Fn = (K0 * (1 - 0.5 * wet) * pen_n - CD * vn) * m0
                if Fn < 0:
                    Fn = 0.0
                vt = pvx * tx + pvy * ty
                mu = MU0 * st["grip"] * (1 - st["mudk"] * wet)        # wet ground = slippery
                if sub > 0:
                    mu *= 1 - 0.45 * min(sub / 6, 1.0)                # aquaplaning
                if is_wheel:
                    slip = wh[0] * r - vt
                    lim = mu * Fn
                    Ft = max(-lim, min(lim, KS * m0 * slip))
                    iw = I_W * m0 * (r / 6.0) ** 2
                    wh[0] += (self.drive_torque(wh[0], th, r) - Ft * r) / iw * dt
                    rrs = 0.05 if sand[ix] else 0.0                   # soft sand drags
                    Ft -= (0.012 + st["rr"] + rrs + 0.08 * wet) * Fn * math.tanh(vt / 12.0)
                    asl = abs(slip)
                    self.slip_max = max(self.slip_max, asl)
                    # a spinning wheel digs a rut in wet ground
                    if asl > 12 and wet > 0.15 and not self.rock[ix] and sub == 0:
                        self.dig(wx, DIG * veh["dig"] * (asl - 12) * wet * (Fn / 120) * dt)
                        if random.random() < min(1.0, asl * 0.003):
                            col = (214, 190, 120) if sand[ix] and wet < 0.65 else random.choice(
                                [(96, 62, 34), (70, 46, 26), (120, 80, 44)])
                            self.burst(wx, wy + 3, -math.copysign(35, slip) + vx * 0.3, -50, col)
                    if sub > 0 and (abs(vt) > 20 or asl > 30) and random.random() < 0.3:
                        self.burst(wx, wy - sub, vx * 0.3, -60, (190, 225, 255))
                else:
                    lim = (0.8 + 0.6 * wet) * Fn
                    Ft = -max(-lim, min(lim, KS * m0 * vt))
                ffx = nx * Fn + tx * Ft
                ffy = ny * Fn + ty * Ft
                fx += ffx
                fy += ffy
                tq += rx * ffy - ry * ffx
            elif is_wheel:
                iwk = m0 * (r / 6.0) ** 2
                wh[0] += (self.drive_torque(wh[0], th, r) - wh[0] * 0.2 * iwk) / (I_W * iwk) * dt

            if is_wheel:
                if self.hand:
                    wh[0] = 0.0
                wh[1] += wh[0] * dt

        # --- winch
        if self.winch:
            ax, ay, L = self.winch
            hx_l, hy_l = veh["hook"][0] * face, veh["hook"][1]
            rxh = c * hx_l - s * hy_l
            ryh = s * hx_l + c * hy_l
            dx, dy = ax - (x + rxh), ay - (y + ryh)
            dist = math.hypot(dx, dy) or 1e-6
            if self.reel:
                L = max(8.0, L - st["w_speed"] * dt)
                self.winch[2] = L
            taut = dist - L
            if taut > 0:
                ux, uy = dx / dist, dy / dist
                vrel = (vx - om * ryh) * ux + (vy + om * rxh) * uy
                F = min(st["w_max"], 25 * m0 * taut)
                F = max(0.0, F - 1.5 * m0 * max(vrel, 0.0))
                fx += F * ux
                fy += F * uy
                tq += rxh * F * uy - ryh * F * ux

        # --- integration (real mass: cargo makes the vehicle heavier)
        vx += fx / m * dt
        vy += (fy / m + G) * dt
        om += tq / (veh["inertia"] * m / m0) * dt
        if self.lean:
            om += self.lean * face * (6.0 if not grounded else 1.5) * dt
        om -= om * 0.15 * dt
        self.x, self.y = x + vx * dt, y + vy * dt
        self.vx, self.vy, self.om = vx, vy, om
        self.ang += om * dt
        self.grounded = grounded
        if self.x < 15:
            self.x, self.vx = 15.0, max(self.vx, 0.0)
        if self.x > N - 15:
            self.x, self.vx = N - 15.0, min(self.vx, 0.0)

    # ---------------- water and wet ground ----------------
    def sim_water(self):
        g, w, wet, base, rock = self.ground, self.water, self.wet, self.base, self.rock
        i0 = max(1, int(self.cam_x) - 120)
        i1 = min(N - 2, int(self.cam_x) + VW + 120)
        for i in range(i0, i1):                       # water flows towards the lower surface
            wi, wj = w[i], w[i + 1]
            if wi == 0.0 and wj == 0.0:
                continue
            flux = ((g[i + 1] - wj) - (g[i] - wi)) * 0.22
            if flux > 0:
                flux = min(flux, wi * 0.5)
            else:
                flux = max(flux, -wj * 0.5)
            w[i] = wi - flux
            w[i + 1] = wj + flux
        for i in range(i0, i1):
            if w[i] < 0.02:
                w[i] = 0.0
            if not rock[i]:                           # soil under water turns into mud
                if w[i] > 0.5:
                    wet[i] += (max(base[i], 0.7) - wet[i]) * 0.6 * DT
                else:
                    wet[i] += (base[i] - wet[i]) * 0.03 * DT

    # ---------------- per-frame update ----------------
    def update(self, keys):
        self.t += DT
        gas = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        rev = keys[pygame.K_a] or keys[pygame.K_LEFT]
        self.hand = keys[pygame.K_SPACE]
        self.reel = keys[pygame.K_f]
        self.lean = int(bool(keys[pygame.K_s] or keys[pygame.K_DOWN])) - \
            int(bool(keys[pygame.K_w] or keys[pygame.K_UP]))
        self.throttle = (float(bool(gas)) - float(bool(rev))) if (self.engine_on and not self.won) else 0.0
        if not self.won:
            self.time += DT
            if not self.cargo_mode and self.frames % GHOST_STEP == 0:      # record the run
                self.rec += [int(round(self.x * 10)), int(round(self.y * 10)),
                             int(round(self.ang * 1000)), self.rec_flag | (2 if self.facing < 0 else 0)]
                self.rec_flag = 0
            self.frames += 1
        self.slip_max = 0.0
        self.vy_before = self.vy
        self.was_grounded = self.grounded

        for _ in range(SUB):
            self.physics(DT / SUB)

        c, s = math.cos(self.ang), math.sin(self.ang)
        # air intake under water -> the engine stalls
        ik = self.st["intake"]
        ikx = ik[0] * self.facing
        ix_ = max(1, min(N - 2, int(self.x + c * ikx - s * ik[1])))
        iy_ = self.y + s * ikx + c * ik[1]
        in_water = self.water[ix_] > 0.3 and iy_ > self.ground[ix_] - self.water[ix_]
        if in_water:
            self.flood_t += DT
            if self.flood_t > 1.2 and self.engine_on:
                self.engine_on, self.flooded, self.restart_t = False, True, 0.0
                self.say("ENGINE FLOODED! Use the winch (E, F)", 4)
        else:
            self.flood_t = max(0.0, self.flood_t - DT * 0.5)
            if self.flooded:
                self.restart_t += DT
                if self.restart_t > 1.5 and self.fuel > 0:
                    self.engine_on, self.flooded = True, False
                    self.say("Engine restarted", 2)

        # fuel
        if self.engine_on:
            self.fuel -= ((0.04 + 0.35 * abs(self.throttle)) * self.st["fuel"] * self.fuel_scale
                          * (self.m / self.m0) ** 0.5 * DT)
            if self.fuel <= 0:
                self.fuel, self.engine_on = 0.0, False
                self.say("OUT OF FUEL! Press R" + (" to get towed" if self.cargo_mode else " to respawn"), 5)

        # mud on the vehicle
        ix = max(1, min(N - 2, int(self.x)))
        if self.water[ix] > 6:
            self.dirt = max(0.0, self.dirt - DT * 0.4)
        elif abs(self.vx) > 5 and self.wet[ix] > 0.3:
            self.dirt = min(1.0, self.dirt + DT * 0.05 * self.wet[ix])

        # winch: auto-detach when pulled up close
        if self.winch:
            hk = self.veh["hook"]
            hkx = hk[0] * self.facing
            hx = self.x + c * hkx - s * hk[1]
            hy = self.y + s * hkx + c * hk[1]
            if math.hypot(self.winch[0] - hx, self.winch[1] - hy) < 14:
                self.winch = None
                self.say("Winch detached", 2)

        # upside down
        if math.cos(self.ang) < 0.1:
            self.flip_t += DT
            if self.flip_t > 2:
                self.say("Flipped! Press R to respawn", 2)
        else:
            self.flip_t = 0.0

        # checkpoints and the finish line (time trial only)
        if not self.cargo_mode:
            for cx in CPS:
                if cx > self.cp and self.x > cx:
                    self.cp = cx
                    self.fuel = self.tank
                    self.say("CHECKPOINT! Fuel refilled", 3)
            if self.x > GOAL_X and not self.won:
                self.won = True
                key = rec_key(self.idx, self.vi)
                self.new_best = key not in BEST or self.time < BEST[key]
                if self.new_best:
                    BEST[key] = round(self.time, 1)
                old = GHOSTS.get(key)
                if old is None or self.time < old["t"]:           # the best run becomes the ghost
                    GHOSTS[key] = dict(t=round(self.time, 2), s=self.rec, v=self.vi)
                save_all()
                self.say("", 0)

        self.extra_update(keys)
        self.sim_water()
        for p in self.parts:                                      # particles
            p[3] += G * DT
            p[0] += p[2] * DT
            p[1] += p[3] * DT
            p[4] -= DT
        self.parts = [p for p in self.parts if p[4] > 0 and p[1] < self.ground[max(0, min(N - 1, int(p[0])))]]

        self.msg_t = max(0.0, self.msg_t - DT)
        # camera
        self.cam_x += (max(0, min(N - VW, self.x - 120)) - self.cam_x) * 0.1
        self.cam_y += ((self.y - 115) - self.cam_y) * 0.08

    def extra_update(self, keys):
        """Hook for game modes."""

    # ---------------- player actions ----------------
    def toggle_winch(self):
        if self.winch:
            self.winch = None
            self.say("Winch detached", 2)
            return
        c, sn = math.cos(self.ang), math.sin(self.ang)
        hk = self.veh["hook"]
        hkx = hk[0] * self.facing
        hx = self.x + c * hkx - sn * hk[1]
        hy = self.y + sn * hkx + c * hk[1]
        cands = []
        for ax in TREES:
            ay = self.ground[ax] - 10
            d = math.hypot(ax - hx, ay - hy)
            if d <= self.st["w_range"]:
                cands.append((d, ax, ay, (ax - self.x) * self.facing > -20))
        best, bd = None, 0.0
        for ahead, far in ((True, True), (True, False), (False, True), (False, False)):
            pool = [cd for cd in cands if cd[3] == ahead and (cd[0] >= 80 or not far)]
            if pool:
                bd, ax, ay, _ = min(pool)
                best = (ax, ay)
                break
        if best:
            self.winch = [best[0], best[1], bd]
            self.say("Winch attached - hold F to reel in", 3)
        else:
            self.say("No tree in range", 2)

    def turn_around(self):
        """Mirror the vehicle so it faces the other way (only when almost stopped)."""
        if abs(self.vx) < 15 and self.grounded:
            self.facing = -self.facing
            self.y -= 3
            self.vy = self.om = 0.0
            self.winch = None
            self.say("Turned around", 1.5)
        else:
            self.say("Stop first to turn around (T)", 2)

    def respawn(self):
        self.rec_flag = 1
        self.fuel = max(self.fuel, 0.5 * self.tank)
        self.spawn(self.cp)

    # ---------------- drawing ----------------
    def draw_world(self, cx, cy):
        """Hook for game modes: extra world objects."""

    def draw(self):
        cx, cy = int(self.cam_x), int(self.cam_y)
        low.fill(THEME[0])
        pygame.draw.rect(low, THEME[1], (0, 0, VW, 40))
        pts = [(0, VH)]
        for sx in range(0, VW + 8, 8):
            wx = sx + cx * 0.25
            pts.append((sx, 100 - cy * 0.5 + 14 * math.sin(wx / 41.0) + 8 * math.sin(wx / 17.0 + 2)))
        pts.append((VW, VH))
        pygame.draw.polygon(low, THEME[2], pts)

        for sx in range(VW):                                  # terrain, column by column
            wx = cx + sx
            if wx >= N:
                break
            gy = int(self.ground[wx]) - cy
            if gy >= VH:
                continue
            wt = self.wet[wx]
            if self.rock[wx]:
                top, body = (150, 150, 162), (104, 104, 118)
            elif self.sand[wx] and wt < 0.65:
                top, body = (224, 198, 130), (188, 160, 100)
            else:
                top = lerp((156, 112, 60), (78, 52, 30), min(1.0, wt))
                body = lerp((118, 80, 44), (56, 38, 22), min(1.0, wt))
            pygame.draw.line(low, body, (sx, gy + 3), (sx, VH))
            pygame.draw.line(low, top, (sx, gy), (sx, gy + 2))

        for ax in TREES:                                      # anchor trees
            sx = ax - cx
            if -12 < sx < VW + 12:
                gy = int(self.ground[ax]) - cy
                pygame.draw.rect(low, (84, 52, 30), (sx - 1, gy - 16, 3, 16))
                pygame.draw.circle(low, (46, 120, 60), (sx, gy - 20), 8)
                pygame.draw.circle(low, (36, 100, 50), (sx - 4, gy - 16), 5)
                pygame.draw.circle(low, (36, 100, 50), (sx + 4, gy - 17), 5)
                pygame.draw.rect(low, (240, 210, 60), (sx, gy - 10, 1, 1))
        for cpx in CPS:                                       # checkpoints
            sx = cpx - cx
            if -12 < sx < VW + 12:
                gy = int(self.ground[cpx]) - cy
                col = (60, 200, 80) if self.cp >= cpx else (240, 150, 40)
                pygame.draw.rect(low, (230, 230, 230), (sx, gy - 16, 1, 16))
                pygame.draw.polygon(low, col, [(sx + 1, gy - 16), (sx + 9, gy - 13), (sx + 1, gy - 10)])
        sx = GOAL_X - cx                                      # finish line
        if not self.cargo_mode and -20 < sx < VW + 20:
            gy = int(self.ground[GOAL_X]) - cy
            pygame.draw.rect(low, (230, 230, 230), (sx, gy - 28, 2, 28))
            for i in range(4):
                for j in range(2):
                    col = (20, 20, 20) if (i + j) % 2 else (240, 240, 240)
                    pygame.draw.rect(low, col, (sx + 2 + i * 4, gy - 28 + j * 4, 4, 4))

        self.draw_world(cx, cy)

        if self.winch:                                        # cable
            c, s = math.cos(self.ang), math.sin(self.ang)
            hk = self.veh["hook"]
            hkx = hk[0] * self.facing
            hx = self.x + c * hkx - s * hk[1] - cx
            hy = self.y + s * hkx + c * hk[1] - cy
            pygame.draw.line(low, (235, 210, 70), (int(hx), int(hy)),
                             (int(self.winch[0] - cx), int(self.winch[1] - cy)))

        if PREFS["ghost"] and self.ghost and not self.won:
            pose = self.ghost.pose(self.frames)
            if pose:
                gsurf.fill((0, 0, 0, 0))
                Game.draw_truck(GhostObj(*pose, self.ghost.v), cx, cy, gsurf, True)
                low.blit(gsurf, (0, 0))
        self.draw_truck(cx, cy)

        for p in self.parts:                                  # mud and water splashes
            pygame.draw.rect(low, p[5], (int(p[0] - cx), int(p[1] - cy), 2, 2))

        wsurf.fill((0, 0, 0, 0))                              # water on top of everything
        for sx in range(VW):
            wx = cx + sx
            if wx >= N:
                break
            wd = self.water[wx]
            if wd > 0.3:
                top = int(self.ground[wx] - wd) - cy
                bot = int(self.ground[wx]) - cy
                pygame.draw.line(wsurf, (45, 105, 205, 140), (sx, top), (sx, bot))
                if ((wx + int(self.t * 8)) // 3) % 4:
                    wsurf.set_at((sx, max(0, min(VH - 1, top))), (190, 225, 255, 230))
        low.blit(wsurf, (0, 0))

        screen.blit(pygame.transform.scale(low, (W, H)), (0, 0))
        self.draw_hud()

    def draw_cargo(self, surf, T):
        cg, veh = self.cargo, self.veh
        x0, x1, fy = veh["bed"]
        cols = max(2, (veh["capacity"] + 1) // 2)
        sw = (x1 - x0) / cols
        col = CARGO_TYPES[cg["kind"]]["color"]
        for i in range(cg["units"]):
            cl, row = i % cols, i // cols
            if cg["kind"] == "logs":
                rad = max(2, int(sw * 0.45))
                p = T(x0 + (cl + 0.5) * sw, fy - rad - row * rad * 1.7)
                pygame.draw.circle(surf, col, p, rad)
                pygame.draw.circle(surf, (176, 130, 80), p, max(1, rad - 2))
            else:
                bx, by = x0 + cl * sw + 0.5, fy - (row + 1) * 5
                pygame.draw.polygon(surf, col, [T(bx, by), T(bx + sw - 1, by),
                                                T(bx + sw - 1, by + 5), T(bx, by + 5)])
                pygame.draw.line(surf, lerp(col, (255, 255, 255), 0.45), T(bx, by + 2.5), T(bx + sw - 1, by + 2.5))

    def draw_truck(self, cx, cy, surf=None, ghost=False):
        surf = low if surf is None else surf
        veh = self.veh
        c, s = math.cos(self.ang), math.sin(self.ang)

        def T(lx, ly):
            lx = lx * self.facing
            return (round(self.x + c * lx - s * ly - cx), round(self.y + s * lx + c * ly - cy))

        def C(col):                                           # the ghost is drawn semi-transparent
            return (col[0], col[1], col[2], GHOST_ALPHA) if ghost else col
        if ghost:
            pal = dict(dark=(90, 150, 215), body=(150, 215, 255), bed=(80, 120, 160),
                       glass=(225, 245, 255), cage=(100, 160, 210))
            tire_o, tire_i, spoke, hub = (70, 110, 150), (110, 160, 200), (200, 230, 250), (230, 245, 255)
        else:
            d = self.dirt * 0.75
            base = COLORS[TRUCK["color"]][1]
            dark = lerp(tuple(int(v * 0.68) for v in base), (70, 48, 28), d)
            pal = dict(dark=dark, body=lerp(base, (92, 62, 36), d), bed=(60, 60, 66),
                       glass=(150, 205, 235), cage=dark)
            tire_o, tire_i, spoke, hub = (24, 24, 28), (70, 70, 78), (170, 170, 180), (200, 200, 210)
        for sh in veh["shapes"]:
            pts = [T(*p) for p in sh[2]]
            if sh[0] == "poly":
                pygame.draw.polygon(surf, C(pal[sh[1]]), pts)
            else:
                pygame.draw.lines(surf, C(pal[sh[1]]), False, pts, sh[3])
        if self.cargo and not ghost:
            self.draw_cargo(surf, T)
        if TRUCK["lights"]:
            for lx, ly in veh["lights"]:
                pygame.draw.polygon(surf, C((255, 240, 150)),
                                    [T(lx, ly), T(lx, ly - 2), T(lx + 3, ly - 2), T(lx + 3, ly)])
        if TRUCK["snorkel"]:
            pygame.draw.lines(surf, C((40, 40, 44)), False, [T(*p) for p in veh["pipe"]], 2)
        if TRUCK["bar"]:
            pygame.draw.lines(surf, C((70, 70, 78)), False, [T(*p) for p in veh["bar"]], 1)
        hl = T(*veh["headlight"])
        pygame.draw.rect(surf, C((255, 240, 150)), (hl[0], hl[1], 2, 2))
        knobs = (0, 4, 8)[TRUCK["tires"]]
        for i, (lx, ly, r) in enumerate(veh["wheels"]):
            hx, hy = T(lx, ly)
            pygame.draw.circle(surf, C(tire_o), (hx, hy), r)
            pygame.draw.circle(surf, C(tire_i), (hx, hy), r - 2)
            a = self.wheels[i][1] + self.ang
            for k in range(knobs):                             # tire tread
                ka = a + k * 2 * math.pi / knobs
                pygame.draw.rect(surf, C((125, 125, 135)),
                                 (round(hx + math.cos(ka) * (r - 0.8)), round(hy + math.sin(ka) * (r - 0.8)), 1, 1))
            pygame.draw.line(surf, C(spoke), (hx, hy),
                             (round(hx + math.cos(a) * (r - 2)), round(hy + math.sin(a) * (r - 2))))
            pygame.draw.rect(surf, C(hub), (hx, hy, 1, 1))

    # ---------------- HUD ----------------
    def draw_hud(self):
        self.hud_common()
        self.hud_mode()

    def hud_common(self):
        kmh = int(math.hypot(self.vx, self.vy) * 0.5)
        text(f"{kmh:3d} KM/H", 16, 12)
        eng = (("ENGINE OK", (120, 230, 120)) if self.engine_on else
               ("FLOODED" if self.flooded else "ENGINE OFF", (240, 90, 80)))
        text(eng[0], 16, 38, eng[1])
        if TRUCK["snorkel"]:
            text("SNORKEL", 170, 38, (240, 210, 70))
        pygame.draw.rect(screen, (0, 0, 0), (16, 66, 154, 18))                 # fuel
        fw = int(150 * self.fuel / self.tank)
        pygame.draw.rect(screen, (230, 190, 40) if self.fuel > 0.2 * self.tank else (230, 60, 50),
                         (18, 68, fw, 14))
        text("FUEL", 178, 64)
        ix = max(1, min(N - 2, int(self.x)))                                   # surface under the vehicle
        if self.water[ix] > 0.3:
            ground_txt, gc = f"WATER {int(self.water[ix])}px", (110, 180, 255)
        elif self.rock[ix]:
            ground_txt, gc = "ROCK", (190, 190, 200)
        elif self.sand[ix] and self.wet[ix] < 0.65:
            ground_txt, gc = "SAND", (230, 205, 130)
        else:
            w = self.wet[ix]
            name = "DRY DIRT" if w < 0.25 else ("WET DIRT" if w < 0.55 else "MUD")
            ground_txt, gc = f"{name} {int(w * 100)}%", (210, 160, 100)
        text(ground_txt, 16, 92, gc)
        if self.slip_max > 30:
            text("WHEELSPIN!", 16, 118, (255, 160, 60))
        wtxt = ("WINCH: attached  [F] reel  [E] release" if self.winch
                else "WINCH: [E] attach to a tree")
        text(wtxt, 16, H - 34, (235, 210, 70))
        if self.msg_t > 0:
            text(self.msg, W // 2, H - 90, (255, 255, 255), center=True)

    def hud_mode(self):
        mm, ss = int(self.time) // 60, int(self.time) % 60
        text(f"{mm:02d}:{ss:02d}", W - 110, 12)
        text(LEVELS[self.idx]["name"], W - 300, 40, (200, 200, 215))
        if self.ghost and PREFS["ghost"]:
            pose = self.ghost.pose(self.frames)
            if pose:
                gap = int(self.x - pose[0])
                txt = f"GHOST {fmt_time(self.ghost.t)}  " + (f"{gap} m ahead" if gap >= 0 else f"{-gap} m behind")
                text(txt, W - 300, 66, (120, 230, 120) if gap >= 0 else (255, 170, 80))
            else:
                text(f"GHOST {fmt_time(self.ghost.t)}  finished", W - 300, 66, (150, 200, 255))
        text(self.veh["name"], W - 300, 92, (170, 170, 185))
        bx, bw = W // 2 - 150, 300                                              # level progress
        pygame.draw.rect(screen, (0, 0, 0), (bx - 2, 14, bw + 4, 10))
        pygame.draw.rect(screen, (90, 90, 100), (bx, 17, bw, 4))
        for cpx in CPS:
            pygame.draw.rect(screen, (240, 150, 40), (bx + int(bw * cpx / GOAL_X), 14, 2, 10))
        pygame.draw.rect(screen, (255, 255, 255), (bx + int(bw * min(self.x, GOAL_X) / GOAL_X) - 3, 13, 6, 12))
        if self.won:
            text("DELIVERED!", W // 2, H // 2 - 50, (120, 240, 120), big, center=True)
            extra = "   NEW BEST!" if self.new_best else ""
            text(f"Time {mm:02d}:{ss:02d}{extra}", W // 2, H // 2,
                 (255, 230, 120) if self.new_best else (255, 255, 255), center=True)
            nxt = "ENTER next level   " if self.idx + 1 < len(LEVELS) else ""
            text(f"{nxt}R retry   ESC menu", W // 2, H // 2 + 40, center=True)
        elif self.t < 10:
            text("D/> gas   A/< reverse+brake   W/S lean   SPACE handbrake", W // 2, H - 62,
                 (200, 200, 200), center=True)
            text("E winch   F reel in   R respawn   H ghost   T turn   F11 fullscreen   ESC menu", W // 2, H - 38,
                 (200, 200, 200), center=True)


# ======================= cargo hauling mode =======================
ZONE = 60            # half-width of a loading / unloading zone (px)
ZONE_TIME = 2.5      # seconds you must stand still in the zone
FUEL_PRICE = 0.6     # $ per fuel unit
TOW_FEE = 40
CANCEL_FEE = 30
MMW, MMH = 400, 40


def draw_building(loc, sx, gy):
    """Pixel-art buildings of the cargo map (sx, gy = screen coords of the ground)."""
    R, circ, poly = pygame.draw.rect, pygame.draw.circle, pygame.draw.polygon
    n, role = loc["name"], loc["role"]
    if role == "depot":
        R(low, (92, 102, 128), (sx - 26, gy - 20, 52, 20))
        poly(low, (150, 70, 60), [(sx - 30, gy - 20), (sx, gy - 31), (sx + 30, gy - 20)])
        R(low, (30, 34, 44), (sx - 7, gy - 13, 14, 13))
    elif n in ("Sawmill", "Lumber Camp"):
        R(low, (122, 86, 52), (sx - 22, gy - 16, 44, 16))
        R(low, (70, 50, 30), (sx - 24, gy - 19, 48, 4))
        circ(low, (185, 190, 200), (sx + 32, gy - 8), 7)
        circ(low, (110, 114, 124), (sx + 32, gy - 8), 2)
        for i in range(4):
            circ(low, (140, 98, 56), (sx - 42 + i * 6, gy - 3), 3)
        for i in range(3):
            circ(low, (150, 108, 64), (sx - 39 + i * 6, gy - 8), 3)
    elif n in ("Cement Plant", "Mixer Plant"):
        for k in (-14, 4):
            R(low, (170, 176, 188), (sx + k, gy - 32, 12, 32))
            circ(low, (150, 156, 168), (sx + k + 6, gy - 32), 6)
        R(low, (110, 116, 130), (sx + 22, gy - 12, 18, 12))
        R(low, (80, 84, 96), (sx - 30, gy - 8, 12, 8))
    elif n in ("Brick Works", "Brick Yard"):
        R(low, (150, 70, 50), (sx - 22, gy - 18, 44, 18))
        R(low, (112, 56, 42), (sx + 10, gy - 42, 8, 24))
        R(low, (90, 90, 96), (sx + 9, gy - 44, 10, 3))
        for i in range(3):
            R(low, (192, 82, 56), (sx - 40 + i * 6, gy - 6, 5, 6))
            R(low, (192, 82, 56), (sx - 40 + i * 6, gy - 12, 5, 5))
    elif n == "Harbor":
        for i, col in enumerate([(200, 60, 50), (60, 110, 190), (220, 170, 50)]):
            R(low, col, (sx - 38 + i * 14, gy - 10, 13, 10))
        R(low, (200, 60, 50), (sx - 31, gy - 20, 13, 10))
        R(low, (230, 190, 40), (sx + 22, gy - 44, 4, 44))
        R(low, (230, 190, 40), (sx - 4, gy - 46, 34, 3))
        pygame.draw.line(low, (60, 60, 66), (sx + 2, gy - 43), (sx + 2, gy - 24))
    else:                                                    # construction site with a crane
        R(low, (230, 190, 40), (sx - 2, gy - 40, 4, 40))
        R(low, (230, 190, 40), (sx - 26, gy - 44, 54, 3))
        pygame.draw.line(low, (60, 60, 66), (sx + 20, gy - 41), (sx + 20, gy - 24))
        R(low, (90, 90, 96), (sx + 17, gy - 24, 7, 3))
        R(low, (150, 150, 160), (sx - 40, gy - 4, 20, 4))
        R(low, (120, 120, 130), (sx + 26, gy - 10, 16, 10))


def draw_station(sx, gy):
    R = pygame.draw.rect
    R(low, (200, 50, 40), (sx - 4, gy - 13, 8, 13))
    R(low, (240, 240, 240), (sx - 5, gy - 16, 10, 3))
    R(low, (50, 50, 56), (sx + 5, gy - 8, 3, 8))
    R(low, (230, 230, 230), (sx - 1, gy - 26, 1, 10))
    R(low, (60, 200, 80), (sx, gy - 26, 7, 5))


def make_minimap(game):
    surf = pygame.Surface((MMW, MMH))
    surf.fill((18, 22, 32))
    g = game.ground
    lo, hi = min(g), max(g)
    for px in range(MMW):
        wx = min(N - 1, int(px * N / MMW))
        gy = 4 + (g[wx] - lo) / (hi - lo + 1e-6) * (MMH - 10)
        if game.rock[wx]:
            col = (110, 110, 125)
        elif game.sand[wx]:
            col = (200, 175, 110)
        elif game.base[wx] > 0.4:
            col = (86, 58, 34)
        else:
            col = (130, 100, 60)
        pygame.draw.line(surf, col, (px, gy), (px, MMH))
        if game.water[wx] > 0.3:
            wy = 4 + (g[wx] - game.water[wx] - lo) / (hi - lo + 1e-6) * (MMH - 10)
            pygame.draw.line(surf, (60, 120, 220), (px, wy), (px, gy))
    return surf


class CargoGame(Game):
    fuel_scale = 4.0

    def __init__(self, hauler):
        self.hauler = hauler
        super().__init__(idx=-1, veh=HAULERS[hauler], level=CARGO_MAP)
        self.home = LOCATIONS[0]["x"]
        self.spawn(self.home)
        self.cam_x = max(0, self.x - 120)
        self.job = None
        self.jobs = []
        self.board = False
        self.bsel = 0
        self.zone_t = 0.0
        self.tilt_t = 0.0
        self.wet_t = 0.0
        self.props = []
        self.refueling = False
        self.make_jobs()
        self.mm = make_minimap(self)

    # ---------------- jobs ----------------
    def new_job(self, avoid=()):
        srcs = [l for l in LOCATIONS if l["role"] == "source"]
        sites = [l for l in LOCATIONS if l["role"] == "site"]
        cap = self.veh["capacity"]
        for _ in range(200):
            a, b = random.choice(srcs), random.choice(sites)
            dist = abs(a["x"] - b["x"])
            if dist < 600 or any(j["src"] is a and j["dst"] is b for j in avoid):
                continue
            lo, hi = sorted((a["x"], b["x"]))
            if a["cargo"] == "cement" and max(self.water[i] for i in range(lo, hi, 4)) > 17:
                continue                                   # cement would be ruined on the way
            qty = max(1, int(round(cap * random.uniform(0.5, 1.0))))
            ct = CARGO_TYPES[a["cargo"]]
            return dict(kind=a["cargo"], qty=qty, src=a, dst=b, dist=dist,
                        pay=int(qty * ct["pay"] * (0.6 + dist / 1000.0)), limit=int(dist / 38 + 45))
        return None

    def make_jobs(self):
        jobs = []
        while len(jobs) < 4:
            j = self.new_job(jobs)
            if j is None:
                break
            jobs.append(j)
        jobs.sort(key=lambda j: j["dist"])
        self.jobs = jobs

    def job_limit(self, j):
        """Delivery time limit + the time needed to reach the pick-up point from where you are."""
        return j["limit"] + int(abs(self.x - j["src"]["x"]) / 38)

    def board_key(self, k):
        if k in (pygame.K_UP, pygame.K_w):
            self.bsel = (self.bsel - 1) % len(self.jobs)
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.bsel = (self.bsel + 1) % len(self.jobs)
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.cargo:
                self.say("Finish or cancel (C) your current delivery first!", 3)
            else:
                j = self.jobs[self.bsel]
                self.job = dict(j, state="load", elapsed=0.0, limit=self.job_limit(j))
                self.jobs[self.bsel] = self.new_job(self.jobs) or j
                self.zone_t = 0.0
                self.say(f"Job accepted: go to the {j['src']['name']}", 3)
            self.board = False
        elif k in (pygame.K_j, pygame.K_ESCAPE):
            self.board = False

    def open_board(self):
        if self.cargo:
            self.say("You are carrying cargo - deliver it (or cancel with C).", 3)
        else:
            self.board, self.bsel = True, 0

    def cancel_job(self):
        if not self.job:
            self.say("No active job.", 2)
            return
        if self.cargo:
            self.lose_units(self.cargo["units"], "Cargo dumped")
        self.job = None
        fee = min(CAREER["money"], CANCEL_FEE)
        CAREER["money"] -= fee
        self.say(f"Job cancelled (-${int(fee)})", 3)
        save_all()

    def complete_job(self):
        j, cg = self.job, self.cargo
        units = cg["units"] if cg else 0
        on_time = j["elapsed"] <= j["limit"]
        pay = int(j["pay"] * units / j["qty"] * (1.25 if on_time else 0.8))
        CAREER["money"] += pay
        CAREER["jobs"] += 1
        CAREER["units"] += units
        self.say(f"Delivered {units}/{j['qty']} {CARGO_TYPES[j['kind']]['name']}  +${pay}"
                 + ("  (on-time bonus!)" if on_time else "  (late)"), 5)
        self.cargo = None
        self.job = None
        self.refresh_mass()
        save_all()

    # ---------------- cargo ----------------
    def refresh_mass(self):
        self.m = self.m0 + (self.cargo["units"] * CARGO_TYPES[self.cargo["kind"]]["mass"] if self.cargo else 0.0)

    def lose_units(self, n, why):
        cg = self.cargo
        if not cg or n <= 0:
            return
        n = min(n, cg["units"])
        c, s = math.cos(self.ang), math.sin(self.ang)
        x0, x1, fy = self.veh["bed"]
        for _ in range(n):
            bx = random.uniform(x0, x1) * self.facing
            self.props.append(dict(kind=cg["kind"], x=self.x + c * bx - s * fy, y=self.y + s * bx + c * fy - 4,
                                   vx=self.vx * 0.5 + random.uniform(-20, 20), vy=-30 + random.uniform(-20, 0),
                                   rest=False))
        del self.props[:max(0, len(self.props) - 40)]
        cg["units"] -= n
        self.say(why, 3)
        if cg["units"] <= 0:
            self.cargo = None
            if self.job and self.job["state"] == "deliver":
                self.job = None
                self.say("Job failed - all cargo lost!", 4)
        self.refresh_mass()

    def update(self, keys):
        if self.board:                                     # the world is paused while the board is open
            self.t += DT
            return
        self.refresh_mass()
        super().update(keys)

    def extra_update(self, keys):
        dt = DT
        c, s = math.cos(self.ang), math.sin(self.ang)
        speed = math.hypot(self.vx, self.vy)
        landed = self.grounded and not self.was_grounded
        cg = self.cargo
        if cg:                                             # --- cargo can be damaged or lost
            kind = cg["kind"]
            if math.cos(self.ang) < -0.2:
                self.lose_units(cg["units"], "Rolled over - cargo spilled!")
            elif kind == "logs":
                if abs(math.sin(self.ang)) > 0.6 and math.cos(self.ang) > 0:
                    self.tilt_t += dt
                    if self.tilt_t > 0.5:
                        self.tilt_t = 0.0
                        self.lose_units(1, "A log rolled off the truck!")
                else:
                    self.tilt_t = max(0.0, self.tilt_t - dt)
            elif kind == "cement":
                x0, x1, fy = self.veh["bed"]
                bx = (x0 + x1) / 2.0 * self.facing
                wx = self.x + c * bx - s * fy
                wy = self.y + s * bx + c * fy
                wi = max(0, min(N - 1, int(wx)))
                if self.water[wi] > 0.3 and wy > self.ground[wi] - self.water[wi]:
                    self.wet_t += dt
                    if self.wet_t > 0.8:
                        self.wet_t = 0.0
                        self.lose_units(1, "Cement soaked and ruined!")
                else:
                    self.wet_t = max(0.0, self.wet_t - dt)
            elif kind == "bricks":
                if landed and self.vy_before > 140:
                    self.lose_units(2 if self.vy_before > 230 else 1, "Bricks cracked on the landing!")

        j = self.job                                       # --- loading and unloading
        if j:
            j["elapsed"] += dt
            loc = j["src"] if j["state"] == "load" else j["dst"]
            if abs(self.x - loc["x"]) <= ZONE and speed < 14 and self.grounded:
                self.zone_t += dt / ZONE_TIME
            else:
                self.zone_t = max(0.0, self.zone_t - dt / 1.5)
            if self.zone_t >= 1.0:
                self.zone_t = 0.0
                if j["state"] == "load":
                    self.cargo = dict(kind=j["kind"], units=j["qty"])
                    j["state"] = "deliver"
                    self.refresh_mass()
                    self.say(f"Loaded {j['qty']} {CARGO_TYPES[j['kind']]['name']}! "
                             f"Deliver to the {j['dst']['name']}", 4)
                else:
                    self.complete_job()
        else:
            self.zone_t = 0.0

        near = next((st for st in STATIONS if abs(self.x - st) <= 50), None)   # --- fuel stations
        was = self.refueling
        self.refueling = False
        if near is not None:
            self.home = near
            if speed < 15 and self.fuel < self.tank and CAREER["money"] > 0:
                add = min(self.tank - self.fuel, 14 * dt, CAREER["money"] / FUEL_PRICE)
                self.fuel += add
                CAREER["money"] -= add * FUEL_PRICE
                self.refueling = True
                if not self.engine_on and not self.flooded and self.fuel > 0:
                    self.engine_on = True
        if was and not self.refueling:
            save_all()

        for p in self.props:                               # dropped cargo falls to the ground
            if p["rest"]:
                continue
            p["vy"] += G * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            gi = max(0, min(N - 1, int(p["x"])))
            if p["y"] >= self.ground[gi] - 3:
                p["y"], p["rest"] = self.ground[gi] - 3, True

    def respawn(self):
        fee = min(CAREER["money"], TOW_FEE)
        CAREER["money"] -= fee
        self.fuel = max(self.fuel, 0.3 * self.tank)
        self.spawn(self.home)
        self.say(f"Towed back to the nearest station (-${int(fee)})", 3)
        save_all()

    # ---------------- drawing ----------------
    def target(self):
        if not self.job:
            return None
        return self.job["src"] if self.job["state"] == "load" else self.job["dst"]

    def draw_world(self, cx, cy):
        tgt = self.target()
        blink = int(self.t * 4) % 2
        for loc in LOCATIONS:
            sx = loc["x"] - cx
            if -90 < sx < VW + 90:
                gy = int(self.ground[loc["x"]]) - cy
                draw_building(loc, sx, gy)
                if loc["role"] != "depot":
                    col = ((60, 230, 90) if blink else (240, 240, 240)) if loc is tgt else (240, 200, 50)
                    for dx in (-ZONE, ZONE):
                        pygame.draw.rect(low, col, (sx + dx - 1, int(self.ground[loc["x"] + dx]) - cy - 10, 2, 10))
        for stx in STATIONS:
            sx = stx - cx
            if -20 < sx < VW + 20:
                draw_station(sx, int(self.ground[stx]) - cy)
        for p in self.props:
            sx, sy = int(p["x"] - cx), int(p["y"] - cy)
            if -10 < sx < VW + 10:
                col = CARGO_TYPES[p["kind"]]["color"]
                if p["kind"] == "logs":
                    pygame.draw.circle(low, col, (sx, sy), 3)
                else:
                    pygame.draw.rect(low, col, (sx - 3, sy - 2, 6, 5))

    def hud_mode(self):
        cx, cy = int(self.cam_x), int(self.cam_y)
        tgt = self.target()
        # names of nearby sites
        for loc in LOCATIONS:
            sx = loc["x"] - cx
            if -60 < sx < VW + 60:
                gy = int(self.ground[loc["x"]]) - cy
                text(loc["name"], sx * SCALE, (gy - 52) * SCALE, (255, 230, 140) if loc is tgt else (235, 235, 235),
                     small, center=True)
        for stx in STATIONS:
            sx = stx - cx
            if -20 < sx < VW + 20:
                text("FUEL", sx * SCALE, (int(self.ground[stx]) - cy - 34) * SCALE, (120, 240, 140), small, center=True)

        # minimap of the whole map
        mx, my = W // 2 - MMW // 2, 8
        screen.blit(self.mm, (mx, my))
        pygame.draw.rect(screen, (240, 190, 60), (mx - 1, my - 1, MMW + 2, MMH + 2), 1)
        for loc in LOCATIONS:
            px = mx + int(loc["x"] / N * MMW)
            col = {"depot": (240, 240, 240), "source": (240, 200, 50), "site": (90, 200, 255)}[loc["role"]]
            pygame.draw.rect(screen, col, (px - 2, my + 2, 4, 6))
        for stx in STATIONS:
            pygame.draw.rect(screen, (90, 230, 120), (mx + int(stx / N * MMW) - 1, my + MMH - 8, 3, 6))
        if tgt and int(self.t * 3) % 2:
            tx = mx + int(tgt["x"] / N * MMW)
            pygame.draw.rect(screen, (255, 255, 255), (tx - 5, my - 3, 10, MMH + 6), 2)
        pygame.draw.rect(screen, (255, 70, 60), (mx + int(self.x / N * MMW) - 3, my + 12, 6, 14))

        # money and job panel
        rx = W - 270
        text(f"$ {int(CAREER['money'])}", rx, 12, (120, 240, 140), mid)
        j = self.job
        if j:
            ct = CARGO_TYPES[j["kind"]]
            text(f"{j['qty']}x {ct['name']}", rx, 44, ct["color"] if j["kind"] != "cement" else (200, 205, 220))
            text(f"{j['src']['name']} > {j['dst']['name']}", rx, 68, (210, 210, 225), small)
            late = j["elapsed"] > j["limit"]
            text(f"TIME {fmt_time(j['elapsed'])} / {fmt_time(j['limit'])}", rx, 90,
                 (255, 120, 90) if late else (230, 230, 230))
            text(f"PAY ${j['pay']}", rx, 114, (240, 210, 70))
            if tgt:
                dist = int(abs(self.x - tgt["x"]))
                arrow = ">>" if tgt["x"] > self.x else "<<"
                lab = "LOAD AT" if j["state"] == "load" else "DELIVER TO"
                text(f"{lab} {tgt['name'].upper()}: {dist} m {arrow}", W // 2, 62, (255, 230, 140), center=True)
        else:
            text("No job - press J", rx, 44, (200, 200, 215))
        if self.cargo:
            tons = self.m * 2.0
            text(f"LOAD {self.cargo['units']} {CARGO_TYPES[self.cargo['kind']]['name']}   WEIGHT {tons:.1f} t",
                 16, H - 62, (230, 230, 240))
        else:
            text(f"EMPTY   WEIGHT {self.m * 2.0:.1f} t   CAPACITY {self.veh['capacity']}", 16, H - 62, (170, 170, 185))
        if self.zone_t > 0.02:
            bx, by = W // 2 - 150, H // 2 + 70
            pygame.draw.rect(screen, (0, 0, 0), (bx - 3, by - 3, 306, 26))
            pygame.draw.rect(screen, (60, 220, 100), (bx, by, int(300 * min(1.0, self.zone_t)), 20))
            text("LOADING..." if j and j["state"] == "load" else "UNLOADING...", W // 2, by - 18, center=True)
        if self.refueling:
            text("REFUELING...  (" + f"${FUEL_PRICE}/unit)", W // 2, H // 2 + 20, (120, 240, 140), center=True)
        elif any(abs(self.x - st) <= 50 for st in STATIONS) and self.fuel < self.tank * 0.98:
            text("FUEL STATION - stop here to refuel", W // 2, H // 2 + 20, (120, 240, 140), center=True)
        if self.t < 12 and not self.board:
            text("J jobs   C cancel   R tow   E winch   F reel   T turn around   F11 fullscreen   ESC menu",
                 W // 2, H - 38, (200, 200, 200), center=True)
        if self.board:
            self.draw_board()

    def draw_board(self):
        ov.fill((0, 0, 0, 0))
        pygame.draw.rect(ov, (0, 0, 0, 200), (110, 80, 740, 380))
        screen.blit(ov, (0, 0))
        text("JOB BOARD", W // 2, 112, (240, 190, 60), mid, center=True)
        for i, j in enumerate(self.jobs):
            y = 140 + i * 66
            on = i == self.bsel
            if on:
                pygame.draw.rect(screen, (240, 190, 60), (122, y, 716, 60), 3)
            ct = CARGO_TYPES[j["kind"]]
            text(f"{j['qty']}x {ct['name']}   {j['src']['name']} > {j['dst']['name']}", 136, y + 6,
                 (255, 230, 140) if on else (230, 230, 230))
            text(f"{j['dist']} m    time limit {fmt_time(self.job_limit(j))}    pay ${j['pay']}", 136, y + 32,
                 (190, 190, 205))
        text("UP/DOWN select    ENTER accept    J or ESC close", W // 2, 436, (200, 200, 200), center=True)


# ======================= menus, garage and the main loop =======================
PREVIEWS = []
CARGO_PREVIEW = None


def render_profile(lv, pw, ph):
    """Side profile of a level (rock / mud / sand / water) for the menu cards."""
    apply_level(lv)
    g, water, wet, base, rock, bed, orig, sand = build_level()
    n = lv["n"]
    surf = pygame.Surface((pw, ph))
    surf.fill(lv["theme"][0])
    lo = min(g[i] - water[i] for i in range(n))
    hi = max(g) + 4
    for px in range(pw):
        wx = min(n - 1, int(px / pw * n))
        gy = 12 + (g[wx] - lo) / (hi - lo) * (ph - 24)
        if rock[wx]:
            col = (120, 120, 135)
        elif sand[wx]:
            col = (200, 175, 110)
        elif base[wx] > 0.4:
            col = (80, 54, 30)
        else:
            col = (150, 108, 58)
        pygame.draw.line(surf, col, (px, gy), (px, ph))
        if water[wx] > 0.3:
            wy = 12 + (g[wx] - water[wx] - lo) / (hi - lo) * (ph - 24)
            pygame.draw.line(surf, (60, 120, 220), (px, wy), (px, gy))
    return surf


def make_previews():
    global CARGO_PREVIEW
    pw, ph = 440, 140
    for lv in LEVELS:
        surf = render_profile(lv, pw, ph)
        for cp in lv["cps"]:
            pygame.draw.rect(surf, (240, 150, 40), (int(cp / lv["n"] * pw), 4, 2, 10))
        pygame.draw.rect(surf, (255, 255, 255), (int(lv["goal"] / lv["n"] * pw), 2, 3, 14))
        PREVIEWS.append(surf)
    surf = render_profile(CARGO_MAP, pw, ph)
    n = CARGO_MAP["n"]
    for loc in LOCATIONS:
        col = {"depot": (240, 240, 240), "source": (240, 200, 50), "site": (90, 200, 255)}[loc["role"]]
        pygame.draw.rect(surf, col, (int(loc["x"] / n * pw) - 1, 3, 3, 14))
    for stx in STATIONS:
        pygame.draw.rect(surf, (90, 230, 120), (int(stx / n * pw) - 1, ph - 10, 3, 8))
    CARGO_PREVIEW = surf
    apply_level(LEVELS[0])


def draw_scene(t, deco):
    """Shared background of the menus: sky, hills, road and a vehicle driving on the spot."""
    low.fill((118, 178, 230))
    pygame.draw.rect(low, (150, 205, 240), (0, 0, VW, 50))
    pts = [(0, VH)]
    for sx in range(0, VW + 8, 8):
        wx = sx + t * 20
        pts.append((sx, 112 + 14 * math.sin(wx / 41.0) + 8 * math.sin(wx / 17.0 + 2)))
    pts.append((VW, VH))
    pygame.draw.polygon(low, (96, 150, 120), pts)
    pygame.draw.rect(low, (110, 76, 42), (0, 150, VW, VH - 150))
    pygame.draw.rect(low, (150, 108, 58), (0, 150, VW, 3))
    for i in range(-1, 12):
        pygame.draw.rect(low, (80, 54, 30), (int(i * 32 - (t * 60) % 32), 164, 14, 2))
    deco.x, deco.y, deco.ang = 245.0, 150.0 - deco.bottom + math.sin(t * 14) * 0.6, math.sin(t * 3) * 0.02
    for w in deco.wheels:
        w[1] += 0.18
    deco.draw_truck(0, 0)
    screen.blit(pygame.transform.scale(low, (W, H)), (0, 0))


def accel_of(st):
    return sum(st["torque"] / w[2] for w in st["veh"]["wheels"]) / st["veh"]["mass"]


def speed_of(st):
    return st["wmax"] * st["veh"]["wheels"][0][2]


def stat_bar(label, frac, x, y, w=200, off=170):
    text(label, x, y)
    pygame.draw.rect(screen, (0, 0, 0), (x + off, y + 2, w, 18))
    pygame.draw.rect(screen, (90, 200, 110), (x + off + 2, y + 4, int((w - 4) * max(0.05, min(1.0, frac))), 14))


MAIN_ITEMS = ["TIME TRIAL", "CARGO HAULING", "GARAGE", "FULLSCREEN", "QUIT"]


def draw_main(sel, t, deco):
    draw_scene(t, deco)
    ov.fill((0, 0, 0, 0))
    pygame.draw.rect(ov, (0, 0, 0, 130), (36, 140, 400, len(MAIN_ITEMS) * 60 + 14))
    pygame.draw.rect(ov, (0, 0, 0, 130), (464, 140, 456, 250))
    screen.blit(ov, (0, 0))
    text("MUD PIXEL RUNNER", W // 2, 58, (240, 190, 60), title_font, center=True)
    text("trials  -  cargo  -  garage", W // 2, 100, (200, 200, 215), center=True)
    for i, name in enumerate(MAIN_ITEMS):
        y = 148 + i * 60
        on = i == sel
        if on:
            pygame.draw.rect(screen, (240, 190, 60), (44, y, 384, 50), 3)
        label = name if name != "FULLSCREEN" else "FULLSCREEN: " + ("ON" if PREFS["fullscreen"] else "OFF")
        text(label, 62, y + 13, (255, 230, 140) if on else (230, 230, 230), mid)

    name = MAIN_ITEMS[sel]
    x, y = 480, 152
    if name == "TIME TRIAL":
        text("TIME TRIAL", x, y, (255, 230, 140), mid)
        for i, s in enumerate([f"{len(LEVELS)} levels, from easy to brutal", f"{len(VEHICLES)} vehicles, each with its own specs",
                               "Best times and ghost runs", "Winches, snorkels, deep mud and water"]):
            text(s, x, y + 40 + i * 28, (225, 225, 235))
        text(f"Vehicle: {VEHICLES[TRUCK['vehicle']]['name']}", x, y + 170, (140, 205, 255))
    elif name == "CARGO HAULING":
        text("CARGO HAULING", x, y, (255, 230, 140), mid)
        for i, s in enumerate(["Open-world delivery jobs", "Haul LOGS, CEMENT and BRICKS", "Light truck or heavy-duty 6x6",
                               f"A {CARGO_MAP['n']} m map with {len(LOCATIONS)} sites"]):
            text(s, x, y + 40 + i * 28, (225, 225, 235))
        text(f"Money ${int(CAREER['money'])}   Jobs {CAREER['jobs']}", x, y + 170, (120, 240, 140))
    elif name == "GARAGE":
        text("GARAGE", x, y, (255, 230, 140), mid)
        text(f"Points used {truck_cost(TRUCK)}/{BUDGET}", x, y + 38, (240, 210, 70))
        for i, (label, key, _) in enumerate(GARAGE_ROWS):
            text(f"{label:12s} {option_name(key, TRUCK[key])}", x, y + 66 + i * 21, (220, 220, 230), small)
    elif name == "FULLSCREEN":
        text("FULLSCREEN", x, y, (255, 230, 140), mid)
        text("Press ENTER to switch,", x, y + 40, (225, 225, 235))
        text("or press F11 at any time.", x, y + 68, (225, 225, 235))
    else:
        text("QUIT", x, y, (255, 230, 140), mid)
        text("See you on the trails!", x, y + 40, (225, 225, 235))
    text("UP/DOWN select   ENTER open   F11 fullscreen   ESC quit", W // 2, H - 34, (210, 210, 210), center=True)


def draw_trial(sel, t, deco):
    draw_scene(t, deco)
    rows = len(LEVELS)
    ov.fill((0, 0, 0, 0))
    pygame.draw.rect(ov, (0, 0, 0, 130), (36, 98, 412, rows * 46 + 14))
    pygame.draw.rect(ov, (0, 0, 0, 130), (464, 98, 456, 312))
    screen.blit(ov, (0, 0))
    text("TIME TRIAL", W // 2, 48, (240, 190, 60), title_font, center=True)
    vi = TRUCK["vehicle"]
    for i, lv in enumerate(LEVELS):
        y = 106 + i * 46
        on = i == sel
        if on:
            pygame.draw.rect(screen, (240, 190, 60), (44, y, 396, 40), 3)
        text(f"{i + 1}.{lv['name']}", 56, y + 8, (255, 230, 140) if on else (230, 230, 230), mid)
        for d in range(5):
            pygame.draw.rect(screen, (230, 90, 60) if d < lv["diff"] else (70, 70, 70), (284 + d * 13, y + 13, 10, 14))
        b = BEST.get(rec_key(i, vi))
        if b is not None:
            text(fmt_time(b), 360, y + 10, (120, 230, 120))
    lv = LEVELS[sel]
    screen.blit(PREVIEWS[sel], (476, 108))
    pygame.draw.rect(screen, (240, 190, 60), (476, 108, 440, 140), 2)
    text(lv["name"], 476, 254, (255, 230, 140), mid)
    text(lv["desc"][0], 476, 284)
    text(lv["desc"][1], 476, 306)
    key = rec_key(sel, vi)
    b = BEST.get(key)
    text(f"Length {lv['goal']}   Best {fmt_time(b) if b is not None else '--'}", 476, 336, (200, 200, 215))
    text("Ghost run saved" if key in GHOSTS else "No ghost yet for this vehicle", 476, 358, (150, 200, 255))
    text(f"< {VEHICLES[vi]['name']} >", 476, 382, (140, 205, 255))
    text("UP/DOWN level   LEFT/RIGHT vehicle   ENTER start   G garage   ESC back", W // 2, H - 34,
         (210, 210, 210), center=True)


def draw_cargo_hub(t, deco):
    draw_scene(t, deco)
    ov.fill((0, 0, 0, 0))
    pygame.draw.rect(ov, (0, 0, 0, 130), (36, 98, 428, 300))
    pygame.draw.rect(ov, (0, 0, 0, 130), (480, 98, 440, 300))
    screen.blit(ov, (0, 0))
    text("CARGO HAULING", W // 2, 48, (240, 190, 60), title_font, center=True)
    for i, vi in enumerate(HAULERS):
        y = 106 + i * 144
        on = CAREER["hauler"] == i
        v, st = VEHICLES[vi], truck_stats(vi)
        if on:
            pygame.draw.rect(screen, (240, 190, 60), (44, y, 412, 134), 3)
        text(v["role"], 58, y + 8, (255, 230, 140) if on else (230, 230, 230), mid)
        text(f"{v['name']}   capacity {v['capacity']} units   empty {v['mass'] * 2:.1f} t", 58, y + 36,
             (200, 200, 215), small)
        stat_bar("POWER", accel_of(st) / 230, 58, y + 58, 150, 110)
        stat_bar("TOP SPEED", speed_of(st) / 180, 58, y + 80, 150, 110)
        stat_bar("FUEL TANK", st["tank"] / 160, 58, y + 102, 150, 110)
    screen.blit(CARGO_PREVIEW, (488, 106))
    pygame.draw.rect(screen, (240, 190, 60), (488, 106, 440, 140), 2)
    text("yellow = pick-up   blue = drop-off   green = fuel", 488, 252, (210, 210, 225), small)
    text(f"MONEY ${int(CAREER['money'])}", 488, 278, (120, 240, 140), mid)
    text(f"Jobs done {CAREER['jobs']}   Units delivered {CAREER['units']}", 488, 308, (225, 225, 235), small)
    text("LOGS roll off on steep slopes", 488, 334, (176, 130, 80), small)
    text("CEMENT is ruined by water", 488, 354, (190, 195, 215), small)
    text("BRICKS crack on hard landings", 488, 374, (220, 110, 85), small)
    text("LEFT/RIGHT choose truck   ENTER start   G garage   ESC back", W // 2, H - 34, (210, 210, 210), center=True)


def draw_garage(gsel, t, deco, msg):
    draw_scene(t, deco)
    ov.fill((0, 0, 0, 0))
    pygame.draw.rect(ov, (0, 0, 0, 140), (36, 98, 440, len(GARAGE_ROWS) * 44 + 16))
    pygame.draw.rect(ov, (0, 0, 0, 140), (492, 98, 428, 214))
    pygame.draw.rect(ov, (0, 0, 0, 140), (492, 322, 428, 80))
    screen.blit(ov, (0, 0))
    text("GARAGE", W // 2, 48, (140, 205, 255), title_font, center=True)

    used = truck_cost(TRUCK)
    for i, (label, key, count) in enumerate(GARAGE_ROWS):
        y = 106 + i * 44
        on = i == gsel
        if on:
            pygame.draw.rect(screen, (240, 190, 60), (44, y, 424, 38), 3)
        text(label, 58, y + 8, (255, 230, 140) if on else (230, 230, 230))
        v = TRUCK[key]
        if key == "color":
            pygame.draw.rect(screen, COLORS[v][1], (200, y + 8, 18, 22))
        text(f"< {option_name(key, v)} >", 226 if key == "color" else 200, y + 8, (255, 255, 255))
        cost = option_cost(key, v)
        if cost:
            text(f"{cost} pt", 424, y + 8, (240, 210, 70))

    text(f"POINTS {used}/{BUDGET}", 508, 108, (240, 210, 70))
    for i in range(BUDGET):
        pygame.draw.rect(screen, (240, 210, 70) if i < used else (70, 70, 70), (700 + i * 24, 110, 20, 18))
    st = truck_stats()
    stat_bar("POWER", accel_of(st) / 230, 508, 140)
    stat_bar("TOP SPEED", speed_of(st) / 180, 508, 168)
    stat_bar("MUD GRIP", MU0 * st["grip"] * (1 - st["mudk"] * 0.9) / 0.6, 508, 196)
    stat_bar("DRY GRIP", MU0 * st["grip"] / 1.3, 508, 224)
    stat_bar("WINCH PULL", st["w_max"] / 1300, 508, 252)
    cap = st["veh"]["capacity"]
    text(f"Wading {wading_depth(st)} px   " + (f"Cargo bed {cap} units" if cap else "No cargo bed"),
         508, 282, (150, 200, 255))

    label, key, _ = GARAGE_ROWS[gsel]
    info = option_info(key, TRUCK[key])
    text(f"{label}: {option_name(key, TRUCK[key])}", 508, 330, (255, 230, 140))
    text(info[0], 508, 356)
    text(info[1], 508, 376)
    if msg:
        text(msg, W // 2, H - 66, (255, 110, 90), center=True)
    text("UP/DOWN row   LEFT/RIGHT change   ENTER back", W // 2, H - 34, (210, 210, 210), center=True)


def garage_change(row, d):
    """Changes an option; returns an error message when the points budget is exceeded."""
    label, key, count = GARAGE_ROWS[row]
    cfg = dict(TRUCK)
    cfg[key] = (cfg[key] + d) % count
    if truck_cost(cfg) > BUDGET:
        return "NOT ENOUGH POINTS - lower another upgrade first"
    TRUCK.update(cfg)
    save_all()
    return ""


def set_fullscreen(on):
    """Window <-> fullscreen. The game renders at 960x540 and is scaled with bars at the edges."""
    global screen
    flags = FLAGS | (pygame.FULLSCREEN if on else 0)
    try:
        screen = pygame.display.set_mode((W, H), flags)
        PREFS["fullscreen"] = on
    except pygame.error:
        screen = pygame.display.set_mode((W, H), FLAGS)
        PREFS["fullscreen"] = False
    save_all()


def main():
    make_previews()
    if PREFS["fullscreen"]:
        set_fullscreen(True)
    deco = Game(0)
    deco.dirt = 0.4
    state, msel, tsel, gsel, game, t = "main", 0, 0, 0, None, 0.0
    garage_from = "main"
    gmsg, gmsg_t = "", 0.0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type != pygame.KEYDOWN:
                continue
            k = event.key
            enter = k in (pygame.K_RETURN, pygame.K_KP_ENTER)
            up = k in (pygame.K_UP, pygame.K_w)
            down = k in (pygame.K_DOWN, pygame.K_s)
            left = k in (pygame.K_LEFT, pygame.K_a)
            right = k in (pygame.K_RIGHT, pygame.K_d)
            if k == pygame.K_F11 or (enter and event.mod & pygame.KMOD_ALT):
                set_fullscreen(not PREFS["fullscreen"])
                continue
            if state == "main":
                if k == pygame.K_ESCAPE:
                    running = False
                elif up:
                    msel = (msel - 1) % len(MAIN_ITEMS)
                elif down:
                    msel = (msel + 1) % len(MAIN_ITEMS)
                elif enter:
                    name = MAIN_ITEMS[msel]
                    if name == "TIME TRIAL":
                        state = "trial"
                    elif name == "CARGO HAULING":
                        state = "cargo"
                    elif name == "GARAGE":
                        state, garage_from = "garage", "main"
                    elif name == "FULLSCREEN":
                        set_fullscreen(not PREFS["fullscreen"])
                    else:
                        running = False
            elif state == "trial":
                if k == pygame.K_ESCAPE:
                    state = "main"
                elif up:
                    tsel = (tsel - 1) % len(LEVELS)
                elif down:
                    tsel = (tsel + 1) % len(LEVELS)
                elif left or right:
                    garage_change(0, 1 if right else -1)              # row 0 = VEHICLE
                elif k == pygame.K_g:
                    state, garage_from = "garage", "trial"
                elif enter:
                    game, state = Game(tsel), "play"
                elif pygame.K_1 <= k <= pygame.K_9 and k - pygame.K_1 < len(LEVELS):
                    tsel = k - pygame.K_1
            elif state == "cargo":
                if k == pygame.K_ESCAPE:
                    state = "main"
                elif up or down or left or right:
                    CAREER["hauler"] = 1 - CAREER["hauler"]
                    save_all()
                elif k == pygame.K_g:
                    state, garage_from = "garage", "cargo"
                elif enter:
                    game, state = CargoGame(CAREER["hauler"]), "cargoplay"
            elif state == "garage":
                if k in (pygame.K_ESCAPE, pygame.K_g) or enter:
                    state = garage_from
                elif up:
                    gsel = (gsel - 1) % len(GARAGE_ROWS)
                elif down:
                    gsel = (gsel + 1) % len(GARAGE_ROWS)
                elif left or right:
                    gmsg = garage_change(gsel, 1 if right else -1)
                    gmsg_t = 2.5
            elif state == "play":
                if k == pygame.K_ESCAPE:
                    tsel, state = game.idx, "trial"
                elif k == pygame.K_r:
                    if game.won:
                        game = Game(game.idx)
                    else:
                        game.respawn()
                elif k == pygame.K_e:
                    game.toggle_winch()
                elif k == pygame.K_t:
                    game.turn_around()
                elif k == pygame.K_h:
                    PREFS["ghost"] = not PREFS["ghost"]
                    game.say("Ghost shown" if PREFS["ghost"] else "Ghost hidden", 2)
                    save_all()
                elif enter and game.won:
                    if game.idx + 1 < len(LEVELS):
                        game = Game(game.idx + 1)
                    else:
                        tsel, state = game.idx, "trial"
            elif state == "cargoplay":
                if game.board:
                    game.board_key(k)
                elif k == pygame.K_ESCAPE:
                    save_all()
                    state = "cargo"
                elif k == pygame.K_j:
                    game.open_board()
                elif k == pygame.K_e:
                    game.toggle_winch()
                elif k == pygame.K_t:
                    game.turn_around()
                elif k == pygame.K_r:
                    game.respawn()
                elif k == pygame.K_c:
                    game.cancel_job()
        t += DT
        gmsg_t = max(0.0, gmsg_t - DT)
        if state in ("main", "trial", "garage", "cargo"):
            want = HAULERS[CAREER["hauler"]] if state == "cargo" else TRUCK["vehicle"]
            if deco.vi != want:
                deco.set_vehicle(want)
        if state == "main":
            draw_main(msel, t, deco)
        elif state == "trial":
            draw_trial(tsel, t, deco)
        elif state == "cargo":
            draw_cargo_hub(t, deco)
        elif state == "garage":
            draw_garage(gsel, t, deco, gmsg if gmsg_t > 0 else "")
        else:
            game.update(pygame.key.get_pressed())
            game.draw()
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()


if __name__ == "__main__":
    main()
