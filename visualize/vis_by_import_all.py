import bpy, os, re
import glob
from mathutils import Vector

#########################
# 1. 只需要改这两行
SHAPE_DIR      = f"/home/linycs/Downloads/idea_1_stage0-1-2/Idea1_not_very_smooth/2025*stage012_*/optimized/batch0"
# SHAPE_DIR  = "/media/linycs/Elements SE/datasets/synadata/outputs/grasp_nailong/b204cbaea57c88afa1172f7b8fb84b3a/smplx_with_obj_mesh_smooth"  # 你的 ply 目录
POINT_RADIUS = 0.005                   # 小球半径，根据场景单位调
start_frame = 1
out_dir     = f"{SHAPE_DIR}/../render_out"     # 渲染输出目录
file_format = 'PNG'           # 'PNG' / 'FFMPEG'
fps         = 30              # 帧率
resolution  = (1920, 1080)    # 宽×高
engine      = 'BLENDER_EEVEE_NEXT'
os.makedirs(out_dir, exist_ok=True)
#########################

ext = "obj"
pattern = f'*.{ext}'
pattern   = os.path.join(SHAPE_DIR, pattern)
files     = sorted(glob.glob(pattern))


# ---------- 计算统一偏移量 ----------
first_path = os.path.join(SHAPE_DIR, files[0])
if ext == 'ply':
    bpy.ops.wm.ply_import(filepath=first_path)
elif ext == 'obj':
    bpy.ops.wm.obj_import(filepath=first_path)
elif ext == 'stl':
    bpy.ops.wm.stl_import(filepath=first_path)
elif ext == 'fbx':
    bpy.ops.io_scene_fbx.fbx_import(filepath=first_path)
elif ext in ('gltf', 'glb'):
    bpy.ops.import_scene.gltf(filepath=first_path)
else:
    exit(f"Unsupported file extension: {ext}")

first_obj = bpy.context.active_object

# 计算重心
verts_co = [v.co for v in first_obj.data.vertices]
center = sum(verts_co, Vector()) / len(verts_co)
offset = -center           # 负向量，直接搬到原点

# 删除临时对象，后面正式导入时再统一使用 offset
bpy.data.objects.remove(first_obj, do_unlink=True)
# ------------------------------------

# 清场
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# mesh 公用材质
def create_default_material():
    if "SeqMat" in bpy.data.materials:
        return bpy.data.materials["SeqMat"]
    mat = bpy.data.materials.new(name="SeqMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1)
    return mat

# 点云公用材质
def create_vertex_color_material():
    if "VertexColorMat" in bpy.data.materials:
        return bpy.data.materials["VertexColorMat"]
    mat = bpy.data.materials.new(name="VertexColorMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    attr = mat.node_tree.nodes.new(type="ShaderNodeAttribute")
    attr.attribute_name = "Col"
    mat.node_tree.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    return mat

if ext in ['ply']:
    vertex_color_mat = create_vertex_color_material()
else:
    default_mat = create_default_material()

# 设置光照
bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
sun = bpy.context.object
sun.rotation_euler = (0.785, 0, 0)          # 45° 俯视
sun.data.energy = 3                         # 亮度可调

# 设置渲染参数
scene = bpy.context.scene
scene.frame_start = start_frame
scene.frame_end   = start_frame + len(files) - 1
scene.render.fps  = fps

scene.render.filepath = os.path.join(out_dir, "frame_")
scene.render.resolution_x, scene.render.resolution_y = resolution
scene.render.engine   = engine
if file_format == 'FFMPEG':
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format           = 'MPEG4'
    scene.render.ffmpeg.codec            = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'HIGH'
else:
    scene.render.image_settings.file_format = 'PNG'

# 设置相机
bpy.ops.object.camera_add(location=(5, -5, 4))
cam = bpy.context.object
cam.rotation_euler = (1.1, 0, 0.785)
bpy.context.scene.camera = cam
# cam_col.objects.link(cam)

for idx, fname in enumerate(files):
    full_path = os.path.join(SHAPE_DIR, fname)
    ext = fname.split('.')[-1].lower()

    if ext == 'ply':
        bpy.ops.wm.ply_import(filepath=full_path)
    elif ext == 'obj':
        bpy.ops.wm.obj_import(filepath=full_path)
    elif ext == 'stl':
        bpy.ops.wm.stl_import(filepath=full_path)
    elif ext == 'fbx':
        bpy.ops.io_scene_fbx.fbx_import(filepath=full_path)
    elif ext in ('gltf', 'glb'):
        bpy.ops.import_scene.gltf(filepath=full_path)
    else:
        continue

    obj = bpy.context.active_object
    obj.name = f"Frame_{idx:04d}"

    obj.location += offset

    if ext in ['ply']:
        # 加 Geometry Nodes
        mod = obj.modifiers.new(name="Points", type='NODES')

        # 创建节点组
        ng = bpy.data.node_groups.new("GN_Points", 'GeometryNodeTree')
        mod.node_group = ng

        # 声明接口
        ng.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        ng.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

        # 节点
        in_node   = ng.nodes.new('NodeGroupInput')
        out_node  = ng.nodes.new('NodeGroupOutput')
        mesh2pts  = ng.nodes.new('GeometryNodeMeshToPoints')
        set_mat   = ng.nodes.new('GeometryNodeSetMaterial')

        mesh2pts.inputs['Radius'].default_value = POINT_RADIUS
        set_mat.inputs['Material'].default_value = vertex_color_mat

        # 连线
        ng.links.new(in_node.outputs[0], mesh2pts.inputs['Mesh'])
        ng.links.new(mesh2pts.outputs['Points'], set_mat.inputs['Geometry'])
        ng.links.new(set_mat.outputs['Geometry'], out_node.inputs[0])
    else:
        obj.active_material = default_mat

    # 可见性关键帧
    obj.hide_viewport = True
    obj.hide_render   = True
    obj.keyframe_insert("hide_viewport", frame=idx)
    obj.keyframe_insert("hide_render",   frame=idx)

    obj.hide_viewport = False
    obj.hide_render   = False
    obj.keyframe_insert("hide_viewport", frame=idx+1)
    obj.keyframe_insert("hide_render",   frame=idx+1)

    obj.hide_viewport = True
    obj.hide_render   = True
    obj.keyframe_insert("hide_viewport", frame=idx+2)
    obj.keyframe_insert("hide_render",   frame=idx+2)

# 把帧范围自动设成序列长度
bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end   = len(files) - 1
