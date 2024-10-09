import sys
import bpy
import argparse


def render_scene(file_path, scene_name, border, frame_number, device, save_path):
    bpy.ops.wm.open_mainfile(filepath=file_path)

    if scene_name not in bpy.data.scenes:
        raise ValueError(f"Scene '{scene_name}' not found in the file.")

    scene = bpy.data.scenes[scene_name]
    bpy.context.window.scene = scene

    scene.frame_set(frame_number)

    scene.render.use_border = True

    scene.render.border_min_x = border[0]
    scene.render.border_max_x = border[1]
    scene.render.border_min_y = border[2]
    scene.render.border_max_y = border[3]
    scene.render.filepath = save_path

    if bpy.context.scene.render.engine == "CYCLES" and device == "GPU":
        bpy.context.scene.render.engine = "CYCLES"
        bpy.context.scene.cycles.device = "GPU"
    bpy.ops.render.render(write_still=True)
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render a Blender file.")
    parser.add_argument("file_path", type=str, help="Path to the blend file")
    parser.add_argument("scene_name", type=str, help="Name of the scene to render")
    parser.add_argument(
        "--border",
        type=float,
        nargs=4,
        help="Render border (min_x min_y max_x max_y)",
        required=True,
    )
    parser.add_argument(
        "--frame_number", type=int, help="Frame number to render", required=True
    )
    parser.add_argument(
        "--device", type=str, help="Set render device:CPU/GPU", required=True
    )
    parser.add_argument(
        "--save_path", type=str, help="Temp file save path", required=True
    )

    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    try:
        output_file = render_scene(
            args.file_path,
            args.scene_name,
            args.border,
            args.frame_number,
            args.device,
            args.save_path,
        )
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
