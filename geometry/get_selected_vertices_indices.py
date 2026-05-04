import bpy
import bmesh
import os

def export_selected_vertices_indices(filepath):
    obj = bpy.context.active_object
    
    if not obj or obj.type != 'MESH':
        print("请先选择一个网格对象")
        return
    
    # 确保在编辑模式
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    # 获取选中顶点
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    
    selected_verts = [v.index for v in bm.verts if v.select]
    
    # 导出到文件
    with open(filepath, 'w') as f:
#        f.write("选中的顶点索引:\n")
        for idx in selected_verts:
            f.write(f"{idx}\n")
    
    print(f"已导出 {len(selected_verts)} 个顶点索引到: {filepath}")
    
    # 返回到对象模式
    bpy.ops.object.mode_set(mode='OBJECT')


def set_selected_vertices_indices(indices):
    obj = bpy.context.active_object
    
    if not obj or obj.type != 'MESH':
        print("请先选择一个网格对象")
        return
    
    # 确保在编辑模式
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    # 获取选中顶点
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    for index in indices:
        bm.verts[index].select = True
        
export_selected_vertices_indices("/media/linycs/ssd1T/projects_docker/Annotation/blender_tools/geometry/vertex_indices.txt")
# indices = [
#    # thumb inner tip & root
#    736,737,738,739,740,741,742,743,755,756,757,758,759,760,761,762,763,764,766,767,768,
#    704, 711, 713, 714, 267, 124, 753, 754, 125, 698, 699, 700, 701, 31, 7, 123, 126, 
# ]
#set_selected_vertices_indices(indices)
