# 安装与运行

## 目标环境

- Raspberry Pi 4B
- Raspbian Buster
- Python 3.7 或更高版本
- GCC 和 GNU Make
- wiringPi
- OpenCV 4.x

当前 Yahboom 系统镜像已经确认包含 Python 3.7.3、OpenCV 4.1.2 和 GCC。

## 安装依赖

树莓派接入可访问互联网的 Wi-Fi 后执行：

```bash
sudo apt-get update
sudo apt-get install build-essential python3-opencv python3-serial
```

如果树莓派只连接自身热点且无法访问互联网，应先让树莓派连接路由器或手机热点，也可以在其他电脑下载依赖后通过 SSH 复制。

## 编译与测试

```bash
cd /home/pi/SmartCarV2
make install
make test
```

`make install` 编译 C 语言硬件抽象层并生成 `libsmartcar.so`。`make test` 运行不驱动真实电机的自动化测试。

## 防止 GPIO 冲突

原厂镜像通过 `/home/pi/bluetooth.sh` 启动 `/home/pi/SmartCar/bluetooth_control`。原厂程序和 SmartCarV2 会访问相同的 GPIO 和 PWM，不能同时运行。

启动 SmartCarV2 前检查并停止旧进程：

```bash
pgrep -af bluetooth_control
sudo pkill -f '^./bluetooth_control$'
```

长期使用 SmartCarV2 时，应从系统自启动配置中移除原厂脚本，同时保留恢复原厂程序的方法。

## USB SSH 配置

修改系统启动文件前先备份 SD 卡。

1. 在 `/boot/config.txt` 末尾加入 `dtoverlay=dwc2`。
2. 在 `/boot/cmdline.txt` 原有单行中加入 `modules-load=dwc2,g_ether`。
3. 执行 `sudo systemctl enable ssh`。
4. 重启后使用支持数据传输的 USB-C 线连接电脑。
5. 在 Windows 中确认 RNDIS 或 USB Ethernet 网卡正常识别。

`cmdline.txt` 必须保持为一整行。配置 USB SSH 时应保留 Wi-Fi SSH 作为故障恢复路径。

## 首次运行

1. 架空四个轮子，确认车辆不会接触地面。
2. 保留可以立即关闭的电源开关或拔线位置。
3. 停止原厂 `bluetooth_control`。
4. 执行 `make install` 和 `make test`。
5. 先运行只读传感器监视：

```bash
PYTHONPATH=. python3 tools/sensor_monitor.py --duration 30
```

6. 以低速启动红外巡线模式：

```bash
PYTHONPATH=. python3 main.py --line-source ir --motor-backend gpio
```

7. 逐个确认车轮方向、刹车和 `Ctrl+C` 退出行为。
8. 障碍停车和异常停车通过后，才允许把小车放到地面测试。

## 摄像头模式

```bash
PYTHONPATH=. python3 main.py --line-source camera --motor-backend gpio
```

当前实机摄像头识别为 `Sanhao Face`，图像节点为 `/dev/video0`。如果报告设备忙，先执行：

```bash
fuser -v /dev/video0
```

结束占用摄像头的程序后再测试。必要时重新插拔 USB 摄像头或重启树莓派。

## Arduino 后端

连接 Arduino 并确认实际电机驱动引脚后执行：

```bash
PYTHONPATH=. python3 main.py --line-source ir \
  --motor-backend arduino --arduino-port /dev/ttyACM0
```

没有完成 Arduino 看门狗和失联刹车测试前，不得进行地面行驶。

## 当前按钮限制

原厂不同示例把 wiringPi 10 分别定义为按钮或蜂鸣器，当前小车照片也没有显示可确认的实体按钮。SmartCarV2 暂时保留按钮接口，同时支持经过认证且受安全状态机约束的 TCP `RESUME`。

## 中文网页控制面板

```bash
cd /home/pi/SmartCarV2
chmod +x start_panel.sh
export SMARTCAR_PANEL_TOKEN='请替换为强密码'
./start_panel.sh
```

随后访问 `http://树莓派IP:8081`，使用用户名 `smartcar` 和设置的面板密码登录。8080 端口由摄像头视频服务占用。面板启动本身不会初始化 GPIO 或转动电机。点击启动循迹前必须确认轮子架空，并停止原厂控制程序。
