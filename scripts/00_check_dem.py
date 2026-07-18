# -*- coding: utf-8 -*-
"""
Vancouver Flood Risk Assessment

Step 0: Check DEM

Author: Uzair

Description:
    This script checks the Vancouver DEM file and creates
    a quick preview map without loading the full-resolution
    raster into memory.

Input:
    - data/raw/dem/vancouver_dem_2013.tif

Output:
    - maps/dem_preview.png
"""

# ============================================================
# Libraries
# ============================================================

from pathlib import Path

import rasterio
import matplotlib.pyplot as plt

# ============================================================
# Paths
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

DEM_PATH = PROJECT_DIR / "data" / "raw" / "dem" / "vancouver_dem_2013.tif"
MAPS_DIR = PROJECT_DIR / "maps"

MAPS_DIR.mkdir(parents=True, exist_ok=True)

DEM_PREVIEW = MAPS_DIR / "dem_preview.png"


# ============================================================
# Check DEM
# ============================================================

if not DEM_PATH.exists():
    raise FileNotFoundError(f"DEM file not found: {DEM_PATH}")

with rasterio.open(DEM_PATH) as src:
    print("DEM loaded successfully")
    print("-" * 50)
    print(f"File: {DEM_PATH.name}")
    print(f"CRS: {src.crs}")
    print(f"Width: {src.width}")
    print(f"Height: {src.height}")
    print(f"Number of bands: {src.count}")
    print(f"Resolution: {src.res}")
    print(f"NoData value: {src.nodata}")
    print(f"Bounds: {src.bounds}")

    # Downsample for preview so we do not load the full 1m DEM
    max_preview_size = 2000
    scale = max(src.width / max_preview_size, src.height / max_preview_size, 1)

    preview_width = int(src.width / scale)
    preview_height = int(src.height / scale)

    dem_preview = src.read(
        1,
        out_shape=(preview_height, preview_width),
        masked=True
    )

    print("-" * 50)
    print("Preview statistics")
    print(f"Minimum elevation: {dem_preview.min():.2f}")
    print(f"Maximum elevation: {dem_preview.max():.2f}")
    print(f"Mean elevation: {dem_preview.mean():.2f}")


# ============================================================
# Plot DEM preview
# ============================================================

plt.figure(figsize=(15, 10))

plt.imshow(dem_preview, cmap="terrain")
plt.colorbar(label="Elevation")
plt.title("Vancouver DEM Preview")
plt.axis("off")

plt.savefig(DEM_PREVIEW, dpi=300, bbox_inches="tight")
plt.show()

print(f"\nDEM preview saved to: {DEM_PREVIEW}")