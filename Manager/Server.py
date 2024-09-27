import os
import threading
import time
import bpy
import socket


class Server:

    def __init__(self, host="127.0.0.1", port=9815):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        self.conn_list = {}

    def run_server(self):
        try:
            context = bpy.context
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind((self.host, self.port))
            self.sock.listen()
            self.running = True
            context.scene.ServerStatus = "Server is running..."

        except Exception as e:
            print(f"[Error] server error:{e}")
            try:
                self.sock.close()
            except Exception as e:
                print(f"[Error] close server error:{e}")
                context.scene.ServerStatus = "Server cause error"

        while self.running:
            try:
                conn, addr = self.sock.accept()
                if addr[0] in self.conn_list.keys():
                    conn.close()
                    break
                self.conn_list[addr[0]] = conn
                self.add_host_to_list(addr[0])
                threading.Thread(target=self.handle_client,
                                 args=(conn, addr[0])).start()

            except socket.error as e:
                print(f"[Error] runserver error:{e}")
                break

        if self.sock:
            self.sock.close()

    def add_host_to_list(self, host):
        scene = bpy.context.scene
        new_item = scene.Workers.add()
        new_item.host = host

    def del_host_from_list(self, client_address):
        try:
            self.conn_list[client_address].close()
            del self.conn_list[client_address]
        except Exception as e:
            print(f"[Error] delete host error:{e}")

    def handle_client(self, conn, addr):
        with conn:
            while True:
                try:
                    data = conn.recv(1024)
                    if not data:
                        break
                    else:
                        print(data)
                except Exception as e:
                    print(f"[Error] connect error: {e}")
                    break

    def send_data(self, data, addr):
        try:
            conn = self.conn_list[addr]
            conn.sendall(data)
        except Exception as e:
            print("[Error] send data error", e)

    def recv_data(self, addr):
        try:
            conn = self.conn_list[addr]
            data = conn.recv(1024)
            return data.decode("utf-8")
        except Exception as e:
            print(f"[Error] recv data error:{e}")

    def stop_server(self):
        context = bpy.context

        self.running = False
        for ip in self.conn_list:
            self.conn_list[ip].close()
            context.scene.Workers.clear()
        self.conn_list = {}
        if self.sock:
            self.sock.close()
            self.sock = None
        context.scene.ServerStatus = "Server is stopped"
