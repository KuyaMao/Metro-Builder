# Renders impostor views of a Poly Haven tree with Cycles: 8 azimuths x 2 elevations, RGBA, transparent background
import bpy, sys, math, os, mathutils
args = sys.argv[sys.argv.index('--') + 1:]
blend, out, obj_name, res, samples = args[0], args[1], args[2], int(args[3]), int(args[4])
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
# keep only the chosen tree object
for o in list(sc.objects):
    if o.name != obj_name: o.hide_render = True
tree = sc.objects[obj_name]; tree.hide_render = False
bb = [tree.matrix_world @ mathutils.Vector(c) for c in tree.bound_box]
mn = mathutils.Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
mx = mathutils.Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
rad = max(math.hypot(v.x, v.y) for v in bb); ctr = mathutils.Vector((0, 0, mx.z / 2)); size = max(2 * rad, mx.z) * 1.02
print('impostor', 'height', mx.z, 'frame', size)
print('bounds', mn, mx)
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
sc.render.film_transparent = True; sc.render.resolution_x = sc.render.resolution_y = res; sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
sc.view_settings.view_transform = 'Standard'
# soft daylight: uniform sky plus a gentle sun from above
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.75, 0.8, 0.9, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 2.2; sun.data.angle = math.radians(25); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(25), 0, math.radians(30))
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = size
for ei, el in enumerate((20, 55)):
    for ai in range(8):
        az = ai * 2 * math.pi / 8
        d = mathutils.Vector((math.cos(math.radians(el)) * math.sin(az), -math.cos(math.radians(el)) * math.cos(az), math.sin(math.radians(el))))
        cam.location = ctr + d * size * 3
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(out, f'v{ei}_{ai}.png')
        bpy.ops.render.render(write_still=True)
        print('done', ei, ai, flush=True)
