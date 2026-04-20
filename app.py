from pathlib import Path
import re

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from streamlit_js_eval import streamlit_js_eval
from streamlit_drawable_canvas import st_canvas


DATA_FILE = Path("datasource01.xlsx")
DEFAULT_FIELD_IMAGE = Path("baseball-field-diagram.png")


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
BASE_CANVAS_HEIGHT = 500
CANVAS_ASPECT_RATIO = BASE_CANVAS_HEIGHT / BASE_CANVAS_WIDTH

# 以 800x500 画布为基准的粗略球场坐标，适配常见的上半场区在上、内野菱形在中部的底图。
POSITION_COORDS = {
    "P": (400, 300),   # 投手
    "C": (400, 435),   # 捕手
    "1B": (510, 345),
    "2B": (400, 250),
    "3B": (290, 345),
    "SS": (340, 275),
    "LF": (220, 180),
    "CF": (400, 130),
    "RF": (580, 180),
    "B": (400, 455),   # 打者
    "R1": (535, 365),  # 一垒跑者
    "R2": (400, 230),  # 二垒跑者
    "R3": (265, 365),  # 三垒跑者
    "H": (400, 400),   # 本垒(传球目标)
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


def resolve_background_image(row: pd.Series):
    image_hint = str(row.get("Tactical Image", "")).strip()
    if image_hint:
        p = Path(image_hint)
        if p.exists() and p.is_file():
            return Image.open(p)

    if DEFAULT_FIELD_IMAGE.exists() and DEFAULT_FIELD_IMAGE.is_file():
        return Image.open(DEFAULT_FIELD_IMAGE)

    return None


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

    # 回退逻辑：如果有击球语义但没命中细分规则，就用第一个防守区域目标
    if not ball_paths and any(v in normalized for v in ["击向", "飞向", "飞球", "地滚球", "平飞球"]):
        for d in destinations:
            if d in {"SS", "LF", "CF", "RF", "3B", "2B", "1B"}:
                ball_paths.append(("B", d, "球路"))
                break

    # 传球线路：防守球员 -> 目标垒位/区域（也按球路处理）
    if any(v in normalized for v in ["传向", "传到", "传回", "传给"]):
        source_priority = ["C", "P", "SS", "3B", "2B", "1B", "LF", "CF", "RF"]
        source = next((s for s in source_priority if s in entities), None)
        if source:
            for d in destinations:
                if d != source:
                    ball_paths.append((source, d, "球路"))
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


def draw_arrow(draw: ImageDraw.ImageDraw, start, end, color, width=4):
    draw.line([start, end], fill=color, width=width)
    ex, ey = end
    sx, sy = start
    dx, dy = ex - sx, ey - sy
    length = max((dx * dx + dy * dy) ** 0.5, 1.0)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    size = 10
    p1 = (ex - ux * size + px * (size * 0.6), ey - uy * size + py * (size * 0.6))
    p2 = (ex - ux * size - px * (size * 0.6), ey - uy * size - py * (size * 0.6))
    draw.polygon([end, p1, p2], fill=color)


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
    draw_arrow(draw, start, end, color=color, width=width)


def scale_point(point, scale_x, scale_y):
    x, y = point
    return int(x * scale_x), int(y * scale_y)


def annotate_background_image(base_image: Image.Image, row: pd.Series, canvas_width: int, canvas_height: int):
    text = f"{row.get('Scenario Name', '')}\n{row.get('Description', '')}\n{row.get('Key Question', '')}"
    entities = find_entities(text)
    ball_paths, runner_paths = make_paths_from_text(text, entities)

    annotated = base_image.convert("RGBA").resize((canvas_width, canvas_height))
    overlay = Image.new("RGBA", annotated.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.load_default()
    scale_x = canvas_width / BASE_CANVAS_WIDTH
    scale_y = canvas_height / BASE_CANVAS_HEIGHT

    # 每次进入详情页，固定标注全部防守位
    for key in DEFENDER_KEYS:
        x, y = scale_point(POSITION_COORDS[key], scale_x, scale_y)
        r = 12
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 244, 180, 220), outline=(20, 20, 20, 255), width=2)
        draw.text((x + 10, y - 10), LABELS[key], fill=(20, 20, 20, 255), font=font)

    # 额外标注识别到的跑垒员位置
    for runner_key in ["R1", "R2", "R3", "B"]:
        if runner_key in entities and runner_key in POSITION_COORDS:
            x, y = scale_point(POSITION_COORDS[runner_key], scale_x, scale_y)
            r = 10
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(180, 230, 255, 220), outline=(20, 20, 20, 255), width=2)
            draw.text((x + 8, y - 10), LABELS[runner_key], fill=(20, 20, 20, 255), font=font)

    for src, dst, _kind in ball_paths:
        if src not in POSITION_COORDS or dst not in POSITION_COORDS:
            continue
        # 红色虚线：球路
        draw_dashed_arrow(
            draw,
            scale_point(POSITION_COORDS[src], scale_x, scale_y),
            scale_point(POSITION_COORDS[dst], scale_x, scale_y),
            color=(255, 80, 80, 230),
            width=4,
        )

    for src, dst, _kind in runner_paths:
        if src not in POSITION_COORDS or dst not in POSITION_COORDS:
            continue
        # 蓝色实线：跑垒员跑动
        draw_arrow(
            draw,
            scale_point(POSITION_COORDS[src], scale_x, scale_y),
            scale_point(POSITION_COORDS[dst], scale_x, scale_y),
            color=(80, 160, 255, 230),
            width=4,
        )

    return Image.alpha_composite(annotated, overlay), entities, ball_paths, runner_paths


def ensure_state():
    if "selected_id" not in st.session_state:
        st.session_state.selected_id = None
    if "canvas_rev" not in st.session_state:
        st.session_state.canvas_rev = 0


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

    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("返回列表"):
            st.session_state.selected_id = None
            st.rerun()
    with c2:
        st.subheader(f"#{row['ID']:03d} {title}")

    st.write(f"Category: {row['Category'] or '未分类'}")
    st.markdown("### 局面描述")
    st.write(row["Description"] or "（暂无）")
    st.markdown("### 向你提问")
    st.write(row["Key Question"] or "（暂无）")

    st.markdown("### 交互式战术板")
    viewport_width = streamlit_js_eval(
        js_expressions="window.innerWidth",
        key=f"viewport_width_{scenario_id}",
        want_output=True,
    )
    # 根据浏览器宽度做响应式计算，给工具栏与边距预留空间
    if isinstance(viewport_width, (int, float)):
        canvas_width = int(max(320, min(BASE_CANVAS_WIDTH, viewport_width - 260)))
    else:
        canvas_width = BASE_CANVAS_WIDTH
    canvas_height = int(canvas_width * CANVAS_ASPECT_RATIO)

    bg_image = resolve_background_image(row)
    auto_entities = set()
    auto_ball_paths = []
    auto_runner_paths = []
    if bg_image is None:
        st.info("未找到战术底图。请将 `baseball-field-diagram.png` 放在项目根目录。")
    else:
        bg_image, auto_entities, auto_ball_paths, auto_runner_paths = annotate_background_image(
            bg_image, row, canvas_width, canvas_height
        )

    draw_col, tool_col = st.columns([5, 2])
    with tool_col:
        stroke_width = st.slider("画笔粗细", 1, 15, 3)
        stroke_color = st.color_picker("画笔颜色", "#ff0000")
        if st.button("一键清除画板", use_container_width=True):
            st.session_state.canvas_rev += 1
            st.rerun()

    with draw_col:
        st_canvas(
            fill_color="rgba(255, 165, 0, 0.2)",
            stroke_width=stroke_width,
            stroke_color=stroke_color,
            background_image=bg_image,
            # 避免每一笔都触发整页重跑，导致背景图媒体 URL 失效
            update_streamlit=False,
            height=canvas_height,
            width=canvas_width,
            drawing_mode="freedraw",
            key=f"canvas_{scenario_id}_{st.session_state.canvas_rev}",
        )

    with st.expander("查看自动标注明细（基于文字规则）", expanded=False):
        if auto_entities:
            st.write("已标注人员/位置:", ", ".join(sorted(auto_entities)))
        else:
            st.write("已标注人员/位置: 无")

        if auto_ball_paths:
            st.write("已标注球路（红色虚线）:")
            for src, dst, _ in auto_ball_paths:
                st.write(f"- 球路: {src} -> {dst}")
        else:
            st.write("已标注球路: 无")

        if auto_runner_paths:
            st.write("已标注跑垒线路（蓝色实线）:")
            for src, dst, _ in auto_runner_paths:
                st.write(f"- 跑垒: {src} -> {dst}")
        else:
            st.write("已标注跑垒线路: 无")

    st.markdown("### 解析与反馈")
    flag_key = f"show_analysis_{scenario_id}"
    if flag_key not in st.session_state:
        st.session_state[flag_key] = False

    if not st.session_state[flag_key]:
        if st.button("查看解析"):
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
    ensure_state()

    if not DATA_FILE.exists():
        st.error("未找到数据文件 `datasource01.xlsx`。请将它放到项目根目录。")
        return

    df = load_scenarios(DATA_FILE)
    if st.session_state.selected_id is None:
        show_dashboard(df)
    else:
        show_detail(df, st.session_state.selected_id)


if __name__ == "__main__":
    main()
