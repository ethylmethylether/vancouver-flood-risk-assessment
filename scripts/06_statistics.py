# -*- coding: utf-8 -*-
"""
Vancouver Flood Risk Assessment

Step 6: Flood Risk Statistics

Author: Uzair

Description:
    This script calculates neighbourhood-level flood risk statistics
    using the final flood susceptibility score and class rasters.

Inputs:
    - data/processed/flood_susceptibility_score_5m.tif
    - data/processed/flood_susceptibility_class_5m.tif
    - data/processed/local_areas.geojson

Outputs:
    - data/outputs/neighbourhood_flood_risk_summary.csv
    - data/outputs/neighbourhood_risk_class_area.csv
    - data/outputs/local_areas_flood_risk_summary.geojson

Figures:
    - figures/top_10_high_very_high_risk_neighbourhoods.png
    - figures/average_flood_score_by_neighbourhood.png
    - figures/citywide_flood_risk_distribution.png
"""

# ============================================================
# Libraries
# ============================================================

from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
import matplotlib.pyplot as plt


# ============================================================
# Paths
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
OUTPUTS_DIR = PROJECT_DIR / "data" / "outputs"
FIGURES_DIR = PROJECT_DIR / "figures"

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

FLOOD_SCORE_PATH = PROCESSED_DIR / "flood_susceptibility_score_5m.tif"
FLOOD_CLASS_PATH = PROCESSED_DIR / "flood_susceptibility_class_5m.tif"
LOCAL_AREAS_PATH = PROCESSED_DIR / "local_areas.geojson"

SUMMARY_CSV = OUTPUTS_DIR / "neighbourhood_flood_risk_summary.csv"
CLASS_AREA_CSV = OUTPUTS_DIR / "neighbourhood_risk_class_area.csv"
SUMMARY_GEOJSON = OUTPUTS_DIR / "local_areas_flood_risk_summary.geojson"

TOP_10_CHART = FIGURES_DIR / "top_10_high_very_high_risk_neighbourhoods.png"
AVG_SCORE_CHART = FIGURES_DIR / "average_flood_score_by_neighbourhood.png"
CITYWIDE_DISTRIBUTION_CHART = FIGURES_DIR / "citywide_flood_risk_distribution.png"


# ============================================================
# Class labels
# ============================================================

class_names = {
    1: "Very Low Risk",
    2: "Low Risk",
    3: "Moderate Risk",
    4: "High Risk",
    5: "Very High Risk"
}


# ============================================================
# Load local areas
# ============================================================

local_areas = gpd.read_file(LOCAL_AREAS_PATH)

print("Local areas loaded")
print("-" * 50)
print(f"Number of local areas: {len(local_areas)}")
print(f"Columns: {local_areas.columns.tolist()}")


# ============================================================
# Open rasters
# ============================================================

with rasterio.open(FLOOD_SCORE_PATH) as score_src, rasterio.open(FLOOD_CLASS_PATH) as class_src:

    nodata = score_src.nodata
    raster_crs = score_src.crs
    transform = score_src.transform

    cell_area_m2 = abs(transform.a * transform.e)
    cell_area_km2 = cell_area_m2 / 1_000_000

    print("\nRaster information")
    print("-" * 50)
    print(f"CRS: {raster_crs}")
    print(f"NoData value: {nodata}")
    print(f"Cell area: {cell_area_m2:.2f} m²")

    # Make sure local areas use same CRS as raster
    local_areas = local_areas.to_crs(raster_crs)

    summary_records = []
    class_area_records = []
    
    # ========================================================
    # Loop through each neighbourhood
    # ========================================================

    for _, row in local_areas.iterrows():

        neighbourhood = row["name"]
        geometry = [row.geometry]

        print(f"Processing: {neighbourhood}")

        # Clip score raster to neighbourhood
        score_clip, _ = mask(
            score_src,
            geometry,
            crop=True,
            filled=True,
            nodata=nodata
        )

        # Clip class raster to neighbourhood
        class_clip, _ = mask(
            class_src,
            geometry,
            crop=True,
            filled=True,
            nodata=nodata
        )

        score_array = score_clip[0]
        class_array = class_clip[0]

        valid_score = score_array[score_array != nodata]
        valid_class = class_array[class_array != nodata]

        if valid_score.size == 0:
            continue

        # Basic area
        total_cells = valid_class.size
        total_area_km2 = total_cells * cell_area_km2

        # Average and maximum score
        avg_score = float(np.mean(valid_score))
        max_score = float(np.max(valid_score))

        # Risk class counts
        unique_classes, class_counts = np.unique(valid_class, return_counts=True)

        class_count_dict = {
            int(risk_class): int(count)
            for risk_class, count in zip(unique_classes, class_counts)
        }

        # Dominant class
        dominant_class = max(class_count_dict, key=class_count_dict.get)
        dominant_label = class_names[dominant_class]

        # High + Very High area
        high_cells = class_count_dict.get(4, 0)
        very_high_cells = class_count_dict.get(5, 0)

        high_area_km2 = high_cells * cell_area_km2
        very_high_area_km2 = very_high_cells * cell_area_km2
        high_very_high_area_km2 = high_area_km2 + very_high_area_km2

        high_very_high_pct = (
            high_very_high_area_km2 / total_area_km2
        ) * 100

        # Save one summary row per neighbourhood
        summary_records.append(
            {
                "name": neighbourhood,
                "total_area_km2": total_area_km2,
                "average_flood_score": avg_score,
                "max_flood_score": max_score,
                "dominant_risk_class": dominant_class,
                "dominant_risk_label": dominant_label,
                "high_risk_area_km2": high_area_km2,
                "very_high_risk_area_km2": very_high_area_km2,
                "high_very_high_area_km2": high_very_high_area_km2,
                "high_very_high_pct": high_very_high_pct,
            }
        )

        # Save detailed class area rows
        for risk_class in range(1, 6):

            cell_count = class_count_dict.get(risk_class, 0)
            area_km2 = cell_count * cell_area_km2
            percentage = (area_km2 / total_area_km2) * 100

            class_area_records.append(
                {
                    "name": neighbourhood,
                    "risk_class": risk_class,
                    "risk_label": class_names[risk_class],
                    "cell_count": cell_count,
                    "area_km2": area_km2,
                    "percentage": percentage,
                }
            )
            
# ============================================================
# Create DataFrames
# ============================================================

summary_df = pd.DataFrame(summary_records)
class_area_df = pd.DataFrame(class_area_records)

summary_df = summary_df.sort_values(
    "high_very_high_pct",
    ascending=False
)

class_area_df = class_area_df.sort_values(
    ["name", "risk_class"]
)

# ============================================================
# Save CSV outputs
# ============================================================

summary_df.to_csv(SUMMARY_CSV, index=False)
class_area_df.to_csv(CLASS_AREA_CSV, index=False)

print("\nNeighbourhood summary saved:")
print(SUMMARY_CSV)

print("\nRisk class area table saved:")
print(CLASS_AREA_CSV)

# ============================================================
# Save GeoJSON with summary joined to local areas
# ============================================================

local_areas_summary = local_areas.merge(
    summary_df,
    on="name",
    how="left"
)

local_areas_summary.to_file(SUMMARY_GEOJSON, driver="GeoJSON")

print("\nLocal areas summary GeoJSON saved:")
print(SUMMARY_GEOJSON)

# ============================================================
# Print top neighbourhoods
# ============================================================

print("\nTop 10 neighbourhoods by High + Very High Risk percentage")
print("-" * 50)
print(
    summary_df[
        [
            "name",
            "average_flood_score",
            "high_very_high_area_km2",
            "high_very_high_pct",
            "dominant_risk_label"
        ]
    ].head(10)
)


# ============================================================
# Figure 1: Top 10 High + Very High Risk Percentage
# ============================================================

top_10 = summary_df.head(10).sort_values(
    "high_very_high_pct",
    ascending=True
)

plt.figure(figsize=(10, 7))

plt.barh(
    top_10["name"],
    top_10["high_very_high_pct"]
)

plt.xlabel("High + Very High Risk Area (%)")
plt.ylabel("Neighbourhood")
plt.title("Top 10 Vancouver Local Areas by High and Very High Flood Risk")
plt.grid(axis="x", alpha=0.3)

plt.savefig(TOP_10_CHART, dpi=300, bbox_inches="tight")
plt.show()

print(f"\nTop 10 chart saved: {TOP_10_CHART}")


# ============================================================
# Figure 2: Average Flood Score by Neighbourhood
# ============================================================

avg_score_plot = summary_df.sort_values(
    "average_flood_score",
    ascending=True
)

plt.figure(figsize=(10, 9))

plt.barh(
    avg_score_plot["name"],
    avg_score_plot["average_flood_score"]
)

plt.xlabel("Average Flood Susceptibility Score")
plt.ylabel("Neighbourhood")
plt.title("Average Flood Susceptibility Score by Vancouver Local Area")
plt.grid(axis="x", alpha=0.3)

plt.savefig(AVG_SCORE_CHART, dpi=300, bbox_inches="tight")
plt.show()

print(f"Average score chart saved: {AVG_SCORE_CHART}")


# ============================================================
# Figure 3: Citywide Risk Distribution
# ============================================================

citywide_distribution = (
    class_area_df
    .groupby(["risk_class", "risk_label"])["area_km2"]
    .sum()
    .reset_index()
)

plt.figure(figsize=(9, 6))

plt.bar(
    citywide_distribution["risk_label"],
    citywide_distribution["area_km2"]
)

plt.xlabel("Flood Risk Class")
plt.ylabel("Area (km²)")
plt.title("Citywide Flood Risk Distribution")
plt.xticks(rotation=30, ha="right")
plt.grid(axis="y", alpha=0.3)

plt.savefig(CITYWIDE_DISTRIBUTION_CHART, dpi=300, bbox_inches="tight")
plt.show()

print(f"Citywide distribution chart saved: {CITYWIDE_DISTRIBUTION_CHART}")


print("\nStatistics step completed successfully.")




































