"""glTF (.glb) facts shared by the Blender steps: the json chunk and the texture-atlas layout.

A DayZ clothing p3d here has ONE texture set (hiddenSelections 'camo'). A model with several materials (backpack
of 04/10/2026: bag + harness, each with its own maps) gets them packed into an atlas: one square cell per
material, side by side. s02d remaps the UVs and s05b builds the images with the SAME rule below.
"""
import json
import struct


def read_json(path):
    data = open(path, "rb").read()
    n = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20 + n])


def atlas_materials(j):
    """indices of the materials the meshes use, in index order = atlas cell order"""
    return sorted({p["material"] for m in j.get("meshes", []) for p in m["primitives"] if "material" in p})


def atlas_cells(n):
    """cells across the atlas: next power of two (DayZ textures are power-of-two sized)"""
    c = 1
    while c < n:
        c *= 2
    return c
