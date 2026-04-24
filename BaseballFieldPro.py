import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import math

class BaseballFieldPro:
    def __init__(self, size=12):
        self.size = size
        # 严格参照 diagram1 的明快配色
        self.colors = {
            'grass': '#4A9E54',      # 亮草绿
            'dirt': '#D3A671',       # 暖沙土
            'line': '#FFFFFF',       # 纯白标线
            'outline': '#000000',    # 黑色轮廓线
            'bg': '#FFFFFF'          # 纯白背景
        }

        # 几何参数
        self.outer_radius = 112.0
        self.outfield_curve_scale = 1.30
        self.infield_radius = self.outer_radius * 0.60
        self.diamond_radius = 27.5
        self.base_path = 31.8
        self.pitcher_y = 45.0

    def _fan_points(self, radius, curve_scale, steps=181):
        points = [[0.0, 0.0]]
        for theta in np.linspace(-45.0, 45.0, steps):
            rad = math.radians(theta)
            x = radius * math.sin(rad)
            t = abs(theta) / 45.0
            bulge_weight = max(0.0, 1.0 - t * t)
            y = radius * math.cos(rad) * (1.0 + (curve_scale - 1.0) * bulge_weight)
            points.append([x, y])
        return np.array(points)

    def _diamond_points(self, radius):
        return np.array([
            [0.0, 0.0],
            [radius, radius],
            [0.0, radius * 2.0],
            [-radius, radius],
        ])

    def draw(self, players=None):
        fig, ax = plt.subplots(figsize=(self.size, self.size))
        ax.set_aspect('equal')
        fig.patch.set_facecolor(self.colors['bg'])
        ax.set_facecolor(self.colors['bg'])

        # 统一描边参数，这是让图表变“高级”的关键
        stroke = {'edgecolor': self.colors['outline'], 'linewidth': 0.8}

        # 1. 外场：严格 90° 扇形，顶部弧线额外抬高 30%
        outfield_pts = self._fan_points(self.outer_radius, self.outfield_curve_scale)
        ax.add_patch(patches.Polygon(outfield_pts, closed=True, color=self.colors['grass'], **stroke, zorder=1))

        # 2. 内场：与外场同比例的扇形，只取 60% 半径
        infield_pts = self._fan_points(self.infield_radius, self.outfield_curve_scale)
        ax.add_patch(patches.Polygon(infield_pts, closed=True, color=self.colors['dirt'], **stroke, zorder=2))

        # 3. 钻石草皮区域扩大 10%，并取消内部单独黄土块
        diamond_grass = self._diamond_points(self.diamond_radius)
        ax.add_patch(patches.Polygon(diamond_grass, closed=True, color=self.colors['grass'], **stroke, zorder=3))

        # 4. 保留本垒区泥地，钻石内部不再额外铺黄土
        ax.add_patch(patches.Circle((0, 0), 8, color=self.colors['dirt'], **stroke, zorder=4))

        # 5. 白色标线，扇形底边保持 90° 视觉
        foul_end = self.outer_radius / math.sqrt(2.0)
        ax.plot([0, foul_end], [0, foul_end], color=self.colors['line'], lw=1.5, zorder=6)
        ax.plot([0, -foul_end], [0, foul_end], color=self.colors['line'], lw=1.5, zorder=6)

        # 6. 投手板
        ax.add_patch(
            patches.Rectangle(
                (-2.0, self.pitcher_y),
                4.0,
                0.6,
                color='white',
                ec=self.colors['outline'],
                lw=0.5,
                zorder=7,
            )
        )

        # 7. 绘制垒包 (白底黑边)
        # 本垒五角形
        home_v = [[0,0], [1,1], [1,2.5], [-1,2.5], [-1,1]]
        ax.add_patch(patches.Polygon(home_v, color='white', ec=self.colors['outline'], lw=0.6, zorder=8))
        # 三个垒包 (菱形)
        for x, y in [(self.base_path, self.base_path), (0, self.base_path * 2.0), (-self.base_path, self.base_path)]:
            ax.add_patch(patches.RegularPolygon((x, y), 4, radius=2.2, orientation=0, 
                                               color='white', ec=self.colors['outline'], lw=0.6, zorder=8))

        # 8. 球员渲染 (优化文字居中)
        if players:
            for p in players:
                px, py = p['pos']
                ax.add_patch(patches.Circle((px, py), 4.5, color='#E53935', ec='white', lw=1, zorder=10))
                ax.text(px, py, p['label'], color='white', fontsize=7, ha='center', 
                        va='center', fontweight='bold', zorder=11)

        ax.set_xlim(-130, 130)
        ax.set_ylim(-15, 160)
        ax.axis('off')
        return fig
