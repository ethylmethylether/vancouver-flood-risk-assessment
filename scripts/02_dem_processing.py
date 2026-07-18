# -*- coding: utf-8 -*-
"""
Vancouver Flood Risk Assessment

Step 2: DEM Processing

Author: Uzair

Description:
    This script resamples the original 0.5 m Vancouver DEM
    to 5 m resolution and clips it to the Vancouver study area.

Inputs:
    - data/raw/dem/vancouver_dem_2013.tif
    - data/processed/study_area.geojson

Outputs:
    - data/processed/vancouver_dem_5m.tif
    - maps/vancouver_dem_5m_preview.png
"""

from pathlib import Path
from math import ceil

import geopandas as gpd
import rasterio
from rasterio.enums import Resampling
from rasterio.mask import mask
from rasterio.vrt import WarpedVRT
from rasterio.transform import from_origin

import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# Paths
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

RAW_DEM = PROJECT_DIR / "data" / "raw" / "dem" / "vancouver_dem_2013.tif"
STUDY_AREA_PATH = PROJECT_DIR / "data" / "processed" / "study_area.geojson"

PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
MAPS_DIR = PROJECT_DIR / "maps"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MAPS_DIR.mkdir(parents=True, exist_ok=True)

DEM_5M_OUT = PROCESSED_DIR / "vancouver_dem_5m.tif"
DEM_5M_PREVIEW = MAPS_DIR / "vancouver_dem_5m_preview.png"


# ============================================================
# Settings
# ============================================================

TARGET_RESOLUTION = 5  # meters


#------Loading Study Area----------------------

study_area  = gpd.read_file(STUDY_AREA_PATH)

# ============================================================
# Resample and clip DEM
# ============================================================

with rasterio.open(RAW_DEM) as src:
    print("Original DEM")
    print("-" * 50)
    print(f"CRS: {src.crs}")
    print(f"Resolution: {src.res}")
    print(f"Width: {src.width}")
    print(f"Height: {src.height}")
    print(f"NoData: {src.nodata}")
    
    print("\nResampling Digital Elevation Model to 5m....")
    print("-" * 50)
    study_area = study_area.to_crs(src.crs)
    
    left, bottom, right, top = src.bounds
    
    new_width = ceil((right - left) / TARGET_RESOLUTION)
    new_height = ceil((top - bottom) / TARGET_RESOLUTION)

    new_transform = from_origin(
        left,
        top,
        TARGET_RESOLUTION,
        TARGET_RESOLUTION
    )

    with WarpedVRT(
        src,
        crs=src.crs,
        transform=new_transform,
        width = new_width,
        height = new_height,
        resampling = Resampling.bilinear,
        src_nodata = src.nodata,
        nodata=src.nodata
    )as vrt:
        
        dem_data, dem_transform = mask(
            vrt,
            study_area.geometry,
            crop=True,
            filled=True,
            nodata=src.nodata
        )
        
        dem_meta = vrt.meta.copy()
        
        dem_meta.update(
            {
                "driver": "GTiff",
                "height": dem_data.shape[1],
                "width": dem_data.shape[2],
                "transform": dem_transform,
                "nodata": src.nodata,
                "dtype": "float32",
                "compress": "lzw"
                
                }
            )

# Convert to float32 before saving
dem_data = dem_data.astype("float32")

with rasterio.open(DEM_5M_OUT, "w", **dem_meta) as dst:
    dst.write(dem_data)

print("\n5 m DEM saved:")
print(DEM_5M_OUT)

# ============================================================
# Statistics
# ============================================================

nodata = dem_meta["nodata"]
dem_array = dem_data[0]

dem_masked = np.ma.masked_equal(dem_array, nodata)

print("\nResampled DEM statistics")
print("-" * 50)
print(f"Resolution: {TARGET_RESOLUTION} m")
print(f"Width: {dem_array.shape[1]}")
print(f"Height: {dem_array.shape[0]}")
print(f"Minimum elevation: {dem_masked.min():.2f}")
print(f"Maximum elevation: {dem_masked.max():.2f}")
print(f"Mean elevation: {dem_masked.mean():.2f}")

print("\nGenerating plot...")
print("-" * 50)
# ============================================================
# Plot preview
# ============================================================

plt.figure(figsize=(15, 10))

plt.imshow(dem_masked, cmap="terrain")
plt.colorbar(label="Elevation (m)")
plt.title("Vancouver DEM Resampled to 5 m")
plt.axis("off")

plt.savefig(DEM_5M_PREVIEW, dpi=300, bbox_inches="tight")
plt.show()

print("\nPreview map saved:")
print(DEM_5M_PREVIEW)
































