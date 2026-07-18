# -*- coding: utf-8 -*-
"""
Vancouver Flood Risk Assessment

Step 4: Floodplain Exposure Layer

Author: Uzair

Description:
    This script converts the City of Vancouver Designated Floodplain
    polygon dataset into a raster exposure layer that matches the
    processed 5 m DEM grid.

Inputs:
    - data/processed/vancouver_dem_5m.tif
    - data/processed/designated_floodplain.geojson

Outputs:
    - data/processed/floodplain_exposure_5m.tif

Maps:
    - maps/floodplain_exposure_5m_map.png
"""
# ============================================================
# Libraries
# ============================================================

from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from rasterio.plot import plotting_extent
from matplotlib.patches import Patch


# ============================================================
# Paths
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
MAPS_DIR = PROJECT_DIR / "maps"

MAPS_DIR.mkdir(parents=True, exist_ok=True)

DEM_5M_PATH = PROCESSED_DIR / "vancouver_dem_5m.tif"
FLOODPLAIN_PATH = PROCESSED_DIR / "designated_floodplain.geojson"

FLOODPLAIN_EXPOSURE_OUT = PROCESSED_DIR / "floodplain_exposure_5m.tif"
FLOODPLAIN_EXPOSURE_MAP = MAPS_DIR / "floodplain_exposure_5m_map.png"

#-----------Loading refrence Digital elevation Model 5m-----------

with rasterio.open(DEM_5M_PATH) as src:
    dem = src.read(1)
    meta = src.meta.copy()
    transform = src.transform
    crs = src.crs
    nodata = src.nodata
    height = src.height
    width = src.width

valid_mask = dem != nodata

print("Reference DEM loaded")
print("-" * 50)
print(f"CRS: {crs}")
print(f"Width: {width}")
print(f"Height: {height}")
print(f"NoData: {nodata}")


#---------Loading Flood plain official data from city of Vancouver-------

floodplain = gpd.read_file(FLOODPLAIN_PATH)
floodplain = floodplain.to_crs(crs)

print("\nFloodplain loaded")
print("-" * 50)
print(f"Floodplain features: {len(floodplain)}")
print(f"Columns: {floodplain.columns.tolist()}")

# ============================================================
# Assign exposure values based on floodplain type
# ============================================================

"""
Floodplain exposure logic:

    5 = Very High Exposure
        - Fraser Risk Today 1/500 Storm
        - Still Creek Floodplain
        - Designated Floodplain (FCL 4.6m)

    4 = High Exposure
        - Wave Effect Zone

    1 = Very Low Exposure
        - Areas outside the designated floodplain,
          but still inside Vancouver.

    -9999 = NoData
        - Areas outside the study area.
"""

def get_floodplain_score(name):
    """
    Assign floodplain exposure score based on polygon name.
    """
    if name == "Wave Effect Zone":
        return 4

    elif name in [
        "Fraser Risk Today 1/500 Storm",
        "Still Creek Floodplain",
        "Designated Floodplain (FCL 4.6m)"
    ]:
        return 5

    else:
        return 1


# Start with NoData everywhere
floodplain_exposure = np.full(
    (height, width),
    nodata,
    dtype="float32"
)

# Set all valid Vancouver cells to very low exposure first
floodplain_exposure[valid_mask] = 1


# Rasterize each floodplain polygon separately
# If polygons overlap, keep the highest exposure score.
for _, row in floodplain.iterrows():

    geometry = row.geometry

    if geometry is None or geometry.is_empty:
        continue

    score = get_floodplain_score(row["name"])

    single_polygon_raster = rasterize(
        shapes=[(geometry, score)],
        out_shape=(height, width),
        transform=transform,
        fill=0,
        dtype="float32"
    )

    floodplain_exposure = np.where(
        (single_polygon_raster > floodplain_exposure) & valid_mask,
        single_polygon_raster,
        floodplain_exposure
    )


# ============================================================
# Floodplain area summary
# ============================================================

floodplain["area_m2_calc"] = floodplain.geometry.area
floodplain["area_km2_calc"] = floodplain["area_m2_calc"] / 1_000_000

floodplain_area_summary = (
    floodplain
    .groupby("name")["area_km2_calc"]
    .sum()
    .reset_index()
    .sort_values("area_km2_calc", ascending=False)
)

print("\nFloodplain area summary")
print("-" * 50)
print(floodplain_area_summary)

# ============================================================
# Save raster output
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

with rasterio.open(FLOODPLAIN_EXPOSURE_OUT, "w", **out_meta) as dst:
    dst.write(floodplain_exposure, 1)

print("\nFloodplain exposure raster saved:")
print(FLOODPLAIN_EXPOSURE_OUT)

print("\nGenerating plot...")
print("-" * 50)
# ============================================================
# Plot: Floodplain Exposure Layer - Clean Legend Style
# ============================================================

FLOODPLAIN_EXPOSURE_MAP = MAPS_DIR / "floodplain_exposure_5m_map.png"

# Mask NoData
floodplain_plot = np.ma.masked_equal(floodplain_exposure, nodata)

# Softer custom colours:
# 1 = outside floodplain
# 2 and 3 = unused
# 4 = wave effect zone
# 5 = official floodplain
floodplain_cmap = ListedColormap([
    "#eeeeee",  # 1 Outside floodplain
    "#eeeeee",  # 2 unused
    "#eeeeee",  # 3 unused
    "#4cc9f0",  # 4 Wave Effect Zone
    "#d73027"   # 5 Official floodplain
])

floodplain_bounds = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
floodplain_norm = BoundaryNorm(floodplain_bounds, floodplain_cmap.N)

extent = plotting_extent(floodplain_exposure, transform=transform)

fig, ax = plt.subplots(figsize=(11, 9))

# Raster exposure layer
ax.imshow(
    floodplain_plot,
    cmap=floodplain_cmap,
    norm=floodplain_norm,
    extent=extent
)

# Separate wave zone and official floodplain polygons
wave_zone = floodplain[floodplain["name"] == "Wave Effect Zone"]
official_floodplain = floodplain[floodplain["name"] != "Wave Effect Zone"]

# Add subtle official floodplain boundary
official_floodplain.boundary.plot(
    ax=ax,
    color="#7f0000",
    linewidth=0.4,
    alpha=0.7
)

# Make wave effect zone easier to see without making the map ugly
wave_zone.plot(
    ax=ax,
    facecolor="#4cc9f0",
    edgecolor="#005f73",
    linewidth=1.2,
    alpha=0.95
)

# Legend instead of colorbar
legend_items = [
    Patch(facecolor="#eeeeee", edgecolor="none", label="Outside Floodplain"),
    Patch(facecolor="#d73027", edgecolor="#7f0000", label="Official Floodplain"),
    Patch(facecolor="#4cc9f0", edgecolor="#005f73", label="Wave Effect Zone"),
]

ax.legend(
    handles=legend_items,
    loc="lower left",
    frameon=True,
    title="Floodplain Exposure"
)

ax.set_title("Vancouver Designated Floodplain Exposure Layer")
ax.axis("off")

plt.savefig(FLOODPLAIN_EXPOSURE_MAP, dpi=300, bbox_inches="tight")
plt.show()

print(f"Floodplain exposure map saved: {FLOODPLAIN_EXPOSURE_MAP}")

















