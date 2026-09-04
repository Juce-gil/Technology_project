# SmartCarV2 软件架构

## 总体结构

```text
四路红外 ──> IRLineSource ───────────┐
摄像头 ────> CameraLineSource ───────┼──> BehaviorManager ──> MotorBackend
超声波和红外 ─> ObstacleDetector ────┤                         ├──> GPIO 和 C HAL
按钮或 TCP 恢复请求 ─────────────────┘                         └──> Arduino 串口

Python ──ctypes──> libsmartcar.so ──wiringPi──> Raspberry Pi GPIO
```

C 语言硬件抽象层负责 GPIO、PWM、超声波时序和传感器读取。Python 层把硬件读数转换为统一数据结构，由 `BehaviorManager` 按安全优先级处理，再通过统一的 `MotorBackend` 输出速度。

## 行为循环

行为循环默认以 10 Hz 运行。每次循环依次完成：

1. 读取并去抖实体按钮。
2. 读取超声波和左右红外避障状态。
3. 检查可选人形检测结果和视觉线程健康状态。
4. 优先处理障碍、传感器错误和停车恢复状态。
5. 在安全条件满足时读取选定的巡线源。
6. 由带误差 EMA、微分低通和速度变化率限制的 PD 控制器计算左右轮速度。
7. 向 GPIO 或 Arduino 后端发送电机命令。

## 停止恢复状态机

```text
RUNNING -- 障碍 人形确认或传感器失败 --> PAUSED
PAUSED  -- 障碍消失 ------------------> WAIT_CLEAR
WAIT_CLEAR -- 稳定清除和人工恢复请求 --> RUNNING
RUNNING -- 丢线超过停止时限 ---------> FAULT
FAULT   -- 重启并重新完成自检 --------> RUNNING
```

检测到阻挡或连续传感器错误时，系统立即执行刹车。障碍消失后先进入 `WAIT_CLEAR` 并计算稳定清除时间。只有去抖后的实体按钮按下边沿，或者经过认证的 TCP `RESUME` 请求，才能在安全条件满足后恢复。

按钮必须先被检测为释放状态，持续按住按钮不能导致意外恢复。TCP 恢复请求如果遇到障碍再次出现会立即取消。`FAULT` 是锁定状态，不能通过按钮或网络自行恢复。

## 控制优先级

1. 未处理异常、巡线源失效或通信失败：立即刹车。
2. 阻挡距离、红外障碍或连续多帧确认人形：立即刹车并暂停。
3. 警告距离：以限制速度直行。
4. 安全状态：交给所选巡线源和 PD 差速控制。
5. 丢线：先低速保持，再按照最后方向搜索，超过时限后进入 `FAULT`。

## 巡线源

`IRLineSource` 和 `CameraLineSource` 都返回：

```python
LineReading(error, confidence, detected, timestamp)
```

`error` 为归一化横向误差，范围约为 `-1.0` 至 `1.0`。一周版本通过 `--line-source ir|camera` 选择数据源，不自动融合两个巡线结果。

控制器先平滑横向误差，再对误差变化率进行低通滤波，减少红外跳变或图像噪声造成的左右轮瞬时抖动。左右轮命令按照 `max_speed_change_per_second` 限制变化速度。障碍、故障和丢线超时直接调用电机刹车，不经过该限制器。每次安全停车都会清除旧速度、滤波状态和丢线方向，恢复后从零速重新建立控制输出。

## 电机后端

`GPIOMotorBackend` 使用 C HAL 直接控制树莓派 GPIO。`ArduinoMotorBackend` 使用带 CRC8 的二进制串口协议发送命令。两者均提供：

```python
run(left, right)
brake()
close()
```

Arduino 固件具有独立看门狗。如果超过 500 ms 没有收到满足条件的合法命令，Arduino 会主动刹车。

## 并发边界

摄像头采集和 DNN 推理可以在独立线程运行，行为循环只读取最新结果。TCP `STATUS` 返回行为循环缓存的传感器快照，不会在网络线程中再次触发超声波测量。远程线程只能请求停车或恢复，最终状态转换由行为循环完成。
