![logo](./img/logo.png)
---
**RenderWorkshop** is an open source rendering tool for [Blender](https://www.blender.org/) that renders single frame images/image sequences using multiple devices, dramatically speeding up rendering, especially for small studios/companies/personal intranet environments with multiple devices.

[中文文档](./README_zh.md)

Pictures
---
![manager](/img/image.png)

![manager-render](/img/animation.png)

![worker](/img/worker.png)

![render_image](/img/render_image.png)

![render_animation](/img/render_animation.png)

How to use
---
1. Select the packaged resource in File - External Data and set the rendering content (rendering engine, sample rate...) and save the file
2. Place the blend file in a shared directory accessible to all workers.
3. Open the blend file using blender in manager.
4. Find RenderWorkshop in the output panel and start the server.
5. Configure the config file on the worker and run the worker.
   1. server_ip: the IP address of the server (manager)
   2. server_port: port address (manager and worker must be unified)
   3. blender_path:location of the blender executable (absolute address and preferably the same as the blender version of manger))
6. manger's parameter list will show the connected workers.
7. In the worker list, set the location where they can access the blend file (e.g. X:/render/test.blend for worker1, Z:/render/test.blend for worker2. It's better to set a uniform network path, e.g. //192.168.0.100/render).
8. Click to refresh the scene list, select the scene to be rendered, and set the corresponding parameters.
   1. if you are rendering an image, set the frame to be rendered (the default is the current frame of the scene) and the number of tiles, the recommended number of tiles is 2-10
   2. if rendering animation (frame range), set the start frame and end frame of rendering, set the number of frames to be rendered for each task (e.g., if the start frame is set to 1, the end frame is set to 10, and the number of frames to be rendered is set to 3, then it will be divided into four tasks (1-3, 4-6, 7-9, 10) to be assigned to the worker)
   3. if it is rendering animation (image tiles), set the start frame and end frame of rendering and the number of tiles, it is recommended that the number of tiles 2-10
9. click render, if it is an image, it will save the image to the blend file directory, the file name is the scene name; if it is an animation, it will save the image sequence to the folder under the blend file directory, the folder name is the scene name (Note: only png format is supported for the time being)

Working Principle
---
RenderWorkshop is divided into manager and worker.

### For Image
The manager takes the files that need to be rendered and calculates the scope of area rendering (tiles), formulates the tasks for area rendering rendering, connects to the worker host, and distributes the tasks to the available workers.
The worker is responsible for rendering the area rendering tasks distributed by the manger, and sends them to the manager after rendering is complete, so that it can continue to ‘collect’ the next task.
After all regions of the image have been rendered, the manger will use the blender compositor to merge all the tiles into a complete image.

### For Image sequence (Video)
Image sequence rendering has two modes
1. You can choose the same slice rendering mode as for images, where each frame is distributed to all workers for rendering (the current frame is rendered before the next one is rendered)
2. You can choose to set different frame ranges for different workers, similar to [Flamenco](https://flamenco.blender.org/).


### Development progress
 - [x] manager basic framework
 - [x] worker application and rendering files
 - [x] manger and worker socket communication
 - [x] manger slicing and task distribution
 - [x] worker image return
 - [x] manager merge image
 - [ ] animation rendering (partitioned rendering)
 - [x] animation rendering (multi-frame rendering)
 - [x] Add render queue(image)
 - [x] Add render queue(animation)
 - [ ] Support more file formats (Only PNG now)
 - [x] worker file packing executable
 - [ ] worker online status feedback
 - [ ] UI active refresh (current UI will not be actively refreshed, you need to move the mouse, etc. to refresh)
 - [ ] multi-platform blender test (currently based on Windows)
 - [ ] multi-version blender rendering test (currently based on blender 4.2.1)
 - [ ] Code Optimisation
 - [ ] multi-language support
  
Other
---
This project references [CrowdRender](https://www.crowd-render.com/), [BlendFarm](https://github.com/LogicReinc/LogicReinc.BlendFarm), [Flamenco]( https://flamenco.blender.org/) and other projects thoughts and ideas, the project is still under development and improvement, welcome to try and put forward your comments and suggestions to issue or send mail to [magician33333@gmail.com](magician33333@gmail.com)