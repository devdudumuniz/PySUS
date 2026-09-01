"""GeoJSON export for geographic columns.

Exports DataFrames with lat/lon columns to GeoJSON FeatureCollection.

Usage::

    from pysus.api.export.geojson import to_geojson

    to_geojson(df, "output.geojson", lat_col="LATITUDE", lon_col="LONGITUDE")
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class GeoOptions:
    """Options for GeoJSON export."""

    lat_col: str = "LATITUDE"
    lon_col: str = "LONGITUDE"
    geocode_col: str | None = None
    properties: list[str] | None = None


def to_geojson(
    df: pd.DataFrame,
    path: str | Path,
    options: GeoOptions | str | None = None,
    *args: Any,
    **kwargs: Any,
) -> Path:
    """Export DataFrame to GeoJSON with Point geometries.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    path : str or Path
        Output file path.
    options : GeoOptions, optional
        Options for export including column names and properties.
    *args, **kwargs
        Legacy support for passing geographic columns positionally or as keywords
        (lat_col, lon_col, geocode_col, properties).

    Returns
    -------
    Path
        Path to created file.
    """
    if not isinstance(options, GeoOptions):
        lat_col = options if isinstance(options, str) else kwargs.get("lat_col", "LATITUDE")
        lon_col = args[0] if len(args) > 0 else kwargs.get("lon_col", "LONGITUDE")
        geocode_col = args[1] if len(args) > 1 else kwargs.get("geocode_col")
        properties = args[2] if len(args) > 2 else kwargs.get("properties")
        options = GeoOptions(lat_col, lon_col, geocode_col, properties)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    features = []

    for idx, row in df.iterrows():
        lat = row.get(options.lat_col)
        lon = row.get(options.lon_col)
        if pd.notna(lat) and pd.notna(lon):
            geometry = {
                "type": "Point",
                "coordinates": [
                    float(str(lon)),
                    float(str(lat)),
                ],
            }

            props: dict[str, str | None] = {}
            if options.geocode_col and options.geocode_col in row:
                props["geocode"] = str(row[options.geocode_col])

            if options.properties:
                for prop in options.properties:
                    if prop in row:
                        props[prop] = (
                            str(row[prop]) if pd.notna(row[prop]) else None
                        )

            features.append(
                {
                    "type": "Feature",
                    "id": (
                        int(idx) if isinstance(idx, (int, float)) else str(idx)
                    ),
                    "geometry": geometry,
                    "properties": props,
                }
            )

    geojson = {"type": "FeatureCollection", "features": features}

    path.write_text(
        json.dumps(geojson, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path
