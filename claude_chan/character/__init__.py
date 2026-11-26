"""Cửa sổ nhân vật trên màn hình (Character) và đường chuyển động theo cảm xúc (motion)."""
from ._art import food_image, overlay
from ._character import Character
from ._motion import motion, rubbed, spun

__all__ = ["Character", "food_image", "motion", "overlay", "rubbed", "spun"]
