"""Tách nền trắng thành trong suốt (PNG RGBA), giữ cả hiệu ứng rời (dấu !, sao, mây hơi, dơi...).
Chạy: python transparent.py <thư_mục_vào> <thư_mục_ra>
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage
from rembg import new_session, remove


def white_bg(rgb, a_char):
    """Nền = vùng gần trắng nối mép ảnh, cộng các lỗ trắng kín sát nhân vật mà rembg bảo không phải nhân vật
    (lòng vòng tóc ahoge, khe giữa lọn tóc). Lòng mây hơi/dấu ∩ nằm rời nhân vật nên vẫn giữ."""
    near_white = rgb.min(axis=2) > 225
    lab, n = ndimage.label(near_white)
    ids = np.arange(1, n + 1)
    edge = np.isin(ids, np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    inside = ndimage.mean(a_char, lab, ids)  # rembg: vùng này có thuộc nhân vật không
    # tỉ lệ viền quanh mỗi vùng là nhân vật (lan nhãn sang pixel kề bên)
    # dải ~12px: mép rembg mờ dần vài px nên dải hẹp chỉ chạm phần mờ, không tới tóc đặc
    spill = ndimage.grey_dilation(lab, size=25) * ~near_white
    hug = np.nan_to_num(ndimage.mean(a_char > 0.5, spill, ids))
    is_bg = edge | ((inside < 0.5) & (hug > 0.5))
    return np.isin(lab, ids[is_bg])


def main(src, dst):
    session = new_session("isnet-anime")
    Path(dst).mkdir(exist_ok=True)
    for f in sorted(Path(src).glob("*.png")):
        img = Image.open(f).convert("RGB")
        rgb = np.asarray(img).astype(np.float32)
        a_char = np.asarray(remove(img, session=session).getchannel("A")).astype(np.float32) / 255
        # nền = trắng nối mép, trừ chỗ rembg bảo là nhân vật (áo trắng, khăn voan chạm mép ảnh)
        bg = white_bg(rgb, a_char) & (a_char < 0.5)
        # giữ mọi thứ còn lại: nhân vật + hiệu ứng rời rembg bỏ sót (dấu !, sao, dơi, gối...)
        a = (~bg).astype(np.float32)
        # dải mép 3px: độ trong theo mức pha trắng, so với màu đậm nhất ngay bên trong
        band = ~bg & ndimage.binary_dilation(bg, iterations=3)
        mn = rgb.min(axis=2)
        darkest = ndimage.minimum_filter(mn, size=7)
        a[band] = np.clip((255 - mn) / np.maximum(255 - darkest, 1), 0, 1)[band]
        # bỏ các mảnh rời chỉ mảnh 1-2px (vòng xám sót quanh sao/mây hơi từ lần đổi nền trước)
        solid = a > 0.1
        lab, n = ndimage.label(solid)
        thick = np.unique(lab[ndimage.binary_opening(solid, iterations=2)])
        a[~np.isin(lab, thick[thick > 0])] = 0
        # khử viền trắng: ảnh vốn ghép trên nền trắng nên C = a*F + (1-a)*255  =>  F = (C - (1-a)*255) / a
        safe = np.maximum(a, 1e-3)[..., None]
        fg = np.where(a[..., None] > 0.02, (rgb - (1 - a[..., None]) * 255) / safe, rgb)
        out = np.dstack([np.clip(fg, 0, 255), a * 255]).round().astype(np.uint8)
        Image.fromarray(out, "RGBA").save(Path(dst) / f.name)
        print(f.name)


if __name__ == "__main__":
    main(*sys.argv[1:3])
