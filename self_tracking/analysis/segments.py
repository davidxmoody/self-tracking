import osmnx as ox
import folium

center_point = (51.4545, -2.5879)
radius_m = 2000

G = ox.graph_from_point(center_point, dist=radius_m, network_type='bike')

edges = ox.graph_to_gdfs(G, nodes=False)

center = edges.unary_union.centroid
m = folium.Map(tiles=None, location=[center.y, center.x], zoom_start=13)
m.add_child(folium.TileLayer("CartoDB PositronNoLabels", name="Greyscale"))

for _, row in edges.iterrows():
    if row.geometry.geom_type == 'LineString':
        coords = [(lat, lon) for lon, lat in row.geometry.coords]
        folium.PolyLine(coords, color='green', weight=2).add_to(m)
    elif row.geometry.geom_type == 'MultiLineString':
        for line in row.geometry:
            coords = [(lat, lon) for lon, lat in line.coords]
            folium.PolyLine(coords, color='green', weight=2).add_to(m)

m.show_in_browser()
