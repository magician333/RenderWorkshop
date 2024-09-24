package main

import (
	"encoding/json"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"time"
)

type Client struct {
	serverAddr string
	port       int
	conn       net.Conn
	running    bool
	blendFile  string
	scene      string
	border     []float64
	frame      int
	flag       bool
}

func (c *Client) runClient() {
	address := fmt.Sprintf("%s:%d", c.serverAddr, c.port)
	conn, err := net.Dial("tcp", address)
	if err != nil {
		fmt.Printf("[Error] worker start error: %v\n", err)
		c.running = false
		return
	}

	c.conn = conn
	c.running = true
	fmt.Println("[Success] Connected success")
}

func (c *Client) recv() {
	buffer := make([]byte, 1024)
	for {
		n, err := c.conn.Read(buffer)
		if err != nil {
			fmt.Printf("[Error] recv data error: %v\n", err)
			break
		}

		var data map[string]interface{}
		if err := json.Unmarshal(buffer[:n], &data); err != nil {
			fmt.Printf("[Error] json unmarshal error: %v\n", err)
			continue
		}

		switch data["flag"] {
		case "sync":
			c.blendFile = data["blend_file"].(string)
			c.scene = data["scene"].(string)
			borderData := data["border"].([]interface{})
			c.border = make([]float64, len(borderData))
			for i, v := range borderData {
				c.border[i] = v.(float64)
			}
			c.frame = int(data["frame"].(float64))
			c.flag = true
			fmt.Println("[Info] recv render data", c)
			c.conn.Write([]byte("ok"))

		case "render":
			blendFilePath := filepath.Dir(c.blendFile)
			tempPath := filepath.Join(blendFilePath, "temp")

			keyTime := strconv.FormatInt(time.Now().Unix(), 10)
			tempFilename := filepath.Join(tempPath, keyTime+".png")
			if c.flag {
				fmt.Println("[Info] start render ", c.border)
				command := exec.Command(
					blenderPath, "-b", "--python", "./render.py", "--", c.blendFile, c.scene,
					"--border",
					strconv.FormatFloat(c.border[0], 'f', -1, 64),
					strconv.FormatFloat(c.border[1], 'f', -1, 64),
					strconv.FormatFloat(c.border[2], 'f', -1, 64),
					strconv.FormatFloat(c.border[3], 'f', -1, 64),
					"--frame_number", strconv.Itoa(c.frame),
					"--save_path", tempFilename,
				)
				out, err := command.CombinedOutput()
				if err != nil {
					fmt.Printf("[Error] get command error: %v\n", err)
				}
				fmt.Println(string(out))
				if err := command.Run(); err == nil {
					fmt.Println(err)
				}
				c.conn.Write([]byte(keyTime + ".png"))
				fmt.Println("[Info] success render image ", c.border, tempFilename)

			}
		}
	}
}

var blenderPath string

func main() {
	fmt.Println("RenderWorkShop [worker] is running...")
	configData, err := os.ReadFile("./config.json")
	if err != nil {
		fmt.Printf("[Error] reading config file: %v\n", err)
		return
	}

	var config map[string]interface{}
	if err := json.Unmarshal(configData, &config); err != nil {
		fmt.Printf("[Error] json unmarshal error: %v\n", err)
		return
	}

	serverIP := config["server_ip"].(string)
	fmt.Printf("[Info] server ip: %s\n", serverIP)

	serverPort := int(config["server_port"].(float64))
	fmt.Printf("[Info] server port: %d\n", serverPort)

	blenderPath = config["blender_path"].(string)
	fmt.Printf("[Info] blender path: %s\n", blenderPath)

	client := &Client{
		serverAddr: serverIP,
		port:       serverPort,
	}

	client.runClient()
	client.recv()
}
