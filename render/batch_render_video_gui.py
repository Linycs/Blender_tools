import bpy
import os, sys
import mathutils
import glob
import time
import math

# --- Configuration ---
input_folder="/media/linycs/ssd1T/projects_dataset/data_deliver/smpl2qiaojie/output/vis/vis3d/results_filter/354630_03-period_0-0_600_validated"
output_folder="/media/linycs/ssd1T/projects_docker/Annotation/vis_blender"

file_pattern="frame_*.obj"
overwrite_output = 1
track_axis = "TRACK_NEGATIVE_Z"
up_axis = "UP_Y"
output_video = "/media/linycs/ssd1T/projects_docker/Annotation/blender_render/tmp_output"
temp_img_dir = "/media/linycs/ssd1T/projects_docker/Annotation/blender_render/temp_frames"

cam_ratioD_Rxy_Rz = "3_90_90"
cam_ratioD_Rxy_Rz = list(map(float, cam_ratioD_Rxy_Rz.split('_')))
print(f'cam_ratioD_Rxy_Rz: [{cam_ratioD_Rxy_Rz}]')

light_bias = (0,2,2)

set_note = False

def init_io():
    if not os.path.exists(temp_img_dir):
        os.makedirs(temp_img_dir)
    elif len(os.listdir(temp_img_dir)) > 0:
        # clear existing files
        os.system(f"rm {temp_img_dir}/*")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    elif not overwrite_output:
        print(f"Output folder {output_folder} already exists.")
        exit(0)

    # 1. Clear Scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # 2. Import All Meshes
    files = sorted([
                os.path.basename(f) for f in glob.glob(
                    os.path.join(input_folder, file_pattern)
                )
            ])

    for f in files:
        fp = os.path.join(input_folder, f)
        file_extension = file_pattern.split('.')[-1].lower()
        if file_extension == 'obj': bpy.ops.wm.obj_import(filepath=fp)
        elif file_extension == 'ply': bpy.ops.wm.ply_import(filepath=fp)
        elif file_extension == 'stl': bpy.ops.wm.stl_import(filepath=fp)

def init_global_info():
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        
    # 3. Calculate Global Bounds
    all_min = mathutils.Vector((float('inf'), float('inf'), float('inf')))
    all_max = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))

    for obj in mesh_objects:
        bpy.context.view_layer.update()
        
        bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
        for corner in bbox_corners:
            for i in range(3):
                all_min[i] = min(all_min[i], corner[i])
                all_max[i] = max(all_max[i], corner[i])

    g_center = (all_min + all_max) / 2
    max_dim = max(all_max - all_min)
    
    return {
        'mesh_objects': mesh_objects, 
        'g_center': g_center, 
        'max_dim': max_dim, 
    }
    
def set_camera_light(global_info):
    dist_ratio, R_xy_angle, R_z_angle = cam_ratioD_Rxy_Rz
    # object is face to -Y axis, and stand upright
    R_xy_angle, R_z_angle = R_xy_angle * math.pi/ 180, R_z_angle * math.pi / 180
    dist = global_info['max_dim'] * dist_ratio
    x_coord = dist * math.cos(R_xy_angle) * math.sin(R_z_angle)
    y_coord = dist * math.sin(R_xy_angle) * math.sin(R_z_angle)
    z_coord = dist * math.cos(R_z_angle)
    
    offset = mathutils.Vector([
        x_coord, y_coord, z_coord
    ])
    bpy.ops.object.camera_add(location=global_info['g_center'] + offset)
    cam = bpy.context.object
    bpy.context.scene.camera = cam

    # Static Tracking
    empty = bpy.data.objects.new("Target", None)
    bpy.context.collection.objects.link(empty)
    empty.location = global_info['g_center']
    track = cam.constraints.new(type='TRACK_TO')
    track.target = empty
    track.track_axis = track_axis # Z
    track.up_axis = up_axis

    # bpy.ops.object.light_add(type='SUN', location=global_info['g_center'] + mathutils.Vector(light_bias))
    bpy.ops.object.light_add(type='AREA', location=global_info['g_center'] + mathutils.Vector(light_bias))
    area_light = bpy.context.object
    area_light.data.color = (1, 1, 1)  # 白色光
    area_light.data.size = 5  # 增加光源尺寸来软化阴影
    area_light.data.energy = 250
    area_light_track = area_light.constraints.new(type='TRACK_TO')
    area_light_track.target = empty

def set_render():
    # 5. Metadata/Stamp Setup
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'# Use 'BLENDER_EEVEE' for older versions
    scene.eevee.taa_render_samples = 8 # higher samples for better quality

    if set_note:
        scene.render.use_stamp = True
        scene.render.use_stamp_note = True
        scene.render.stamp_background = (0, 0, 0, 0.5)
        scene.render.stamp_font_size = 15

    # 6. Render individual frames to PNG first
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 150
    scene.render.image_settings.file_format = 'PNG'

def render(global_info):
    scene = bpy.context.scene
    mesh_objects = global_info['mesh_objects']
    
    render_start_time = time.time()
    for i, obj in enumerate(mesh_objects):
        # Visibility
        for o in mesh_objects: o.hide_render = True
        obj.hide_render = False
        
        # Metadata note (Index)
        if set_note:
            scene.render.stamp_note_text = f"Mesh Index: {i} | Name: {obj.name}"
            # Render Frame
        scene.render.filepath = os.path.join(temp_img_dir, f"frame_{i:04d}.png")
        bpy.ops.render.render(write_still=True)

    render_end_time = time.time()
    print(f"Rendered {len(mesh_objects)} frames in {render_end_time - render_start_time:.2f} seconds.")

def render_video(global_info):
    scene = bpy.context.scene
    mesh_objects = global_info['mesh_objects']

    scene.render.use_stamp = False 
    
    # Setup Sequencer
    if not scene.sequence_editor:
        scene.sequence_editor_create()

    # Clear existing strips to avoid overlap
    for s in scene.sequence_editor.sequences:
        scene.sequence_editor.sequences.remove(s)
        
    # Add images to sequencer
    frame_count = len(mesh_objects)
    img_strip = scene.sequence_editor.sequences.new_image(
        name="MyVideoExport",
        filepath=os.path.join(temp_img_dir, "frame_0000.png"),
        channel=1, frame_start=1
    )

    for i in range(frame_count):
        img_strip.elements.append(f"frame_{i:04d}.png")

    # Video Export Settings
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.fps = 30
    scene.render.filepath = output_video
    scene.frame_start = 1
    scene.frame_end = frame_count

    # Final render to video file
    print("Compiling video...")
    bpy.ops.render.render(animation=True)

    print(f"Process complete. Video saved to: {output_video}")

if __name__ == '__main__':
    init_io()
    global_info = init_global_info()
    set_camera_light(global_info)
    set_render()
    render(global_info)
    render_video(global_info)
