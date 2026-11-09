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
I_BODY = 260.0
DW, BF = 0.35, 1.1       # сопротивление воды и выталкивающая сила
DIG = 0.06               # скорость вырывания колеи
FUEL_MAX = 100.0
GHOST_STEP = 3           # призрак записывается раз в 3 кадра
GHOST_ALPHA = 120

# точки контакта кузова: (x, y, радиус, колесо?)  — первые две точки это колёса
POINTS = [(-14, 6, 6, True), (14, 6, 6, True), (0, 6, 3, False),
          (-22, 3, 2, False), (22, 3, 2, False), (-9, -12, 3, False), (8, -12, 3, False)]
HOOK = (22, 3)           # крюк лебёдки

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
    global N, GOAL_X, CTRL, PONDS, MUD, ROCK, TREES, CPS, THEME
    N, GOAL_X = lv["n"], lv["goal"]
    CTRL, PONDS, MUD, ROCK = lv["ctrl"], lv["ponds"], lv["mud"], lv["rock"]
    TREES, CPS, THEME = make_trees(lv), list(lv["cps"]), lv["theme"]


# ======================= кастомизация грузовика =======================
COLORS = [("RED", (200, 52, 42)), ("ORANGE", (228, 126, 36)), ("YELLOW", (232, 204, 50)),
          ("GREEN", (58, 160, 72)), ("BLUE", (56, 104, 212)), ("WHITE", (226, 226, 232)),
          ("BLACK", (52, 52, 60)), ("PURPLE", (142, 72, 192))]
TIRES = [
    dict(name="ROAD", cost=0, grip=1.12, mudk=0.92, rr=0.0,
         info=("Best on rock and dry dirt.", "Hopeless in mud.")),
    dict(name="ALL-TERRAIN", cost=1, grip=1.0, mudk=0.85, rr=0.004,
         info=("Balanced tires for every surface.", "Average in mud.")),
    dict(name="MUD", cost=2, grip=0.9, mudk=0.66, rr=0.012,
         info=("Knobby tires: much better grip in mud,", "but weaker on dry ground and heavier to roll.")),
]
ENGINES = [
    dict(name="STOCK", cost=0, torque=450.0, wmax=20.0, fuel=1.0,
         info=("Standard engine.", "")),
    dict(name="TUNED", cost=2, torque=560.0, wmax=21.5, fuel=1.25,
         info=("+25% power, higher top speed.", "Burns 25% more fuel. Costs 2 points.")),
    dict(name="RACING", cost=3, torque=680.0, wmax=23.0, fuel=1.6,
         info=("+50% power, much higher top speed.", "Burns 60% more fuel. Costs 3 points.")),
]
WINCHES = [
    dict(name="STOCK", cost=0, pull=300.0, speed=40.0, range=280.0,
         info=("Standard winch.", "Range 280 px.")),
    dict(name="HEAVY", cost=1, pull=420.0, speed=50.0, range=340.0,
         info=("Stronger pull, faster reel,", "range 340 px. Costs 1 point.")),
    dict(name="PRO", cost=2, pull=560.0, speed=65.0, range=400.0,
         info=("Best pull and speed, range 400 px.", "Costs 2 points.")),
]
SNORKEL_COST = 2
BUDGET = 7
SNORKEL_INFO = {0: ("No snorkel: the engine floods when", "water is deeper than 14 px."),
                1: ("Raised air intake: the engine floods only", "when water is deeper than 27 px. Costs 2 points.")}
GARAGE_ROWS = [("COLOR", "color", len(COLORS)), ("TIRES", "tires", len(TIRES)),
               ("ENGINE", "engine", len(ENGINES)), ("WINCH", "winch", len(WINCHES)),
               ("SNORKEL", "snorkel", 2), ("ROOF LIGHTS", "lights", 2), ("BULL BAR", "bar", 2)]
DEFAULT_TRUCK = dict(color=0, tires=1, engine=0, winch=0, snorkel=0, lights=0, bar=0)
TRUCK = dict(DEFAULT_TRUCK)


def truck_cost(cfg):
    return (TIRES[cfg["tires"]]["cost"] + ENGINES[cfg["engine"]]["cost"]
            + WINCHES[cfg["winch"]]["cost"] + SNORKEL_COST * cfg["snorkel"])


def truck_stats():
    t, e, w = TIRES[TRUCK["tires"]], ENGINES[TRUCK["engine"]], WINCHES[TRUCK["winch"]]
    return dict(grip=t["grip"], mudk=t["mudk"], rr=t["rr"], torque=e["torque"], wmax=e["wmax"],
                fuel=e["fuel"], w_max=w["pull"], w_speed=w["speed"], w_range=w["range"],
                intake=(12, -15) if TRUCK["snorkel"] else (19, -2))     # воздухозаборник


def option_name(key, v):
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


# настройки и рекорды сохраняются в файл рядом со скриптом
BEST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mud_runner_best.json")


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
        if isinstance(v, int) and 0 <= v < count:
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
    return ({k: v for k, v in best.items() if isinstance(v, (int, float))}, cfg, ghosts, prefs)


def save_all():
    try:
        with open(BEST_FILE, "w", encoding="utf-8") as f:
            json.dump({"best": BEST, "truck": TRUCK, "ghosts": GHOSTS, "prefs": PREFS}, f,
                      separators=(",", ":"))
    except OSError:
        pass


DEFAULT_PREFS = dict(fullscreen=False, ghost=True)
BEST, _cfg, GHOSTS, PREFS = load_save()
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
    for c, hw, d in PONDS:                       # выкапываем котлованы
        for x in range(max(0, c - 3 * hw), min(N, c + 3 * hw)):
            g[x] += d / (1 + (abs(x - c) / hw) ** 6)
    water = [0.0] * N
    for c, hw, d in PONDS:                       # заполняем водой до уровня берегов
        a, b = int(c - 1.6 * hw), int(c + 1.6 * hw)
        level = max(g[a], g[b]) + 1.0
        for x in range(a, b + 1):
            if g[x] > level:
                water[x] = g[x] - level
    base = [0.06] * N
    rock = [False] * N
    for a, b, wv in MUD:
        for x in range(a, b):
            base[x] = wv
    for a, b in ROCK:
        for x in range(a, b):
            rock[x] = True
            base[x] = 0.0
    bed = [g[x] + (0 if rock[x] else 14) for x in range(N)]   # коренная порода: глубже не копается
    TREES[:] = [x for x in TREES if 0 <= x < N and water[x] <= 0.3]   # деревья не в воде
    return g, water, base[:], base, rock, bed, g[:]


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


class GhostRun:
    """Запись лучшего заезда: позиции раз в GHOST_STEP кадров, между ними интерполяция."""

    def __init__(self, data):
        sm = data["s"]
        self.t = data["t"]
        self.xs, self.ys, self.rs, self.fl = sm[0::4], sm[1::4], sm[2::4], sm[3::4]
        self.n = len(self.xs)

    def pose(self, frames):
        f = frames / GHOST_STEP
        i = int(f)
        if i >= self.n - 1:
            return None                                    # призрак уже финишировал
        a = f - i
        x0, y0, r0 = self.xs[i] / 10, self.ys[i] / 10, self.rs[i] / 1000
        if self.fl[i + 1]:                                 # телепорт (респаун) - без интерполяции
            return x0, y0, r0
        x1, y1, r1 = self.xs[i + 1] / 10, self.ys[i + 1] / 10, self.rs[i + 1] / 1000
        return x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, r0 + (r1 - r0) * a


class GhostObj:
    """Минимальный объект с полями, которые нужны draw_truck."""

    def __init__(self, x, y, ang):
        self.x, self.y, self.ang, self.dirt = x, y, ang, 0.0
        self.wheels = [[0.0, x / R_W], [0.0, x / R_W]]     # колёса катятся без проскальзывания


class Game:
    def __init__(self, idx=0):
        self.idx = idx
        self.st = truck_stats()
        apply_level(LEVELS[idx])
        (self.ground, self.water, self.wet, self.base, self.rock,
         self.bedrock, self.orig) = build_level()
        self.parts = []
        self.t = 0.0
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.cp = 60
        self.fuel = FUEL_MAX
        self.time = 0.0
        self.won = False
        self.new_best = False
        self.frames = 0
        self.rec = []
        self.rec_flag = 0
        gd = GHOSTS.get(str(idx))
        self.ghost = GhostRun(gd) if gd else None
        self.dirt = 0.0
        self.msg, self.msg_t = "", 0.0
        self.slip_max = 0.0
        self.spawn(self.cp)
        self.cam_x = max(0, self.x - 120)

    # ---------------- появление / респаун ----------------
    def spawn(self, x):
        self.x = float(x)
        self.y = self.ground[int(x)] - 24
        self.ang = 0.0
        self.vx = self.vy = self.om = 0.0
        self.wheels = [[0.0, 0.0], [0.0, 0.0]]        # [угловая скорость, угол]
        self.winch = None
        self.flood_t = 0.0
        self.flooded = False
        self.restart_t = 0.0
        self.flip_t = 0.0
        self.engine_on = self.fuel > 0
        self.throttle = 0.0

    def say(self, s, t=3.0):
        self.msg, self.msg_t = s, t

    # ---------------- грунт: вырывание колеи ----------------
    def dig(self, wx, d):
        ix = int(wx)
        for k in range(-4, 5):
            i = ix + k
            if 0 <= i < N:
                self.ground[i] = min(self.bedrock[i], self.ground[i] + d * max(0.0, 1 - abs(k) / 5))
        for k in (-8, -7, 7, 8):                       # вытесненная грязь собирается валиками
            i = ix + k
            if 0 <= i < N and not self.rock[i]:
                self.ground[i] = max(self.orig[i] - 3.0, self.ground[i] - d * 0.1)

    def burst(self, x, y, vx, vy, color):
        if len(self.parts) < 300:
            self.parts.append([x, y, vx + random.uniform(-25, 25), vy + random.uniform(-40, 0),
                               random.uniform(0.4, 1.0), color])

    # ---------------- шаг физики ----------------
    def drive_torque(self, w, th):
        if th != 0 and th * w < 0 and abs(w) > 1.0:
            return -math.copysign(BRAKE_T, w)             # тормозим двигателем
        if th == 0:
            return -w * (1.5 if self.engine_on else 0.3)
        lim = max(0.0, 1 - abs(w) / self.st["wmax"])
        tq = self.st["torque"]
        return th * (tq if th > 0 else tq * 0.7) * lim

    def physics(self, dt):
        c, s = math.cos(self.ang), math.sin(self.ang)
        x, y, vx, vy, om = self.x, self.y, self.vx, self.vy, self.om
        fx = fy = tq = 0.0
        grounded = False
        ground, water, wetarr = self.ground, self.water, self.wet

        for k, (lx, ly, r, is_wheel) in enumerate(POINTS):
            rx = c * lx - s * ly
            ry = s * lx + c * ly
            wx, wy = x + rx, y + ry
            pvx, pvy = vx - om * ry, vy + om * rx
            ix = max(1, min(N - 2, int(wx)))
            gy = ground[ix]

            # --- вода: выталкивание и сопротивление
            sub = 0.0
            wd = water[ix]
            if wd > 0.3:
                sub = wy - (gy - wd)
                if sub > 0:
                    sub = min(sub, 14.0)
                    f = min(sub / 8, 1.0)
                    wfx = -DW * pvx * f
                    wfy = -BF * sub - DW * pvy * f
                    fx += wfx
                    fy += wfy
                    tq += rx * wfy - ry * wfx
                else:
                    sub = 0.0

            pen = wy + r - gy
            th = self.throttle
            wh = self.wheels[k] if is_wheel else None
            if pen > 0:
                grounded = True
                sl = (ground[ix + 1] - ground[ix - 1]) * 0.5
                nl = math.sqrt(1 + sl * sl)
                tx, ty = 1 / nl, sl / nl
                nx, ny = sl / nl, -1 / nl
                pen_n = min(pen / nl, 12.0)
                vn = pvx * nx + pvy * ny
                wet = wetarr[ix]
                Fn = K0 * (1 - 0.5 * wet) * pen_n - CD * vn
                if Fn < 0:
                    Fn = 0.0
                vt = pvx * tx + pvy * ty
                mu = MU0 * self.st["grip"] * (1 - self.st["mudk"] * wet)                 # мокрая земля = скользко
                if sub > 0:
                    mu *= 1 - 0.45 * min(sub / 6, 1.0)      # аквапланирование
                if is_wheel:
                    slip = wh[0] * R_W - vt
                    lim = mu * Fn
                    Ft = max(-lim, min(lim, KS * slip))
                    wh[0] += (self.drive_torque(wh[0], th) - Ft * R_W) / I_W * dt
                    Ft -= (0.012 + self.st["rr"] + 0.08 * wet) * Fn * math.tanh(vt / 12.0)   # сопротивление качению
                    asl = abs(slip)
                    self.slip_max = max(self.slip_max, asl)
                    # колесо буксует в мокрой земле -> роет колею
                    if asl > 12 and wet > 0.15 and not self.rock[ix] and sub == 0:
                        self.dig(wx, DIG * (asl - 12) * wet * (Fn / 120) * dt)
                        if random.random() < min(1.0, asl * 0.003):
                            self.burst(wx, wy + 3, -math.copysign(35, slip) + vx * 0.3, -50,
                                       random.choice([(96, 62, 34), (70, 46, 26), (120, 80, 44)]))
                    if sub > 0 and (abs(vt) > 20 or asl > 30) and random.random() < 0.3:
                        self.burst(wx, wy - sub, vx * 0.3, -60, (190, 225, 255))
                else:
                    lim = (0.8 + 0.6 * wet) * Fn
                    Ft = -max(-lim, min(lim, KS * vt))
                ffx = nx * Fn + tx * Ft
                ffy = ny * Fn + ty * Ft
                fx += ffx
                fy += ffy
                tq += rx * ffy - ry * ffx
            elif is_wheel:
                wh[0] += (self.drive_torque(wh[0], th) - wh[0] * 0.2) / I_W * dt

            if is_wheel:
                if self.hand:
                    wh[0] = 0.0
                wh[1] += wh[0] * dt

        # --- лебёдка
        if self.winch:
            ax, ay, L = self.winch
            hx_l, hy_l = HOOK
            rxh = c * hx_l - s * hy_l
            ryh = s * hx_l + c * hy_l
            dx, dy = ax - (x + rxh), ay - (y + ryh)
            dist = math.hypot(dx, dy) or 1e-6
            if self.reel:
                L = max(8.0, L - self.st["w_speed"] * dt)
                self.winch[2] = L
            taut = dist - L
            if taut > 0:
                ux, uy = dx / dist, dy / dist
                vrel = (vx - om * ryh) * ux + (vy + om * rxh) * uy
                F = min(self.st["w_max"], 25 * taut)
                F = max(0.0, F - 1.5 * max(vrel, 0.0))
                fx += F * ux
                fy += F * uy
                tq += rxh * F * uy - ryh * F * ux

        # --- интегрирование
        vx += fx * dt
        vy += (fy + G) * dt
        om += tq / I_BODY * dt
        if self.lean:
            om += self.lean * (6.0 if not grounded else 1.5) * dt
        om -= om * 0.15 * dt
        self.x, self.y = x + vx * dt, y + vy * dt
        self.vx, self.vy, self.om = vx, vy, om
        self.ang += om * dt
        if self.x < 15:
            self.x, self.vx = 15.0, max(self.vx, 0.0)
        if self.x > N - 15:
            self.x, self.vx = N - 15.0, min(self.vx, 0.0)

    # ---------------- вода и мокрая земля ----------------
    def sim_water(self):
        g, w, wet, base, rock = self.ground, self.water, self.wet, self.base, self.rock
        i0 = max(1, int(self.cam_x) - 120)
        i1 = min(N - 2, int(self.cam_x) + VW + 120)
        for i in range(i0, i1):                       # вода течёт туда, где уровень ниже
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
            if not rock[i]:                           # под водой земля превращается в грязь
                if w[i] > 0.5:
                    wet[i] += (max(base[i], 0.7) - wet[i]) * 0.6 * DT
                else:
                    wet[i] += (base[i] - wet[i]) * 0.03 * DT

    # ---------------- обновление кадра ----------------
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
            if self.frames % GHOST_STEP == 0:               # запись текущего заезда
                self.rec += [int(round(self.x * 10)), int(round(self.y * 10)),
                             int(round(self.ang * 1000)), self.rec_flag]
                self.rec_flag = 0
            self.frames += 1
        self.slip_max = 0.0

        for _ in range(SUB):
            self.physics(DT / SUB)

        c, s = math.cos(self.ang), math.sin(self.ang)
        # воздухозаборник под водой -> двигатель глохнет
        ik = self.st["intake"]
        ix_ = max(1, min(N - 2, int(self.x + c * ik[0] - s * ik[1])))
        iy_ = self.y + s * ik[0] + c * ik[1]
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

        # топливо
        if self.engine_on:
            self.fuel -= (0.04 + 0.35 * abs(self.throttle)) * self.st["fuel"] * DT
            if self.fuel <= 0:
                self.fuel, self.engine_on = 0.0, False
                self.say("OUT OF FUEL! Press R to respawn", 5)

        # грязь на машине
        ix = max(1, min(N - 2, int(self.x)))
        if self.water[ix] > 6:
            self.dirt = max(0.0, self.dirt - DT * 0.4)
        elif abs(self.vx) > 5 and self.wet[ix] > 0.3:
            self.dirt = min(1.0, self.dirt + DT * 0.05 * self.wet[ix])

        # лебёдка: автоотцепление, если подтянулись вплотную
        if self.winch:
            hx = self.x + c * HOOK[0] - s * HOOK[1]
            hy = self.y + s * HOOK[0] + c * HOOK[1]
            if math.hypot(self.winch[0] - hx, self.winch[1] - hy) < 14:
                self.winch = None
                self.say("Winch detached", 2)

        # вверх колёсами
        if math.cos(self.ang) < 0.1:
            self.flip_t += DT
            if self.flip_t > 2:
                self.say("Flipped! Press R to respawn", 2)
        else:
            self.flip_t = 0.0

        # чекпоинты и финиш
        for cx in CPS:
            if cx > self.cp and self.x > cx:
                self.cp = cx
                self.fuel = FUEL_MAX
                self.say("CHECKPOINT! Fuel refilled", 3)
        if self.x > GOAL_X and not self.won:
            self.won = True
            key = str(self.idx)
            self.new_best = key not in BEST or self.time < BEST[key]
            if self.new_best:
                BEST[key] = round(self.time, 1)
            old = GHOSTS.get(key)
            if old is None or self.time < old["t"]:           # лучший заезд становится призраком
                GHOSTS[key] = dict(t=round(self.time, 2), s=self.rec)
            save_all()
            self.say("", 0)

        self.sim_water()
        # частицы
        for p in self.parts:
            p[3] += G * DT
            p[0] += p[2] * DT
            p[1] += p[3] * DT
            p[4] -= DT
        self.parts = [p for p in self.parts if p[4] > 0 and p[1] < self.ground[max(0, min(N - 1, int(p[0])))]]

        self.msg_t = max(0.0, self.msg_t - DT)
        # камера
        self.cam_x += (max(0, min(N - VW, self.x - 120)) - self.cam_x) * 0.1
        self.cam_y += ((self.y - 115) - self.cam_y) * 0.08

    # ---------------- действия игрока ----------------
    def toggle_winch(self):
        if self.winch:
            self.winch = None
            self.say("Winch detached", 2)
            return
        c, sn = math.cos(self.ang), math.sin(self.ang)
        hx = self.x + c * HOOK[0] - sn * HOOK[1]
        hy = self.y + sn * HOOK[0] + c * HOOK[1]
        cands = []
        for ax in TREES:
            ay = self.ground[ax] - 10
            d = math.hypot(ax - hx, ay - hy)
            if d <= self.st["w_range"]:
                cands.append((d, ax, ay, ax > self.x - 20))
        best, bd = None, 0.0
        for ahead, far in ((True, True), (True, False), (False, True), (False, False)):
            pool = [c for c in cands if c[3] == ahead and (c[0] >= 80 or not far)]
            if pool:
                bd, ax, ay, _ = min(pool)
                best = (ax, ay)
                break
        if best:
            self.winch = [best[0], best[1], bd]
            self.say("Winch attached - hold F to reel in", 3)
        else:
            self.say("No tree in range", 2)

    def respawn(self):
        self.rec_flag = 1
        self.fuel = max(self.fuel, 50.0)
        self.spawn(self.cp)

    # ---------------- отрисовка ----------------
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

        for sx in range(VW):                                  # земля по колонкам
            wx = cx + sx
            if wx >= N:
                break
            gy = int(self.ground[wx]) - cy
            if gy >= VH:
                continue
            wt = self.wet[wx]
            if self.rock[wx]:
                top, body = (150, 150, 162), (104, 104, 118)
            else:
                top = lerp((156, 112, 60), (78, 52, 30), min(1.0, wt))
                body = lerp((118, 80, 44), (56, 38, 22), min(1.0, wt))
            pygame.draw.line(low, body, (sx, gy + 3), (sx, VH))
            pygame.draw.line(low, top, (sx, gy), (sx, gy + 2))

        for ax in TREES:                                      # деревья-якоря
            sx = ax - cx
            if -12 < sx < VW + 12:
                gy = int(self.ground[ax]) - cy
                pygame.draw.rect(low, (84, 52, 30), (sx - 1, gy - 16, 3, 16))
                pygame.draw.circle(low, (46, 120, 60), (sx, gy - 20), 8)
                pygame.draw.circle(low, (36, 100, 50), (sx - 4, gy - 16), 5)
                pygame.draw.circle(low, (36, 100, 50), (sx + 4, gy - 17), 5)
                pygame.draw.rect(low, (240, 210, 60), (sx, gy - 10, 1, 1))
        for cpx in CPS:                                       # чекпоинты
            sx = cpx - cx
            if -12 < sx < VW + 12:
                gy = int(self.ground[cpx]) - cy
                col = (60, 200, 80) if self.cp >= cpx else (240, 150, 40)
                pygame.draw.rect(low, (230, 230, 230), (sx, gy - 16, 1, 16))
                pygame.draw.polygon(low, col, [(sx + 1, gy - 16), (sx + 9, gy - 13), (sx + 1, gy - 10)])
        sx = GOAL_X - cx                                      # финиш
        if -20 < sx < VW + 20:
            gy = int(self.ground[GOAL_X]) - cy
            pygame.draw.rect(low, (230, 230, 230), (sx, gy - 28, 2, 28))
            for i in range(4):
                for j in range(2):
                    col = (20, 20, 20) if (i + j) % 2 else (240, 240, 240)
                    pygame.draw.rect(low, col, (sx + 2 + i * 4, gy - 28 + j * 4, 4, 4))

        if self.winch:                                        # трос
            c, s = math.cos(self.ang), math.sin(self.ang)
            hx = self.x + c * HOOK[0] - s * HOOK[1] - cx
            hy = self.y + s * HOOK[0] + c * HOOK[1] - cy
            pygame.draw.line(low, (235, 210, 70), (int(hx), int(hy)),
                             (int(self.winch[0] - cx), int(self.winch[1] - cy)))

        if PREFS["ghost"] and self.ghost and not self.won:
            pose = self.ghost.pose(self.frames)
            if pose:
                gsurf.fill((0, 0, 0, 0))
                Game.draw_truck(GhostObj(*pose), cx, cy, gsurf, True)
                low.blit(gsurf, (0, 0))
        self.draw_truck(cx, cy)

        for p in self.parts:                                  # брызги грязи и воды
            pygame.draw.rect(low, p[5], (int(p[0] - cx), int(p[1] - cy), 2, 2))

        wsurf.fill((0, 0, 0, 0))                              # вода поверх всего
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

    def draw_truck(self, cx, cy, surf=None, ghost=False):
        surf = low if surf is None else surf
        c, s = math.cos(self.ang), math.sin(self.ang)

        def T(lx, ly):
            return (round(self.x + c * lx - s * ly - cx), round(self.y + s * lx + c * ly - cy))

        def C(col):                                           # призрак рисуется полупрозрачным
            return (col[0], col[1], col[2], GHOST_ALPHA) if ghost else col
        if ghost:
            body, dark = (150, 215, 255), (90, 150, 215)
            bed, glass = (80, 120, 160), (225, 245, 255)
            tire_o, tire_i, spoke, hub = (70, 110, 150), (110, 160, 200), (200, 230, 250), (230, 245, 255)
        else:
            d = self.dirt * 0.75
            base = COLORS[TRUCK["color"]][1]
            body = lerp(base, (92, 62, 36), d)
            dark = lerp(tuple(int(v * 0.68) for v in base), (70, 48, 28), d)
            bed, glass = (60, 60, 66), (150, 205, 235)
            tire_o, tire_i, spoke, hub = (24, 24, 28), (70, 70, 78), (170, 170, 180), (200, 200, 210)
        poly = pygame.draw.polygon
        poly(surf, C(dark), [T(-22, -3), T(22, -3), T(23, 5), T(-23, 5)])
        poly(surf, C(bed), [T(-22, -6), T(-6, -6), T(-6, -3), T(-22, -3)])
        poly(surf, C(body), [T(-4, -3), T(-2, -11), T(10, -11), T(14, -3)])
        poly(surf, C(glass), [T(-1, -4), T(0, -9), T(8, -9), T(11, -4)])
        if TRUCK["lights"]:
            for lx in (0, 5):
                poly(surf, C((255, 240, 150)), [T(lx, -11), T(lx, -13), T(lx + 3, -13), T(lx + 3, -11)])
        if TRUCK["snorkel"]:
            pygame.draw.line(surf, C((40, 40, 44)), T(12, -4), T(12, -15), 2)
            pygame.draw.line(surf, C((40, 40, 44)), T(12, -15), T(15, -15), 2)
        if TRUCK["bar"]:
            pygame.draw.lines(surf, C((70, 70, 78)), False, [T(22, -2), T(26, -2), T(26, 5), T(22, 5)], 1)
        hl = T(22, -1)
        pygame.draw.rect(surf, C((255, 240, 150)), (hl[0], hl[1], 2, 2))
        knobs = (0, 4, 8)[TRUCK["tires"]]
        for i in range(2):
            lx, ly = POINTS[i][0], POINTS[i][1]
            hx, hy = T(lx, ly)
            pygame.draw.circle(surf, C(tire_o), (hx, hy), 6)
            pygame.draw.circle(surf, C(tire_i), (hx, hy), 4)
            a = self.wheels[i][1] + self.ang
            for k in range(knobs):                             # протектор шин
                ka = a + k * 2 * math.pi / knobs
                pygame.draw.rect(surf, C((125, 125, 135)),
                                 (round(hx + math.cos(ka) * 5.2), round(hy + math.sin(ka) * 5.2), 1, 1))
            pygame.draw.line(surf, C(spoke), (hx, hy),
                             (round(hx + math.cos(a) * 4), round(hy + math.sin(a) * 4)))
            pygame.draw.rect(surf, C(hub), (hx, hy, 1, 1))

    def draw_hud(self):
        kmh = int(math.hypot(self.vx, self.vy) * 0.5)
        text(f"{kmh:3d} KM/H", 16, 12)
        eng = (("ENGINE OK", (120, 230, 120)) if self.engine_on else
               ("FLOODED" if self.flooded else "ENGINE OFF", (240, 90, 80)))
        text(eng[0], 16, 38, eng[1])
        if TRUCK["snorkel"]:
            text("SNORKEL", 170, 38, (240, 210, 70))
        # топливо
        pygame.draw.rect(screen, (0, 0, 0), (16, 66, 154, 18))
        fw = int(150 * self.fuel / FUEL_MAX)
        pygame.draw.rect(screen, (230, 190, 40) if self.fuel > 20 else (230, 60, 50), (18, 68, fw, 14))
        text("FUEL", 178, 64)
        # поверхность под машиной
        ix = max(1, min(N - 2, int(self.x)))
        if self.water[ix] > 0.3:
            ground_txt, gc = f"WATER {int(self.water[ix])}px", (110, 180, 255)
        elif self.rock[ix]:
            ground_txt, gc = "ROCK", (190, 190, 200)
        else:
            w = self.wet[ix]
            name = "DRY DIRT" if w < 0.25 else ("WET DIRT" if w < 0.55 else "MUD")
            ground_txt, gc = f"{name} {int(w * 100)}%", (210, 160, 100)
        text(ground_txt, 16, 92, gc)
        if self.slip_max > 30:
            text("WHEELSPIN!", 16, 118, (255, 160, 60))
        wtxt = ("WINCH: attached  [F] reel  [E] release" if self.winch
                else "WINCH: [E] attach to nearest tree")
        text(wtxt, 16, H - 34, (235, 210, 70))
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
        # прогресс по уровню
        bx, bw = W // 2 - 150, 300
        pygame.draw.rect(screen, (0, 0, 0), (bx - 2, 14, bw + 4, 10))
        pygame.draw.rect(screen, (90, 90, 100), (bx, 17, bw, 4))
        for cpx in CPS:
            pygame.draw.rect(screen, (240, 150, 40), (bx + int(bw * cpx / GOAL_X), 14, 2, 10))
        pygame.draw.rect(screen, (255, 255, 255), (bx + int(bw * min(self.x, GOAL_X) / GOAL_X) - 3, 13, 6, 12))

        if self.msg_t > 0:
            text(self.msg, W // 2, H - 90, (255, 255, 255), center=True)
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
            text("E winch   F reel in   R respawn   H ghost   F11 fullscreen   ESC menu", W // 2, H - 38, (200, 200, 200), center=True)


# ======================= главное меню и гараж =======================
PREVIEWS = []


def make_previews():
    """Рисует профиль каждого уровня для карточки в меню."""
    pw, ph = 440, 140
    for lv in LEVELS:
        apply_level(lv)
        g, water, wet, base, rock, bed, orig = build_level()
        surf = pygame.Surface((pw, ph))
        surf.fill(lv["theme"][0])
        lo = min(g[i] - water[i] for i in range(N))
        hi = max(g) + 4
        for px in range(pw):
            wx = min(N - 1, int(px / pw * N))
            gy = 12 + (g[wx] - lo) / (hi - lo) * (ph - 24)
            if rock[wx]:
                col = (120, 120, 135)
            elif base[wx] > 0.4:
                col = (80, 54, 30)
            else:
                col = (150, 108, 58)
            pygame.draw.line(surf, col, (px, gy), (px, ph))
            if water[wx] > 0.3:
                wy = 12 + (g[wx] - water[wx] - lo) / (hi - lo) * (ph - 24)
                pygame.draw.line(surf, (60, 120, 220), (px, wy), (px, gy))
        for cp in lv["cps"]:
            px = int(cp / N * pw)
            pygame.draw.rect(surf, (240, 150, 40), (px, 4, 2, 10))
        px = int(lv["goal"] / N * pw)
        pygame.draw.rect(surf, (255, 255, 255), (px, 2, 3, 14))
        PREVIEWS.append(surf)
    apply_level(LEVELS[0])


def fmt_time(t):
    t = int(t)
    return f"{t // 60:02d}:{t % 60:02d}"


def draw_scene(t, deco):
    """Общий фон меню и гаража: небо, холмы, дорога и едущий на месте грузовик."""
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
    deco.x, deco.y, deco.ang = 245.0, 138.0 + math.sin(t * 14) * 0.6, math.sin(t * 3) * 0.02
    for w in deco.wheels:
        w[1] += 0.18
    deco.draw_truck(0, 0)
    screen.blit(pygame.transform.scale(low, (W, H)), (0, 0))


def draw_menu(sel, t, deco):
    draw_scene(t, deco)
    rows = len(LEVELS) + 1
    ov.fill((0, 0, 0, 0))
    pygame.draw.rect(ov, (0, 0, 0, 130), (36, 98, 412, rows * 46 + 14))
    pygame.draw.rect(ov, (0, 0, 0, 130), (464, 98, 456, 290))
    screen.blit(ov, (0, 0))
    text("MUD PIXEL RUNNER", W // 2, 48, (240, 190, 60), title_font, center=True)
    for i in range(rows):
        y = 106 + i * 46
        on = i == sel
        if on:
            pygame.draw.rect(screen, (240, 190, 60), (44, y, 396, 40), 3)
        col = (255, 230, 140) if on else (230, 230, 230)
        if i < len(LEVELS):
            lv = LEVELS[i]
            text(f"{i + 1}.{lv['name']}", 56, y + 8, col, mid)
            for d in range(5):
                pygame.draw.rect(screen, (230, 90, 60) if d < lv["diff"] else (70, 70, 70),
                                 (284 + d * 13, y + 13, 10, 14))
            b = BEST.get(str(i))
            if b is not None:
                text(fmt_time(b), 360, y + 10, (120, 230, 120))
        else:
            text("GARAGE", 56, y + 8, (140, 205, 255) if not on else (190, 235, 255), mid)
            text("customize truck", 250, y + 10, (170, 170, 180))

    if sel < len(LEVELS):
        lv = LEVELS[sel]
        screen.blit(PREVIEWS[sel], (476, 108))
        pygame.draw.rect(screen, (240, 190, 60), (476, 108, 440, 140), 2)
        text(lv["name"], 476, 258, (255, 230, 140), mid)
        text(lv["desc"][0], 476, 292)
        text(lv["desc"][1], 476, 316)
        b = BEST.get(str(sel))
        text(f"Length {lv['goal']}   Checkpoints {len(lv['cps'])}   "
             + (f"Best {fmt_time(b)}" if b is not None else "No record"), 476, 346, (200, 200, 215))
        text("Ghost run saved" if str(sel) in GHOSTS else "No ghost yet - finish the level",
             476, 370, (150, 200, 255))
    else:
        text("GARAGE", 476, 112, (190, 235, 255), mid)
        text(f"Points used {truck_cost(TRUCK)}/{BUDGET}", 476, 150, (240, 210, 70))
        for i, (label, key, _) in enumerate(GARAGE_ROWS):
            text(f"{label:12s} {option_name(key, TRUCK[key])}", 476, 188 + i * 24, (220, 220, 230))
        text("ENTER or G to open", 476, 360, (170, 170, 180))
    text("UP/DOWN select   ENTER start   G garage   F11 fullscreen   ESC quit", W // 2, H - 34, (210, 210, 210), center=True)


def stat_bar(label, frac, x, y):
    text(label, x, y)
    pygame.draw.rect(screen, (0, 0, 0), (x + 170, y + 2, 200, 18))
    pygame.draw.rect(screen, (90, 200, 110), (x + 172, y + 4, int(196 * max(0.05, min(1.0, frac))), 14))


def draw_garage(gsel, t, deco, msg):
    draw_scene(t, deco)
    ov.fill((0, 0, 0, 0))
    pygame.draw.rect(ov, (0, 0, 0, 140), (36, 98, 440, len(GARAGE_ROWS) * 48 + 16))
    pygame.draw.rect(ov, (0, 0, 0, 140), (492, 98, 428, 214))
    pygame.draw.rect(ov, (0, 0, 0, 140), (492, 322, 428, 74))
    screen.blit(ov, (0, 0))
    text("GARAGE", W // 2, 48, (140, 205, 255), title_font, center=True)

    used = truck_cost(TRUCK)
    for i, (label, key, count) in enumerate(GARAGE_ROWS):
        y = 106 + i * 48
        on = i == gsel
        if on:
            pygame.draw.rect(screen, (240, 190, 60), (44, y, 424, 42), 3)
        text(label, 58, y + 9, (255, 230, 140) if on else (230, 230, 230))
        v = TRUCK[key]
        if key == "color":
            pygame.draw.rect(screen, COLORS[v][1], (212, y + 10, 18, 22))
        text(f"< {option_name(key, v)} >", 238 if key == "color" else 214, y + 9, (255, 255, 255))
        cost = option_cost(key, v)
        text(f"{cost} pt" if cost else "free", 410, y + 9, (240, 210, 70) if cost else (150, 150, 150))

    text(f"POINTS {used}/{BUDGET}", 508, 108, (240, 210, 70))
    for i in range(BUDGET):
        pygame.draw.rect(screen, (240, 210, 70) if i < used else (70, 70, 70), (700 + i * 24, 110, 20, 18))
    st = truck_stats()
    stat_bar("POWER", st["torque"] / 680, 508, 142)
    stat_bar("TOP SPEED", st["wmax"] / 23, 508, 172)
    stat_bar("MUD GRIP", MU0 * st["grip"] * (1 - st["mudk"] * 0.9) / 0.55, 508, 202)
    stat_bar("DRY GRIP", MU0 * st["grip"] / 1.3, 508, 232)
    stat_bar("WINCH PULL", st["w_max"] / 560, 508, 262)
    text(f"Engine floods in water deeper than {27 if TRUCK['snorkel'] else 14} px", 508, 286, (150, 200, 255))

    label, key, _ = GARAGE_ROWS[gsel]
    info = option_info(key, TRUCK[key])
    text(f"{label}: {option_name(key, TRUCK[key])}", 508, 328, (255, 230, 140))
    text(info[0], 508, 352)
    text(info[1], 508, 372)
    if msg:
        text(msg, W // 2, H - 66, (255, 110, 90), center=True)
    text("UP/DOWN row   LEFT/RIGHT change   ENTER back", W // 2, H - 34, (210, 210, 210), center=True)


def garage_change(row, d):
    """Меняет опцию; возвращает сообщение об ошибке, если не хватает очков."""
    label, key, count = GARAGE_ROWS[row]
    cfg = dict(TRUCK)
    cfg[key] = (cfg[key] + d) % count
    if truck_cost(cfg) > BUDGET:
        return "NOT ENOUGH POINTS - lower another upgrade first"
    TRUCK.update(cfg)
    save_all()
    return ""


def set_fullscreen(on):
    """Переключает окно/полный экран. Игра рисуется в 960x540 и масштабируется с полосами по краям."""
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
    deco.dirt = 0.5
    state, sel, gsel, game, t = "menu", 0, 0, None, 0.0
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
            if k == pygame.K_F11 or (enter and event.mod & pygame.KMOD_ALT):
                set_fullscreen(not PREFS["fullscreen"])
                continue
            if state == "menu":
                if k == pygame.K_ESCAPE:
                    running = False
                elif k in (pygame.K_UP, pygame.K_w):
                    sel = (sel - 1) % (len(LEVELS) + 1)
                elif k in (pygame.K_DOWN, pygame.K_s):
                    sel = (sel + 1) % (len(LEVELS) + 1)
                elif k == pygame.K_g:
                    state = "garage"
                elif enter:
                    if sel == len(LEVELS):
                        state = "garage"
                    else:
                        game, state = Game(sel), "play"
                elif pygame.K_1 <= k <= pygame.K_9 and k - pygame.K_1 < len(LEVELS):
                    sel = k - pygame.K_1
            elif state == "garage":
                if k in (pygame.K_ESCAPE, pygame.K_g) or enter:
                    state = "menu"
                elif k in (pygame.K_UP, pygame.K_w):
                    gsel = (gsel - 1) % len(GARAGE_ROWS)
                elif k in (pygame.K_DOWN, pygame.K_s):
                    gsel = (gsel + 1) % len(GARAGE_ROWS)
                elif k in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                    gmsg = garage_change(gsel, 1 if k in (pygame.K_RIGHT, pygame.K_d) else -1)
                    gmsg_t = 2.5
            else:
                if k == pygame.K_ESCAPE:
                    sel, state = game.idx, "menu"
                elif k == pygame.K_r:
                    if game.won:
                        game = Game(game.idx)
                    else:
                        game.respawn()
                elif k == pygame.K_e:
                    game.toggle_winch()
                elif k == pygame.K_h:
                    PREFS["ghost"] = not PREFS["ghost"]
                    game.say("Ghost shown" if PREFS["ghost"] else "Ghost hidden", 2)
                    save_all()
                elif enter and game.won:
                    if game.idx + 1 < len(LEVELS):
                        game = Game(game.idx + 1)
                    else:
                        sel, state = game.idx, "menu"
        t += DT
        gmsg_t = max(0.0, gmsg_t - DT)
        if state == "menu":
            draw_menu(sel, t, deco)
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
