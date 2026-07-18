# -*- coding: utf-8 -*-
"""
Vancouver Flood Risk Assessment

Step 1: Prepare Vector Data

Author: Uzair

Description:
    This script prepares the main vector datasets for the flood
    susceptibility and floodplain exposure analysis.

Important:
    The study area is created from the Local Area Boundary dataset
    because it provides proper neighbourhood polygons covering Vancouver.

Inputs:
    - data/raw/boundary/local_area_boundary.geojson
    - data/raw/floodplain/designated_floodplain.geojson
    - data/raw/dem/vancouver_dem_2013.tif

Outputs:
    - data/processed/study_area.geojson
    - data/processed/local_areas.geojson
    - data/processed/designated_floodplain.geojson
"""

from pathlib import Path

import geopandas as gpd
import rasterio


# ============================================================
# Paths
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

DEM_PATH = RAW_DIR / "dem" / "vancouver_dem_2013.tif"

LOCAL_AREAS_PATH = RAW_DIR / "boundary" / "local_area_boundary.geojson"
FLOODPLAIN_PATH = RAW_DIR / "floodplain" / "designated_floodplain.geojson"

STUDY_AREA_OUT = PROCESSED_DIR / "study_area.geojson"
LOCAL_AREAS_OUT = PROCESSED_DIR / "local_areas.geojson"
FLOODPLAIN_OUT = PROCESSED_DIR / "designated_floodplain.geojson"


# ============================================================
# Helper function
# ============================================================

def clean_geometries(gdf):
    """
    Fix invalid geometries and remove empty geometries.
    """
    gdf = gdf.copy()

    gdf = gdf[gdf.geometry.notnull()]
    gdf = gdf[~gdf.geometry.is_empty]

    # buffer(0) is a common fix for minor invalid polygon issues
    gdf["geometry"] = gdf.geometry.buffer(0)

    return gdf


# ============================================================
# Get DEM CRS
# ============================================================

with rasterio.open(DEM_PATH) as src:
    analysis_crs = src.crs

print("Analysis CRS from DEM:")
print(analysis_crs)


# ============================================================
# Load datasets
# ============================================================

local_areas = gpd.read_file(LOCAL_AREAS_PATH)
floodplain = gpd.read_file(FLOODPLAIN_PATH)

print("\nOriginal CRS:")
print(f"Local areas: {local_areas.crs}")
print(f"Floodplain: {floodplain.crs}")

print("\nOriginal feature counts:")
print(f"Local areas: {len(local_areas)}")
print(f"Floodplain: {len(floodplain)}")


# ============================================================
# Reproject to DEM CRS
# ============================================================

local_areas = local_areas.to_crs(analysis_crs)
floodplain = floodplain.to_crs(analysis_crs)


# ============================================================
# Clean geometries
# ============================================================

local_areas = clean_geometries(local_areas)
floodplain = clean_geometries(floodplain)


# ============================================================
# Create study area from local areas
# ============================================================

study_area = local_areas.dissolve()
study_area = study_area.reset_index(drop=True)

# Clip floodplain to Vancouver study area
floodplain = gpd.clip(floodplain, study_area)


# ============================================================
# Save processed files
# ============================================================

study_area.to_file(STUDY_AREA_OUT, driver="GeoJSON")
local_areas.to_file(LOCAL_AREAS_OUT, driver="GeoJSON")
floodplain.to_file(FLOODPLAIN_OUT, driver="GeoJSON")

print("\nProcessed files saved:")
print(STUDY_AREA_OUT)
print(LOCAL_AREAS_OUT)
print(FLOODPLAIN_OUT)


# ============================================================
# Summary
# ============================================================

print("\nSummary:")
print(f"Study area features: {len(study_area)}")
print(f"Local area features: {len(local_areas)}")
print(f"Floodplain features: {len(floodplain)}")

print("\nStudy area columns:")
print(study_area.columns.tolist())

print("\nLocal area columns:")
print(local_areas.columns.tolist())

print("\nFloodplain columns:")
print(floodplain.columns.tolist())