"""Đồng bộ tông màu tóc/da giữa các ảnh: đo màu tóc (cam-hồng) từng ảnh, kéo về màu trung vị chung.
Chạy: python match_colors.py <thư_mục_ảnh_gốc> <thư_mục_ra>
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image


def hair_mask(hsv):
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    # tông cam-hồng-đỏ: hue 0..30° hoặc 340..360°, đủ đậm và sáng (loại nền trắng, viền tối)
    warm = (h <= 30) | (h >= 340)
    return warm & (s > 0.35) & (v > 0.45)


def to_hsv(img):
    a = np.asarray(img.convert("HSV"), dtype=np.float32)
    return np.stack([a[..., 0] * 360 / 255, a[..., 1] / 255, a[..., 2] / 255], -1)


def from_hsv(hsv):
    a = np.stack([hsv[..., 0] % 360 * 255 / 360, hsv[..., 1] * 255, hsv[..., 2] * 255], -1)
    return Image.fromarray(np.clip(a, 0, 255).round().astype(np.uint8), "HSV").convert("RGB")


def stats(hsv):
    m = hair_mask(hsv)
    hue = np.where(hsv[..., 0] > 180, hsv[..., 0] - 360, hsv[..., 0])[m]  # để hue liên tục quanh 0°
    return np.median(hue), np.median(hsv[..., 1][m]), np.median(hsv[..., 2][m])


def main(src, dst):
    files = sorted(Path(src).glob("*.webp"), key=lambda p: int(p.stem))
    imgs = {f: to_hsv(Image.open(f)) for f in files}
    st = {f: stats(h) for f, h in imgs.items()}
    th, ts, tv = np.median(np.array(list(st.values())), axis=0)
    print(f"target hair: hue={th:.1f} sat={ts:.2f} val={tv:.2f}")
    Path(dst).mkdir(exist_ok=True)
    for f, hsv in imgs.items():
        h, s, v = st[f]
        # giới hạn nhỏ: ảnh có ánh sáng riêng (ác quỷ, nền tím) bị kéo mạnh sẽ ngả nâu
        dh = np.clip(th - h, -3, 3)
        ks = np.clip(ts / s, 0.93, 1.1)
        kv = 1.0
        # trọng số mềm: pixel càng đúng tông tóc càng được chỉnh nhiều, da nhạt/nền gần như không đổi
        hue = hsv[..., 0]
        dist = np.minimum(np.abs(hue - th % 360), 360 - np.abs(hue - th % 360))
        w = np.clip(1 - dist / 45, 0, 1) * np.clip((hsv[..., 1] - 0.12) / 0.25, 0, 1)
        out = hsv.copy()
        out[..., 0] = hue + dh * w
        out[..., 1] = np.clip(hsv[..., 1] * (1 + (ks - 1) * w), 0, 1)
        out[..., 2] = np.clip(hsv[..., 2] * (1 + (kv - 1) * w), 0, 1)
        from_hsv(out).save(Path(dst) / f"{f.stem}.png")
        print(f"{f.name}: hue {h:+.1f}->{th:+.1f}  sat x{ks:.2f}  val x{kv:.2f}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
