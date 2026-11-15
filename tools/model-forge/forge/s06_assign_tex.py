"""Assign the baked _co (image texture on UVMap) to 'vest' and save: blender -b skin.blend --python s06_assign_tex.py -- <co.png> <out.blend>"""
import sys
import bpy

co, outb = sys.argv[sys.argv.index("--") + 1:][:2]
vest = bpy.data.objects["vest"]
m = bpy.data.materials.new("forge_preview")
m.use_nodes = True
nt = m.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.85
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = bpy.data.images.load(co)
tex.image.pack()
uvn = nt.nodes.new("ShaderNodeUVMap")
uvn.uv_map = "UVMap"
nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
vest.data.materials.clear()
vest.data.materials.append(m)
bpy.ops.wm.save_as_mainfile(filepath=outb)
print("SAVED", outb)
