import pandas as pd
import numpy as np
import json
import os
from scipy.spatial import KDTree


def convert_backend_data_to_frontend_format(backend_data_file, output_format="json"):
    """
    Convert data from the backend format to a format suitable for the frontend visualization.

    Args:
        backend_data_file: Path to the backend data file (CSV or JSON)
        output_format: Format to convert to ("json" or "csv")

    Returns:
        Path to the converted file
    """
    # Load the backend data
    if backend_data_file.endswith('.csv'):
        df = pd.read_csv(backend_data_file)
    elif backend_data_file.endswith('.json'):
        with open(backend_data_file, 'r') as f:
            data = json.load(f)
            # Convert to DataFrame if needed
            if isinstance(data, dict):
                # Convert nested structure to flat
                rows = []
                for risk_type, points in data.items():
                    for point in points:
                        row = {
                            'risk_type': risk_type,
                            'latitude': point['coordinates'][1],
                            'longitude': point['coordinates'][0],
                            'risk_level': point['risk_level']
                        }
                        rows.append(row)
                df = pd.DataFrame(rows)
            else:
                df = pd.DataFrame(data)
    else:
        raise ValueError("Unsupported file format. Expected CSV or JSON.")

    # Process data - e.g., ensure consistent column names
    if 'lat' in df.columns and 'latitude' not in df.columns:
        df.rename(columns={'lat': 'latitude'}, inplace=True)
    if 'lon' in df.columns and 'longitude' not in df.columns:
        df.rename(columns={'lon': 'longitude'}, inplace=True)

    # Save in requested format
    if output_format.lower() == 'json':
        output_file = 'processed_risk_data.json'

        # Convert to the format expected by the frontend
        result = {}
        for risk_type in df['risk_type'].unique():
            risk_df = df[df['risk_type'] == risk_type]
            result[risk_type] = [
                {
                    'coordinates': [row['longitude'], row['latitude']],
                    'risk_level': row['risk_level']
                }
                for _, row in risk_df.iterrows()
            ]

        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

    elif output_format.lower() == 'csv':
        output_file = 'processed_risk_data.csv'
        df.to_csv(output_file, index=False)
    else:
        raise ValueError("Unsupported output format. Expected 'json' or 'csv'.")

    return output_file


def interpolate_risk_data(points, values, grid_size=50, polygon=None):
    """
    Interpolate risk data from scattered points to a regular grid.

    Args:
        points: List of [lat, lon] coordinates
        values: Corresponding risk values
        grid_size: Number of points in each dimension of output grid
        polygon: Optional polygon to limit interpolation area

    Returns:
        Dictionary with grid coordinates and interpolated values
    """
    from scipy.interpolate import griddata

    # Extract bounds
    points = np.array(points)
    min_lat, max_lat = points[:, 0].min(), points[:, 0].max()
    min_lon, max_lon = points[:, 1].min(), points[:, 1].max()

    # Create grid
    grid_lat = np.linspace(min_lat, max_lat, grid_size)
    grid_lon = np.linspace(min_lon, max_lon, grid_size)
    grid_lat, grid_lon = np.meshgrid(grid_lat, grid_lon)

    # Flatten for interpolation
    grid_points = np.vstack([grid_lat.flatten(), grid_lon.flatten()]).T

    # Interpolate values
    grid_values = griddata(points, values, grid_points, method='cubic', fill_value=np.nan)

    # Convert back to list format
    result = []
    for i in range(len(grid_points)):
        result.append({
            'coordinates': [float(grid_points[i, 1]), float(grid_points[i, 0])],
            'risk_level': float(grid_values[i]) if not np.isnan(grid_values[i]) else 0.0
        })

    return result


def combine_risk_layers(risk_data, weights=None):
    """
    Combine multiple risk layers into an overall risk assessment

    Args:
        risk_data: Dictionary with risk type as key and list of risk points as value
        weights: Dictionary with risk type as key and weight as value

    Returns:
        List of points with overall risk values
    """
    if weights is None:
        # Default weights
        weights = {
            'flood_risk': 0.3,
            'drought_risk': 0.25,
            'water_source_risk': 0.2,
            'temperature_risk': 0.25
        }

    # Get all unique coordinates
    all_coords = set()
    for risk_type, points in risk_data.items():
        if risk_type != 'overall_risk':  # Skip if already calculated
            for point in points:
                coord_tuple = tuple(point['coordinates'])
                all_coords.add(coord_tuple)

    # For each unique coordinate, calculate weighted average
    overall_risk = []
    for coord in all_coords:
        risk_sum = 0
        weight_sum = 0

        for risk_type, risk_weight in weights.items():
            if risk_type in risk_data:
                # Find closest point for this risk type
                closest_point = None
                min_dist = float('inf')

                for point in risk_data[risk_type]:
                    dist = ((point['coordinates'][0] - coord[0]) ** 2 +
                            (point['coordinates'][1] - coord[1]) ** 2) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
                        closest_point = point

                if closest_point and min_dist < 0.001:  # Only use if close enough
                    risk_sum += closest_point['risk_level'] * risk_weight
                    weight_sum += risk_weight

        if weight_sum > 0:
            overall_risk.append({
                'coordinates': list(coord),
                'risk_level': round(risk_sum / weight_sum, 2)
            })

    return overall_risk


def generate_risk_report(risk_data, polygon_coordinates):
    """
    Generate a textual risk report based on the risk data

    Args:
        risk_data: Dictionary with risk type as key and list of risk points as value
        polygon_coordinates: List of [lon, lat] coordinates defining the area

    Returns:
        Dictionary with risk report information
    """
    report = {
        "summary": {},
        "recommendations": {},
        "detailed_analysis": {}
    }

    # Calculate summary statistics for each risk type
    for risk_type, points in risk_data.items():
        risk_levels = [point['risk_level'] for point in points]
        if not risk_levels:
            continue

        avg_risk = sum(risk_levels) / len(risk_levels)
        max_risk = max(risk_levels)
        min_risk = min(risk_levels)

        report["summary"][risk_type] = {
            "average": round(avg_risk, 2),
            "maximum": round(max_risk, 2),
            "minimum": round(min_risk, 2),
            "category": get_risk_category(avg_risk)
        }

        # Add recommendations based on risk level
        recommendations = []
        if risk_type == "flood_risk":
            if avg_risk > 0.7:
                recommendations = [
                    "Implement comprehensive flood protection systems",
                    "Set up early warning systems for flooding",
                    "Avoid new construction in high-risk areas",
                    "Maintain emergency evacuation plans"
                ]
            elif avg_risk > 0.4:
                recommendations = [
                    "Maintain drainage systems regularly",
                    "Implement flood-resistant building techniques",
                    "Develop basic flood response plans"
                ]
            else:
                recommendations = [
                    "Regular monitoring of water levels",
                    "Basic drainage maintenance"
                ]
        elif risk_type == "drought_risk":
            if avg_risk > 0.7:
                recommendations = [
                    "Implement water conservation measures",
                    "Develop drought-resistant agriculture",
                    "Create water storage solutions",
                    "Set up water recycling systems"
                ]
            elif avg_risk > 0.4:
                recommendations = [
                    "Moderate water usage monitoring",
                    "Plant drought-tolerant vegetation",
                    "Basic rainwater harvesting"
                ]
            else:
                recommendations = [
                    "Regular monitoring of water resources",
                    "Basic water conservation awareness"
                ]
        # Add similar recommendations for other risk types

        report["recommendations"][risk_type] = recommendations

        # Add detailed analysis
        high_risk_areas = len([r for r in risk_levels if r > 0.7])
        medium_risk_areas = len([r for r in risk_levels if 0.4 < r <= 0.7])
        low_risk_areas = len([r for r in risk_levels if r <= 0.4])

        report["detailed_analysis"][risk_type] = {
            "high_risk_percentage": round(high_risk_areas / len(risk_levels) * 100, 1),
            "medium_risk_percentage": round(medium_risk_areas / len(risk_levels) * 100, 1),
            "low_risk_percentage": round(low_risk_areas / len(risk_levels) * 100, 1)
        }

    return report


def get_risk_category(risk_level):
    """Convert numeric risk level to category"""
    if risk_level < 0.2:
        return "foarte scăzut"
    elif risk_level < 0.4:
        return "scăzut"
    elif risk_level < 0.6:
        return "moderat"
    elif risk_level < 0.8:
        return "ridicat"
    else:
        return "foarte ridicat"