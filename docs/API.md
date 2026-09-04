# 公共接口说明

## C 语言硬件抽象层

### hal_init

```c
int hal_init(void);
```

初始化 GPIO、PWM 和硬件状态。成功返回 `0`，失败返回负值并释放已经初始化的资源。调用失败后不得发送电机运行命令。

### hal_cleanup

```c
void hal_cleanup(void);
```

执行电机刹车、停止 PWM、关闭可控 RGB 输出并释放 HAL 状态。程序正常退出和异常退出都必须调用。

### motor_run

```c
void motor_run(int left, int right);
```

设置左右轮组速度，范围为 `-255` 至 `255`。正负号表示方向，绝对值表示 PWM 强度，超出范围的输入会被限制。

### motor_brake

```c
void motor_brake(void);
```

把电机 PWM 和方向输出置为停止状态。传感器错误、丢线超时、通信失败和程序退出时必须优先调用。

### servo_set_angle

```c
int servo_set_angle(int channel, int angle);
```

设置舵机角度。通道范围为 `0` 至 `2`，角度范围为 `0` 至 `180`。非法通道或角度返回错误。

### sensor_distance_filtered

```c
float sensor_distance_filtered(void);
```

触发超声波并返回过滤后的厘米距离。超时或无效测量返回负值，行为层会累计失败次数并按安全故障处理。

### sensor_read_tracking

```c
int sensor_read_tracking(int state[4]);
```

读取四路巡线状态，顺序设计为左外、左内、右内、右外。实车标定完成前必须再次确认物理顺序和有效电平。

### sensor_read_avoid

```c
int sensor_read_avoid(int state[2]);
```

读取左右红外避障状态。实车标定时需要分别遮挡两块模块，确认左右顺序和触发电平。

### button_read

```c
int button_read(void);
```

读取预留的低有效车载按钮，按下返回 `1`。当前硬件尚未确认存在实体按钮，正式使用前必须核对 GPIO。

### led_set

```c
void led_set(int red, int green, int blue);
```

设置 RGB 通道，参数范围为 `0` 至 `255`。当前 `BST-03 V2.0` 灯板实测持续红灯，接口代码已完成，但硬件线序和驱动方式仍需确认。

## Python 接口

### LineSource

```python
line_source.read() -> LineReading(error, confidence, detected, timestamp)
```

- `error`：归一化横向误差。
- `confidence`：当前结果可信度。
- `detected`：是否检测到线路。
- `timestamp`：采样时间。

### MotorBackend

```python
motor.run(left, right)
motor.brake()
motor.close()
```

`GPIOMotorBackend` 和 `ArduinoMotorBackend` 使用相同接口。`close()` 必须先尝试刹车，再释放底层资源。

### ObstacleDetector

```python
obstacle_detector.read() -> ObstacleReading
```

返回障碍等级、超声波距离、左右红外状态和时间戳。可能的等级为 `CLEAR`、`WARNING`、`BLOCKED` 和 `SENSOR_ERROR`。

### BehaviorManager

```python
manager.update(now=None) -> RunState
manager.pause(reason="operator")
manager.request_resume() -> bool
manager.status() -> dict
manager.shutdown()
```

`request_resume()` 只在 `WAIT_CLEAR` 状态接受请求，返回 `True` 也不表示电机立即运行。后续循环仍会检查稳定清除时间和全部安全输入。

### Detection

```python
Detection(class_name, confidence, bbox)
```

视觉检测的通用结果。`bbox` 为 `(x1, y1, x2, y2)`。分类置信度低于阈值时应返回 `unknown`。

## Arduino 串口协议

```text
AA | version | command | sequence | payload_length | payload | CRC8
```

- 帧头：`0xAA`
- CRC8 多项式：`0x07`
- 校验范围：从 `version` 到 `payload` 的全部字节
- 多字节整数：小端序

| 命令值 | 名称 | 负载 |
|---|---|---|
| `0x01` | `SET_MOTOR` | `left:int16, right:int16` |
| `0x02` | `BRAKE` | 无 |
| `0x03` | `HEARTBEAT` | 无 |
| `0x04` | `GET_STATUS` | 无 |
| `0x81` | `STATUS` | `battery_mV:uint16, left:int16, right:int16, error_flags:uint8` |

电池电压不可用时 `battery_mV` 返回 `0`。错误 CRC、非法长度、未知命令和重复数据不能改变电机输出。Arduino 超过 500 ms 未满足看门狗条件时自动刹车。

## TCP 诊断协议

TCP 服务默认关闭，启用时必须通过 `--tcp-token` 或环境变量 `SMARTCAR_TCP_TOKEN` 提供非空令牌。

```text
$4WD,AUTH,<token>#
$4WD,STATUS#
$4WD,STOP#
$4WD,RESUME#
$4WD,SPEED,<value>#
$4WD,LED,<r>,<g>,<b>#
```

服务只接受一个客户端，限制接收缓存大小，并处理分片或连续数据帧。`STATUS` 使用行为循环缓存数据，不会并发触发超声波测量。

`STOP` 立即调用行为层停车。`RESUME` 只提交请求，并且不能清除 `FAULT` 或绕过障碍检测。

## 视觉辅助接口

- `ColorDetector.detect(frame)`：返回画面中最大的 HSV 颜色目标，并处理红色的两个色相区间。
- `TargetTracker.command(detection, frame_shape)`：把目标位置转换为左右轮差速命令；目标缺失时请求停车。
- `CameraStream.latest()`：读取最新视频帧，采集线程失效时健康检查返回失败。
- `DNNDetector.latest()`：返回最近一次推理结果，推理线程与行为循环解耦。
