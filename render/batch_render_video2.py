import bpy
import os, sys
import mathutils
import glob
import time
import math
import yaml
import argparse

def parse_args():
    sys_args = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Batch Render Video from Meshes")
    parser.add_argument('--config', type=str, required=True, help='Path to YAML configuration file')
    args = parser.parse_args(sys_args)
    return args

def init_io():
    input_folder =config['input']['folder']
    file_pattern =config['input']['file_pattern']

    output_folder=config['output']['folder']
    config['output']['temp_img_dir'] = os.path.join(
            output_folder, 
            config['output']['temp_img_dir']
        )
    config['output']['output_video'] = os.path.join(
            output_folder, 
            config['output']['output_video']
        )
    
    os.makedirs(output_folder, exist_ok=True)
    if not config['output']['overwrite']:
        print(f"Output folder {output_folder} already exists.")
        exit(0)

    temp_img_dir = config['output']['temp_img_dir']
    os.makedirs(temp_img_dir, exist_ok=True)
    if len(os.listdir(temp_img_dir)) > 0:
        # clear existing files
        os.system(f"rm {temp_img_dir}/*")

    output_video = config['output']['output_video']
    os.makedirs(output_video, exist_ok=True)

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
    dist_ratio = config['camera']['Distance_ratio']
    R_xy_angle = config['camera']['R_xy_angle']
    R_z_angle  = config['camera']['R_z_angle']
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
    ## * camera
    empty = bpy.data.objects.new("Target", None)
    bpy.context.collection.objects.link(empty)
    empty.location = global_info['g_center']
    track = cam.constraints.new(type='TRACK_TO')
    track.target = empty
    track.track_axis = config['camera']['track_axis']
    track.up_axis = config['camera']['up_axis']

    ## * light
    bpy.ops.object.light_add(
        type=config['light']['type'], 
        location=global_info['g_center'] + \
            mathutils.Vector(config['light']['position_bias'])
    )
    area_light = bpy.context.object
    for key in config['light']['kwargs']:
        if hasattr(area_light.data, key):
            setattr(area_light.data, key, config['light']['kwargs'][key])
            
    area_light_track = area_light.constraints.new(type='TRACK_TO')
    area_light_track.target = empty

def set_render():
    # 5. Metadata/Stamp Setup
    scene = bpy.context.scene

    # set render engine and quality
    engine_type = config['render']['engine']
    scene.render.engine = engine_type
    kwargs_render = config['render']['kwargs']
    if 'eevee' in engine_type.lower():
        for key in kwargs_render:
            if hasattr(scene.eevee, key):
                setattr(scene.eevee, key, kwargs_render[key])

    if config['render']['set_note']:
        scene.render.use_stamp = True
        scene.render.use_stamp_note = True
        scene.render.stamp_background = (0, 0, 0, 0.5)
        scene.render.stamp_font_size = 15

    # 6. Render individual frames to PNG first
    scene.render.resolution_x = config['render']['resolution_x']
    scene.render.resolution_y = config['render']['resolution_y']
    scene.render.resolution_percentage = config['render']['resolution_percentage']
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
        if config['render']['set_note']:
            scene.render.stamp_note_text = f"Mesh Index: {i} | Name: {obj.name}"
            # Render Frame
        scene.render.filepath = os.path.join(config['output']['temp_img_dir'], f"frame_{i:04d}.png")
        bpy.ops.render.render(write_still=True)

    render_end_time = time.time()
    print(f"Rendered {len(mesh_objects)} frames in {render_end_time - render_start_time:.2f} seconds.")

def render_video(global_info):
    output_video = config['output']['output_video']

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
        filepath=os.path.join(config['output']['temp_img_dir'], "frame_0000.png"),
        channel=1, frame_start=1
    )

    for i in range(frame_count):
        img_strip.elements.append(f"frame_{i:04d}.png")

    # Video Export Settings
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.fps = config['video']['fps']
    scene.render.filepath = output_video
    scene.frame_start = 1
    scene.frame_end = frame_count

    # Final render to video file
    print("Compiling video...")
    bpy.ops.render.render(animation=True)

    print(f"Process complete. Video saved to: {output_video}")

if __name__ == '__main__':
    args = parse_args()
    config_name = args.config

    cwd = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(cwd, config_name)
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    init_io()
    global_info = init_global_info()
    set_camera_light(global_info)
    set_render()
    render(global_info)
    render_video(global_info)
