# -*- coding: utf-8 -*-
"""
Vancouver Flood Risk Assessment

Step 7: Neighbourhood Maps and Model Methodology Figure

Author: Uzair

Description:
    This script creates neighbourhood-level flood risk maps using
    the local_areas_flood_risk_summary.geojson output from Step 6,
    and also creates a methodology figure showing the weighted
    overlay model used for flood susceptibility.

Input:
    - data/outputs/local_areas_flood_risk_summary.geojson

Outputs:
    - maps/neighbourhood_high_very_high_risk_pct_map.png
    - maps/neighbourhood_average_flood_score_map.png
    - figures/flood_susceptibility_methodology.png
"""

# ============================================================
# Libraries
# ============================================================

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


# ============================================================
# Paths
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

OUTPUTS_DIR = PROJECT_DIR / "data" / "outputs"
MAPS_DIR = PROJECT_DIR / "maps"
FIGURES_DIR = PROJECT_DIR / "figures"

MAPS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_GEOJSON = OUTPUTS_DIR / "local_areas_flood_risk_summary.geojson"

MAP1 = MAPS_DIR / "neighbourhood_high_very_high_risk_pct_map.png"
MAP2 = MAPS_DIR / "neighbourhood_average_flood_score_map.png"
METHOD_FIGURE = FIGURES_DIR / "flood_susceptibility_methodology.png"


# ============================================================
# Load neighbourhood summary layer
# ============================================================

gdf = gpd.read_file(SUMMARY_GEOJSON)

print("Neighbourhood summary layer loaded")
print("-" * 50)
print(f"Number of features: {len(gdf)}")
print(f"Columns: {gdf.columns.tolist()}")


# ============================================================
# Create class labels for High + Very High Risk %
# ============================================================

bins = [0, 2, 5, 10, 20, 100]
labels = [
    "0–2%",
    ">2–5%",
    ">5–10%",
    ">10–20%",
    ">20%"
]

gdf["risk_pct_class"] = pd.cut(
    gdf["high_very_high_pct"],
    bins=bins,
    labels=labels,
    include_lowest=True
)

print("\nRisk percentage classes:")
print(gdf[["name", "high_very_high_pct", "risk_pct_class"]].head())


# ============================================================
# Map 1: High + Very High Risk Percentage
# ============================================================

fig, ax = plt.subplots(figsize=(12, 10))

gdf.plot(
    column="risk_pct_class",
    ax=ax,
    legend=True,
    cmap="OrRd",
    edgecolor="black",
    linewidth=0.5,
    legend_kwds={
        "title": "High + Very High\nRisk Area (%)",
        "loc": "lower left"
    }
)

for _, row in gdf.iterrows():
    point = row.geometry.representative_point()
    ax.text(
        point.x,
        point.y,
        row["name"],
        fontsize=7,
        ha="center"
    )

ax.set_title(
    "Vancouver Neighbourhoods by High and Very High Flood Risk Area",
    fontsize=16
)
ax.axis("off")

plt.savefig(MAP1, dpi=300, bbox_inches="tight")
plt.show()

print(f"\nMap saved: {MAP1}")


# ============================================================
# Map 2: Average Flood Susceptibility Score
# ============================================================

fig, ax = plt.subplots(figsize=(12, 10))

gdf.plot(
    column="average_flood_score",
    ax=ax,
    legend=True,
    cmap="YlGnBu",
    edgecolor="black",
    linewidth=0.5,
    legend_kwds={
        "label": "Average Flood Susceptibility Score",
        "shrink": 0.7
    }
)

for _, row in gdf.iterrows():
    point = row.geometry.representative_point()
    ax.text(
        point.x,
        point.y,
        row["name"],
        fontsize=7,
        ha="center"
    )

ax.set_title(
    "Average Flood Susceptibility Score by Vancouver Neighbourhood",
    fontsize=16
)
ax.axis("off")

plt.savefig(MAP2, dpi=300, bbox_inches="tight")
plt.show()

print(f"Map saved: {MAP2}")


# ============================================================
# Helper functions for methodology figure
# ============================================================

def add_box(ax, x, y, width, height, text, facecolor, edgecolor="black"):
    box = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        linewidth=1.2,
        edgecolor=edgecolor,
        facecolor=facecolor
    )
    ax.add_patch(box)

    ax.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=11,
        wrap=True
    )


def add_arrow(ax, start, end):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="->",
        mutation_scale=18,
        linewidth=1.5,
        color="black"
    )
    ax.add_patch(arrow)


# ============================================================
# Methodology Figure
# ============================================================

fig, ax = plt.subplots(figsize=(14, 8))

ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

ax.text(
    0.5,
    0.94,
    "Flood Susceptibility Model Methodology",
    ha="center",
    va="center",
    fontsize=20,
    fontweight="bold"
)

ax.text(
    0.5,
    0.89,
    "Weighted overlay model combining terrain risk and official floodplain exposure",
    ha="center",
    va="center",
    fontsize=12
)

# Input boxes
add_box(
    ax,
    0.05,
    0.62,
    0.25,
    0.16,
    "Elevation Risk\nWeight: 45%\n\nLower elevation = higher flood\n susceptibility",
    "#d9f0a3"
)

add_box(
    ax,
    0.05,
    0.40,
    0.25,
    0.16,
    "Floodplain Exposure\nWeight: 40%\n\nOfficial floodplain zones = higher \nexposure",
    "#fdae61"
)

add_box(
    ax,
    0.05,
    0.18,
    0.25,
    0.16,
    "Slope Risk\nWeight: 15%\n\nFlatter terrain = higher flood \nsusceptibility",
    "#abd9e9"
)

# Formula box
formula_text = (
    "Final Flood Susceptibility Score\n\n"
    "Score =\n"
    "(0.45 × Elevation Risk)\n"
    "+ (0.40 × Floodplain Exposure)\n"
    "+ (0.15 × Slope Risk)"
)

add_box(
    ax,
    0.40,
    0.36,
    0.28,
    0.28,
    formula_text,
    "#f7f7f7"
)

# Output box
output_text = (
    "Final Risk Classes\n\n"
    "1 = Very Low Risk\n"
    "2 = Low Risk\n"
    "3 = Moderate Risk\n"
    "4 = High Risk\n"
    "5 = Very High Risk"
)

add_box(
    ax,
    0.75,
    0.36,
    0.20,
    0.28,
    output_text,
    "#fee08b"
)

# Arrows
add_arrow(ax, (0.30, 0.70), (0.40, 0.52))
add_arrow(ax, (0.30, 0.48), (0.40, 0.50))
add_arrow(ax, (0.30, 0.26), (0.40, 0.48))
add_arrow(ax, (0.68, 0.50), (0.75, 0.50))

# Bottom note
ax.text(
    0.5,
    0.07,
    "All input layers were standardized to a common 1–5 risk scale before weighted overlay.",
    ha="center",
    va="center",
    fontsize=11,
    style="italic"
)

plt.savefig(METHOD_FIGURE, dpi=300, bbox_inches="tight")
plt.show()

print(f"Methodology figure saved: {METHOD_FIGURE}")