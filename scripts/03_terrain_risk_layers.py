# -*- coding: utf-8 -*-
"""
Vancouver Flood Risk Assessment

Step 3: Terrain Risk Layers

Author: Uzair

Description:
    This script creates terrain-based flood risk layers from the
    processed 5 m Vancouver DEM.

Inputs:
    - data/processed/vancouver_dem_5m.tif

Outputs:
    - data/processed/slope_5m.tif
    - data/processed/elevation_risk_5m.tif
    - data/processed/slope_risk_5m.tif

Maps:
    - maps/slope_5m_map.png
    - maps/elevation_risk_5m_map.png
    - maps/slope_risk_5m_map.png
"""


#--------Libraries----------------

from pathlib import Path

import numpy as np
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm

# ============================================================
# Paths
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
MAPS_DIR = PROJECT_DIR / "maps"

MAPS_DIR.mkdir(parents=True, exist_ok=True)

DEM_5M_PATH = PROCESSED_DIR / "vancouver_dem_5m.tif"

SLOPE_OUT = PROCESSED_DIR / "slope_5m.tif"
ELEVATION_RISK_OUT = PROCESSED_DIR / "elevation_risk_5m.tif"
SLOPE_RISK_OUT = PROCESSED_DIR / "slope_risk_5m.tif"

SLOPE_MAP = MAPS_DIR / "slope_5m_map.png"
ELEVATION_RISK_MAP = MAPS_DIR / "elevation_risk_5m_map.png"
SLOPE_RISK_MAP = MAPS_DIR / "slope_risk_5m_map.png"


#-----------Loading Digital Elevation Model Resampled to 5m--------------


with rasterio.open(DEM_5M_PATH) as src:
    dem = src.read(1)
    meta = src.meta.copy()
    nodata = src.nodata
    transform = src.transform
    x_res = abs(transform.a)
    y_res = abs(transform.e)

print("DEM loaded successfully")
print("-" * 50)
print(f"DEM path: {DEM_5M_PATH}")
print(f"Resolution X: {x_res}")
print(f"Resolution Y: {y_res}")
print(f"NoData value: {nodata}")



#-------Prparing DEM Array---------------------

# Convert DEM to float so we can use NaN for NoData areas
dem_float = dem.astype("float32")

# Mask NoData values
dem_float[dem_float == nodata] = np.nan

valid_mask = ~np.isnan(dem_float)

print("\nDEM statistics")
print("-" * 50)
print(f"Minimum elevation: {np.nanmin(dem_float):.2f}")
print(f"Maximum elevation: {np.nanmax(dem_float):.2f}")
print(f"Mean elevation: {np.nanmean(dem_float):.2f}")

# ============================================================
# Calculate slope
# ============================================================

"""
Slope is calculated from the change in elevation in the X and Y directions.

np.gradient() calculates elevation change between neighbouring cells.

The formula is:

    slope_radians = arctan(sqrt(dz/dx² + dz/dy²))

Then we convert radians to degrees.
"""

dy, dx = np.gradient(dem_float, y_res, x_res)

slope_radians = np.arctan(np.sqrt(dx**2 + dy**2))
slope_degrees = np.degrees(slope_radians)

#Setting no data aeas back to NoData
slope_degrees[~valid_mask] = nodata
slope_degrees = slope_degrees.astype("float32")

print("\ncalculated slope statistics")
print("-" * 50)
print(f"Minimum slope: {np.nanmin(np.where(slope_degrees == nodata, np.nan, slope_degrees)):.2f}°")
print(f"Maximum slope: {np.nanmax(np.where(slope_degrees == nodata, np.nan, slope_degrees)):.2f}°")
print(f"Mean slope: {np.nanmean(np.where(slope_degrees == nodata, np.nan, slope_degrees)):.2f}°")


# ============================================================
# Elevation risk classification
# ============================================================

"""
Elevation risk logic:

Lower elevation = higher flood susceptibility.

Risk classes:
    5 = Very High Risk  <= 5 m
    4 = High Risk       > 5 m and <= 10 m
    3 = Moderate Risk   > 10 m and <= 20 m
    2 = Low Risk        > 20 m and <= 50 m
    1 = Very Low Risk   > 50 m
"""

elevation_risk = np.full(dem_float.shape, nodata, dtype="float32")

elevation_risk[(dem_float <= 5) & valid_mask] = 5
elevation_risk[(dem_float > 5) & (dem_float <= 10) & valid_mask] = 4
elevation_risk[(dem_float > 10) & (dem_float <= 20) & valid_mask] = 3
elevation_risk[(dem_float > 20) & (dem_float <= 50) & valid_mask] = 2
elevation_risk[(dem_float > 50) & valid_mask] = 1

valid_elevation_risk = elevation_risk[elevation_risk != nodata]

print("\nElevation statistics")
print("-" * 50)
print("Valid cells:", valid_elevation_risk.size)
print("Unique risk values:", np.unique(valid_elevation_risk))

# ============================================================
# Slope risk classification
# ============================================================

"""
Slope risk logic:

Flat terrain = higher flood susceptibility.

Updated risk classes:
    5 = Very High Risk  <= 1 degree
    4 = High Risk       > 1 and <= 3 degrees
    3 = Moderate Risk   > 3 and <= 5 degrees
    2 = Low Risk        > 5 and <= 10 degrees
    1 = Very Low Risk   > 10 degrees
"""

slope_valid = np.where(slope_degrees == nodata, np.nan, slope_degrees)

slope_risk = np.full(slope_degrees.shape, nodata, dtype="float32")

slope_risk[(slope_valid <= 1) & valid_mask] = 5
slope_risk[(slope_valid > 1) & (slope_valid <= 3) & valid_mask] = 4
slope_risk[(slope_valid > 3) & (slope_valid <= 5) & valid_mask] = 3
slope_risk[(slope_valid > 5) & (slope_valid <= 10) & valid_mask] = 2
slope_risk[(slope_valid > 10) & valid_mask] = 1

valid_slope_risk = slope_risk[slope_risk != nodata]

print("\nSlope statistics")
print("-" * 50)
print("Valid cells:", valid_slope_risk.size)
print("Unique risk values:", np.unique(valid_slope_risk))

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

with rasterio.open(SLOPE_OUT, "w", **out_meta) as dst:
    dst.write(slope_degrees, 1)

with rasterio.open(ELEVATION_RISK_OUT, "w", **out_meta) as dst:
    dst.write(elevation_risk, 1)

with rasterio.open(SLOPE_RISK_OUT, "w", **out_meta) as dst:
    dst.write(slope_risk, 1)

print("\nRaster outputs saved:")
print("-" * 50)
print(SLOPE_OUT)
print(ELEVATION_RISK_OUT)
print(SLOPE_RISK_OUT)


print("\nGenerating plots...")
print("-" * 50)

# ============================================================
# Plot 1: Slope Map
# ============================================================

slope_plot = np.ma.masked_equal(slope_degrees, nodata)

plt.figure(figsize=(15, 10))

img = plt.imshow(
    slope_plot,
    cmap="viridis",
    vmin=0,
    vmax=15
)

plt.colorbar(img, label="Slope (degrees)")
plt.title("Vancouver Slope Map from 5 meters Digital Elevation Model")
plt.axis("off")

plt.savefig(SLOPE_MAP, dpi=300, bbox_inches="tight")
plt.show()

print(f"Slope map saved: {SLOPE_MAP}")

# ============================================================
# Plot 2: Elevation Risk Layer
# ============================================================

elevation_risk_plot = np.ma.masked_equal(elevation_risk, nodata)

risk_cmap = plt.get_cmap("RdYlGn_r", 5)
risk_bounds = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
risk_norm = BoundaryNorm(risk_bounds, risk_cmap.N)

plt.figure(figsize=(15, 10))

img = plt.imshow(
    elevation_risk_plot,
    cmap=risk_cmap,
    norm=risk_norm
)

cbar = plt.colorbar(
    img,
    ticks=[1, 2, 3, 4, 5],
    label="Risk Score"
)

cbar.ax.set_yticklabels([
    "1 Very Low",
    "2 Low",
    "3 Moderate",
    "4 High",
    "5 Very High"
])

plt.title("Vancouver Elevation Risk Layer")
plt.axis("off")

plt.savefig(ELEVATION_RISK_MAP, dpi=300, bbox_inches="tight")
plt.show()

print(f"Elevation risk map saved: {ELEVATION_RISK_MAP}")

# ============================================================
# Plot 3: Slope Risk Layer
# ============================================================

slope_risk_plot = np.ma.masked_equal(slope_risk, nodata)

risk_cmap = plt.get_cmap("RdYlGn_r", 5)
risk_bounds = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
risk_norm = BoundaryNorm(risk_bounds, risk_cmap.N)

plt.figure(figsize=(15, 10))

img = plt.imshow(
    slope_risk_plot,
    cmap=risk_cmap,
    norm=risk_norm
)

cbar = plt.colorbar(
    img,
    ticks=[1, 2, 3, 4, 5],
    label="Risk Score"
)

cbar.ax.set_yticklabels([
    "1 Very Low",
    "2 Low",
    "3 Moderate",
    "4 High",
    "5 Very High"
])

plt.title("Vancouver Slope Risk Layer")
plt.axis("off")

plt.savefig(SLOPE_RISK_MAP, dpi=300, bbox_inches="tight")
plt.show()

print(f"Slope risk map saved: {SLOPE_RISK_MAP}")

# ============================================================
# Risk class summary
# ============================================================

def print_risk_summary(risk_array, layer_name):
    """
    Print count of cells in each risk class.
    """
    valid = risk_array[risk_array != nodata]

    unique, counts = np.unique(valid, return_counts=True)

    print(f"\n{layer_name} risk class counts")
    print("-" * 50)

    for risk_class, count in zip(unique, counts):
        print(f"Class {int(risk_class)}: {count:,} cells")


print_risk_summary(elevation_risk, "Elevation")
print_risk_summary(slope_risk, "Slope")











