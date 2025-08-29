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
import random
from io import StringIO

import svgwrite

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# CONFIGURATION: Easily customize the avatar options here
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

# Color Palettes
VEHICLE_COLORS = [
    "#d25959",
    "#2d5f75",
    "#3f704d",
    "#a36d4f",
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
]
BACKGROUND_COLORS = [
    "#f0f0f0",
    "#d8e2dc",
    "#a0c8d1",
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
]

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# Vehicle Drawing Functions: Each function draws a specific vehicle
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---


def draw_classic_car(dwg, colors):
    """Draws a flat, side-view of a classic car."""
    primary, secondary = colors
    vehicle = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round")

    # Body
    vehicle.add(dwg.path(d="M 15 60 C 5 50, 20 40, 35 40 L 65 40 C 80 40, 95 50, 85 60 Z", fill=primary))
    # Cabin
    vehicle.add(dwg.path(d="M 30 40 L 40 25 L 60 25 L 70 40 Z", fill=secondary))
    # Wheels
    vehicle.add(dwg.circle(center=(30, 60), r=8, fill="#333333"))
    vehicle.add(dwg.circle(center=(70, 60), r=8, fill="#333333"))
    dwg.add(vehicle)


def draw_motorbike(dwg, colors):
    """Draws a flat, side-view of a motorbike."""
    primary, _ = colors
    vehicle = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round")

    # Wheels
    vehicle.add(dwg.circle(center=(25, 65), r=10, fill="none"))
    vehicle.add(dwg.circle(center=(75, 65), r=10, fill="none"))
    # Frame and Body
    vehicle.add(dwg.path(d="M 25 65 L 45 45 L 60 55 L 75 65", fill="none"))
    # Seat
    vehicle.add(dwg.path(d="M 55 40 L 70 40 C 75 40, 75 45, 70 45 L 55 45 Z", fill=primary))
    # Handlebars
    vehicle.add(dwg.path(d="M 45 45 L 35 35 L 30 40", fill="none"))
    dwg.add(vehicle)


def draw_bicycle(dwg, colors):
    """Draws a flat, side-view of a bicycle."""
    primary, _ = colors
    vehicle = dwg.g(
        stroke="#1E1E1E", stroke_width=2, fill="none", stroke_linejoin="round", stroke_linecap="round"
    )

    # Wheels
    vehicle.add(dwg.circle(center=(25, 65), r=12))
    vehicle.add(dwg.circle(center=(75, 65), r=12))
    # Frame
    vehicle.add(dwg.path(d="M 25 65 L 45 40 L 75 65 L 50 65 L 45 40", stroke=primary))
    # Seat and Handlebars
    vehicle.add(dwg.line(start=(45, 40), end=(40, 30)))
    vehicle.add(dwg.line(start=(68, 48), end=(75, 65)))
    vehicle.add(dwg.line(start=(65, 45), end=(70, 45)))  # Seat
    dwg.add(vehicle)


def draw_boat(dwg, colors):
    """Draws a simple sailboat."""
    primary, secondary = colors
    vehicle = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round")

    # Hull
    vehicle.add(dwg.path(d="M 15 60 Q 50 80, 85 60 L 80 50 L 20 50 Z", fill=primary))
    # Mast
    vehicle.add(dwg.line(start=(50, 50), end=(50, 20), stroke_width=3))
    # Sail
    vehicle.add(dwg.path(d="M 53 25 L 75 45 L 53 45 Z", fill=secondary))
    dwg.add(vehicle)


def draw_aeroplane(dwg, colors):
    """Draws a small propeller airplane."""
    primary, secondary = colors
    vehicle = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round")

    # Fuselage
    vehicle.add(dwg.path(d="M 20 50 C 30 45, 70 45, 85 50 C 90 52, 70 55, 20 55 Z", fill=primary))
    # Wing and Tail
    vehicle.add(dwg.path(d="M 40 50 L 60 50 L 70 30 L 50 30 Z", fill=secondary))  # Wing
    vehicle.add(dwg.path(d="M 80 50 L 90 40 L 90 50 Z", fill=secondary))  # Tail
    # Propeller
    vehicle.add(dwg.circle(center=(20, 52), r=3, fill="white"))
    dwg.add(vehicle)


def draw_truck(dwg, colors):
    """Draws a semi-truck cab."""
    primary, _ = colors
    vehicle = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round")

    # Cab and Hood
    vehicle.add(dwg.rect(insert=(20, 35), size=(40, 30), fill=primary))
    vehicle.add(dwg.rect(insert=(60, 45), size=(25, 20), fill=primary))
    # Wheels
    vehicle.add(dwg.circle(center=(30, 65), r=8, fill="#333333"))
    vehicle.add(dwg.circle(center=(75, 65), r=8, fill="#333333"))
    # Smokestack
    vehicle.add(dwg.rect(insert=(25, 25), size=(5, 10), fill="#767478"))
    dwg.add(vehicle)


def draw_helicopter(dwg, colors):
    """Draws a simple helicopter."""
    primary, _ = colors
    vehicle = dwg.g(stroke="#1E1E1E", stroke_width=2, stroke_linejoin="round", stroke_linecap="round")

    # Body
    vehicle.add(dwg.path(d="M 25 45 C 15 55, 25 65, 40 65 L 70 65 C 80 65, 85 55, 75 45 Z", fill=primary))
    # Cockpit
    vehicle.add(dwg.circle(center=(35, 48), r=12, fill="#c9ddff"))
    # Tail
    vehicle.add(dwg.path(d="M 70 55 L 90 50 L 90 55 Z", fill=primary))
    # Rotor
    vehicle.add(dwg.line(start=(20, 25), end=(80, 25), stroke_width=3))
    vehicle.add(dwg.line(start=(50, 40), end=(50, 25)))
    dwg.add(vehicle)


def draw_background(dwg, seed):
    """Draws a simple background."""
    random.seed(seed)
    color = random.choice(BACKGROUND_COLORS)
    dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill=color))


# A dictionary to easily access the drawing functions
VEHICLE_TYPES = {
    "classic_car": draw_classic_car,
    "motorbike": draw_motorbike,
    "bicycle": draw_bicycle,
    "boat": draw_boat,
    "aeroplane": draw_aeroplane,
    "truck": draw_truck,
    "helicopter": draw_helicopter,
}

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# Main Generator Function
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---


def generate_vehicle_avatar(vehicle_type="random", seed=None):
    """
    Generates a complete SVG vehicle avatar and returns it as a string.
    """
    if vehicle_type not in VEHICLE_TYPES and vehicle_type != "random":
        vehicle_type = "random"

    if seed is None:
        seed = random.randint(0, 1000000)

    def part_seed(part_name):
        return int(hashlib.sha256(f"{seed}-{part_name}".encode("utf-8")).hexdigest(), 16)

    if vehicle_type == "random":
        random.seed(part_seed("vehicle_type"))
        vehicle_type = random.choice(list(VEHICLE_TYPES.keys()))

    # Use an in-memory string buffer
    svg_io = StringIO()
    dwg = svgwrite.Drawing(fileobj=svg_io, size=("200px", "200px"), viewBox="0 0 100 100")

    # --- Drawing Order ---
    draw_background(dwg, part_seed("background"))

    draw_func = VEHICLE_TYPES[vehicle_type]

    colors = random.sample(VEHICLE_COLORS, 2)

    draw_func(dwg, colors)

    # Get the SVG content from the buffer
    dwg.save()
    return svg_io.getvalue()
