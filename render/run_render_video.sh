input_folder="/home/jeff/Downloads/scp_save/milk-pickup_9708-20260120-131546/optimized/batch0"
output_folder="/home/jeff/linycs/Annotations/blender_render/test"
log_fpath="render.log"

file_pattern="f000*.obj"
overwrite_output=true

blender_path=/opt/blender-4.2.16-linux-x64/blender

# Camera orientation
# track_to_axis = TRACK_NEGATIVE_X/Y/Z or TRACK_X/Y/Z
# up_axis = UP_X/Y/Z
track_to_axis=TRACK_NEGATIVE_Z
up_axis=UP_Y
save_video_path=$output_folder/render-$track_to_axis-$up_axis.mp4
temp_img_dir=/home/jeff/linycs/Annotations/blender_render/temp_frames

echo "start rendering..."
$blender_path -b -P code/render/batch_render_video.py --\
    $input_folder \
    $output_folder \
    $file_pattern \
    $overwrite_output \
    $track_to_axis \
    $up_axis \
    $save_video_path \
    $temp_img_dir \
    > $log_fpath

echo "done."
