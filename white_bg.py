"""Đổi nền các ảnh sang trắng (ảnh đã có nền trắng thì giữ nguyên).
Chạy: python white_bg.py <thư_mục_vào> <thư_mục_ra>
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
from rembg import new_session, remove


def has_white_bg(img):
    a = np.asarray(img.convert("L"))
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    return np.mean(border > 240) > 0.4  # tóc chạm mép nhiều nên chỉ cần một phần viền là trắng


def sticker_fx(hsv, char_alpha):
    """Hiệu ứng kiểu sticker nằm ngoài nhân vật (mây hơi, dơi): viền trắng/hồng-tím, kín, nhỏ."""
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    white = (v > 235) & (s < 60)
    pink = ((h >= 205) | (h <= 3)) & (s > 60) & (v > 150)  # hồng đến tím (290..360°)
    seed = (white | pink) & (char_alpha < 50)
    filled = ndimage.binary_fill_holes(ndimage.binary_closing(seed, iterations=2))
    lab, n = ndimage.label(filled)
    sizes = ndimage.sum(filled, lab, range(1, n + 1))
    # bỏ chấm nhiễu và mảng sáng lớn (tường, cửa sổ)
    keep = np.flatnonzero((sizes > 400) & (sizes < 0.02 * filled.size)) + 1
    b = 10  # khung cửa sổ sát mép (ảnh nén nên có thể chưa chạm hẳn pixel mép)
    edge = np.unique(np.concatenate([lab[:b].ravel(), lab[-b:].ravel(), lab[:, :b].ravel(), lab[:, -b:].ravel()]))
    return np.isin(lab, np.setdiff1d(keep, edge))


def main(src, dst):
    session = new_session("isnet-anime")
    Path(dst).mkdir(exist_ok=True)
    for f in sorted(Path(src).glob("*.png"), key=lambda p: int(p.stem)):
        img = Image.open(f).convert("RGB")
        if has_white_bg(img):
            out = img
        else:
            cut = remove(img, session=session)
            # rembg bỏ mất dấu "!" và ngôi sao vàng: lấy lại các pixel vàng tươi (kèm viền)
            hsv = np.asarray(img.convert("HSV")).astype(int)
            yellow = (hsv[..., 0] >= 28) & (hsv[..., 0] <= 46) & (hsv[..., 1] > 60) & (hsv[..., 2] > 170)
            mask = yellow | sticker_fx(hsv, np.asarray(cut.getchannel("A")))
            fx = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
            alpha = np.maximum(np.asarray(cut.getchannel("A")), np.asarray(fx))
            cut = img.convert("RGBA")  # rembg xoá màu chỗ alpha=0, nên lấy màu từ ảnh gốc
            cut.putalpha(Image.fromarray(alpha))
            out = Image.new("RGBA", img.size, "white")
            out.alpha_composite(cut)
            out = out.convert("RGB")
        out.save(Path(dst) / f.name)
        print(f.name, "kept" if out is img else "replaced")


if __name__ == "__main__":
    main(*sys.argv[1:3])
