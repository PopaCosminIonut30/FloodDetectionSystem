import json
import random
import numpy as np
import pandas as pd
from scipy.interpolate import griddata
import os


def point_in_polygon(x, y, polygon):
    """Determine if a point is inside a polygon using ray casting algorithm"""
    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def generate_realistic_risk_data(polygon_coordinates, grid_size=30):
    """
    Generate more realistic risk data for a polygon area using interpolation.
    Returns detailed risk data for visualization.
    """
    # Flip coordinates to [lat, lon] format for easier processing
    polygon = [(coord[1], coord[0]) for coord in polygon_coordinates]

    # Calculate polygon bounds
    lats = [p[0] for p in polygon]
    lons = [p[1] for p in polygon]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    # Add some buffer
    lat_buffer = (max_lat - min_lat) * 0.1
    lon_buffer = (max_lon - min_lon) * 0.1
    min_lat -= lat_buffer
    max_lat += lat_buffer
    min_lon -= lon_buffer
    max_lon += lon_buffer

    # Create a grid of points
    lat_grid = np.linspace(min_lat, max_lat, grid_size)
    lon_grid = np.linspace(min_lon, max_lon, grid_size)
    grid_points = []

    for lat in lat_grid:
        for lon in lon_grid:
            if point_in_polygon(lon, lat, polygon_coordinates):
                grid_points.append((lat, lon))

    # Generate seed points for interpolation
    num_seed_points = max(10, len(grid_points) // 10)
    seed_indices = random.sample(range(len(grid_points)), min(num_seed_points, len(grid_points)))
    seed_points = [grid_points[i] for i in seed_indices]

    # Generate risk values for seed points
    flood_seed_values = [random.uniform(0, 1) for _ in seed_points]
    drought_seed_values = [random.uniform(0, 1) for _ in seed_points]
    water_source_seed_values = [random.uniform(0, 1) for _ in seed_points]
    temperature_seed_values = [random.uniform(0, 1) for _ in seed_points]

    # Add spatial correlation (nearby points have similar risks)
    risk_types = {
        "flood_risk": [],
        "drought_risk": [],
        "water_source_risk": [],
        "temperature_risk": [],
    }

    # Convert seed points to arrays for interpolation
    seed_points_array = np.array(seed_points)

    # Interpolate risk values for all grid points
    for lat, lon in grid_points:
        point = np.array([lat, lon])

        try:
            # Interpolate each risk type
            flood_risk = griddata(seed_points_array, flood_seed_values, point, method='cubic')
            drought_risk = griddata(seed_points_array, drought_seed_values, point, method='cubic')
            water_risk = griddata(seed_points_array, water_source_seed_values, point, method='cubic')
            temp_risk = griddata(seed_points_array, temperature_seed_values, point, method='cubic')

            # Handle NaN values (can happen with cubic interpolation)
            flood_risk = max(0, min(1, float(flood_risk))) if not np.isnan(flood_risk) else random.random()
            drought_risk = max(0, min(1, float(drought_risk))) if not np.isnan(drought_risk) else random.random()
            water_risk = max(0, min(1, float(water_risk))) if not np.isnan(water_risk) else random.random()
            temp_risk = max(0, min(1, float(temp_risk))) if not np.isnan(temp_risk) else random.random()

            # Add some noise to make it look more realistic
            flood_risk = max(0, min(1, flood_risk + random.uniform(-0.05, 0.05)))
            drought_risk = max(0, min(1, drought_risk + random.uniform(-0.05, 0.05)))
            water_risk = max(0, min(1, water_risk + random.uniform(-0.05, 0.05)))
            temp_risk = max(0, min(1, temp_risk + random.uniform(-0.05, 0.05)))

            # Round to 2 decimal places
            flood_risk = round(flood_risk, 2)
            drought_risk = round(drought_risk, 2)
            water_risk = round(water_risk, 2)
            temp_risk = round(temp_risk, 2)

            # Add to respective risk arrays
            risk_types["flood_risk"].append({
                "coordinates": [lon, lat],
                "risk_level": flood_risk
            })

            risk_types["drought_risk"].append({
                "coordinates": [lon, lat],
                "risk_level": drought_risk
            })

            risk_types["water_source_risk"].append({
                "coordinates": [lon, lat],
                "risk_level": water_risk
            })

            risk_types["temperature_risk"].append({
                "coordinates": [lon, lat],
                "risk_level": temp_risk
            })

        except Exception as e:
            print(f"Error interpolating point {lat}, {lon}: {e}")
            # Fall back to random values if interpolation fails
            risk_types["flood_risk"].append({
                "coordinates": [lon, lat],
                "risk_level": round(random.random(), 2)
            })
            risk_types["drought_risk"].append({
                "coordinates": [lon, lat],
                "risk_level": round(random.random(), 2)
            })
            risk_types["water_source_risk"].append({
                "coordinates": [lon, lat],
                "risk_level": round(random.random(), 2)
            })
            risk_types["temperature_risk"].append({
                "coordinates": [lon, lat],
                "risk_level": round(random.random(), 2)
            })

    # Calculate overall risk as weighted average
    risk_types["overall_risk"] = []
    for i in range(len(risk_types["flood_risk"])):
        overall_risk = (
                risk_types["flood_risk"][i]["risk_level"] * 0.3 +
                risk_types["drought_risk"][i]["risk_level"] * 0.25 +
                risk_types["water_source_risk"][i]["risk_level"] * 0.2 +
                risk_types["temperature_risk"][i]["risk_level"] * 0.25
        )

        risk_types["overall_risk"].append({
            "coordinates": risk_types["flood_risk"][i]["coordinates"],
            "risk_level": round(overall_risk, 2)
        })

    return risk_types


def save_risk_data_to_files(risk_data):
    """Save risk data to various file formats that could be used by the frontend"""

    # Save as JSON
    with open("risk_data.json", "w") as f:
        json.dump(risk_data, f, indent=2)

    # Save as CSV files (one for each risk type)
    for risk_type, points in risk_data.items():
        df = pd.DataFrame([
            {
                "latitude": point["coordinates"][1],
                "longitude": point["coordinates"][0],
                "risk_level": point["risk_level"]
            }
            for point in points
        ])
        df.to_csv(f"{risk_type}.csv", index=False)

    # Save as a single CSV file with all risk types
    all_data = []
    for i in range(len(risk_data["flood_risk"])):
        coords = risk_data["flood_risk"][i]["coordinates"]
        row = {
            "latitude": coords[1],
            "longitude": coords[0],
            "flood_risk": risk_data["flood_risk"][i]["risk_level"],
            "drought_risk": risk_data["drought_risk"][i]["risk_level"],
            "water_source_risk": risk_data["water_source_risk"][i]["risk_level"],
            "temperature_risk": risk_data["temperature_risk"][i]["risk_level"],
            "overall_risk": risk_data["overall_risk"][i]["risk_level"]
        }
        all_data.append(row)

    pd.DataFrame(all_data).to_csv("all_risk_data.csv", index=False)

    print(f"Risk data saved to files: risk_data.json, all_risk_data.csv, and individual CSV files")

# Example usage
# polygon_coordinates = [[lon1, lat1], [lon2, lat2], ...]
# risk_data = generate_realistic_risk_data(polygon_coordinates)
# save_risk_data_to_files(risk_data)