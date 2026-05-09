
blender_path=/opt/blender-4.2.16-linux-x64/blender

echo "start rendering..."
$blender_path -b -P code/render/batch_render_video2.py --config config/local_config.yaml

echo "done."
