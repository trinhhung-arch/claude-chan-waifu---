"""game: đồ ăn đặt xa nhân vật, trong màn hình; mỗi bước đi đúng hướng, không vượt đích."""
import math
import random

from claude_chan.game import far_spot, step

rnd = random.Random(1)
work, mouth = (0, 0, 1920, 1040), (1700, 950)
for _ in range(50):
    x, y = far_spot(work, mouth, rnd)
    assert 60 <= x <= 1860 and 60 <= y <= 980 and math.dist((x, y), mouth) >= 350
assert far_spot((0, 0, 400, 300), (200, 150), rnd)  # màn hình bé: vẫn ra một chỗ
assert step(0, 0, 300, 400, 50) == (30.0, 40.0)
assert step(0, 0, 3, 4, 50) == (3, 4)  # gần hơn một bước: tới luôn, không lố
