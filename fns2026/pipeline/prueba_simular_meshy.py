"""
Arma un GLB que imita lo que baja de Meshy, para probar blender_refinar.py sin red:
escala cualquiera (27 unidades de largo), origen corrido, vértices duplicados en
costuras, textura de 4K y un rig simple con una animación.
    python3 prueba_simular_meshy.py salida.glb
"""
import math, sys
import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)
# cuerpo + cola + cuello: un "terópodo" de juguete, largo en X
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, location=(0, 0, 6))
cuerpo = bpy.context.object; cuerpo.scale = (6, 3, 3)
bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=2.2, depth=14, location=(-12, 0, 6), rotation=(0, math.radians(-90), 0))
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1.2, depth=7, location=(7, 0, 9), rotation=(0, math.radians(50), 0))
for x in (-2, 2):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.9, depth=6, location=(0, x, 2))
bpy.ops.object.select_all(action="SELECT")
bpy.context.view_layer.objects.active = cuerpo
bpy.ops.object.join()
m = bpy.context.object
bpy.ops.object.transform_apply(scale=True)
# duplicar vértices como en una costura de UV de Meshy
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.edge_split(); bpy.ops.object.mode_set(mode="OBJECT")
m.location = (35, -12, 4)           # origen corrido, como viene
# textura de 4K
img = bpy.data.images.new("meshy_base_color", 4096, 4096)
img.generated_type = "UV_GRID"
mat = bpy.data.materials.new("Material_0"); mat.use_nodes = True
tex = mat.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = img
mat.node_tree.links.new(tex.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
m.data.materials.append(mat)
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.uv.smart_project(); bpy.ops.object.mode_set(mode="OBJECT")
img.pack()
# rig de 3 huesos (cola, cadera, cuello) y una animación de caminata
bpy.ops.object.armature_add(location=(35, -12, 10))
arm = bpy.context.object
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones; b0 = eb[0]; b0.name = "cadera"; b0.head = (0, 0, 0); b0.tail = (4, 0, 0)
cola = eb.new("cola"); cola.head = (0, 0, 0); cola.tail = (-18, 0, 0); cola.parent = b0
cuello = eb.new("cuello"); cuello.head = (4, 0, 0); cuello.tail = (9, 0, 4); cuello.parent = b0
bpy.ops.object.mode_set(mode="OBJECT")
# pesos explícitos por zona (como un rig de Meshy: cada vértice a un hueso)
for nom in ("cadera", "cola", "cuello"):
    m.vertex_groups.new(name=nom)
for v in m.data.vertices:
    x = (m.matrix_world @ v.co).x - 35
    nom = "cola" if x < -3 else ("cuello" if x > 4 else "cadera")
    m.vertex_groups[nom].add([v.index], 1.0, "REPLACE")
m.parent = arm
m.matrix_parent_inverse = arm.matrix_world.inverted()
mod = m.modifiers.new("Armature", "ARMATURE"); mod.object = arm
arm.animation_data_create(); act = bpy.data.actions.new("caminar"); arm.animation_data.action = act
pb = arm.pose.bones["cola"]
for f, ang in ((1, -0.3), (15, 0.3), (30, -0.3)):
    pb.rotation_mode = "XYZ"; pb.rotation_euler = (0, 0, ang); pb.keyframe_insert("rotation_euler", frame=f)
salida = sys.argv[-1]
if salida.endswith(".fbx"):
    bpy.ops.export_scene.fbx(filepath=salida, add_leaf_bones=False, bake_anim=True)
else:
    bpy.ops.export_scene.gltf(filepath=salida, export_format="GLB")
print("tri:", sum(len(p.vertices) - 2 for p in m.data.polygons))
