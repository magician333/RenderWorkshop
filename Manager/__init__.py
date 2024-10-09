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

import threading
import bpy
import socket

from . import utils, Server

bl_info = {
    "name": "RenderWorkshop",
    "author": "purplefire",
    "description": "Implement distributed rendering for blender to speed up rendering",
    "blender": (4, 00, 0),
    "version": (0, 0, 1),
    "location": "",
    "warning": "",
    "category": "Generic",
}


hostname = socket.gethostname()
ip = socket.gethostbyname(hostname)
server = Server.Server(host=ip)


class RenderWorkshopMenu(bpy.types.Panel):
    bl_label = "RenderWorkshop"
    bl_idname = "renderworkshop"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        server_box = layout.box()
        server_box.operator(
            StartServerOperator.bl_idname, text=StartServerOperator.bl_label
        )
        server_box.prop(scene, "ServerPort", text="Port")
        net_row = server_box.row()
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        net_row.label(text="Local IP: " + ip)
        net_row.label(text="Port: " + str(context.scene.ServerPort))
        server_box.label(text=context.scene.ServerStatus)
        layout.separator()
        layout.template_list(
            "WorkerItemList",
            "Workers_list",
            scene,
            "Workers_list",
            scene,
            "Workers_index",
            type="DEFAULT",
        )
        layout.separator(type="LINE")

        tab = layout.column().box()
        tabrow = tab.row()
        tabs = tabrow.row()
        tabs.prop(context.scene, "TabIndex", expand=True)

        if scene.TabIndex == "Image":
            render_setting = tab.column()
            render_setting.prop(scene, "ShowImagePreview", text="Show Image Preview")
            render_setting.label(
                text="Can't render without setting camera", icon="INFO"
            )
            render_setting.template_list(
                "SCENE_IMAGE_UL_scene_list",
                "",
                scene,
                "Scene_image_list",
                scene,
                "Scene_image_index",
                type="DEFAULT",
            )
            render_setting.separator()
            render_button = render_setting.row()
            render_button.operator(
                RefreshSceneImageListOperator.bl_idname,
                text=RefreshSceneImageListOperator.bl_label,
                icon="FILE_REFRESH",
            )
            render_button.operator(
                RenderImageOperator.bl_idname,
                text=RenderImageOperator.bl_label,
                icon="FILE_IMAGE",
            )

        elif scene.TabIndex == "Animation":
            render_setting = tab.column()
            render_setting.separator()

            animation_tab = render_setting.column()
            animation_tab_row = animation_tab.row()
            animation_tabs = animation_tab_row.row()
            animation_tabs.alignment = "CENTER"

            animation_tabs.prop(scene, "AnimationFun", text="Render Method")

            if scene.AnimationFun == "Frames":
                render_setting.label(
                    text="Can't render without setting camera", icon="INFO"
                )
                render_setting.template_list(
                    "SCENE_ANIMATION_UL_scene_list",
                    "SceneAnimationItem",
                    scene,
                    "Scene_animation_list",
                    scene,
                    "Scene_animation_index",
                    type="DEFAULT",
                )
            elif scene.AnimationFun == "Tiles":
                render_setting.separator()
            render_setting.separator()
            render_button = render_setting.row()
            render_button.operator(
                RefreshSceneImageListOperator.bl_idname,
                text=RefreshSceneImageListOperator.bl_label,
                icon="FILE_REFRESH",
            )
            render_button.operator(
                RenderAnimatonOperator.bl_idname,
                text=RenderAnimatonOperator.bl_label,
                icon="FILE_MOVIE",
            )
        render_setting.enabled = True


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

        return {"FINISHED"}


class WorkerItem(bpy.types.PropertyGroup):
    host: bpy.props.StringProperty(name="Host")  # type: ignore

    blendfile: bpy.props.StringProperty(name="blendfile")  # type: ignore


class WorkerItemList(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        row = layout.row(align=True)
        row.label(text=item.host)
        row.prop(item, "blendfile", text="")
        row.operator(DeleteHostOperator.bl_idname, text="", icon="X").index = index


class DeleteHostOperator(bpy.types.Operator):
    bl_idname = "render.deletehost"
    bl_label = "Delete Host"

    index: bpy.props.IntProperty()  # type: ignore

    def execute(self, context):
        scene = context.scene

        item = scene.Workers_list[self.index]
        server.del_host_from_list(item.host)
        self.report({"INFO"}, f"{item.host} closed.")

        scene.Workers_list.remove(self.index)
        return {"FINISHED"}


class RefreshSceneImageListOperator(bpy.types.Operator):
    bl_idname = "render.refresh_image_scene"
    bl_label = "Refresh Scene"

    def has_camera(self, scene):
        for obj in scene.objects:
            if obj.type == "CAMERA":
                return True
        return False

    def execute(self, context):
        context.scene.Scene_image_list.clear()
        for scene in bpy.data.scenes:
            item = context.scene.Scene_image_list.add()
            item.scene_name = scene.name
            item.frame = scene.frame_current
            item.tiles = 4
            item.render = False
            item.enabled = self.has_camera(scene)

        context.scene.Scene_animation_list.clear()
        for scene in bpy.data.scenes:
            item = context.scene.Scene_animation_list.add()
            item.scene_name = scene.name
            item.frame_start = 1
            item.frame_end = scene.frame_end
            item.render = False
            item.enabled = self.has_camera(scene)

        return {"FINISHED"}


class SceneImageItem(bpy.types.PropertyGroup):
    render: bpy.props.BoolProperty(
        name="Render", default=False, description="Check the item to render"
    )  # type: ignore
    scene_name: bpy.props.StringProperty(name="Scene name")  # type: ignore
    frame: bpy.props.IntProperty(name="Frame", description="Set render frame")  # type: ignore
    tiles: bpy.props.IntProperty(
        name="Tiles", min=2, max=10, description="Set tiles to render"
    )  # type: ignore
    enabled: bpy.props.BoolProperty(default=True)  # type: ignore


class SCENE_IMAGE_UL_scene_list(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        row = layout.row(align=True)
        row.prop(item, "render", text="")
        row.label(text=item.scene_name, translate=False)
        row.prop(item, "frame", text="Frame")
        row.prop(
            item,
            "tiles",
            text="Tiles",
        )
        row.enabled = item.enabled


class SceneAnimationItem(bpy.types.PropertyGroup):
    render: bpy.props.BoolProperty(
        name="Render", default=False, description="Check the item to render"
    )  # type: ignore
    scene_name: bpy.props.StringProperty(name="Scene name", description="Scene Name")  # type: ignore
    frame_start: bpy.props.IntProperty(name="Start", description="Set start Frame")  # type: ignore
    frame_end: bpy.props.IntProperty(name="End", description="Set end Frame")  # type: ignore
    frame_split: bpy.props.IntProperty(
        name="FrameSplit", description="Set frame split num", default=15
    )  # type: ignore
    enabled: bpy.props.BoolProperty(default=True)  # type: ignore


class SCENE_ANIMATION_UL_scene_list(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        row = layout.row(align=True)
        row.prop(item, "render", text="")
        row.label(text=item.scene_name, translate=False)
        row.prop(item, "frame_start", text="Start")
        row.prop(item, "frame_end", text="End")
        row.prop(item, "frame_split", text="Frame Split")
        row.enabled = item.enabled


class RenderImageOperator(bpy.types.Operator):
    bl_idname = "render.render_image"
    bl_label = "Render Image"

    def has_select(self):
        for i in bpy.context.scene.Scene_image_list:
            if i.render:
                return True
        return False

    def execute(self, context):
        area = None
        if bpy.data.filepath == "":
            self.report(type={"ERROR"}, message="Must save file to share storage")
            return {"FINISHED"}
        if len(context.scene.Workers_list) == 0:
            self.report(type={"ERROR"}, message="No workers available")
            return {"FINISHED"}
        if not self.has_select():
            self.report(type={"ERROR"}, message="No scene selected for rendering")
            return {"FINISHED"}

        self.report(type={"INFO"}, message="Start Render Image")
        if context.scene.ShowImagePreview:
            bpy.ops.wm.window_new()
            area = bpy.context.window_manager.windows[-1].screen.areas[0]
            area.ui_type = "IMAGE_EDITOR"
        utils.process_scene_list(
            context=context, server=server, area=area, method="image"
        )
        return {"FINISHED"}


class RenderAnimatonOperator(bpy.types.Operator):
    bl_idname = "render.render_animation"
    bl_label = "Render Animation"

    def has_select(self):
        for i in bpy.context.scene.Scene_animation_list:
            if i.render:
                return True
        return False

    def execute(self, context):
        if bpy.data.filepath == "":
            self.report(type={"ERROR"}, message="Must save file to share storage")
            return {"FINISHED"}
        if len(context.scene.Workers_list) == 0:
            self.report(type={"ERROR"}, message="No workers available")
            return {"FINISHED"}
        if not self.has_select():
            self.report(type={"ERROR"}, message="No scene selected for rendering")
            return {"FINISHED"}
        # bpy.ops.wm.window_new()
        # area = bpy.context.window_manager.windows[-1].screen.areas[0]
        # area.ui_type = "FILES"
        if context.scene.AnimationFun == "Frames":
            self.report(type={"INFO"}, message="Start Render Animation")
            utils.process_scene_list(context, server, None, "animation")
        else:
            self.report(
                type={"INFO"}, message="Render Animation by tiles is coming soon"
            )
            # utils.render_animation_tiles(context,server,start_frame,end_frame)

        return {"FINISHED"}


def register():
    bpy.utils.register_class(RenderWorkshopMenu)
    bpy.utils.register_class(StartServerOperator)
    bpy.utils.register_class(WorkerItemList)
    bpy.utils.register_class(DeleteHostOperator)
    bpy.utils.register_class(RenderImageOperator)
    bpy.utils.register_class(RenderAnimatonOperator)
    bpy.utils.register_class(WorkerItem)
    bpy.utils.register_class(SceneImageItem)
    bpy.utils.register_class(SCENE_IMAGE_UL_scene_list)
    bpy.utils.register_class(RefreshSceneImageListOperator)
    bpy.utils.register_class(SceneAnimationItem)
    bpy.utils.register_class(SCENE_ANIMATION_UL_scene_list)

    bpy.types.Scene.Scene_image_list = bpy.props.CollectionProperty(type=SceneImageItem)
    bpy.types.Scene.Scene_image_index = bpy.props.IntProperty()
    bpy.types.Scene.ShowImagePreview = bpy.props.BoolProperty(
        name="ImagePreview", default=True
    )
    bpy.types.Scene.Scene_animation_list = bpy.props.CollectionProperty(
        type=SceneAnimationItem
    )
    bpy.types.Scene.Scene_animation_index = bpy.props.IntProperty()
    bpy.types.Scene.Workers_list = bpy.props.CollectionProperty(type=WorkerItem)
    bpy.types.Scene.Workers_index = bpy.props.IntProperty()

    bpy.types.Scene.Frames = bpy.props.IntProperty(
        name="Frames",
        description="Selecting the number of frame split",
        default=15,
        min=1,
        max=50,
    )
    bpy.types.Scene.Host = bpy.props.StringProperty(name="Host", description="Add Host")
    bpy.types.Scene.ServerPort = bpy.props.IntProperty(
        name="ServerPort", description="set server port", default=9815
    )
    bpy.types.Scene.ServerStatus = bpy.props.StringProperty(
        name="Server Status", default="Server is stopped"
    )

    bpy.types.Scene.FrameStart = bpy.props.IntProperty(
        name="FrameStart", default=1, min=0
    )
    bpy.types.Scene.FrameEnd = bpy.props.IntProperty(name="FrameEnd", default=1, min=0)

    bpy.types.Scene.RenderSettingEnable = bpy.props.BoolProperty(
        name="RenderSettingEnable", default=True
    )
    bpy.types.Scene.TabIndex = bpy.props.EnumProperty(
        items=[
            ("Image", "Image", "Render Image tab"),
            ("Animation", "Animation", "Render Animation tab"),
        ],
        default="Image",
    )
    bpy.types.Scene.AnimationFun = bpy.props.EnumProperty(
        items=[
            ("Frames", "Frames", "Use Frames to render animation"),
            ("Tiles", "Tiles", "Use Tiles to render animation"),
        ],
        default="Frames",
    )


def unregister():
    bpy.utils.unregister_class(RenderWorkshopMenu)
    bpy.utils.unregister_class(StartServerOperator)
    bpy.utils.unregister_class(WorkerItemList)
    bpy.utils.unregister_class(DeleteHostOperator)
    bpy.utils.unregister_class(RenderImageOperator)
    bpy.utils.unregister_class(RenderAnimatonOperator)
    bpy.utils.unregister_class(WorkerItem)
    bpy.utils.unregister_class(SceneImageItem)
    bpy.utils.unregister_class(SCENE_IMAGE_UL_scene_list)
    bpy.utils.unregister_class(RefreshSceneImageListOperator)
    bpy.utils.unregister_class(SceneAnimationItem)
    bpy.utils.unregister_class(SCENE_ANIMATION_UL_scene_list)

    del bpy.types.Scene.Workers_list
    del bpy.types.Scene.Workers_index
    del bpy.types.Scene.Frames
    del bpy.types.Scene.Host
    del bpy.types.Scene.FrameStart
    del bpy.types.Scene.FrameEnd
    del bpy.types.Scene.RenderSettingEnable
    del bpy.types.Scene.TabIndex
    del bpy.types.Scene.Scene_image_list
    del bpy.types.Scene.Scene_image_index
    del bpy.types.Scene.Scene_animation_list
    del bpy.types.Scene.Scene_animation_index
