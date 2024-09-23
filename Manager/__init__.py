# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "Renderworkshop",
    "author": "purplefire",
    "description":
    "Implement distributed rendering for blender to speed up rendering",
    "blender": (4, 00, 0),
    "version": (0, 0, 1),
    "location": "",
    "warning": "",
    "category": "Generic",
}

import json
import threading
import bpy
import socket
from . import utils, Server

hostname = socket.gethostname()
ip = socket.gethostbyname(hostname)
server = Server.Server(host=ip)


class RenderWorkshopMenu(bpy.types.Panel):
    bl_label = "RenderWorkshop"
    bl_idname = "RENDER_PT_renderworkshop"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        server_box = layout.box()
        server_box.operator(StartServerOperator.bl_idname,
                            text=StartServerOperator.bl_label)
        server_box.prop(scene, "ServerPort", text="Port")
        net_row = server_box.row()
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        net_row.label(text="Local IP: " + ip)
        net_row.label(text="Port: " + str(context.scene.ServerPort))

        server_box.label(text=context.scene.ServerStatus)
        layout.separator()
        layout.template_list("WorkerItemList",
                             "Workers",
                             scene,
                             "Workers",
                             scene,
                             "Workers_index",
                             type="DEFAULT")
        render_setting = layout.column()
        render_setting.prop(scene, "Tiles", text="Tile Split")
        frame_row = render_setting.row(align=True)
        frame_row.prop(scene, "FrameStart", text="Frame Start")
        frame_row.prop(scene, "FrameEnd", text="Frame End")

        render_row = render_setting.row()
        render_row.operator(RenderImageOperator.bl_idname,
                            text=RenderImageOperator.bl_label,
                            icon="FILE_IMAGE")
        render_row.operator(RenderAnimatonOperator.bl_idname,
                            text=RenderAnimatonOperator.bl_label,
                            icon="FILE_MOVIE")
        render_setting.enabled = scene.RenderSettingEnable


class StartServerOperator(bpy.types.Operator):
    bl_idname = "render.start_server"
    bl_label = "Start Server"

    def execute(self, context):
        if not server.running:
            try:
                server.port = context.scene.ServerPort
                server.conn_list = {}
                server_thread = threading.Thread(target=server.run_server)
                server_thread.start()
                self.report({"INFO"}, message="Server start")
                StartServerOperator.bl_label = "Stop Server"
            except Exception as e:
                print(f"[Error] Stop Server error:{e}")
                server.stop_server()
                StartServerOperator.bl_label = "Start Server"

        else:
            server.stop_server()
            self.report({"INFO"}, message="Server stop")
            StartServerOperator.bl_label = "Start Server"

        return {'FINISHED'}


class WorkerItem(bpy.types.PropertyGroup):

    host: bpy.props.StringProperty(name="Host")  # type: ignore
    status: bpy.props.StringProperty(name="Connection Status",
                                     get=lambda self: "Connected",
                                     options={'HIDDEN'})  # type: ignore
    blendfile: bpy.props.StringProperty(name="blendfile")  # type: ignore


class WorkerItemList(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        row = layout.row(align=True)
        row.label(text=item.host)
        row.prop(item, "blendfile", text="")
        row.operator(SyncDataOperator.bl_idname,
                     icon="KEYTYPE_JITTER_VEC",
                     text="").index = index
        row.operator(DeleteHostOperator.bl_idname, text="",
                     icon='X').index = index


class SyncDataOperator(bpy.types.Operator):
    bl_idname = "render.verify"
    bl_label = "Verify"

    index: bpy.props.IntProperty()  # type: ignore

    def execute(self, context):
        scene = context.scene
        render_item = scene.Workers[self.index]
        borders = utils.getborders(context.scene.Tiles)
        send_data = {
            "flag": "sync",
            "blend_file": render_item.blendfile,
            "scene": bpy.context.scene.name,
            "border": borders[0],
            "frame": 1
        }
        server.send_data(
            json.dumps(send_data).encode("utf-8"), render_item.host)
        return {'FINISHED'}


class DeleteHostOperator(bpy.types.Operator):
    bl_idname = "render.deletehost"
    bl_label = "Delete Host"

    index: bpy.props.IntProperty()  # type: ignore

    def execute(self, context):
        scene = context.scene

        item = scene.Workers[self.index]
        server.del_host_from_list(item.host)
        self.report({'INFO'}, f"{item.host} closed.")

        scene.Workers.remove(self.index)
        return {'FINISHED'}


class RenderImageOperator(bpy.types.Operator):
    bl_idname = "render.render_image"
    bl_label = "Render Image"

    def execute(self, context):
        tasklist = []
        for index, border in enumerate(utils.getborders(context.scene.Tiles)):
            task = {
                "index": index,
                "border": border,
                "worker": "",
                "start_time": 0,
                "end_time": 0,
                "complete": False
            }
            tasklist.append(task)

        workerlist = []
        for item in context.scene.Workers:
            worker = {
                "host": item.host,
                "render": True,
                "online": True,
                "blendfile": item.blendfile.strip('"')
            }
            workerlist.append(worker)

        bpy.ops.wm.window_new()
        area = bpy.context.window_manager.windows[-1].screen.areas[0]
        area.ui_type = 'IMAGE_EDITOR'

        utils.manage_threads(server, area, tasklist, workerlist)

        return {'FINISHED'}


class RenderAnimatonOperator(bpy.types.Operator):
    bl_idname = "render.render_animation"
    bl_label = "Render Animation"

    def execute(self, context):
        return {'FINISHED'}


def register():
    bpy.utils.register_class(RenderWorkshopMenu)
    bpy.utils.register_class(StartServerOperator)
    bpy.utils.register_class(WorkerItemList)
    bpy.utils.register_class(DeleteHostOperator)
    bpy.utils.register_class(RenderImageOperator)
    bpy.utils.register_class(RenderAnimatonOperator)
    bpy.utils.register_class(SyncDataOperator)
    bpy.utils.register_class(WorkerItem)

    bpy.types.Scene.Workers = bpy.props.CollectionProperty(type=WorkerItem)
    bpy.types.Scene.Workers_index = bpy.props.IntProperty()
    bpy.types.Scene.Tiles = bpy.props.IntProperty(
        name="Tiles",
        description="Selecting the number of cuts",
        default=4,
        min=2,
        max=10)
    bpy.types.Scene.Host = bpy.props.StringProperty(name="Host",
                                                    description="Add Host")
    bpy.types.Scene.ServerPort = bpy.props.IntProperty(
        name="ServerPort", description="set server port", default=9815)
    bpy.types.Scene.ServerStatus = bpy.props.StringProperty(
        name="Server Status", default="Server is stopped")

    bpy.types.Scene.FrameStart = bpy.props.IntProperty(name="FrameStart",
                                                       default=1,
                                                       min=0)
    bpy.types.Scene.FrameEnd = bpy.props.IntProperty(name="FrameEnd",
                                                     default=1,
                                                     min=0)

    bpy.types.Scene.RenderSettingEnable = bpy.props.BoolProperty(
        name="RenderSettingEnable", default=True)


def unregister():
    bpy.utils.unregister_class(RenderWorkshopMenu)
    bpy.utils.unregister_class(StartServerOperator)
    bpy.utils.unregister_class(WorkerItemList)
    bpy.utils.unregister_class(DeleteHostOperator)
    bpy.utils.unregister_class(RenderImageOperator)
    bpy.utils.unregister_class(RenderAnimatonOperator)
    bpy.utils.unregister_class(WorkerItem)
    bpy.utils.unregister_class(SyncDataOperator)

    del bpy.types.Scene.Workers
    del bpy.types.Scene.Workers_index
    del bpy.types.Scene.Tiles
    del bpy.types.Scene.Host
    del bpy.types.Scene.FrameStart
    del bpy.types.Scene.FrameEnd
    del bpy.types.Scene.RenderSettingEnable
