import json
import os
import shutil
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


def merge_image(area, outputfilepath, outputfilename):
    tempfilepath = os.path.join(os.path.dirname(bpy.data.filepath), "temp")
    if not os.path.exists(tempfilepath):
        print(f"[Error] temp path error")
        return

    images = []
    for i in os.listdir(tempfilepath):
        if i.endswith(".png"):
            tmpfile = os.path.join(tempfilepath, i)
            images.append(bpy.data.images.load(tmpfile))

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

    composite_file_path = os.path.join(outputfilepath, outputfilename)
    scene.render.filepath = composite_file_path
    scene.render.use_border = False
    bpy.ops.render.render(write_still=True)

    for n in tree.nodes:
        tree.nodes.remove(n)
    bpy.context.scene.use_nodes = False
    image = bpy.data.images.load(composite_file_path)
    area.spaces.active.image = image


def render_image(server, area, task, worker):
    scene = bpy.context.scene
    if worker["render"] and worker["online"]:
        print(f"{worker['host']} is rendering tile {task['index']}")
        send_data = {
            "flag": "sync",
            "blend_file": worker["blendfile"],
            "scene": scene.name,
            "border": task["border"],
            "frame": task["frame"]
        }
        task["start_time"] = time.time()
        if task["lock"] is not None and task["lock"] != worker["host"]:
            print(
                f"[Info] task {task['frame_range']} is already locked by {task['lock']}"
            )
            return
        server.send_data(json.dumps(send_data).encode("utf-8"), worker["host"])
        server.send_data(
            json.dumps({
                "flag": "render_image"
            }).encode("utf-8"), worker["host"])
        worker["render"] = False

        try:
            tempfilename = server.recv_data(worker["host"])
            if tempfilename == "ok":
                return
            if tempfilename:
                img = os.path.join(os.path.dirname(bpy.data.filepath), "temp",
                                   tempfilename)

                image = bpy.data.images.load(img)
                area.spaces.active.image = image
                task["worker"] = worker["host"]
                task["end_time"] = time.time()
                worker["render"] = True
                task["complete"] = True
        except Exception as e:
            worker["online"] = False
            print(f"[Error] task run error: {e}")
        finally:
            task["lock"] = None


def worker_image_thread(server, area, tasklist, worker):
    while any(not task["complete"] for task in tasklist):
        if worker["render"] and worker["online"]:
            for task in tasklist:
                if not task["complete"] and task["lock"] is None:
                    if worker.get("task_lock", None) is None:
                        worker["task_lock"] = threading.Lock()
                    with worker["task_lock"]:
                        if task["lock"] is None:
                            task["lock"] = worker["host"]
                            render_image(server, area, task, worker)
                            break
        time.sleep(0.1)


def manage_image_threads(server, area, tasklist, workerlist, outputfilepath,
                         outputfilename):
    threads = []
    tempfilepath = os.path.join(os.path.dirname(bpy.data.filepath), "temp")
    if os.path.exists(tempfilepath):
        shutil.rmtree(tempfilepath)
        os.mkdir(tempfilepath)
    else:
        os.mkdir(tempfilepath)
    for worker in workerlist:
        thread = threading.Thread(target=worker_image_thread,
                                  args=(server, area, tasklist, worker))
        thread.start()
        threads.append(thread)

    def check_threads():
        if any(thread.is_alive() for thread in threads):
            return 1.0
        bpy.context.scene.RenderSettingEnable = True
        merge_image(area,
                    outputfilepath=outputfilepath,
                    outputfilename=outputfilename)
        shutil.rmtree(tempfilepath)
        return None

    bpy.app.timers.register(check_threads)


def render_animation(server, worker, task):
    scene = bpy.context.scene
    renderfilepath = os.path.join(os.path.dirname(bpy.data.filepath),
                                  scene.name)

    if not os.path.exists(renderfilepath):
        os.mkdir(renderfilepath)

    print(f"{worker['host']} is rendering")
    send_data = {
        "flag": "sync",
        "blend_file": worker["blendfile"],
        "scene": scene.name,
        "border": task["border"],
        "frame": task["frame_range"]
    }
    task["start_time"] = time.time()
    if task["lock"] is not None and task["lock"] != worker["host"]:
        print(
            f"[Info] task {task['frame_range']} is already locked by {task['lock']}"
        )
        return
    server.send_data(json.dumps(send_data).encode("utf-8"), worker["host"])
    server.send_data(
        json.dumps({
            "flag": "render_animation"
        }).encode("utf-8"), worker["host"])
    worker["render"] = False
    try:
        status = server.recv_data(worker["host"])
        if status:
            task["worker"] = worker["host"]
            task["end_time"] = time.time()
            task["complete"] = True
            worker["render"] = True
            print(f"[Info] {worker['host']} render image success")
    except Exception as e:
        worker["online"] = False
        print(f"[Error] Task run error: {e}")
    finally:
        task["lock"] = None


def worker_animation_thread(server, tasklist, worker):
    while any(not task["complete"] for task in tasklist):
        if worker["render"] and worker["online"]:
            for task in tasklist:
                if not task["complete"] and task["lock"] is None:
                    if worker.get("task_lock", None) is None:
                        worker["task_lock"] = threading.Lock()
                    with worker["task_lock"]:
                        if task["lock"] is None:
                            task["lock"] = worker["host"]
                            render_animation(server, worker, task)
                            break
        time.sleep(0.1)


def manage_animation_threads(server, tasklist, workerlist):
    threads = []
    for worker in workerlist:
        if worker["render"] and worker["online"]:
            thread = threading.Thread(target=worker_animation_thread,
                                      args=(server, tasklist, worker))
            thread.start()
            threads.append(thread)

    def check_threads():
        if any(thread.is_alive() for thread in threads):
            return 1.0
        bpy.context.scene.RenderSettingEnable = True
        return None

    bpy.app.timers.register(check_threads)
