![logo](./img/logo.png)
---
**RenderWorkshop** enhances [Blender](https://www.blender.org/)'s rendering capabilities by leveraging multiple devices to render single-frame images or image sequences, significantly accelerating the process. This open-source tool is ideal for small studios, companies, and personal networks with multiple devices.

[中文文档](./README_zh.md)

## Screenshots
![Manager Interface](/img/manager_image.png)

![Rendering Animation](/img/manager_animation.png)

![Worker Rendering](/img/worker_image.png)

![Worker Animation](/img/worker_animation.png)

![Tile Rendering](/img/render_tiles.png)

## How to Use
**Important:** Ensure all computers involved in rendering are set not to hibernate automatically.
1. Choose the packaged resource in File > External Data, configure the rendering settings (engine, sample rate, etc.), and save.
2. Store the `.blend` file in a shared directory accessible by all workers.
3. Launch Blender as the manager and open the `.blend` file.
4. Access RenderWorkshop in the N panel to initiate the server.
5. On worker computers, configure the settings in the config file and launch the worker. For GPU rendering, adjust "Cycles rendering devices" in Blender's Edit > Preferences > System.
   - **server_ip:** The manager's IP address.
   - **server_port:** The port used by both manager and workers.
   - **blender_path:** The absolute path to the Blender executable, preferably matching the manager's version.
6. The manager's parameter list will display connected workers.
7. In the worker list, specify the network path to access the `.blend` file (e.g., `//192.168.0.100/render` for all workers).
8. Refresh the scene list, select the scene to render, and configure the parameters:
   - For single images, set the frame and the number of tiles (recommended: 2-10).
   - For animations, set the start and end frames and the number of frames per task.
9. Click render. Images will be saved in the `.blend` directory under the scene name. Animations will be saved in a folder named after the scene within the `.blend` directory.

## Working Principle
RenderWorkshop operates with a manager and workers.

### For Single Images
The manager processes the files to be rendered, calculates the rendering area (tiles), assigns tasks, connects to worker hosts, and distributes these tasks.
Workers execute the assigned rendering tasks and return them to the manager, which then proceeds to assign the next task.
Once all image areas are rendered, the manager uses Blender's compositor to compile the tiles into a complete image.

![Image Rendering Process](/img/interpret_image.png)

### For Image Sequences (Video)
Specify the frame range and the number of splits; the manager automatically divides the frame range and assigns segments to different workers.
Workers handle the frame range rendering tasks assigned by the manager, similar to [Flamenco](https://flamenco.blender.org/).

![Animation Rendering Process](/img/interpret_animation.png)

## Development Status
- [x] Manager framework established
- [x] Worker application and file rendering
- [x] Socket communication between manager and worker
- [x] Task slicing and distribution by manager
- [x] Worker image return
- [x] Manager image merging
- [x] Animation rendering support
- [x] Render queue added for images and animations
- [x] GPU rendering support (Cycles only)
- [x] Info List added
- [x] Render animation support check missing frames and re-render it
- [ ] Expanded file format support (currently PNG only)
- [x] Worker file packaging for executables
- [ ] Real-time worker status feedback
- [ ] Active UI refresh (current UI requires user interaction to refresh)
- [ ] Cross-platform Blender compatibility testing
- [ ] Multi-version Blender rendering compatibility testing
- [ ] Code optimization

## Acknowledgements
This project draws inspiration from [CrowdRender](https://www.crowd-render.com/), [BlendFarm](https://github.com/LogicReinc/LogicReinc.BlendFarm), [Flamenco](https://flamenco.blender.org/), and other projects. It is actively being developed and improved. Feedback and suggestions are welcome via issue tracking or by emailing [magician33333@gmail.com](mailto:magician33333@gmail.com).