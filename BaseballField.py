import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

class BaseballField:
    def __init__(self, grass_color='#45a247', dirt_color='#b5651d', line_color='white', size=10):
        self.grass_color = grass_color
        self.dirt_color = dirt_color
        self.line_color = line_color
        self.size = size
        
    def draw(self, players=None):
        """
        players: list of dict, e.g., [{'pos': (0,0), 'label': 'C', 'color': 'red'}]
        """
        fig, ax = plt.subplots(figsize=(self.size, self.size))
        ax.set_aspect('equal')
        ax.axis('off')

        # 1. 绘制外野草地（大扇形）
        outfield = patches.Wedge((0, 0), 90, 45, 135, color=self.grass_color, zorder=1)
        ax.add_patch(outfield)

        # 2. 绘制内野泥地（正方形旋转45度）
        # 本垒坐标为 (0,0)
        infield_dirt = patches.RegularPolygon((0, 45), 4, radius=45, orientation=0, 
                                             color=self.dirt_color, zorder=2)
        ax.add_patch(infield_dirt)

        # 3. 绘制内野草地
        infield_grass = patches.RegularPolygon((0, 45), 4, radius=25, orientation=0, 
                                              color=self.grass_color, zorder=3)
        ax.add_patch(infield_grass)

        # 4. 绘制垒位线 (Foul Lines)
        ax.plot([0, 70], [0, 70], color=self.line_color, lw=2, zorder=4)
        ax.plot([0, -70], [0, 70], color=self.line_color, lw=2, zorder=4)

        # 5. 绘制垒包 (Base positions)
        base_size = 3
        # 本垒 (0,0)
        ax.add_patch(patches.Rectangle((-1.5, -1.5), 3, 3, color='white', zorder=5))
        # 一垒 (30, 30)
        ax.add_patch(patches.Rectangle((28.5, 28.5), 3, 3, color='white', zorder=5, angle=45))
        # 二垒 (0, 60)
        ax.add_patch(patches.Rectangle((-1.5, 58.5), 3, 3, color='white', zorder=5, angle=45))
        # 三垒 (-30, 30)
        ax.add_patch(patches.Rectangle((-31.5, 28.5), 3, 3, color='white', zorder=5, angle=45))

        # 6. 绘制球员
        if players:
            for p in players:
                x, y = p['pos']
                ax.scatter(x, y, s=400, color=p.get('color', 'blue'), edgecolors='white', zorder=10)
                ax.text(x, y, p['label'], color='white', ha='center', va='center', 
                        fontweight='bold', zorder=11)

        ax.set_xlim(-100, 100)
        ax.set_ylim(-20, 110)
        return fig

# --- 应用场景示例 ---
# field = BaseballField(grass_color='#2d5a27')
# players = [
#     {'pos': (0, 0), 'label': 'C'},   # 本垒捕手
#     {'pos': (30, 30), 'label': '1B'}, # 一垒手
#     {'pos': (0, 40), 'label': 'P'}    # 投手
# ]
# fig = field.draw(players=players)