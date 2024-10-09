![logo](./img/logo.png)
---
**RenderWorkshop** 是适用于 [Blender](https://www.blender.org/) 的开源的分布式渲染工具，使用多台设备渲染单帧图像/图像序列，大幅加快渲染速度，尤其适用于拥有多设备的小型工作室/公司/个人内网环境。

[English Docs](./README.md)

图片
---

![manager](/img/manager_image.png)

![manager-render](/img/manager_animation.png)

![render_image](/img/worker_image.png)

![render_animation](/img/worker_animation.png)

![render_tiles](/img/render_tiles.png)

如何使用
---
1. 在文件-外部数据中选择打包资源，并设置好渲染内容（渲染引擎、采样率...）并保存文件
2. 将blend文件放在所有worker可以访问到的共享目录上
3. 使用manager的blender打开blend文件
4. 在输出面板中找到RenderWorkshop，启动服务器
5. 在worker电脑上配置好config文件，并运行worker；如果需要GPU渲染，请在worker电脑的blender-编辑-偏好设置-系统中设置"Cycles渲染设备"
   1. server_ip:即服务器（manager）的IP地址
   2. server_port:端口地址（manager和worker必须统一）
   3. blender_path:blender可执行文件位置（绝对地址且最好和manger的blender版本相同））
6. manger的参数列表将会出现已连接的worker
7. 在worker列表中设置他们访问blend文件的位置（比如worker1为X:/render/test.blend，worker2为Z:/render/test.blend。最好设置一个统一的网络路径，比如//192.168.0.100/render）
8. 点击刷新场景列表，选择需要渲染的场景，设置相应参数
   1. 如果是渲染图像，设置渲染的帧（默认为场景当前帧）和切片数量，建议切片数量2-10
   2. 如果是渲染动画(帧范围)，设置渲染的起始帧和结束帧，设置每个任务需要渲染的帧数（如起始帧设置为1，结束帧设置为10，渲染的帧数设置为3，则会分割为四个任务(1-3,4-6,7-9,10)分配给worker）
   3. 如果是渲染动画（图像分块），设置渲染的起始帧和结束帧和切片数量，建议切片数量2-10
9.  点击渲染，如果是图像，则会将图像保存到blend文件目录下，文件名为场景名；如果是动画，则会将图像序列保存到blend文件目录下的文件夹下，文件夹名为场景名（注：暂时只支持png格式）

工作原理
---
RenderWorkshop分为manager和worker两部分。

### 对于图像
manager获取需要渲染的文件并计算区域渲染的分块（tiles），制定区域渲染的渲染任务，连接 worker 主机，并将任务分配给可用的 worker。
worker负责渲染manager分发的区域渲染任务，并在渲染完成后将任务发送给manager，然后 “领取 ”下一个任务。
图像的所有区域渲染完成后，manager会使用 blender 合成器将所有分区合并成完整的图像。

### 图像序列（视频）
图像序列渲染有两种模式
1. 您可以选择与图像相同的切片渲染模式，即每一帧都分配给所有worker进行渲染（在渲染下一帧之前，先渲染当前帧）
2. 您可以选择为不同的worker设置不同的帧范围，类似于 [Flamenco](https://flamenco.blender.org/)。


开发进度
---
 - [x] manager基本框架
 - [x] worker程序及渲染文件
 - [x] manger和worker socket通信
 - [x] manger切片及任务分发
 - [x] worker图像回传
 - [x] manager图像拼接及展示
 - [ ] 动画渲染（分区渲染）
 - [x] 动画渲染（多帧渲染）
 - [x] 添加渲染队列（图像）
 - [x] 添加渲染队列（动画）
 - [x] 支持GPU渲染（仅Cycles）
 - [ ] 支持更多文件格式（目前仅支持PNG）
 - [x] worker文件打包可执行文件
 - [ ] worker在线状态反馈
 - [ ] 界面UI主动刷新（当前UI界面不会主动刷新，需要移动鼠标等方式进行刷新）
 - [ ] 多平台blender测试（当前基于Windows）
 - [ ] 多版本blender渲染测试（当前基于blender4.2.1）
 - [ ] 代码优化
 - [ ] 多语言支持


其他
---
该项目参考了[CrowdRender](https://www.crowd-render.com/)、[BlendFarm](https://github.com/LogicReinc/LogicReinc.BlendFarm)、[Flamenco](https://flamenco.blender.org/)等项目的思路和想法，该项目还在开发完善中，欢迎尝试并提出您的意见和建议至issue或发送邮件至[magician33333@gmail.com](magician33333@gmail.com)