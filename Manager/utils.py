import json
import os
import shutil
import threading
import time
import bpy
from enum import Enum, auto


class RenderStatus(Enum):
    PENDING = auto()
    RENDERING = auto()
    COMPLETED = auto()


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
        item = bpy.context.scene.Scene_Msg_list.add()
        item.msg = "[Error] temp path error"
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
        input_image = tree.nodes.new(type="CompositorNodeImage")
        input_image.image = image
        input_nodes.append(input_image)
    result_image = input_nodes[0]
    for i in range(1, len(input_nodes)):
        merge_node = tree.nodes.new(type="CompositorNodeAlphaOver")
        links.new(result_image.outputs[0], merge_node.inputs[1])
        links.new(input_nodes[i].outputs[0], merge_node.inputs[2])
        result_image = merge_node

    result_node = tree.nodes.new(type="CompositorNodeComposite")
    links.new(result_image.outputs[0], result_node.inputs[0])

    composite_file_path = os.path.join(outputfilepath, outputfilename)
    scene.render.filepath = composite_file_path
    scene.render.use_border = False
    bpy.ops.render.render(write_still=True)

    for n in tree.nodes:
        tree.nodes.remove(n)
    bpy.context.scene.use_nodes = False
    if area:
        image = bpy.data.images.load(composite_file_path)
        area.spaces.active.image = image


def image_task(server, area, task, worker):
    if worker["render"] and worker["online"]:
        item = bpy.context.scene.Scene_Msg_list.add()
        item.msg = f"{worker['host']} is rendering tile {task['index']}"
        send_data = {
            "flag": "sync",
            "blend_file": worker["blendfile"],
            "scene": task["scene_name"],
            "border": task["border"],
            "device": worker["device"],
            "frame": task["frame"],
        }
        task["start_time"] = time.time()
        if task["lock"] is not None and task["lock"] != worker["host"]:
            print(
                f"[Info] task {task['frame_range']} is already locked by {task['lock']}"
            )
            return
        server.send_data(json.dumps(send_data).encode("utf-8"), worker["host"])
        server.send_data(
            json.dumps({"flag": "render_image"}).encode("utf-8"), worker["host"]
        )
        worker["render"] = False

        try:
            tempfilename = server.recv_data(worker["host"])
            if tempfilename == "ok":
                return
            if tempfilename:
                img = os.path.join(
                    os.path.dirname(bpy.data.filepath), "temp", tempfilename
                )
                if area:
                    image = bpy.data.images.load(img)
                    area.spaces.active.image = image
                task["worker"] = worker["host"]
                task["end_time"] = time.time()
                worker["render"] = True
                task["complete"] = RenderStatus.COMPLETED
        except Exception as e:
            worker["online"] = False
            item = bpy.context.scene.Scene_Msg_list.add()
            item.msg = f"[Error] task run error: {e}"
        finally:
            task["lock"] = None


def worker_thread(server, area, tasklist, worker, method):
    while any(task["complete"] != RenderStatus.COMPLETED for task in tasklist):
        if worker["render"] and worker["online"]:
            for task in tasklist:
                if task["complete"] == RenderStatus.PENDING and task["lock"] is None:
                    if worker.get("task_lock", None) is None:
                        worker["task_lock"] = threading.Lock()
                    with worker["task_lock"]:
                        if task["lock"] is None:
                            task["lock"] = worker["host"]
                            task["complete"] = RenderStatus.RENDERING
                            if method == "image":
                                image_task(server, area, task, worker)
                            else:
                                animation_task(server, worker, task)
                            break
        time.sleep(0.1)


def manage_image_threads(
    server, area, tasklist, workerlist, outputfilepath, outputfilename, finish_callback
):
    threads = []
    tempfilepath = os.path.join(os.path.dirname(bpy.data.filepath), "temp")
    if os.path.exists(tempfilepath):
        shutil.rmtree(tempfilepath)
        os.mkdir(tempfilepath)
    else:
        os.mkdir(tempfilepath)
    for worker in workerlist:
        thread = threading.Thread(
            target=worker_thread, args=(server, area, tasklist, worker, "image")
        )
        thread.start()
        threads.append(thread)

    def check_threads():
        if any(thread.is_alive() for thread in threads):
            return 1.0
        else:
            for thread in threads:
                thread.join()
            merge_image(
                area,
                outputfilepath=outputfilepath,
                outputfilename=outputfilename,
            )
            # Clear temp directory and temp image
            shutil.rmtree(tempfilepath)
            # Clear temp image perview in blender
            for image in bpy.data.images:
                if not image.users:
                    bpy.data.images.remove(image)
            finish_callback()
            return None

    bpy.app.timers.register(check_threads)


def animation_task(server, worker, task):
    scene = bpy.context.scene
    renderfilepath = os.path.join(os.path.dirname(bpy.data.filepath), scene.name)

    if not os.path.exists(renderfilepath):
        os.mkdir(renderfilepath)
    item = bpy.context.scene.Scene_Msg_list.add()
    item.msg = f"{worker['host']} is rendering"
    send_data = {
        "flag": "sync",
        "blend_file": worker["blendfile"],
        "device": worker["device"],
        "scene": task["scene_name"],
        "border": task["border"],
        "frame": task["frame_range"],
    }
    task["start_time"] = time.time()
    if task["lock"] is not None and task["lock"] != worker["host"]:
        print(f"[Info] task {task['frame_range']} is already locked by {task['lock']}")
        return
    server.send_data(json.dumps(send_data).encode("utf-8"), worker["host"])
    server.send_data(
        json.dumps({"flag": "render_animation"}).encode("utf-8"), worker["host"]
    )
    worker["render"] = False
    try:
        status = server.recv_data(worker["host"])
        if status:
            task["worker"] = worker["host"]
            task["end_time"] = time.time()
            task["complete"] = RenderStatus.COMPLETED
            worker["render"] = True
            item = bpy.context.scene.Scene_Msg_list.add()
            item.msg = f"[Info] {worker['host']} render image success"
    except Exception as e:
        worker["online"] = False
        item = bpy.context.scene.Scene_Msg_list.add()
        item.msg = f"[Error] Task run error: {e}"
    finally:
        task["lock"] = None


def manage_animation_threads(server, tasklist, workerlist, finish_callback):
    threads = []
    for worker in workerlist:
        if worker["render"] and worker["online"]:
            thread = threading.Thread(
                target=worker_thread, args=(server, None, tasklist, worker, "animation")
            )
            thread.start()
            threads.append(thread)

    def check_threads():
        if any(thread.is_alive() for thread in threads):
            return 1.0
        bpy.context.scene.RenderSettingEnable = True
        finish_callback()
        return None

    bpy.app.timers.register(check_threads)


def manage_animation_tiles_threads(
    server,
    area,
    tasklist,
    workerlist,
    outputfilepath,
    outputfilename,
    rendering,
):
    threads = []
    tempfilepath = os.path.join(os.path.dirname(bpy.data.filepath), "temp")
    if os.path.exists(tempfilepath):
        shutil.rmtree(tempfilepath)
        os.mkdir(tempfilepath)
    else:
        os.mkdir(tempfilepath)
    for worker in workerlist:
        thread = threading.Thread(
            target=worker_thread, args=(server, area, tasklist, worker, "image")
        )
        thread.start()
        threads.append(thread)

    def check_threads():
        nonlocal rendering
        if any(thread.is_alive() for thread in threads):
            return 1.0
        if rendering:
            merge_image(
                area, outputfilepath=outputfilepath, outputfilename=outputfilename
            )
            shutil.rmtree(tempfilepath)
            bpy.context.scene.RenderSettingEnable = True
            rendering = False
        return None

    bpy.app.timers.register(check_threads)


def render_image(context, server, area, scene_name, frame, tiles, callback):
    tasklist = []
    for index, border in enumerate(getborders(tiles)):
        task = {
            "index": index,
            "border": border,
            "worker": "",
            "start_time": 0,
            "end_time": 0,
            "scene_name": scene_name,
            "complete": RenderStatus.PENDING,
            "lock": None,
            "frame": [frame, frame + 1],
        }

        tasklist.append(task)
    workerlist = []
    for item in context.scene.Workers_list:
        worker = {
            "host": item.host,
            "render": True,
            "online": True,
            "device": item.device,
            "blendfile": item.blendfile.strip('"'),
        }
        workerlist.append(worker)

    outputfilepath = os.path.dirname(bpy.data.filepath)
    outputfilename = scene_name + ".png"
    context.scene.RenderSettingEnable = False
    manage_image_threads(
        server=server,
        area=area,
        tasklist=tasklist,
        workerlist=workerlist,
        outputfilepath=outputfilepath,
        outputfilename=outputfilename,
        finish_callback=callback,
    )


def render_animation_frame(
    context, server, scene_name, start_frame, end_frame, step, callback
):
    tasklist = []
    current_start = start_frame
    index = 0
    step = step

    while current_start <= end_frame:
        current_end = min(current_start + step - 1, end_frame)
        task = {
            "index": index,
            "border": [0, 1, 0, 1],
            "worker": "",
            "scene_name": scene_name,
            "start_time": 0,
            "end_time": 0,
            "complete": RenderStatus.PENDING,
            "lock": None,
            "frame_range": [current_start, current_end],
        }
        tasklist.append(task)
        current_start += step
        index += 1

    workerlist = []
    for item in context.scene.Workers_list:
        worker = {
            "host": item.host,
            "render": True,
            "online": True,
            "device": item.device,
            "blendfile": item.blendfile.strip('"'),
        }
        workerlist.append(worker)
    manage_animation_threads(
        server,
        tasklist,
        workerlist,
        finish_callback=callback,
    )


def render_animation_tiles(context, server, start_frame, end_frame, render_finish):
    tasklist = []
    for index, border in enumerate(getborders(context.scene.Tiles)):
        task = {
            "index": index,
            "border": border,
            "worker": "",
            "start_time": 0,
            "end_time": 0,
            "complete": RenderStatus.PENDING,
            "lock": None,
            "frame": [context.scene.frame_current, context.scene.frame_current + 1],
        }
        tasklist.append(task)

    workerlist = []
    for item in context.scene.Workers_list:
        worker = {
            "host": item.host,
            "render": True,
            "online": True,
            "blendfile": item.blendfile.strip('"'),
        }
        workerlist.append(worker)

    bpy.ops.wm.window_new()
    area = bpy.context.window_manager.windows[-1].screen.areas[0]
    area.ui_type = "IMAGE_EDITOR"

    outputfilepath = os.path.join(
        os.path.dirname(bpy.data.filepath), context.scene.name
    )

    if not os.path.exists(outputfilepath):
        os.mkdir(outputfilepath)

    rendering = False

    def render_frame(frame):
        nonlocal rendering
        if not rendering:
            context.scene.RenderSettingEnable = False
            outputfilename = f"{frame:04}.png"
            rendering = True

            manage_animation_tiles_threads(
                server=server,
                area=area,
                tasklist=tasklist,
                workerlist=workerlist,
                outputfilepath=outputfilepath,
                outputfilename=outputfilename,
                rendering=rendering,
                render_finish=render_finish,
            )

    def check_rendering():
        nonlocal current_frame, rendering
        if current_frame <= end_frame and not rendering:

            def render_finish():
                nonlocal current_frame
                bpy.app.timers.register(render_frame(current_frame))

            render_frame(current_frame, render_finish)
            current_frame += 1
            return 0.1
        else:
            return None

    current_frame = start_frame
    bpy.app.timers.register(check_rendering)


def process_scene_list(context, server, area, method):
    if "image" == method:
        scene_items = context.scene.Scene_image_list
    else:
        scene_items = context.scene.Scene_animation_list
    index = 0

    def process_next():
        nonlocal index
        if index < len(scene_items):
            item = scene_items[index]
            if item.render:

                def on_finish():
                    bpy.app.timers.register(process_next)

                if "image" == method:
                    render_image(
                        context=context,
                        server=server,
                        area=area,
                        scene_name=item.scene_name,
                        frame=item.frame,
                        tiles=item.tiles,
                        callback=on_finish,
                    )
                else:
                    render_animation_frame(
                        context,
                        server,
                        scene_name=item.scene_name,
                        start_frame=item.frame_start,
                        end_frame=item.frame_end,
                        step=item.frame_split,
                        callback=on_finish,
                    )
                item.render = False
            else:
                index += 1
                return 0.1
        else:
            return None

    bpy.app.timers.register(process_next)
