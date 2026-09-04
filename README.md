# SmartCarV2

SmartCarV2 将 Yahboom 树莓派四轮小车示例重构为安全、可测试的分层控制系统。C 语言负责 GPIO 时序和底层硬件操作，Python 负责行为状态机、巡线、避障、远程诊断及可选视觉功能。电机在程序启动和退出时均保持刹车。

项目已实现和待完成内容详见 [项目状态与功能清单](PROJECT_STATUS.md)。

## 树莓派快速启动

```bash
cd /home/pi/SmartCarV2
make install
PYTHONPATH=. python3 main.py --line-source ir --motor-backend gpio
```

摄像头巡线：

```bash
PYTHONPATH=. python3 main.py --line-source camera --motor-backend gpio
```

Arduino 电机后端：

```bash
python3 -m pip install --user pyserial
PYTHONPATH=. python3 main.py --line-source ir --motor-backend arduino \
  --arduino-port /dev/ttyACM0
```

可选 MobileNet SSD 人形停车模式。摄像头巡线和人形检测共用同一个视频流：

```bash
PYTHONPATH=. python3 main.py --line-source camera \
  --person-config models/MobileNetSSD_deploy.prototxt \
  --person-model models/MobileNetSSD_deploy.caffemodel
```

仓库不包含模型文件和雕像训练数据。请使用具有合法授权的模型，并按照不同拍摄主体隔离训练集、验证集和测试集。

## TCP 远程诊断

TCP 服务默认关闭。启用时必须设置共享令牌：

```bash
SMARTCAR_TCP_TOKEN='change-this-token' PYTHONPATH=. \
  python3 main.py --line-source ir --tcp
```

命令以 `#` 结束，首先发送 `$4WD,AUTH,change-this-token#` 完成认证。支持：

```text
STATUS
STOP
RESUME
SPEED,<0-200>
LED,<r>,<g>,<b>
```

`RESUME` 只提交恢复请求。只有主行为循环确认障碍持续清除、系统处于 `WAIT_CLEAR` 且稳定时间满足后，车辆才会恢复运行。该方式可用于没有实体启动按钮的硬件版本。

## 安全要求

运行 SmartCarV2 前必须停止原厂 `/home/pi/bluetooth.sh` 和 `bluetooth_control`。两个程序不能同时占用相同的 GPIO 和 PWM。

首次电机测试必须架空四个轮子，并在旁边保留物理断电手段。不要在 RGB 灯板线序未确认时反复进行高占空比输出测试。

只读传感器监视工具会持续保持电机刹车：

```bash
PYTHONPATH=. python3 tools/sensor_monitor.py --duration 30
```

## 中文网页控制面板

在树莓派上设置面板密码并启动：

```bash
cd /home/pi/SmartCarV2
export SMARTCAR_PANEL_TOKEN='请替换为强密码'
./start_panel.sh
```

电脑或手机连接同一网络后访问：

```text
http://树莓派IP:8080
```

浏览器认证用户名固定为 `smartcar`，密码为 `SMARTCAR_PANEL_TOKEN`。面板可以选择红外或摄像头巡线、GPIO 或 Arduino 后端，并提供状态、日志、启动、安全停止、暂停及受状态机约束的恢复请求。

启动循迹前必须勾选轮子已架空和环境安全。原厂 `bluetooth_control` 仍运行时，面板会拒绝启动 SmartCarV2。

## 文档

- [安装与运行](docs/INSTALL.md)
- [软件架构](docs/ARCHITECTURE.md)
- [公共接口](docs/API.md)
- [测试与验收计划](docs/TEST_PLAN.md)
- [开发记录](DEVELOPMENT_LOG.md)
