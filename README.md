# README

A tool repository for visualize/render shape sequence.

## Installation

This repository is developed in blender4.2 or higher version.

Some python package like `yaml` may need to install Manually:

``` bash
# Windows: use command like:
<blender_path>/4.2/python/bin/python.exe -m pip install pyyaml
# Linux: use command like:
<blender_path>/4.2/python/bin/python -m pip install pyyaml
```

## visualize

Load and run visualize/vis_by_import_frame.py in blender to import shape sequence and watch it at any perspective.

## render

Use `bash render/run_render_video.sh` to ender mesh sequence. Note that modify args if necessary.

## geometry

Load geometry/get_selected_vertices_indices.py in blender and select target points, then run the code to export indices of selected points in specific txt file.

## TODO

- [ ] add code to export mesh faces that contain selected points.
- [ ] more setting like materials in visualization/rendering.
