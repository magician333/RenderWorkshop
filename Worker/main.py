import socket
import json
import subprocess
import time


class Client:

    def __init__(self, server_addr="", port=9815) -> None:
        self.port = port
        self.sock = None
        self.server_addr = server_addr
        self.running = False
        self.blend_file = ""
        self.scene = ""
        self.border = ()
        self.frame = 1
        self.flag = False

    def runclient(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.server_addr, self.port))
            self.running = True
            print(f"[Success] Connected success")
        except Exception as e:
            print(f"[Error] worker start error:{e}")
            self.running = False

    def recv(self):
        try:
            while True:
                recvdata = self.sock.recv(1024)
                data = json.loads(recvdata.decode("utf-8"))
                if data["flag"] == "sync":
                    self.blend_file = data["blend_file"]
                    self.scene = data["scene"]
                    self.border = data["border"]
                    self.frame = data["frame"]
                    self.flag = True
                    self.sock.send("ok".encode("utf-8"))
                elif data["flag"] == "render":
                    tmp_filename = str(time.time()) + ".png"
                    if self.flag:
                        command = [
                            blender_path, "-b", "--python", "./render.py",
                            "--", self.blend_file, self.scene, "--border",
                            str(self.border[0]),
                            str(self.border[1]),
                            str(self.border[2]),
                            str(self.border[3]), "--frame_number",
                            str(self.frame), "--render_path",
                            render_path + tmp_filename
                        ]
                        result = subprocess.run(command)
                        if result.returncode == 0:
                            # self.sock.sendall(b'file_transfer:')
                            # with open(render_path + tmp_filename, "rb") as f:
                            #     data = f.read(1024)
                            #     while data:
                            #         self.sock.sendall(data)
                            #         data = f.read(1024)
                            self.sock.send("ok".encode("utf-8"))
                            # print("Send image complete")
        except Exception as e:
            print(f"[Error] recv data error:{e}")


if __name__ == "__main__":
    print("RenderWorkShop [worker] is running...")
    with open("./config.json", "r") as f:
        config_data = json.loads(f.read())
        print(f"[Info] Reading config file")
        server_ip = config_data["server_ip"]
        print(f"[Info] server ip:{server_ip}")
        server_port = config_data["server_port"]
        print(f"[Info] server port:{server_port}")
        blender_path = r'{}'.format(config_data["blender_path"])
        print(f"[Info] blender path:{blender_path}")
        render_path = r'{}'.format(config_data["render_path"])
        print(f"[Info] redner path:{render_path}")

    client = Client(server_addr=server_ip, port=server_port)
    client.runclient()
    client.recv()
