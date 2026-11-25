"""Bộ lọc gần giống style mẫu: tô phẳng tóc, tóc màu hồng-cam nhạt với nét tóc đỏ, viền ngoài đỏ dày, nền trong suốt.
Chỉ lọc màu/nét trên ảnh có sẵn, không vẽ lại dáng/mặt/tỉ lệ.
Chạy: python style.py <thư_mục_PNG_trong_suốt> <thư_mục_ra>
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

LINE = np.array([176, 59, 59], np.float32)  # màu nét tóc đo từ ảnh mẫu (ảnh ngủ)
HAIR = np.array([253, 141, 127], np.float32)  # màu tóc đo từ ảnh mẫu (ảnh ngủ)
OUTLINE_PX = 7


def flatten(rgb, colors=64):
    """Tô phẳng: gom về bảng màu (không dither -> không lốm đốm), rồi lọc mode để xoá đốm lẻ, giữ mép sắc."""
    q = rgb.quantize(colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    return q.filter(ImageFilter.ModeFilter(7)).convert("RGB")


def stylize(rgba):
    a = np.asarray(rgba.getchannel("A"))
    src = rgba.convert("RGB")
    flat = np.asarray(flatten(src)).astype(np.float32)
    hsv = np.asarray(src.convert("HSV")).astype(int)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    # tóc: hồng-đỏ (hue < ~17° hoặc > ~345°), đậm và sáng; loại kẹp cam và mắt hổ phách (hue cao hơn)
    hair = ((h <= 12) | (h >= 245)) & (s > 70) & (v > 190) & (a > 128)
    hair = ndimage.binary_opening(hair, iterations=2)  # bỏ đốm lẻ (má hồng, môi...)
    lab, n = ndimage.label(hair)
    if n:  # chỉ giữ các mảng tóc lớn, bỏ nơ đỏ/má/lưỡi nhỏ lẻ
        sizes = ndimage.sum(hair, lab, range(1, n + 1))
        hair = np.isin(lab, np.flatnonzero(sizes > 0.05 * sizes.max()) + 1)
    if hair.any():  # kéo màu tóc về màu tóc mẫu, giữ sáng tối
        flat[hair] += HAIR - np.median(flat[hair], axis=0)
    # chỉ tóc được tô phẳng; mắt, mặt, áo, hiệu ứng giữ màu gốc (gom bảng màu làm mắt ngả đỏ, dơi mất tím)
    flat = np.where(hair[..., None], flat, np.asarray(src).astype(np.float32))
    # mảng tóc tối lớn (ảnh ác quỷ: cả đỉnh đầu đỏ sẫm) -> về tông tóc chuẩn, giữ sáng tối tương đối để còn nét sợi.
    # sừng cùng sắc đỏ nhưng đậm màu hơn (độ bão hòa > ~180) nên không bị đụng; nét tóc mảnh bị loại bởi opening
    # sắc tóc tối là đỏ hồng-tím (hue >= ~335°); tròng mắt nâu hổ phách có hue thấp hơn nên không bị bắt
    dark = ((h <= 2) | (h >= 238)) & (s > 60) & (s < 178) & (v > 60) & (v <= 190) & (a > 128)
    # chỉ mảng thật rộng (> ~16px): viền nét vẽ chibi dày ~8-10px không bị coi là tóc tối
    core = ndimage.binary_opening(dark, iterations=8)
    dark = ndimage.binary_dilation(core, iterations=8) & dark & ~hair
    lab, n = ndimage.label(dark)
    if n:
        touch = np.unique(lab[ndimage.binary_dilation(hair, iterations=3) & dark])
        dark = np.isin(lab, touch[touch > 0])  # chỉ mảng tối dính liền tóc
    if dark.sum() > 0.15 * hair.sum():  # chỉ ảnh có mảng tóc tối lớn (ác quỷ); ảnh khác giữ cách cũ, khỏi đụng lưỡi/má
        # có mảng tóc tối lớn -> đổi TOÀN BỘ tóc (sáng, tối, vùng chuyển tiếp) bằng một cách duy nhất cho liền, không vá:
        # màu = tóc chuẩn x độ sáng tương đối (nén lại), lấy từ ảnh đã tô phẳng để vẫn ra từng bậc màu
        hairish = ((h <= 12) | (h >= 238)) & (s > 40) & (s < 178) & (v > 60) & (a > 128)
        whole = ndimage.binary_closing(hair | dark | (hairish & ndimage.binary_dilation(hair | dark, iterations=6)),
                                       iterations=2) & hairish
        # lỗ nhỏ đỏ đậm lọt trong vùng tóc (độ bão hòa cao như sừng nhưng nằm giữa tóc) -> cũng là tóc;
        # sừng nằm ở mép ngoài, không phải lỗ kín, nên không bị lấp
        holes = ndimage.binary_fill_holes(whole) & ~whole
        hl, hn = ndimage.label(holes)
        if hn:
            hsz = ndimage.sum(holes, hl, range(1, hn + 1))
            reds = ((h <= 12) | (h >= 238)) & (v > 60)
            small = np.isin(hl, np.flatnonzero(hsz < 4000) + 1)
            whole |= small & reds
        vf = np.asarray(flatten(src).convert("HSV"))[..., 2].astype(np.float32)
        rel = np.clip((vf / np.median(vf[whole])) ** 0.5, 0.72, 1.06)  # trung vị cả vùng tóc -> đúng màu chuẩn
        flat[whole] = np.clip(HAIR * rel[whole][:, None], 0, 255)
        hair = hair | whole
    # nét tóc: pixel tối nằm sát/trong tóc -> đỏ như mẫu (lông mi, mắt ở xa tóc nên không bị đụng)
    near_hair = ndimage.binary_dilation(hair, iterations=3)
    line = near_hair & ~hair & (v < 200) & (v > 70) & ((h <= 15) | (h >= 240)) & (s > 90)
    flat[line] = LINE
    solid = a > 128
    ring = ndimage.binary_dilation(solid, iterations=OUTLINE_PX) & ~solid
    flat[ring] = LINE  # viền ngoài dày quanh cả hình như sticker mẫu
    alpha = np.where(ring, 255, a)  # vẫn nền trong suốt, viền nằm trong ảnh
    return Image.fromarray(np.dstack([np.clip(flat, 0, 255), alpha]).astype(np.uint8), "RGBA")


def main(src, dst):
    Path(dst).mkdir(exist_ok=True)
    for f in sorted(Path(src).glob("*.png"), key=lambda p: int(p.stem)):
        stylize(Image.open(f).convert("RGBA")).save(Path(dst) / f.name)
        print(f.name)


if __name__ == "__main__":
    main(*sys.argv[1:3])
