# -*- coding: utf-8 -*-
"""
Vancouver Flood Risk Assessment

Step 5: Final Flood Susceptibility Model

Author: Uzair

Description:
    This script combines elevation risk, slope risk, and floodplain
    exposure into a final flood susceptibility score using a weighted
    overlay model.

Inputs:
    - data/processed/elevation_risk_5m.tif
    - data/processed/slope_risk_5m.tif
    - data/processed/floodplain_exposure_5m.tif
    - data/processed/local_areas.geojson

Outputs:
    - data/processed/flood_susceptibility_score_5m.tif
    - data/processed/flood_susceptibility_class_5m.tif
    - data/outputs/flood_risk_class_summary.csv

Maps:
    - maps/flood_susceptibility_score_5m_map.png
    - maps/flood_susceptibility_class_5m_map.png
"""


#============================================
# Libraries
#================================================

from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.plot import plotting_extent
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm


# ============================================================
# Paths
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
OUTPUTS_DIR = PROJECT_DIR / "data" / "outputs"
MAPS_DIR = PROJECT_DIR / "maps"

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
MAPS_DIR.mkdir(parents=True, exist_ok=True)

ELEVATION_RISK_PATH = PROCESSED_DIR / "elevation_risk_5m.tif"
SLOPE_RISK_PATH = PROCESSED_DIR / "slope_risk_5m.tif"
FLOODPLAIN_EXPOSURE_PATH = PROCESSED_DIR / "floodplain_exposure_5m.tif"

LOCAL_AREAS_PATH = PROCESSED_DIR / "local_areas.geojson"

FLOOD_SCORE_OUT = PROCESSED_DIR / "flood_susceptibility_score_5m.tif"
FLOOD_CLASS_OUT = PROCESSED_DIR / "flood_susceptibility_class_5m.tif"

FLOOD_SCORE_MAP = MAPS_DIR / "flood_susceptibility_score_5m_map.png"
FLOOD_CLASS_MAP = MAPS_DIR / "flood_susceptibility_class_5m_map.png"

SUMMARY_CSV = OUTPUTS_DIR / "flood_risk_class_summary.csv"

# ============================================================
# Model weights
# ============================================================

ELEVATION_WEIGHT = 0.45
SLOPE_WEIGHT = 0.15
FLOODPLAIN_WEIGHT = 0.40

print("\nFlood Susceptibility Model Weights")
print("-" * 50)
print(f"Elevation risk weight: {ELEVATION_WEIGHT}")
print(f"Slope risk weight: {SLOPE_WEIGHT}")
print(f"Floodplain exposure weight: {FLOODPLAIN_WEIGHT}")

# ============================================================
# Load raster layers
# ============================================================

with rasterio.open(ELEVATION_RISK_PATH) as src:
    elevation_risk = src.read(1).astype("float32")
    meta = src.meta.copy()
    transform = src.transform
    crs = src.crs
    nodata = src.nodata
    height = src.height
    width = src.width
    
with rasterio.open(SLOPE_RISK_PATH) as src:
    slope_risk = src.read(1).astype("float32")
    
with rasterio.open(FLOODPLAIN_EXPOSURE_PATH) as src:
    floodplain_exposure = src.read(1).astype("float32")
    
print("\nRaster layers loaded")
print("-" * 50)
print(f"Raster CRS: {crs}")
print(f"Raster size: {width} x {height}")
print(f"NoData value: {nodata}")

# ============================================================
# Check raster alignment
# ============================================================

if not (
    elevation_risk.shape == slope_risk.shape == floodplain_exposure.shape
):
    raise ValueError("Input raster layers do not have the same shape.")

print("\nRaster alignment check passed.")

# ============================================================
# Create final flood susceptibility score
# ============================================================

valid_mask = (
    (elevation_risk != nodata) &
    (slope_risk != nodata) &
    (floodplain_exposure != nodata)
)

flood_score = np.full(
    elevation_risk.shape,
    nodata,
    dtype="float32"
    )
'''
Example for one pixel:

Elevation risk = 5
Slope risk = 4
Floodplain exposure = 5

Calculation:

(5 × 0.45) + (4 × 0.15) + (5 × 0.40)
= 2.25 + 0.60 + 2.00
= 4.85

So that pixel gets a final flood score of:
4.85

'''
flood_score[valid_mask] = (
    (elevation_risk[valid_mask] * ELEVATION_WEIGHT) +
    (slope_risk[valid_mask] * SLOPE_WEIGHT) +
    (floodplain_exposure[valid_mask] * FLOODPLAIN_WEIGHT)
)

print("\nFlood score statistics")
print("-" * 50)
valid_scores = flood_score[flood_score != nodata]
print(f"Minimum score: {valid_scores.min():.2f}")
print(f"Maximum score: {valid_scores.max():.2f}")
print(f"Mean score: {valid_scores.mean():.2f}")

# ============================================================
# Classify final flood susceptibility
# ============================================================

"""
Final flood susceptibility class logic:

The weighted score ranges from approximately 1 to 5.

Classes:
    1 = Very Low Risk   1.0 to 1.8
    2 = Low Risk        > 1.8 to 2.6
    3 = Moderate Risk   > 2.6 to 3.4
    4 = High Risk       > 3.4 to 4.2
    5 = Very High Risk  > 4.2 to 5.0
"""

flood_class = np.full(
    flood_score.shape,
    nodata,
    dtype="float32"
)

flood_class[(flood_score >= 1.0) & (flood_score <= 1.8) & valid_mask] = 1
flood_class[(flood_score > 1.8) & (flood_score <= 2.6) & valid_mask] = 2
flood_class[(flood_score > 2.6) & (flood_score <= 3.4) & valid_mask] = 3
flood_class[(flood_score > 3.4) & (flood_score <= 4.2) & valid_mask] = 4
flood_class[(flood_score > 4.2) & valid_mask] = 5

# ============================================================
# Save raster outputs
# ============================================================

out_meta = meta.copy()
out_meta.update(
    {
        "driver": "GTiff",
        "dtype": "float32",
        "nodata": nodata,
        "compress": "lzw"
    }
)

with rasterio.open(FLOOD_SCORE_OUT, "w", **out_meta) as dst:
    dst.write(flood_score, 1)

with rasterio.open(FLOOD_CLASS_OUT, "w", **out_meta) as dst:
    dst.write(flood_class, 1)

print("\nFinal raster outputs saved:")
print(FLOOD_SCORE_OUT)
print(FLOOD_CLASS_OUT)

# ============================================================
# Create risk class summary table
# ============================================================

class_names = {
    1: "Very Low Risk",
    2: "Low Risk",
    3: "Moderate Risk",
    4: "High Risk",
    5: "Very High Risk"
}

valid_classes = flood_class[flood_class != nodata]

'''
    This checks how many pixels belong to each final flood class.
    
    Example:
    
    valid_classes = [1, 1, 1, 2, 2, 3, 5]
    
    Then:
    
    unique = [1, 2, 3, 5]
    counts = [3, 2, 1, 1]
    
    Meaning:
    
    Class 1 appears 3 times
    Class 2 appears 2 times
    Class 3 appears 1 time
    Class 5 appears 1 time
'''

unique, counts = np.unique(valid_classes, return_counts=True)

'''
    transform.a is pixel width.
    transform.e is pixel height which is in negative so we use abs.
'''

cell_area_m2 = abs(transform.a * transform.e)
total_area_m2 = counts.sum() * cell_area_m2

summary_records =[]

for risk_class, count in zip(unique, counts):
    area_m2 = count * cell_area_m2
    area_km2 = area_m2 / 1_000_000
    percentage = (area_m2 / total_area_m2) * 100

    summary_records.append(
        {
            "risk_class": int(risk_class),
            "risk_label": class_names[int(risk_class)],
            "cell_count": int(count),
            "area_km2": area_km2,
            "percentage": percentage
        }
    )

summary = pd.DataFrame(summary_records)
summary.to_csv(SUMMARY_CSV, index=False)

print("\nFlood risk class summary")
print("-" * 50)
print(summary)

print("\nSummary CSV saved:")
print(SUMMARY_CSV)

# ============================================================
# Load local areas for map boundaries
# ============================================================

local_areas = gpd.read_file(LOCAL_AREAS_PATH)
local_areas = local_areas.to_crs(crs)

extent = plotting_extent(flood_score, transform=transform)

print("\nGenerating Plots....")
print("-" * 50)

# ============================================================
# Plot 1: Flood Susceptibility Score Map
# ============================================================

score_plot = np.ma.masked_equal(flood_score, nodata)

fig, ax = plt.subplots(figsize=(11, 9))

img = ax.imshow(
    score_plot,
    cmap="RdYlGn_r",
    vmin=1,
    vmax=5,
    extent=extent
)

local_areas.boundary.plot(
    ax=ax,
    color="black",
    linewidth=0.3,
    alpha=0.5
)

cbar = plt.colorbar(
    img,
    ax=ax,
    label="Flood Susceptibility Score",
    fraction=0.035,
    pad=0.02
)

ax.set_title("Vancouver Flood Susceptibility Score")
ax.axis("off")

plt.savefig(FLOOD_SCORE_MAP, dpi=300, bbox_inches="tight")
plt.show()

print(f"\nFlood susceptibility score map saved: {FLOOD_SCORE_MAP}")

# ============================================================
# Plot 2: Final Flood Susceptibility Class Map
# ============================================================

class_plot = np.ma.masked_equal(flood_class, nodata)

risk_cmap = ListedColormap([
    "#006837",  # 1 Very Low
    "#78c679",  # 2 Low
    "#ffffbf",  # 3 Moderate
    "#fdae61",  # 4 High
    "#d73027"   # 5 Very High
])

risk_bounds = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
risk_norm = BoundaryNorm(risk_bounds, risk_cmap.N)

fig, ax = plt.subplots(figsize=(11, 9))

img = ax.imshow(
    class_plot,
    cmap=risk_cmap,
    norm=risk_norm,
    extent=extent
)

local_areas.boundary.plot(
    ax=ax,
    color="black",
    linewidth=0.3,
    alpha=0.5
)

cbar = plt.colorbar(
    img,
    ax=ax,
    ticks=[1, 2, 3, 4, 5],
    label="Flood Susceptibility Class",
    fraction=0.035,
    pad=0.02
)

cbar.ax.set_yticklabels([
    "1 Very Low",
    "2 Low",
    "3 Moderate",
    "4 High",
    "5 Very High"
])

ax.set_title("Vancouver Final Flood Susceptibility Map")
ax.axis("off")

plt.savefig(FLOOD_CLASS_MAP, dpi=300, bbox_inches="tight")
plt.show()

print(f"Final flood susceptibility class map saved: {FLOOD_CLASS_MAP}")









































