import json
import os
import threading
import time
import bpy


def getborders(num):
    scene = bpy.context.scene
    width = scene.render.resolution_x
    part_width = width // num

    borders = []
    for i in range(num):
        scene.render.use_border = True
        min_x = i * part_width / width
        max_x = (i + 1) * part_width / width
        min_y = 0
        max_y = 1
        borders.append((min_x, max_x, min_y, max_y))
    return borders


def render_divided(num, save_path):
    scene = bpy.context.scene
    width = scene.render.resolution_x
    part_width = width // num
    original_output_path = scene.render.filepath

    images = []
    for i in range(num):
        scene.render.use_border = True
        min_x = i * part_width / width
        max_x = (i + 1) * part_width / width
        min_y = 0
        max_y = 1
        scene.render.border_min_x = min_x
        scene.render.border_max_x = max_x
        scene.render.border_min_y = min_y
        scene.render.border_max_y = max_y
        file_name = os.path.join(save_path, f"render_{i:04d}.png")
        scene.render.filepath = file_name
        bpy.ops.render.render(write_still=True)

        if os.path.exists(file_name):
            images.append(bpy.data.images.load(file_name))
    scene.render.filepath = original_output_path

    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    links = tree.links

    for n in tree.nodes:
        tree.nodes.remove(n)

    input_nodes = []
    for image in images:
        input_image = tree.nodes.new(type='CompositorNodeImage')
        input_image.image = image
        input_nodes.append(input_image)

    result_image = input_nodes[0]
    for i in range(1, len(input_nodes)):
        merge_node = tree.nodes.new(type='CompositorNodeAlphaOver')
        links.new(result_image.outputs[0], merge_node.inputs[1])
        links.new(input_nodes[i].outputs[0], merge_node.inputs[2])
        result_image = merge_node

    result_node = tree.nodes.new(type='CompositorNodeComposite')
    links.new(result_image.outputs[0], result_node.inputs[0])

    composite_file_path = os.path.join(save_path, "composite.png")
    scene.render.filepath = composite_file_path
    scene.render.use_border = False
    bpy.ops.render.render(write_still=True)

    for n in tree.nodes:
        tree.nodes.remove(n)
    bpy.context.scene.use_nodes = False
    delete_slice_files(num, save_path)


def merge_image(images, save_path):
    scene = bpy.context.scene
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    links = tree.links

    for n in tree.nodes:
        tree.nodes.remove(n)

    input_nodes = []
    for image in images:
        input_image = tree.nodes.new(type='CompositorNodeImage')
        input_image.image = image
        input_nodes.append(input_image)

    result_image = input_nodes[0]
    for i in range(1, len(input_nodes)):
        merge_node = tree.nodes.new(type='CompositorNodeAlphaOver')
        links.new(result_image.outputs[0], merge_node.inputs[1])
        links.new(input_nodes[i].outputs[0], merge_node.inputs[2])
        result_image = merge_node

    result_node = tree.nodes.new(type='CompositorNodeComposite')
    links.new(result_image.outputs[0], result_node.inputs[0])

    composite_file_path = os.path.join(save_path, "composite.png")
    scene.render.filepath = composite_file_path
    scene.render.use_border = False
    bpy.ops.render.render(write_still=True)

    for n in tree.nodes:
        tree.nodes.remove(n)
    bpy.context.scene.use_nodes = False


def delete_slice_files(num, save_path):
    for i in range(num):
        file_name = os.path.join(save_path, f"render_{i:04d}.png")
        if os.path.exists(file_name):
            os.remove(file_name)


def run_task(server, task, worker):
    scene = bpy.context.scene
    if worker["render"] and worker["online"]:
        scene.RenderStatus = f"{worker['host']} is rendering tile {task['index']}"
        send_data = {
            "flag": "sync",
            "blend_file": worker["blendfile"],
            "scene": scene.name,
            "border": task["border"],
            "frame": scene.frame_start
        }
        task["start_time"] = time.time()
        server.send_data(json.dumps(send_data).encode("utf-8"), worker["host"])
        server.send_data(
            json.dumps({
                "flag": "render"
            }).encode("utf-8"), worker["host"])
        worker["render"] = False

        try:
            # tmp_file = server.recv_file(worker["host"])
            # if tmp_file:
            status = server.recv_data(worker["host"])
            if status == "ok":
                task["worker"] = worker["host"]
                task["end_time"] = time.time()
                worker["render"] = True
                task["complete"] = True
                scene.RenderStatus = f"Tile {task['index']} render success, cost {str(task['end_time'] - task['start_time'])}"
        except Exception as e:
            worker["online"] = False
            print(f"[Error] task run error: {e}")
            scene.RenderStatus = f"Tile {task['index']} render error"


def worker_thread(server, tasklist, worker):
    while any(not task["complete"] for task in tasklist):
        if worker["render"] and worker["online"]:
            for task in tasklist:
                if not task["complete"]:
                    run_task(server, task, worker)
                    break
        time.sleep(0.1)


def manage_threads(server, tasklist, workerlist):
    threads = []
    for worker in workerlist:
        thread = threading.Thread(target=worker_thread,
                                  args=(server, tasklist, worker))
        thread.start()
        threads.append(thread)

    def check_threads():
        if any(thread.is_alive() for thread in threads):
            return 1.0
        bpy.context.scene.RenderSettingEnable = True
        return None

    bpy.app.timers.register(check_threads)
