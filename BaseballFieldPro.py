import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

class BaseballFieldPro:
    """
    接口锁定：
    - 初始化：field = BaseballFieldPro(size=12)
    - 绘图：fig = field.draw(players=None)
    """
    def __init__(self, size=12):
        self.size = size
        # 严格提取自 diagram1.png 的矢量色值
        self.colors = {
            'grass': '#428c42',
            'dirt': '#ce9c63',
            'line': '#FFFFFF',       # 纯白标线
            'outline': '#000000',    # 核心黑色描边
            'bg': '#FFFFFF'          # 纯白背景
        }

    def compute_layout(self):
        outfield_curvature_scale = 1.17
        infield_curvature_scale = 1.22
        outfield_scale = 1.20
        outfield_radius_scale = 0.75
        outfield_corner_radius_ratio = 0.12
        base_dirt_circle_radius = 10
        home_circle_r = 13 * 1.30
        infield_group_shift_y = home_circle_r * 3
        base_pad_scale = 0.8 * 1.6

        outfield_radius = 250 * outfield_radius_scale * 1.20
        outfield_corner_radius = outfield_radius * outfield_corner_radius_ratio

        base_pad_radius = 5.6 * base_pad_scale
        base_pad_side = base_pad_radius * float(np.sqrt(2.0))

        foul_line_width = 1.8
        infield_dirt_origin_y = infield_group_shift_y - (base_pad_side * 0.5 + foul_line_width)
        infield_radius = float(outfield_radius) * 0.60 * 1.30 * 0.80 * 1.30 * 0.75

        diamond_side = float(infield_radius) * (2.0 / 3.0)
        diamond_half_diag = diamond_side / float(np.sqrt(2.0))

        home_xy = (0.0, infield_group_shift_y)
        first_xy = (diamond_half_diag, infield_group_shift_y + diamond_half_diag)
        second_xy = (0.0, infield_group_shift_y + 2.0 * diamond_half_diag)
        third_xy = (-diamond_half_diag, infield_group_shift_y + diamond_half_diag)

        base_center_offset_y = base_pad_radius
        first_base_xy = (first_xy[0], first_xy[1] + base_center_offset_y)
        second_base_xy = (second_xy[0], second_xy[1] + base_center_offset_y)
        third_base_xy = (third_xy[0], third_xy[1] + base_center_offset_y)

        diamond_outer_pts = [
            (second_base_xy[0], second_base_xy[1] + base_pad_radius),
            (first_base_xy[0] + base_pad_radius, first_base_xy[1]),
            home_xy,
            (third_base_xy[0] - base_pad_radius, third_base_xy[1]),
        ]
        outer_side = float(
            np.hypot(
                diamond_outer_pts[1][0] - diamond_outer_pts[0][0],
                diamond_outer_pts[1][1] - diamond_outer_pts[0][1],
            )
        )
        inner_side = max(outer_side - base_pad_side, outer_side * 0.10)
        diamond_inner_scale = inner_side / max(outer_side, 1e-6)
        square_cx = sum(x for x, _ in diamond_outer_pts) / len(diamond_outer_pts)
        square_cy = sum(y for _, y in diamond_outer_pts) / len(diamond_outer_pts)
        diamond_grass_pts = [
            (
                square_cx + (x - square_cx) * diamond_inner_scale,
                square_cy + (y - square_cy) * diamond_inner_scale,
            )
            for x, y in diamond_outer_pts
        ]

        mound_plate_w = base_dirt_circle_radius * 0.75
        mound_plate_h = base_dirt_circle_radius * 0.12 * 3
        pitcher_y = 60.5 + base_dirt_circle_radius + base_dirt_circle_radius + mound_plate_h * 4 + infield_group_shift_y
        foul_line_len = 240

        def scale_point(pt):
            return (pt[0] * outfield_scale, pt[1] * outfield_scale)

        r_out = outfield_radius * 0.82
        rf = scale_point((r_out * float(np.sin(np.deg2rad(28.0))), r_out * float(np.cos(np.deg2rad(28.0)))))
        cf = scale_point((0.0, r_out))
        lf = scale_point((-rf[0], rf[1]))

        ss = scale_point(((second_base_xy[0] + third_base_xy[0]) * 0.5, (second_base_xy[1] + third_base_xy[1]) * 0.5 - base_pad_radius * 0.25))
        c = scale_point((home_xy[0], home_xy[1] - home_circle_r * 1.10))
        b = scale_point((home_xy[0], home_xy[1] - home_circle_r * 0.55))

        return {
            "outfield_curvature_scale": outfield_curvature_scale,
            "infield_curvature_scale": infield_curvature_scale,
            "outfield_scale": outfield_scale,
            "outfield_radius": outfield_radius,
            "outfield_corner_radius": outfield_corner_radius,
            "infield_dirt_origin_y": infield_dirt_origin_y,
            "infield_radius": infield_radius,
            "home_circle_r": home_circle_r,
            "base_dirt_circle_radius": base_dirt_circle_radius,
            "base_pad_scale": base_pad_scale,
            "base_pad_radius": base_pad_radius,
            "base_pad_side": base_pad_side,
            "diamond_grass_pts": [scale_point(p) for p in diamond_grass_pts],
            "home_xy": scale_point(home_xy),
            "first_base_xy": scale_point(first_base_xy),
            "second_base_xy": scale_point(second_base_xy),
            "third_base_xy": scale_point(third_base_xy),
            "pitcher_xy": scale_point((0.0, pitcher_y)),
            "coords": {
                "H": scale_point(home_xy),
                "B": b,
                "C": c,
                "P": scale_point((0.0, pitcher_y)),
                "1B": scale_point(first_base_xy),
                "2B": scale_point(second_base_xy),
                "3B": scale_point(third_base_xy),
                "SS": ss,
                "LF": lf,
                "CF": cf,
                "RF": rf,
            },
            "mound_plate_w": mound_plate_w * outfield_scale,
            "mound_plate_h": mound_plate_h * outfield_scale,
            "foul_line_len": foul_line_len * outfield_scale,
        }


    def draw(self, players=None):
        # 1. 初始化画布，确保比例 1:1
        fig, ax = plt.subplots(figsize=(self.size, self.size))
        ax.set_aspect('equal')
        fig.patch.set_facecolor(self.colors['bg'])
        ax.set_facecolor(self.colors['bg'])

        # 定义统一的描边样式
        stroke = {'edgecolor': self.colors['outline'], 'linewidth': 0.8}

        def build_fan_polygon(
            radius: float,
            curvature_scale: float,
            origin=(0.0, 0.0),
            sample_step_deg: float = 1.0,
        ):
            ox, oy = origin
            points = [(ox, oy)]
            thetas = np.arange(-45.0, 45.0 + sample_step_deg, sample_step_deg)
            for theta_deg in thetas:
                rad = np.deg2rad(theta_deg)
                t = abs(theta_deg) / 45.0
                bulge_weight = max(0.0, 1.0 - t * t)
                x = ox + radius * np.sin(rad)
                y = oy + radius * np.cos(rad) * (1.0 + (curvature_scale - 1.0) * bulge_weight)
                points.append((float(x), float(y)))
            points.append((ox, oy))
            return points

        def build_fan_polygon_rounded_corner(
            radius: float,
            curvature_scale: float,
            corner_radius: float,
            origin=(0.0, 0.0),
            arc_step_deg: float = 1.0,
            corner_step_deg: float = 2.0,
        ):
            ox, oy = origin
            outer = []
            thetas = np.arange(-45.0, 45.0 + arc_step_deg, arc_step_deg)
            for theta_deg in thetas:
                rad = np.deg2rad(theta_deg)
                t = abs(theta_deg) / 45.0
                bulge_weight = max(0.0, 1.0 - t * t)
                x = ox + radius * np.sin(rad)
                y = oy + radius * np.cos(rad) * (1.0 + (curvature_scale - 1.0) * bulge_weight)
                outer.append((float(x), float(y)))

            cr = max(float(corner_radius), 0.0)
            if cr <= 0.0:
                return [(ox, oy)] + outer + [(ox, oy)]

            cr = min(cr, float(radius) * 0.45)
            s2 = float(np.sqrt(2.0))
            left_tan = (ox - cr / s2, oy + cr / s2)
            right_tan = (ox + cr / s2, oy + cr / s2)
            cx, cy = ox, oy + cr * s2

            corner_arc = []
            angles = np.arange(-45.0, -135.0 - corner_step_deg, -corner_step_deg)
            for a in angles:
                rad = np.deg2rad(a)
                x = cx + cr * np.cos(rad)
                y = cy + cr * np.sin(rad)
                corner_arc.append((float(x), float(y)))

            return [left_tan] + outer + [right_tan] + corner_arc[1:-1]

        layout = self.compute_layout()
        outfield_curvature_scale = layout["outfield_curvature_scale"]
        infield_curvature_scale = layout["infield_curvature_scale"]
        outfield_radius = layout["outfield_radius"]
        outfield_corner_radius = layout["outfield_corner_radius"]
        infield_dirt_origin_y = layout["infield_dirt_origin_y"]
        infield_radius = layout["infield_radius"]
        home_circle_r = layout["home_circle_r"]
        base_dirt_circle_radius = layout["base_dirt_circle_radius"]
        base_pad_scale = layout["base_pad_scale"]
        base_pad_radius = layout["base_pad_radius"]
        base_pad_side = layout["base_pad_side"]
        home_xy = layout["home_xy"]
        first_base_xy = layout["first_base_xy"]
        second_base_xy = layout["second_base_xy"]
        third_base_xy = layout["third_base_xy"]
        pitcher_x, pitcher_y = layout["pitcher_xy"]
        mound_plate_w = layout["mound_plate_w"]
        mound_plate_h = layout["mound_plate_h"]
        foul_line_len = layout["foul_line_len"]

        # 2. 绘制外野大扇形 (Outfield)
        outfield_pts = build_fan_polygon_rounded_corner(
            outfield_radius,
            outfield_curvature_scale,
            outfield_corner_radius,
        )
        outfield_pts = [(x * layout["outfield_scale"], y * layout["outfield_scale"]) for x, y in outfield_pts]
        outfield = patches.Polygon(outfield_pts, closed=True, color=self.colors['grass'], edgecolor='none', linewidth=0, zorder=1)
        ax.add_patch(outfield)

        # 3. 绘制内野泥地小扇形 (Infield Dirt Fan)
        # 扇形底点：在本垒圆圆心向下半个一垒垒垫的边长距离
        foul_line_width = 1.8
        show_infield_dirt_fan = True
        if show_infield_dirt_fan:
            infield_pts = build_fan_polygon(infield_radius, infield_curvature_scale, origin=(0.0, infield_dirt_origin_y))
            infield_pts = [(x * layout["outfield_scale"], y * layout["outfield_scale"]) for x, y in infield_pts]
            infield_dirt_fan = patches.Polygon(infield_pts, closed=True, color=self.colors['dirt'], **stroke, zorder=2)
            ax.add_patch(infield_dirt_fan)

        ax.add_patch(
            patches.Polygon(
                outfield_pts,
                closed=True,
                fill=False,
                edgecolor=self.colors['outline'],
                linewidth=1.2,
                zorder=20,
            )
        )

        # 4. 绘制钻石型垒区 (Diamond)
        infield_grass = patches.Polygon(layout["diamond_grass_pts"], closed=True, color=self.colors['grass'], **stroke, zorder=3)
        ax.add_patch(infield_grass)

        # 5. 核心圆区细节：投手丘与本垒
        # 投手丘 (Mound)
        ax.add_patch(patches.Circle((pitcher_x, pitcher_y), base_dirt_circle_radius, color=self.colors['dirt'], **stroke, zorder=4))
        # 投手板（纯白、无描边、居中于投手圆）
        ax.add_patch(
            patches.Rectangle(
                (pitcher_x - mound_plate_w / 2, pitcher_y - mound_plate_h / 2),
                mound_plate_w,
                mound_plate_h,
                color='white',
                ec='none',
                lw=0,
                zorder=5,
            )
        )
        # 本垒圆区（圆心与钻石底点重合）
        ax.add_patch(patches.Circle(home_xy, home_circle_r, color=self.colors['dirt'], **stroke, zorder=4))
        # 1/2/3 垒的土色圆形包围（圆心与钻石三个角顶点重合）
        for x, y in [first_base_xy, second_base_xy, third_base_xy]:
            ax.add_patch(patches.Circle((x, y), base_pad_side, color=self.colors['dirt'], **stroke, zorder=4))

        # 6. 绘制白色标线 (Foul Lines)
        # 标线置于描边之上，增加清晰度
        line_opt = {'color': self.colors['line'], 'linewidth': 1.8, 'zorder': 30}
        hx, hy = home_xy
        ax.plot([hx, hx + foul_line_len], [hy, hy + foul_line_len], **line_opt)
        ax.plot([hx, hx - foul_line_len], [hy, hy + foul_line_len], **line_opt)

        # 7. 绘制垒包 (白底黑边)
        # 本垒垒垫：倒置小房子形状（纯白，无黑边），居中于本垒圆
        home_pad_scale = 1.6
        home_pad_w = home_circle_r * 0.22 * home_pad_scale
        home_pad_h = home_circle_r * 0.26 * home_pad_scale
        home_pad_roof_h = home_circle_r * 0.18 * home_pad_scale
        home_pad_offset_y = home_pad_roof_h
        home_pad_pts = [
            (-home_pad_w, home_pad_h + home_pad_offset_y),
            (home_pad_w, home_pad_h + home_pad_offset_y),
            (home_pad_w, 0.0 + home_pad_offset_y),
            (0.0, -home_pad_roof_h + home_pad_offset_y),
            (-home_pad_w, 0.0 + home_pad_offset_y),
        ]
        home_pad_pts = [(hx + x, hy + y) for x, y in home_pad_pts]
        ax.add_patch(patches.Polygon(home_pad_pts, color='white', ec='none', lw=0, zorder=8))
        # 1, 2, 3 垒 (正方形)
        for x, y in [first_base_xy, second_base_xy, third_base_xy]:
            ax.add_patch(
                patches.RegularPolygon(
                    (x, y),
                    4,
                    radius=5.6 * base_pad_scale,
                    orientation=0,
                    color='white',
                    ec='none',
                    lw=0,
                    zorder=8,
                )
            )

        # 8. 渲染球员位置
        if players:
            for p in players:
                px, py = p['pos']
                # 球员图标：红底白边圆圈
                ax.add_patch(patches.Circle((px, py), 5.5, color='#E53935', ec='white', lw=1.2, zorder=10))
                # 居中文字
                ax.text(px, py, p['label'], color='white', fontsize=7.5, ha='center', 
                        va='center', fontweight='black', zorder=11)

        # 9. 裁剪视图，隐藏坐标轴
        xs = [p[0] for p in outfield_pts]
        ys = [p[1] for p in outfield_pts]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        cx = (min_x + max_x) / 2.0
        cy = (min_y + max_y) / 2.0
        span = max(max_x - min_x, max_y - min_y) * 1.05
        ax.set_xlim(cx - span / 2.0, cx + span / 2.0)
        ax.set_ylim(cy - span / 2.0, cy + span / 2.0)
        ax.axis('off')
        
        return fig
