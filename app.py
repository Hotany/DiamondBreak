from pathlib import Path
import re
import math
import io
import os
import base64
import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

try:
    from streamlit_js_eval import streamlit_js_eval
except Exception:
    streamlit_js_eval = None

try:
    from BaseballFieldPro import BaseballFieldPro
    BASEBALL_FIELD_PRO_IMPORT_ERROR = None
except Exception as exc:
    BaseballFieldPro = None
    BASEBALL_FIELD_PRO_IMPORT_ERROR = exc


def render_fieldpro_background(canvas_width: int, canvas_height: int, render_scale: int):
    if BaseballFieldPro is None:
        raise RuntimeError(f"BaseballFieldPro import failed: {BASEBALL_FIELD_PRO_IMPORT_ERROR}")

    dpi = 120
    px_w = int(canvas_width * render_scale)
    px_h = int(canvas_height * render_scale)

    field = BaseballFieldPro(size=max(px_w, px_h) / dpi)
    fig = field.draw(players=None)
    try:
        fig.set_size_inches(px_w / dpi, px_h / dpi)
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
        ax = fig.axes[0]
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, facecolor=fig.get_facecolor(), bbox_inches=None, pad_inches=0)
        buf.seek(0)
        img = Image.open(buf).convert("RGBA")
        return img, xlim, ylim, field.compute_layout()
    finally:
        try:
            import matplotlib.pyplot as plt

            plt.close(fig)
        except Exception:
            pass


DATA_FILE = Path("datasource01.xlsx")
BASE_DIR = Path(__file__).resolve().parent


REQUIRED_COLUMNS = [
    "ID",
    "Scenario Name",
    "Category",
    "Tactical Image",
    "Description",
    "Key Question",
    "Correct Answer",
    "Coach's Tip",
]

BASE_CANVAS_WIDTH = 800
BASE_CANVAS_HEIGHT = 800
CANVAS_ASPECT_RATIO = BASE_CANVAS_HEIGHT / BASE_CANVAS_WIDTH
RENDER_SUPERSAMPLE = 2
FENCE_SAMPLE_STEP_DEG = 0.5
BOUNDARY_SAMPLE_STEP_DEG = 1.0
MIN_CANVAS_WIDTH = 240
MAX_CONTENT_WIDTH = 600
PAGE_SIDE_PADDING = 120
DEFAULT_STROKE_WIDTH = 8
DEFAULT_STROKE_COLOR = "#901342"
MARKER_SCALE = 1.3

# 基于棒球常见尺寸（单位：英尺）
BASE_PATH_FT = 90.0
PITCH_DISTANCE_FT = 60.5  # 60'6"
INFIELD_ARC_FT = 95.0
FOUL_DISTANCE_FT = 330.0
CENTER_ALLEY_FT = 375.0
CENTER_FIELD_FT = 400.0
OUTFIELD_ARC_RADIUS_FT = 380.0
OUTFIELD_ARC_CURVATURE_SCALE = 1.15
INFIELD_ARC_CURVATURE_SCALE = OUTFIELD_ARC_CURVATURE_SCALE
DIAMOND_SCALE = 0.85
HALF_DIAMOND = BASE_PATH_FT / math.sqrt(2.0)
BASE_DISTANCE_SCALE = 1.8
BASE_COORD_HALF = HALF_DIAMOND * BASE_DISTANCE_SCALE
INFIELD_FAN_RADIUS_SCALE = 1.26

# 以本垒为原点的近似实地坐标（英尺）：x 向右，y 向外场
POSITION_COORDS = {
    "H": (0.0, 0.0),                         # 本垒
    "B": (0.0, -8.0),                        # 打者
    "C": (0.0, -18.0),                       # 捕手
    "P": (0.0, PITCH_DISTANCE_FT * BASE_DISTANCE_SCALE + 12.0),  # 投手略向外场抬高
    "1B": (BASE_COORD_HALF, BASE_COORD_HALF),      # 一垒（放大到 2x）
    "2B": (0.0, 2 * BASE_COORD_HALF),              # 二垒（放大到 2x）
    "3B": (-BASE_COORD_HALF, BASE_COORD_HALF),     # 三垒（放大到 2x）
    "SS": (-70.0, 195.5),                    # 游击上提约 15%
    "LF": (-190.0, 242.0),                   # 左外野上提约 10%
    "CF": (0.0, 341.0),                      # 中外野上提约 10%
    "RF": (190.0, 242.0),                    # 右外野上提约 10%
    "R1": (BASE_COORD_HALF + 8.0, BASE_COORD_HALF + 6.0),
    "R2": (0.0, 2 * BASE_COORD_HALF - 8.0),
    "R3": (-BASE_COORD_HALF - 8.0, BASE_COORD_HALF + 6.0),
}

ENTITY_PATTERNS = {
    "P": ["投手", "pitcher"],
    "C": ["捕手", "catcher"],
    "1B": ["一垒手", "1b"],
    "2B": ["二垒手", "2b"],
    "3B": ["三垒手", "3b"],
    "SS": ["游击手", "ss", "游击"],
    "LF": ["左外野手", "左外野", "lf"],
    "CF": ["中外野手", "中外野", "cf"],
    "RF": ["右外野手", "右外野", "rf"],
    "B": ["打者", "击球员", "batter"],
    "R1": ["一垒有人", "一垒跑者"],
    "R2": ["二垒有人", "二垒跑者"],
    "R3": ["三垒有人", "三垒跑者"],
}

DEST_PATTERNS = {
    "1B": ["一垒", "1垒"],
    "2B": ["二垒", "2垒"],
    "3B": ["三垒", "3垒"],
    "SS": ["游击", "游击手", "ss"],
    "LF": ["左外野", "左外野手", "lf"],
    "CF": ["中外野", "中外野手", "cf"],
    "RF": ["右外野", "右外野手", "rf"],
    "H": ["本垒", "本垒板", "home"],
}

LABELS = {
    "P": "P",
    "C": "C",
    "1B": "1B",
    "2B": "2B",
    "3B": "3B",
    "SS": "SS",
    "LF": "LF",
    "CF": "CF",
    "RF": "RF",
    "B": "B",
    "R1": "R1",
    "R2": "R2",
    "R3": "R3",
}

DEFENDER_KEYS = ["P", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"]


def sample_angles(start_deg: float, end_deg: float, step_deg: float):
    if step_deg <= 0:
        return [start_deg, end_deg]
    count = int(round((end_deg - start_deg) / step_deg))
    return [start_deg + i * step_deg for i in range(count + 1)]


def smooth_lerp(v0: float, v1: float, t: float) -> float:
    t = max(0.0, min(1.0, t))
    # Cosine easing gives C1-like smooth visual transition between segments.
    eased = (1.0 - math.cos(math.pi * t)) / 2.0
    return v0 + (v1 - v0) * eased


@st.cache_data
def load_scenarios(excel_path: Path) -> pd.DataFrame:
    df = pd.read_excel(excel_path)
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")].copy()
    df.columns = [str(c).strip() for c in df.columns]

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df["ID"] = pd.to_numeric(df["ID"], errors="coerce")
    df = df.dropna(subset=["ID"]).copy()
    df["ID"] = df["ID"].astype(int)
    df = df.sort_values("ID")

    text_cols = [
        "Scenario Name",
        "Category",
        "Tactical Image",
        "Description",
        "Key Question",
        "Correct Answer",
        "Coach's Tip",
    ]
    for col in text_cols:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df


def draw_rotated_square(draw: ImageDraw.ImageDraw, center, size, fill, outline):
    cx, cy = center
    s = size
    points = [(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)]
    draw.polygon(points, fill=fill, outline=outline)


def load_label_font(size: int):
    font_candidates = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/ARIALBD.TTF",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ]
    for font_path in font_candidates:
        try:
            return ImageFont.truetype(font_path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_bold_text(draw: ImageDraw.ImageDraw, xy, text: str, font, fill):
    x, y = xy
    for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        draw.text((x + dx, y + dy), text, fill=fill, font=font)


def draw_centered_text(draw: ImageDraw.ImageDraw, center_x, center_y, text: str, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = center_x - text_w / 2
    text_y = center_y - text_h / 2 - (4 * MARKER_SCALE)
    draw_bold_text(draw, (text_x, text_y), text, font=font, fill=fill)


def draw_centered_label(draw: ImageDraw.ImageDraw, center_x, top_y, text: str, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_x = center_x - text_w / 2
    draw_bold_text(draw, (text_x, top_y), text, font=font, fill=fill)


def marker_radius_for_key(key: str, render_scale: int):
    if key in DEFENDER_KEYS:
        return 12 * MARKER_SCALE * render_scale
    if key in {"R1", "R2", "R3", "B"}:
        return 10 * MARKER_SCALE * render_scale
    return 0


def trim_path_to_marker_edges(start, end, start_radius=0, end_radius=0):
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    length = max((dx * dx + dy * dy) ** 0.5, 1.0)
    ux, uy = dx / length, dy / length
    safe_start_radius = min(start_radius, length * 0.4)
    safe_end_radius = min(end_radius, length * 0.4)
    trimmed_start = (sx + ux * safe_start_radius, sy + uy * safe_start_radius)
    trimmed_end = (ex - ux * safe_end_radius, ey - uy * safe_end_radius)
    return trimmed_start, trimmed_end


def scale_polygon(points, center, scale):
    cx, cy = center
    return [(cx + (x - cx) * scale, cy + (y - cy) * scale) for x, y in points]


def outfield_radius_ft(theta_deg: float) -> float:
    """Standard outfield arc with a single radius (visually smooth circular top)."""
    _ = theta_deg
    return OUTFIELD_ARC_RADIUS_FT


def outfield_point_ft(theta_deg: float):
    rad = math.radians(theta_deg)
    r = outfield_radius_ft(theta_deg)
    return fan_point_ft(theta_deg, r, OUTFIELD_ARC_CURVATURE_SCALE)


def fan_point_ft(theta_deg: float, radius_ft: float, curvature_scale: float):
    rad = math.radians(theta_deg)
    x = radius_ft * math.sin(rad)
    # 仅抬高中间弧顶（theta=0），在两端(theta=±45)保持不变，保证扇形仍为 90°
    t = abs(theta_deg) / 45.0
    bulge_weight = max(0.0, 1.0 - t * t)  # center=1, edge=0
    y = radius_ft * math.cos(rad) * (1.0 + (curvature_scale - 1.0) * bulge_weight)
    return x, y


def build_canvas_projector(canvas_width: int, canvas_height: int):
    # 投影边界只按球场本体计算，不把守备站位一起算进去，避免球场被整体缩小。
    field_points = [
        POSITION_COORDS["H"],
        POSITION_COORDS["B"],
        POSITION_COORDS["C"],
        POSITION_COORDS["P"],
        POSITION_COORDS["1B"],
        POSITION_COORDS["2B"],
        POSITION_COORDS["3B"],
    ]
    # 加入外场围栏采样点，确保整个球场轮廓都在可视正方形内
    for deg in sample_angles(-45.0, 45.0, BOUNDARY_SAMPLE_STEP_DEG):
        x, y = outfield_point_ft(float(deg))
        field_points.append((x, y))

    xs = [v[0] for v in field_points]
    ys = [v[1] for v in field_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    content_w = max(max_x - min_x, 1.0)
    content_h = max(max_y - min_y, 1.0)
    content_size = max(content_w, content_h)

    padding = int(min(canvas_width, canvas_height) * 0.06)
    square_size = max(220.0, min(canvas_width, canvas_height) - padding * 2)
    scale = square_size / content_size

    content_cx = (min_x + max_x) / 2.0
    content_cy = (min_y + max_y) / 2.0
    canvas_cx = canvas_width / 2.0
    canvas_cy = canvas_height / 2.0

    def project(key_or_point):
        if isinstance(key_or_point, str):
            sx, sy = POSITION_COORDS[key_or_point]
        else:
            sx, sy = key_or_point
        px = (sx - content_cx) * scale + canvas_cx
        # 屏幕坐标 y 轴向下，球场逻辑 y 轴向上（外场在上方）需反转
        py = (content_cy - sy) * scale + canvas_cy
        return px, py

    return project, scale


def draw_field_base(canvas_width: int, canvas_height: int, project, scale):
    grass_main = (66, 140, 66, 255)   # #428c42
    grass_inner = (66, 140, 66, 255)  # #428c42
    dirt = (206, 156, 99, 255)        # #ce9c63
    dirt_dark = (174, 142, 96, 255)
    line = (245, 245, 245, 255)
    outline = (45, 95, 45, 255)

    # 底色白色，满足“图最底下背景色为白色”
    field = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(field, "RGBA")

    home = project("H")
    first = project("1B")
    second = project("2B")
    third = project("3B")
    lf = project("LF")
    cf = project("CF")
    rf = project("RF")
    pitcher = project("P")

    # 真实感外场：330-375-400-375-330 轮廓 + warning track
    playable_arc = []
    fence_arc_outer = []
    fence_arc_inner = []
    warning_track_ft = 12.0
    for deg in sample_angles(-45.0, 45.0, FENCE_SAMPLE_STEP_DEG):
        x_out, y_out = outfield_point_ft(float(deg))
        r_outer = outfield_radius_ft(float(deg))
        r_inner = max(r_outer - warning_track_ft, 200.0)
        ratio = r_inner / max(r_outer, 1.0)
        x_play = x_out * ratio
        y_play = y_out * ratio
        x_in = x_out * ratio
        y_in = y_out * ratio
        playable_arc.append(project((x_play, y_play)))
        fence_arc_outer.append(project((x_out, y_out)))
        fence_arc_inner.append(project((x_in, y_in)))

    draw.polygon([home] + playable_arc, fill=grass_inner, outline=outline)
    draw.polygon(fence_arc_outer + list(reversed(fence_arc_inner)), fill=dirt_dark, outline=outline)

    # 内场土区：使用与外场相同的轮廓函数做缩放，保持形状一致
    home_to_second_ft = math.dist(POSITION_COORDS["H"], POSITION_COORDS["2B"])
    target_center_radius_ft = home_to_second_ft * INFIELD_FAN_RADIUS_SCALE
    infield_shape_scale = target_center_radius_ft / CENTER_FIELD_FT
    infield_fan_pts = []
    for deg in sample_angles(-45.0, 45.0, FENCE_SAMPLE_STEP_DEG):
        x_out, y_out = fan_point_ft(float(deg), OUTFIELD_ARC_RADIUS_FT, INFIELD_ARC_CURVATURE_SCALE)
        x = x_out * infield_shape_scale
        y = y_out * infield_shape_scale
        infield_fan_pts.append(project((x, y)))
    draw.polygon([home] + infield_fan_pts, fill=dirt)

    # 本垒区土圈（半径扩大到 1.5 倍）
    plate_circle_r = int(max(16, int(scale * 18)) * 1.5)
    draw.ellipse(
        (home[0] - plate_circle_r, home[1] - plate_circle_r, home[0] + plate_circle_r, home[1] + plate_circle_r),
        fill=dirt,
    )

    # Diamond：本垒-一二三垒之间的中间正方形区域（按中心缩放）
    diamond_pts = [home, first, second, third]
    diamond_center = (
        sum(p[0] for p in diamond_pts) / 4.0,
        sum(p[1] for p in diamond_pts) / 4.0,
    )
    diamond_scaled_pts = scale_polygon(diamond_pts, diamond_center, DIAMOND_SCALE)
    draw.polygon(diamond_scaled_pts, fill=grass_main, outline=outline)

    # 投手丘（土色）
    mound_r = max(8, int(scale * 9))
    draw.ellipse(
        (pitcher[0] - mound_r, pitcher[1] - mound_r, pitcher[0] + mound_r, pitcher[1] + mound_r),
        fill=dirt,
        outline=outline,
    )

    # 界线
    draw.line([home, project(outfield_point_ft(-45.0))], fill=line, width=2)
    draw.line([home, project(outfield_point_ft(45.0))], fill=line, width=2)
    # 基线白线（更接近示例图风格）
    baseline_w = max(2, int(scale * 1.2))
    draw.line([home, first], fill=line, width=baseline_w)
    draw.line([home, third], fill=line, width=baseline_w)
    # 按需求去掉一垒-二垒、二垒-三垒白线

    # 垒垫（白色）
    base_size = max(5, int(scale * 1.3 * 0.9))
    draw_rotated_square(draw, first, base_size, fill=line, outline=(215, 215, 215, 255))
    draw_rotated_square(draw, second, base_size, fill=line, outline=(215, 215, 215, 255))
    draw_rotated_square(draw, third, base_size, fill=line, outline=(215, 215, 215, 255))

    # 本垒（白色五边形）
    hx, hy = home
    home_size = max(7, int(scale * 1.7))
    home_plate = [
        (hx - home_size, hy),
        (hx + home_size, hy),
        (hx + int(home_size * 0.8), hy + home_size),
        (hx, hy + int(home_size * 1.5)),
        (hx - int(home_size * 0.8), hy + home_size),
    ]
    draw.polygon(home_plate, fill=line, outline=(215, 215, 215, 255))

    # 打击区与捕手区（线框）
    box_w = max(8, int(scale * 5))
    box_h = max(12, int(scale * 9))
    gap = max(4, int(scale * 2.5))
    draw.rectangle(
        (home[0] - gap - box_w, home[1] - box_h, home[0] - gap, home[1] + box_h),
        outline=line,
        width=2,
    )
    draw.rectangle(
        (home[0] + gap, home[1] - box_h, home[0] + gap + box_w, home[1] + box_h),
        outline=line,
        width=2,
    )
    catcher_w = max(10, int(scale * 7))
    catcher_h = max(6, int(scale * 4))
    draw.rectangle(
        (home[0] - catcher_w // 2, home[1] + box_h, home[0] + catcher_w // 2, home[1] + box_h + catcher_h),
        outline=line,
        width=2,
    )

    return field


def normalize_text(text: str) -> str:
    return str(text).replace(" ", "").replace("\u3000", "").lower()


def find_entities(text: str):
    normalized = normalize_text(text)
    entities = set()
    for key, patterns in ENTITY_PATTERNS.items():
        if any(p in normalized for p in patterns):
            entities.add(key)
    return entities


def find_destinations(text: str):
    normalized = normalize_text(text)
    destinations = []
    for key, patterns in DEST_PATTERNS.items():
        if any(p in normalized for p in patterns):
            destinations.append(key)
    return destinations


def find_ordered_position_mentions(text: str):
    normalized = normalize_text(text)
    mentions = []
    pattern_map = {}
    for key, patterns in {**ENTITY_PATTERNS, **DEST_PATTERNS}.items():
        for pattern in patterns:
            pattern_map.setdefault(pattern, key)

    for pattern, key in pattern_map.items():
        start = 0
        while True:
            idx = normalized.find(pattern, start)
            if idx == -1:
                break
            mentions.append((idx, key))
            start = idx + len(pattern)

    mentions.sort(key=lambda item: item[0])
    ordered_keys = []
    for _, key in mentions:
        if not ordered_keys or ordered_keys[-1] != key:
            ordered_keys.append(key)
    return ordered_keys


def make_paths_from_text(text: str, entities: set):
    normalized = normalize_text(text)
    destinations = find_destinations(text)
    ball_paths = []
    runner_paths = []

    ball_target_patterns = [
        (r"(击向|飞向|打向).*(游击手|游击|ss)", "SS"),
        (r"(击向|飞向|打向).*(三垒手|三垒|3垒|3b)", "3B"),
        (r"(击向|飞向|打向).*(二垒手|二垒|2垒|2b)", "2B"),
        (r"(击向|飞向|打向).*(一垒手|一垒|1垒|1b)", "1B"),
        (r"(击向|飞向|打向).*(左外野手|左外野|lf)", "LF"),
        (r"(击向|飞向|打向).*(中外野手|中外野|cf)", "CF"),
        (r"(击向|飞向|打向).*(右外野手|右外野|rf)", "RF"),
    ]
    for pattern, dst in ball_target_patterns:
        if re.search(pattern, normalized):
            ball_paths.append(("B", dst, "球路"))
            break

    fielder_catch_patterns = [
        (r"(游击手|游击|ss).*(接到球|接球|接住|拿到球|处理)", "SS"),
        (r"(三垒手|三垒|3垒|3b).*(接到球|接球|接住|拿到球|处理)", "3B"),
        (r"(二垒手|二垒|2垒|2b).*(接到球|接球|接住|拿到球|处理)", "2B"),
        (r"(一垒手|一垒|1垒|1b).*(接到球|接球|接住|拿到球|处理)", "1B"),
        (r"(左外野手|左外野|lf).*(接到球|接球|接住|拿到球|处理)", "LF"),
        (r"(中外野手|中外野|cf).*(接到球|接球|接住|拿到球|处理)", "CF"),
        (r"(右外野手|右外野|rf).*(接到球|接球|接住|拿到球|处理)", "RF"),
    ]
    if not ball_paths:
        for pattern, dst in fielder_catch_patterns:
            if re.search(pattern, normalized):
                ball_paths.append(("B", dst, "球路"))
                break

    # 回退逻辑：如果有击球语义但没命中细分规则，就用第一个防守区域目标
    if not ball_paths and any(v in normalized for v in ["击向", "飞向", "飞球", "地滚球", "平飞球"]):
        defender_priority = ["SS", "3B", "2B", "1B", "LF", "CF", "RF"]
        picked = next((k for k in defender_priority if k in entities), None)
        if picked:
            ball_paths.append(("B", picked, "球路"))
        else:
            for d in destinations:
                if d in {"SS", "LF", "CF", "RF", "3B", "2B", "1B"}:
                    ball_paths.append(("B", d, "球路"))
                    break

    # 跑垒线路：蓝色实线
    if ("打者" in normalized or "击球员" in normalized or "batter" in normalized) and (
        "跑向一垒" in normalized or "冲向一垒" in normalized or "上一垒" in normalized
    ):
        runner_paths.append(("B", "1B", "跑垒"))

    runner_hints = [
        ("一垒跑者", "跑向二垒", "R1", "2B"),
        ("一垒跑者", "冲向二垒", "R1", "2B"),
        ("二垒跑者", "跑向三垒", "R2", "3B"),
        ("二垒跑者", "冲向三垒", "R2", "3B"),
        ("三垒跑者", "跑向本垒", "R3", "H"),
        ("三垒跑者", "冲向本垒", "R3", "H"),
    ]
    for actor, action, src, dst in runner_hints:
        if actor in normalized and action in normalized:
            runner_paths.append((src, dst, "跑垒"))

    return ball_paths, runner_paths


def make_throw_paths_from_text(text: str, entities: set, fallback_source: str | None = None):
    normalized = normalize_text(text)
    throw_paths = []
    has_throw_verbs = any(v in normalized for v in ["传向", "传到", "传回", "传给", "回传", "再传", "转传"])
    answer_destinations = find_destinations(text)

    if has_throw_verbs:
        ordered_mentions = find_ordered_position_mentions(text)
        valid_throw_nodes = {"C", "P", "SS", "3B", "2B", "1B", "LF", "CF", "RF", "H"}
        ordered_mentions = [key for key in ordered_mentions if key in valid_throw_nodes]

        for src, dst in zip(ordered_mentions, ordered_mentions[1:]):
            if src != dst:
                throw_paths.append((src, dst, "传球"))

    # 回退逻辑：像“正确答案：一垒”这种只写目标垒位的情况，
    # 用题面识别到的最后接球守备员作为传球起点。
    if not throw_paths and fallback_source:
        for dst in answer_destinations:
            if dst in {"1B", "2B", "3B", "H"} and dst != fallback_source:
                throw_paths.append((fallback_source, dst, "传球"))
                break

    deduped_paths = []
    seen = set()
    for path in throw_paths:
        if path[:2] not in seen:
            seen.add(path[:2])
            deduped_paths.append(path)
    return deduped_paths


def draw_arrow(draw: ImageDraw.ImageDraw, start, end, color, width=4):
    draw.line([start, end], fill=color, width=width)
    draw_arrow_head(draw, start, end, color)


def draw_arrow_head(draw: ImageDraw.ImageDraw, start, end, color, size: int = 10):
    ex, ey = end
    sx, sy = start
    dx, dy = ex - sx, ey - sy
    length = max((dx * dx + dy * dy) ** 0.5, 1.0)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    p1 = (ex - ux * size + px * (size * 0.6), ey - uy * size + py * (size * 0.6))
    p2 = (ex - ux * size - px * (size * 0.6), ey - uy * size - py * (size * 0.6))
    draw.polygon([end, p1, p2], fill=color)


def draw_arrow_with_outline(
    draw: ImageDraw.ImageDraw,
    start,
    end,
    color,
    width=4,
    outline_color=(255, 214, 10, 230),
    outline_extra_width=3,
):
    draw.line([start, end], fill=outline_color, width=width + outline_extra_width)
    draw.line([start, end], fill=color, width=width)
    draw_arrow_head(draw, start, end, outline_color, size=int(10 + outline_extra_width))
    draw_arrow_head(draw, start, end, color, size=10)


def draw_dashed_arrow(draw: ImageDraw.ImageDraw, start, end, color, width=4, dash=12, gap=8):
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    length = max((dx * dx + dy * dy) ** 0.5, 1.0)
    step = dash + gap
    dist = 0.0
    while dist < length:
        s_ratio = dist / length
        e_ratio = min(dist + dash, length) / length
        x1 = sx + dx * s_ratio
        y1 = sy + dy * s_ratio
        x2 = sx + dx * e_ratio
        y2 = sy + dy * e_ratio
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
        dist += step
    draw_arrow_head(draw, start, end, color=color)


def draw_dashed_arrow_with_outline(
    draw: ImageDraw.ImageDraw,
    start,
    end,
    color,
    width=4,
    dash=12,
    gap=8,
    outline_color=(30, 30, 30, 220),
    outline_extra_width=3,
):
    draw_dashed_arrow(
        draw,
        start,
        end,
        color=outline_color,
        width=width + outline_extra_width,
        dash=dash,
        gap=gap,
    )
    draw_dashed_arrow(
        draw,
        start,
        end,
        color=color,
        width=width,
        dash=dash,
        gap=gap,
    )


def annotate_background_image(row: pd.Series, canvas_width: int, canvas_height: int, show_answer_paths: bool = False):
    text = f"{row.get('Scenario Name', '')}\n{row.get('Description', '')}\n{row.get('Key Question', '')}"
    entities = find_entities(text)
    ball_paths, runner_paths = make_paths_from_text(text, entities)
    correct_answer_text = row.get("Correct Answer", "")
    coach_tip_text = row.get("Coach's Tip", "")
    answer_text = f"{correct_answer_text}\n{coach_tip_text}"
    answer_entities = find_entities(answer_text)
    fallback_throw_source = ball_paths[-1][1] if ball_paths else None
    throw_paths = (
        make_throw_paths_from_text(answer_text, answer_entities, fallback_source=fallback_throw_source)
        if show_answer_paths
        else []
    )

    render_scale = max(1, int(RENDER_SUPERSAMPLE))
    render_width = canvas_width * render_scale
    render_height = canvas_height * render_scale

    base_img, xlim, ylim, field_layout = render_fieldpro_background(canvas_width, canvas_height, render_scale)
    annotated = base_img
    overlay = Image.new("RGBA", annotated.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    coords = dict(field_layout.get("coords", {}))
    if "1B" in coords:
        coords["R1"] = (coords["1B"][0] + 10 * render_scale, coords["1B"][1] + 8 * render_scale)
    if "2B" in coords:
        coords["R2"] = (coords["2B"][0], coords["2B"][1] - 10 * render_scale)
    if "3B" in coords:
        coords["R3"] = (coords["3B"][0] - 10 * render_scale, coords["3B"][1] + 8 * render_scale)

    x0, x1 = float(xlim[0]), float(xlim[1])
    y0, y1 = float(ylim[0]), float(ylim[1])

    def project(key: str):
        x, y = coords[key]
        px = (x - x0) / (x1 - x0) * render_width
        py = (y1 - y) / (y1 - y0) * render_height
        return (px, py)
    label_font = load_label_font(int(12 * MARKER_SCALE * render_scale))
    # 每次进入详情页，固定标注全部防守位
    for key in DEFENDER_KEYS:
        if key not in coords:
            continue
        x, y = project(key)
        r = 12 * MARKER_SCALE * render_scale
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 255), outline=(40, 40, 40, 255), width=2)
        draw_centered_text(
            draw,
            x,
            y,
            LABELS[key],
            font=label_font,
            fill=(22, 43, 77, 204),
        )

    # 额外标注识别到的跑垒员位置
    for runner_key in ["R1", "R2", "R3", "B"]:
        if runner_key in entities and runner_key in coords:
            x, y = project(runner_key)
            r = 10 * MARKER_SCALE * render_scale
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 255), outline=(40, 40, 40, 255), width=2)
            draw_centered_text(
                draw,
                x,
                y,
                LABELS[runner_key],
                font=label_font,
                fill=(22, 43, 77, 204),
            )

    for src, dst, _kind in ball_paths:
        if src not in coords or dst not in coords:
            continue
        # 明黄虚线 + 深色描边：球路
        start_point, end_point = trim_path_to_marker_edges(
            project(src),
            project(dst),
            marker_radius_for_key(src, render_scale),
            marker_radius_for_key(dst, render_scale),
        )
        draw_dashed_arrow_with_outline(
            draw,
            start_point,
            end_point,
            color=(255, 222, 0, 230),
            width=4 * render_scale,
            outline_color=(70, 55, 0, 230),
            outline_extra_width=3 * render_scale,
        )

    for src, dst, _kind in runner_paths:
        if src not in coords or dst not in coords:
            continue
        # 亮青蓝虚线 + 黑色描边：跑垒员跑动
        start_point, end_point = trim_path_to_marker_edges(
            project(src),
            project(dst),
            marker_radius_for_key(src, render_scale),
            marker_radius_for_key(dst, render_scale),
        )
        draw_dashed_arrow_with_outline(
            draw,
            start_point,
            end_point,
            color=(0, 255, 255, 245),
            width=4 * render_scale,
            outline_color=(0, 0, 0, 230),
            outline_extra_width=3 * render_scale,
        )

    for src, dst, _kind in throw_paths:
        if src not in coords or dst not in coords:
            continue
        start_point, end_point = trim_path_to_marker_edges(
            project(src),
            project(dst),
            marker_radius_for_key(src, render_scale),
            marker_radius_for_key(dst, render_scale),
        )
        draw_arrow_with_outline(
            draw,
            start_point,
            end_point,
            color=(210, 30, 30, 235),
            width=4 * render_scale,
            outline_color=(255, 214, 10, 230),
            outline_extra_width=3 * render_scale,
        )
    final_image = Image.alpha_composite(annotated, overlay)
    if render_scale > 1:
        resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        final_image = final_image.resize((canvas_width, canvas_height), resample=resampling)
    # Cloud compatibility: drawable-canvas is more stable with RGB than RGBA backgrounds.
    return final_image.convert("RGB"), entities, ball_paths, runner_paths, throw_paths


def build_plotly_board(background_image: Image.Image, canvas_width: int, canvas_height: int, stroke_color: str, stroke_width: int):
    png_io = io.BytesIO()
    background_image.save(png_io, format="PNG")
    image_uri = "data:image/png;base64," + base64.b64encode(png_io.getvalue()).decode("ascii")

    fig = go.Figure()
    fig.update_layout(
        width=canvas_width,
        height=canvas_height,
        autosize=False,
        margin=dict(l=0, r=0, t=0, b=0),
        dragmode="drawopenpath",
        newshape=dict(
            line=dict(color=stroke_color, width=stroke_width),
        ),
        images=[
            dict(
                source=image_uri,
                x=0,
                y=canvas_height,
                sizex=canvas_width,
                sizey=canvas_height,
                xref="x",
                yref="y",
                sizing="stretch",
                layer="below",
            )
        ],
        xaxis=dict(
            range=[0, canvas_width],
            visible=False,
            fixedrange=True,
        ),
        yaxis=dict(
            range=[0, canvas_height],
            visible=False,
            fixedrange=True,
            scaleanchor="x",
            scaleratio=1,
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def get_viewport_width():
    fallback_width = BASE_CANVAS_WIDTH + PAGE_SIDE_PADDING

    if streamlit_js_eval is None:
        return st.session_state.get("last_viewport_width", fallback_width)

    viewport_width = streamlit_js_eval(
        js_expressions="window.innerWidth",
        key="diamondbreak_viewport_width",
    )
    if isinstance(viewport_width, int) and viewport_width > 0:
        st.session_state["last_viewport_width"] = viewport_width
        return viewport_width

    return st.session_state.get("last_viewport_width", fallback_width)


def apply_page_width_style():
    st.markdown(
        f"""
        <style>
        .block-container {{
            max-width: {MAX_CONTENT_WIDTH}px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def ensure_state():
    if "selected_id" not in st.session_state:
        st.session_state.selected_id = None
    if "canvas_rev" not in st.session_state:
        st.session_state.canvas_rev = 0
    if "stroke_width" not in st.session_state:
        st.session_state.stroke_width = DEFAULT_STROKE_WIDTH
    if "stroke_color" not in st.session_state:
        st.session_state.stroke_color = DEFAULT_STROKE_COLOR


def show_dashboard(df: pd.DataFrame):
    st.title("Baseball IQ 战术练习")
    st.caption("MVP 版本：局面筛选 + 战术板绘图 + 解析反馈")

    categories = ["全部"] + sorted([c for c in df["Category"].unique() if c])
    selected_category = st.selectbox("按 Category 筛选", categories, index=0)

    if selected_category != "全部":
        df = df[df["Category"] == selected_category]

    st.write(f"共 {len(df)} 个局面")

    if df.empty:
        st.info("没有匹配的局面，请更换筛选条件。")
        return

    for _, row in df.iterrows():
        title = row["Scenario Name"] or f"场景 {row['ID']}"
        category = row["Category"] or "未分类"
        with st.container(border=True):
            st.markdown(f"**#{row['ID']:03d} {title}**")
            st.write(f"Category: {category}")
            if row["Description"]:
                st.write(row["Description"])
            if st.button("进入练习", key=f"open_{row['ID']}", use_container_width=True):
                st.session_state.selected_id = int(row["ID"])
                st.rerun()


def show_detail(df: pd.DataFrame, scenario_id: int):
    row_df = df[df["ID"] == scenario_id]
    if row_df.empty:
        st.error("未找到该场景，已返回列表。")
        st.session_state.selected_id = None
        st.rerun()
        return

    row = row_df.iloc[0]
    title = row["Scenario Name"] or f"场景 {row['ID']}"
    combined_text = "\n\n".join(
        [part for part in [row["Description"].strip(), row["Key Question"].strip()] if part]
    ) or "（暂无）"
    combined_text_html = html.escape(combined_text).replace("\n", "<br>")
    flag_key = f"show_analysis_{scenario_id}"
    if flag_key not in st.session_state:
        st.session_state[flag_key] = False

    header_c1, header_c2 = st.columns([1, 4])
    with header_c1:
        if st.button("返回列表"):
            st.session_state.selected_id = None
            st.rerun()
    with header_c2:
        st.markdown(
            f"<div style='color: #a6a6a6; font-size: 1.06rem; line-height: 2.2;'>#{scenario_id:03d}</div>",
            unsafe_allow_html=True,
        )

    st.subheader(title)
    st.markdown("<div style='font-size: 1.1rem; font-weight: 600; margin-top: 0.25rem; margin-bottom: 0.35rem;'>局面描述</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size: 1.06rem; line-height: 1.8;'>{combined_text_html}</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 0.9rem;'></div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 1.1rem; font-weight: 600; margin-top: 0; margin-bottom: 6px;'>交互式战术板</div>", unsafe_allow_html=True)
    viewport_width = get_viewport_width()
    available_width = max(MIN_CANVAS_WIDTH, viewport_width - PAGE_SIDE_PADDING)
    raw_width = min(MAX_CONTENT_WIDTH, available_width)
    st.session_state.stroke_width = DEFAULT_STROKE_WIDTH
    st.session_state.stroke_color = DEFAULT_STROKE_COLOR

    # 宽度量化：避免浏览器/滚动条带来的 1~几像素抖动，减少背景图反复换 URL
    width_step = 16
    candidate_width = max(MIN_CANVAS_WIDTH, (raw_width // width_step) * width_step)

    width_state_key = f"canvas_width_{scenario_id}"
    prev_width = st.session_state.get(width_state_key)
    # 宽度变化时重建画板（以及背景图 + 自动标注）
    if prev_width is None:
        st.session_state[width_state_key] = candidate_width
    elif abs(prev_width - candidate_width) >= width_step:
        st.session_state[width_state_key] = candidate_width
        st.session_state.canvas_rev += 1

    canvas_width = st.session_state[width_state_key]
    canvas_height = canvas_width

    auto_entities = set()
    auto_ball_paths = []
    auto_runner_paths = []
    auto_throw_paths = []
    bg_image, auto_entities, auto_ball_paths, auto_runner_paths, auto_throw_paths = annotate_background_image(
        row, canvas_width, canvas_height, show_answer_paths=st.session_state[flag_key]
    )

    fig = build_plotly_board(
        bg_image,
        canvas_width,
        canvas_height,
        st.session_state.stroke_color,
        st.session_state.stroke_width,
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displaylogo": False,
            "modeBarButtonsToAdd": ["drawline", "drawopenpath", "eraseshape"],
            "toImageButtonOptions": {"format": "png", "filename": f"scenario_{scenario_id:03d}"},
            "responsive": False,
        },
        key=f"plotly_board_{scenario_id}_{canvas_width}_{st.session_state.canvas_rev}",
    )
    st.markdown(
        "<div style='text-align: center; color: rgb(80, 80, 80); font-size: 0.92rem; margin: 6px 0 20px 0;'>"
        "下载请使用绘图区域右上角的相机按钮"
        "</div>",
        unsafe_allow_html=True,
    )

    if not st.session_state[flag_key]:
        if st.button("查看解析", use_container_width=True):
            st.session_state[flag_key] = True
            st.rerun()
    else:
        st.success("已展开解析")
        st.markdown("**Correct Answer**")
        st.write(row["Correct Answer"] or "（暂无）")
        st.markdown("**Coach's Tip**")
        st.write(row["Coach's Tip"] or "（暂无）")




def main():
    st.set_page_config(page_title="Baseball Tactical Trainer", layout="wide")
    apply_page_width_style()
    ensure_state()

    data_file_path = BASE_DIR / DATA_FILE
    if not data_file_path.exists():
        st.error("未找到数据文件 `datasource01.xlsx`。请将它放到项目根目录。")
        with st.expander("部署环境诊断", expanded=False):
            st.write(f"当前目录: `{Path.cwd()}`")
            st.write(f"应用目录: `{BASE_DIR}`")
            st.write(f"期望数据文件: `{data_file_path}`")
        return

    df = load_scenarios(data_file_path)
    if st.session_state.selected_id is None:
        show_dashboard(df)
    else:
        show_detail(df, st.session_state.selected_id)


if __name__ == "__main__":
    main()
