# Blender 4.4.3 逐帧 mesh/ply 序列脚本（带颜色/默认材质）
import bpy, os, glob
from mathutils import Vector

exp_name = "260121_flip_milk_2_color-20260317-043034"  # 序列 ID
SHAPE_DIR      = f"/media/linycs/ssd1T/projects_dataset/data_deliver/smpl2qiaojie/output/vis/vis3d/fail_delivery/109385_7-period_0-237_1199_validated"
#SHAPE_DIR       = "/home/jeff/Downloads/data_demos/synadata/outputs_seq/apple/apple1/depth_moge_pointclouds"
POINT_RADIUS = 0.005                   # 小球半径，根据场景单位调
#########################

ext = "obj"
pattern     = f"*.{ext}"           # 也可改成 "*.obj" "*.stl" "*.fbx" ...
start_frame = 0
# ===========================

files = sorted(glob.glob(os.path.join(SHAPE_DIR, pattern)))
if not files:
    raise RuntimeError("未找到任何匹配文件！")

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
offset = Vector([0,0,0])

# 删除临时对象，后面正式导入时再统一使用 offset
bpy.data.objects.remove(first_obj, do_unlink=True)
# ------------------------------------

# 清理默认场景
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
default_rotation = (0,180,0)

scene = bpy.context.scene
scene.frame_start = start_frame
scene.frame_end   = start_frame + len(files) - 1

# set active-object's theme color -> transparent

# 通用默认材质（白色 Principled-BSDF）
def create_default_material():
    if "DefaultMat" in bpy.data.materials:
        return bpy.data.materials["DefaultMat"]
    mat = bpy.data.materials.new(name="DefaultMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
    return mat

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
    

# --------------------------
# 帧处理器
# --------------------------
def load_frame(scene):
    frame = scene.frame_current
    idx   = frame - start_frame
    if not (0 <= idx < len(files)):
        return

    # 删除上一帧对象
    for obj in list(bpy.data.objects):
        if obj.type in {'MESH', 'POINTCLOUD'}:
            bpy.data.objects.remove(obj, do_unlink=True)

    fp, ext = files[idx], os.path.splitext(files[idx])[1].lower()

    # ---------- PLY ----------
    if ext == '.ply':
        bpy.ops.wm.ply_import(filepath=fp)
        obj = bpy.context.active_object
        obj.location += offset
        obj.rotation_euler = default_rotation

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
        # 通用导入器
        if   ext == '.obj':  bpy.ops.wm.obj_import(filepath=fp)
        elif ext == '.stl':  bpy.ops.wm.stl_import(filepath=fp)
        elif ext == '.fbx':  bpy.ops.io_scene_fbx.fbx_import(filepath=fp)
        elif ext in ('.gltf', '.glb'): bpy.ops.import_scene.gltf(filepath=fp)
        else: return

        obj = bpy.context.active_object
        obj.location += offset
        obj.rotation_euler = default_rotation

        if obj and obj.type == 'MESH':
            # 赋予默认材质
            if obj.data.materials:
                obj.data.materials.clear()
            obj.data.materials.append(default_mat)

# --------------------------
# 注册帧处理器
# --------------------------


for h in list(bpy.app.handlers.frame_change_pre):
    if h.__name__ == 'load_frame':
        bpy.app.handlers.frame_change_pre.remove(h)
bpy.app.handlers.frame_change_pre.append(load_frame)

# 立即加载第一帧
load_frame(scene)

print(f"就绪：共 {len(files)} 帧，支持实时拖动到任意帧")

#theme.view_3d.object_selected = original # (1.0, 0.522, 0, )

