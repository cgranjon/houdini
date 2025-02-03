import hou

def get_geometry_primitive_counts():
    geo_prim_counts = {}

    # Get all Geometry (Sop) nodes in the scene
    obj_nodes = hou.node("/obj").allSubChildren()
    geo_nodes = [n for n in obj_nodes if n.type().category().name() == "Object" and n.type().name() == "geo"]

    for geo_node in geo_nodes:
        # Get the display node (SOP inside the geometry node)
        sop_node = geo_node.renderNode()
        if sop_node:
            # Evaluate the geometry
            geo = sop_node.geometry()
            if geo:
                # Evaluate amount of primitives
                total_prims = len(geo.prims())  # Get total number of primitives
                unpacked_prims = 0
                for prim in geo.prims():
                    if prim.type().name()=="Polygon":
                        unpacked_prims += 1              
                # Skip nodes with 0 primitives
                if unpacked_prims > 0:
                    geo_prim_counts[geo_node.path()] = (total_prims, unpacked_prims)

    return geo_prim_counts

geo_counts = get_geometry_primitive_counts()

# 
print("-------- Scene Geometry Stats:")
for obj_name, (total, unpacked) in geo_counts.items():
    print(f"{total} primitives ({unpacked} unpacked) - {obj_name}")