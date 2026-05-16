"""
Build a UXsim network from OpenStreetMap for the Aguinaldo Hwy corridor in Dasmariñas.

Uses OSMnx (drive network) inside a bounding box, projects to meters, then adds nodes/links to World.
This avoids UXsim's bundled OSM importer, which can error when OSM lacks maxspeed columns.

Origin / destination for OD snapping match this Google Maps driving route:
  The Zamora Room – Coffee Lab (12 Emilio Aguinaldo Hwy, Sampaloc 1) → Waltermart Dasmariñas
  https://www.google.com/maps/dir/The+Zamora+Room+-+Coffee+Lab,+12+Emilio+Aguinaldo+Hwy,+Sampaloc+1,+Dasmari%C3%B1as,+4114+Cavite/WalterMart+Dasmari%C3%B1as...

Coordinates extracted from that link (!1d lon !2d lat pairs):
  Origin (Coffee Lab):  120.954419°E, 14.3013123°N
  Destination (WM):     120.9414853°E, 14.324744°N

For Robinsons-only OD, override ROUTE_ORIG_LONLAT / ROUTE_DEST_LONLAT after import.
"""

from __future__ import annotations

import re
from typing import Any

import osmnx as ox
from uxsim import World

# (west, south, east, north) in WGS84 — padded box along Coffee Lab → Waltermart (Google Maps corridor)
DEFAULT_BBOX = (120.934, 14.2965, 120.962, 14.331)

# (longitude, latitude) WGS84 — same OD endpoints as your Google Directions link
ROUTE_ORIG_LONLAT = (120.954419, 14.3013123)  # Zamora Room / Coffee Lab
ROUTE_DEST_LONLAT = (120.9414853, 14.324744)  # Waltermart Dasmariñas

# Aliases for older scripts / Robinsons-area studies (near Coffee Lab on Aguinaldo)
ROBINSONS_LONLAT = ROUTE_ORIG_LONLAT
WALTERMART_LONLAT = ROUTE_DEST_LONLAT

DEFAULT_U_MPS = 16.67  # ~60 km/h if OSM maxspeed missing


def _parse_maxspeed_mps(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) / 3.6
    s = str(val).strip().lower()
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    kph = float(m.group(1))
    return kph / 3.6


def _parse_lanes(val: Any) -> int | None:
    if val is None:
        return None
    if isinstance(val, int):
        return max(val, 1)
    s = str(val).strip()
    m = re.search(r"(\d+)", s)
    return max(int(m.group(1)), 1) if m else None


def download_drive_graph(bbox: tuple[float, float, float, float] = DEFAULT_BBOX):
    """Return (graph_latlon, graph_projected)."""
    G = ox.graph.graph_from_bbox(bbox, network_type="drive", simplify=True)
    Gp = ox.project_graph(G)
    return G, Gp


def nearest_osm_node_ids(G_latlon, lon: float, lat: float) -> str:
    nid = ox.distance.nearest_nodes(G_latlon, lon, lat)
    return str(nid)


def add_osm_graph_to_world(W: World, Gp, default_u_mps: float = DEFAULT_U_MPS) -> None:
    """Populate World with projected OSMnx graph (meters). Modifies W in place."""
    for nid, data in Gp.nodes(data=True):
        W.addNode(str(nid), float(data["x"]), float(data["y"]))

    for u, v, k, d in Gp.edges(keys=True, data=True):
        length = float(d.get("length") or 0.0)
        if length <= 1.0:
            continue
        u_s, v_s = str(u), str(v)
        name = f"e_{u_s}_{v_s}_{k}"
        u_mps = _parse_maxspeed_mps(d.get("maxspeed")) or default_u_mps
        lanes = _parse_lanes(d.get("lanes")) or 2
        lanes = min(max(lanes, 1), 6)
        W.addLink(
            name,
            u_s,
            v_s,
            length=length,
            free_flow_speed=u_mps,
            number_of_lanes=lanes,
            auto_rename=True,
        )


def build_corridor_world(
    tmax: float = 7200.0,
    bbox: tuple[float, float, float, float] = DEFAULT_BBOX,
    print_mode: int = 0,
) -> tuple[World, str, str, Any, Any]:
    """
    Create World with OSM network; return (W, orig_node_id, dest_node_id, G, Gp).
    OD nodes are nearest OSM graph nodes to ROUTE_ORIG_LONLAT / ROUTE_DEST_LONLAT
    (Coffee Lab → Waltermart from your Google Maps link).
    """
    G, Gp = download_drive_graph(bbox)
    o = nearest_osm_node_ids(G, *ROUTE_ORIG_LONLAT)
    d = nearest_osm_node_ids(G, *ROUTE_DEST_LONLAT)

    W = World(name="dasma_osm_corridor", print_mode=print_mode, tmax=tmax)
    add_osm_graph_to_world(W, Gp)
    return W, o, d, G, Gp


if __name__ == "__main__":
    W, orig, dest, G, Gp = build_corridor_world(tmax=3600.0, print_mode=1)
    print("OSM nodes/edges:", G.number_of_nodes(), G.number_of_edges())
    print("UXsim nodes/links:", len(W.NODES), len(W.LINKS))
    print("OD (nearest OSM nodes):", orig, "->", dest)
    W.adddemand(orig, dest, 0, 1800, volume=50)
    W.exec_simulation()
    W.analyzer.print_simple_stats(force_print=True)
