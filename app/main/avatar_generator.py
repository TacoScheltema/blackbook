# This file is part of Blackbook.
#
# Blackbook is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Blackbook is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Blackbook.  If not, see <https://www.gnu.org/licenses/>.
import hashlib
import math
import random

import svgwrite

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# CONFIGURATION
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

# Color Palettes
VEHICLE_COLORS = [
    "#6c5b7b",
    "#ffcc00",
    "#767478",
    "#e57373",
    "#f06292",
    "#ba68c8",
    "#9575cd",
    "#7986cb",
    "#64b5f6",
    "#4fc3f7",
    "#4dd0e1",
    "#4db6ac",
    "#81c784",
    "#aed581",
    "#dce775",
    "#fff176",
    "#ffd54f",
    "#ffb74d",
    "#ff8a65",
    "#a1887f",
    "#e0e0e0",
    "#90a4ae",
    "#f67280",
    "#c06c84",
    "#355c7d",
    "#99b898",
    "#feceab",
    "#ff847c",
    "#e84a5f",
    "#2a363b",
]
PLANT_COLORS = ["#4b7f52", "#d96666", "#f2b5a7", "#a7d9b4", "#f2d6b5", "#f2a07b", "#8c6a5d"]
ANIMAL_COLORS = ["#a36d4f", "#f2d6b5", "#6c5b7b", "#d9a46f", "#8c6a5d", "#f2a07b", "#767478"]
BACKGROUND_COLORS = [
    "#e0e4f2",
    "#c9ddff",
    "#f2e2d8",
    "#eeeeee",
    "#e0f2f1",
    "#d1c4e9",
    "#c5cae9",
    "#bbdefb",
    "#b3e5fc",
    "#b2ebf2",
    "#b2dfdb",
    "#c8e6c9",
    "#dcedc8",
    "#f0f4c3",
    "#fff9c4",
    "#ffecb3",
    "#ffe0b2",
    "#ffccbc",
    "#d7ccc8",
    "#cfd8dc",
    "#f8b195",
    "#f67280",
    "#c06c84",
    "#ece5ce",
    "#d5e1df",
    "#e3d3e4",
]

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# Drawing Functions
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---


def draw_background(dwg, seed):
    """Draws a simple background color."""
    random.seed(seed)
    color = random.choice(BACKGROUND_COLORS)
    dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill=color))


# --- Vehicle Drawing Functions ---
def draw_classic_car(dwg, colors):
    """Draws a flat, side-view of a classic car."""
    primary, secondary = colors
    vehicle = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round")
    vehicle.add(dwg.path(d="M 15 60 C 5 50, 20 40, 35 40 L 65 40 C 80 40, 95 50, 85 60 Z", fill=primary))
    vehicle.add(dwg.path(d="M 30 40 L 40 25 L 60 25 L 70 40 Z", fill=secondary))
    vehicle.add(dwg.circle(center=(30, 60), r=8, fill="#333333"))
    vehicle.add(dwg.circle(center=(70, 60), r=8, fill="#333333"))
    dwg.add(vehicle)


def draw_motorbike(dwg, colors):
    """Draws a flat, side-view of a motorbike."""
    primary, _ = colors
    vehicle = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round")
    vehicle.add(dwg.circle(center=(25, 65), r=10, fill="none"))
    vehicle.add(dwg.circle(center=(75, 65), r=10, fill="none"))
    vehicle.add(dwg.path(d="M 25 65 L 45 45 L 60 55 L 75 65", fill="none"))
    vehicle.add(dwg.path(d="M 55 40 L 70 40 C 75 40, 75 45, 70 45 L 55 45 Z", fill=primary))
    vehicle.add(dwg.path(d="M 45 45 L 35 35 L 30 40", fill="none"))
    dwg.add(vehicle)


def draw_bicycle(dwg, colors):
    """Draws a stylized bicycle from an SVG path."""
    primary, secondary = colors
    bicycle = dwg.g(stroke_width=0)
    bicycle.add(
        dwg.path(
            d="M510.2 505m-475.7 0a475.7 475.7 0 1 0 951.4 0 475.7 475.7 0 1 0-951.4 0Z",
            fill=secondary,
        )
    )
    bicycle.add(
        dwg.path(
            d="M177.6 755m-157.9 0a157.9 157.9 0 1 0 315.8 0 157.9 157.9 0 1 0-315.8 0Z",
            fill=primary,
        )
    )
    bicycle.add(
        dwg.path(
            d=(
                "M177.6 922.9C85 922.9 9.7 847.6 9.7 755S85 587.2 177.6 587.2 345.5 662.5 345.5 755s-75.3 "
                "167.9-167.9 167.9z m0-315.7C96 607.2 29.7 673.5 29.7 755S96 902.9 177.6 902.9 325.5 "
                "836.6 325.5 755s-66.4-147.8-147.9-147.8z"
            ),
            fill="#1E1E1E",
        )
    )
    bicycle.add(
        dwg.path(
            d="M842.9 755m-157.9 0a157.9 157.9 0 1 0 315.8 0 157.9 157.9 0 1 0-315.8 0Z",
            fill=primary,
        )
    )
    bicycle.add(
        dwg.path(
            d=(
                "M842.9 922.9C750.3 922.9 675 847.6 675 755s75.3-167.9 167.9-167.9 167.9 75.3 167.9 "
                "167.9-75.3 167.9-167.9 167.9z m0-315.7C761.3 607.2 695 673.5 695 755s66.3 147.9 147.9 "
                "147.9S990.8 836.6 990.8 755s-66.4-147.8-147.9-147.8zM177.6 765c-1.2 "
                "0-2.4-0.2-3.6-0.7-5.1-2-7.7-7.8 -5.7-12.9l190.1-489.7c1.5-3.8 5.2-6.4 "
                "9.3-6.4h101c5.5 0 10 4.5 10 10s-4.5 10-10 10h-94.2L186.9 758.7c-1.5 3.9-5.3 6.3-9.3 6.3z"
            ),
            fill="#1E1E1E",
        )
    )
    bicycle.add(
        dwg.path(
            d=(
                "M603.4 791.7c-2.3 0-4.5-0.8-6.3-2.3L266.3 517.9c-3.3-2.7-4.5-7.1-3.1-11.1s5.2-6.6 "
                "9.4-6.6h386.9c3.2 0 6.1 1.5 8 4L850.9 749c2.1 2.9 2.6 6.7 1.2 10-1.4 3.3-4.5 5.6-8.1 "
                "6l-239.5 26.7h-1.1zM300.6 520.2l305.9 251.1L824.4 747 654.5 520.2H300.6zM783 "
                "398.9H581c-5.5 0-10-4.5-10-10s4.5-10 10-10h202c5.5 0 10 4.5 10 10s-4.5 10-10 10z"
            ),
            fill="#1E1E1E",
        )
    )
    bicycle.add(
        dwg.path(
            d=(
                "M603.4 791.7c-0.7 0-1.4-0.1-2-0.2-5.4-1.1-8.9-6.4-7.8-11.8l81.6-392.9c1.1-5.4 6.4-8.9 "
                "11.8-7.8 5.4 1.1 8.9 6.4 7.8 11.8l-81.6 392.9c-1 4.8-5.1 8-9.8 8z"
            ),
            fill="#1E1E1E",
        )
    )
    dwg.add(bicycle)


def draw_boat(dwg, colors):
    """Draws a simple sailboat."""
    primary, secondary = colors
    vehicle = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round")
    vehicle.add(dwg.path(d="M 15 60 Q 50 80, 85 60 L 80 50 L 20 50 Z", fill=primary))
    vehicle.add(dwg.line(start=(50, 50), end=(50, 20), stroke_width=3))
    vehicle.add(dwg.path(d="M 53 25 L 75 45 L 53 45 Z", fill=secondary))
    dwg.add(vehicle)


def draw_aeroplane(dwg, colors):
    """Draws a small propeller airplane."""
    primary, secondary = colors
    vehicle = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round")
    vehicle.add(dwg.path(d="M 20 50 C 30 45, 70 45, 85 50 C 90 52, 70 55, 20 55 Z", fill=primary))
    vehicle.add(dwg.path(d="M 40 50 L 60 50 L 70 30 L 50 30 Z", fill=secondary))
    vehicle.add(dwg.path(d="M 80 50 L 90 40 L 90 50 Z", fill=secondary))
    vehicle.add(dwg.circle(center=(20, 52), r=3, fill="white"))
    dwg.add(vehicle)


def draw_truck(dwg, colors):
    """Draws a semi-truck cab."""
    primary, _ = colors
    vehicle = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round")
    vehicle.add(dwg.rect(insert=(20, 35), size=(40, 30), fill=primary))
    vehicle.add(dwg.rect(insert=(60, 45), size=(25, 20), fill=primary))
    vehicle.add(dwg.circle(center=(30, 65), r=8, fill="#333333"))
    vehicle.add(dwg.circle(center=(75, 65), r=8, fill="#333333"))
    vehicle.add(dwg.rect(insert=(25, 25), size=(5, 10), fill="#767478"))
    dwg.add(vehicle)


def draw_helicopter(dwg, colors):
    """Draws a simple helicopter."""
    primary, _ = colors
    vehicle = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round")
    vehicle.add(dwg.path(d="M 25 45 C 15 55, 25 65, 40 65 L 70 65 C 80 65, 85 55, 75 45 Z", fill=primary))
    vehicle.add(dwg.circle(center=(35, 48), r=12, fill="#c9ddff"))
    vehicle.add(dwg.path(d="M 70 55 L 90 50 L 90 55 Z", fill=primary))
    vehicle.add(dwg.line(start=(20, 25), end=(80, 25), stroke_width=3))
    vehicle.add(dwg.line(start=(50, 40), end=(50, 25)))
    dwg.add(vehicle)


# --- Plant Drawing Functions ---
def draw_tree(dwg, colors):
    primary, secondary = colors
    plant = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round")
    plant.add(dwg.rect(insert=(45, 60), size=(10, 20), fill=primary))
    plant.add(dwg.circle(center=(50, 45), r=20, fill=secondary))
    dwg.add(plant)


def draw_flower(dwg, colors):
    primary, secondary = colors
    plant = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round")
    plant.add(dwg.line(start=(50, 80), end=(50, 50), stroke=secondary, stroke_width=3))
    plant.add(dwg.circle(center=(50, 40), r=10, fill=primary))
    for i in range(6):
        angle = math.radians(i * 60)
        plant.add(
            dwg.circle(center=(50 + 10 * math.cos(angle), 40 + 10 * math.sin(angle)), r=5, fill=secondary)
        )
    dwg.add(plant)


def draw_cactus(dwg, colors):
    primary, _ = colors
    plant = dwg.g(
        stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round", fill=primary
    )
    plant.add(dwg.path(d="M 50 80 V 40 C 50 30 60 30 60 40 V 55"))
    plant.add(dwg.path(d="M 50 60 C 40 60 40 50 50 50"))
    dwg.add(plant)


def draw_rose(dwg, colors):
    primary, secondary = colors
    plant = dwg.g(stroke="#1E1E1E", stroke_width=2)
    plant.add(dwg.line(start=(50, 80), end=(50, 40), stroke=secondary, stroke_width=3))
    plant.add(dwg.path(d="M50,40 C 40,20 60,20 50,40", fill=primary))
    plant.add(dwg.path(d="M45,35 C 35,25 55,25 45,35", fill=primary))
    plant.add(dwg.path(d="M55,35 C 45,25 65,25 55,35", fill=primary))
    dwg.add(plant)


def draw_orchid(dwg, colors):
    primary, secondary = colors
    plant = dwg.g(stroke="#1E1E1E", stroke_width=2, fill="none")
    plant.add(dwg.path(d="M50,80 C 40,60 60,60 50,40", stroke=secondary))
    plant.add(dwg.path(d="M50,40 C 40,30 60,30 50,40", fill=primary))
    plant.add(dwg.path(d="M50,40 C 45,50 55,50 50,40", fill=primary))
    dwg.add(plant)


# --- Animal Drawing Functions ---
def draw_bird(dwg, colors):
    primary, _ = colors
    animal = dwg.g(stroke="#1E1E1E", stroke_width=2, fill=primary, stroke_linejoin="round")
    animal.add(dwg.path(d="M 30 50 C 20 40, 40 30, 50 40 C 70 50, 60 70, 40 65 Z"))
    animal.add(dwg.circle(center=(55, 38), r=5))
    animal.add(dwg.path(d="M 58 37 L 65 35", fill="none", stroke_width=1))
    dwg.add(animal)


def draw_kangaroo(dwg, colors):
    primary, _ = colors
    animal = dwg.g(stroke="#1E1E1E", stroke_width=2, fill=primary, stroke_linejoin="round")
    animal.add(dwg.path(d="M 40 80 L 50 40 L 60 45 L 70 80 Z"))
    animal.add(dwg.path(d="M 50 40 L 55 25 L 60 30 Z"))
    animal.add(dwg.path(d="M 40 80 L 20 75 L 40 70 Z"))
    dwg.add(animal)


def draw_lion(dwg, colors):
    primary, secondary = colors
    animal = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round")
    animal.add(dwg.circle(center=(50, 50), r=20, fill=primary))
    animal.add(dwg.circle(center=(50, 50), r=25, fill=secondary, opacity=0.5))
    animal.add(dwg.circle(center=(45, 45), r=3, fill="black"))
    animal.add(dwg.circle(center=(55, 45), r=3, fill="black"))
    dwg.add(animal)


def draw_chicken(dwg, colors):
    primary, _ = colors
    animal = dwg.g(stroke="#1E1E1E", stroke_width=2, fill=primary, stroke_linejoin="round")
    animal.add(dwg.circle(center=(50, 60), r=15))
    animal.add(dwg.circle(center=(60, 45), r=8))
    animal.add(dwg.path(d="M 65 43 L 70 45 L 65 47 Z", fill="orange"))
    dwg.add(animal)


def draw_duck(dwg, colors):
    primary, _ = colors
    animal = dwg.g(stroke="#1E1E1E", stroke_width=2, fill=primary, stroke_linejoin="round")
    animal.add(dwg.path(d="M 30 60 C 20 50, 40 40, 55 45 L 65 60 Z"))
    animal.add(dwg.circle(center=(60, 40), r=7))
    animal.add(dwg.path(d="M 65 38 L 75 40 L 65 42 Z", fill="orange"))
    dwg.add(animal)


def draw_dog(dwg, colors):
    primary, _ = colors
    animal = dwg.g(stroke="#1E1E1E", stroke_width=2, fill=primary, stroke_linejoin="round")
    animal.add(dwg.rect(insert=(30, 50), size=(40, 20)))
    animal.add(dwg.circle(center=(60, 40), r=10))
    animal.add(dwg.path(d="M 55 30 L 50 20 L 60 25 Z"))
    animal.add(dwg.path(d="M 65 30 L 70 20 L 60 25 Z"))
    dwg.add(animal)


def draw_cat(dwg, colors):
    primary, _ = colors
    animal = dwg.g(stroke="#1E1E1E", stroke_width=2, fill=primary, stroke_linejoin="round")
    animal.add(dwg.circle(center=(50, 55), r=15))
    animal.add(dwg.circle(center=(50, 40), r=10))
    animal.add(dwg.path(d="M 45 30 L 40 25 L 50 35 Z"))
    animal.add(dwg.path(d="M 55 30 L 60 25 L 50 35 Z"))
    dwg.add(animal)


def draw_mouse(dwg, colors):
    primary, _ = colors
    animal = dwg.g(stroke="#1E1E1E", stroke_width=2, fill=primary, stroke_linejoin="round")
    animal.add(dwg.path(d="M 40 60 C 30 50, 50 40, 60 50 C 70 60, 50 70, 40 60 Z"))
    animal.add(dwg.circle(center=(60, 50), r=5))
    animal.add(dwg.circle(center=(55, 45), r=4, fill="pink"))
    animal.add(dwg.circle(center=(65, 45), r=4, fill="pink"))
    dwg.add(animal)


# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# Dictionaries to categorize avatar types
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

VEHICLE_TYPES = {
    "classic_car": draw_classic_car,
    "motorbike": draw_motorbike,
    "bicycle": draw_bicycle,
    "boat": draw_boat,
    "aeroplane": draw_aeroplane,
    "truck": draw_truck,
    "helicopter": draw_helicopter,
}

PLANT_TYPES = {
    "tree": draw_tree,
    "flower": draw_flower,
    "cactus": draw_cactus,
    "rose": draw_rose,
    "orchid": draw_orchid,
}

ANIMAL_TYPES = {
    "bird": draw_bird,
    "kangaroo": draw_kangaroo,
    "lion": draw_lion,
    "chicken": draw_chicken,
    "duck": draw_duck,
    "dog": draw_dog,
    "cat": draw_cat,
    "mouse": draw_mouse,
}

AVATAR_CATEGORIES = {
    "vehicles": (VEHICLE_TYPES, VEHICLE_COLORS),
    "plants": (PLANT_TYPES, PLANT_COLORS),
    "animals": (ANIMAL_TYPES, ANIMAL_COLORS),
}

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# Main Generator Function
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---


def generate_avatar(seed=None, theme="all"):
    """
    Generates a complete SVG avatar.

    Args:
        seed (str or int): An optional seed for the random number generator
                           to create deterministic avatars.
        theme (str): The category of avatar to generate. Can be 'vehicles',
                     'plants', 'animals', or 'all'.
    """
    if seed is None:
        seed = random.randint(0, 1000000)

    def part_seed(part_name):
        return int(hashlib.sha256(f"{seed}-{part_name}".encode("utf-8")).hexdigest(), 16)

    # Choose a category
    if theme in AVATAR_CATEGORIES:
        categories_to_use = [theme]
    else:
        categories_to_use = list(AVATAR_CATEGORIES.keys())

    random.seed(part_seed("category"))
    chosen_category = random.choice(categories_to_use)
    avatar_types, color_palette = AVATAR_CATEGORIES[chosen_category]

    # Choose a specific avatar type from the category
    random.seed(part_seed("type"))
    chosen_type = random.choice(list(avatar_types.keys()))
    draw_func = avatar_types[chosen_type]

    # Choose two distinct colors for the avatar
    random.seed(part_seed("colors"))
    colors = random.sample(color_palette, 2)

    # Setup the SVG canvas (in-memory)
    dwg = svgwrite.Drawing(size=("200px", "200px"), viewBox="0 0 100 100")

    # --- Drawing Order ---
    draw_background(dwg, part_seed("background"))
    draw_func(dwg, colors)

    return dwg.tostring()
