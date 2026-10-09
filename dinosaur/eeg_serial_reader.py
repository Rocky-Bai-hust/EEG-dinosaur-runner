# -*- coding: utf-8 -*-
"""后台读取 STM32 发来的简化脑电串口数据。

串口数据格式示例：
ATT:65,MED:48,SIG:0,BLINK:1,COUNT:3
"""

from dataclasses import dataclass
import random
import threading
import time

from config import SIMULATE_EEG

try:
    import serial
except ImportError:
    # 未安装 pyserial 时保持游戏可运行，只禁用真实串口读取。
    serial = None


@dataclass
class EEGState:
    """保存最近一帧脑电状态。"""

    attention: int = 0
    meditation: int = 0
    signal: int = 200
    blink: bool = False
    blink_count: int = 0
    connected: bool = False
    last_update: float = 0.0


def parse_line(line: str) -> dict:
    """把一行 STM32 文本解析为字典，坏片段会被自动跳过。"""
    result = {}
    if not line:
        return result

    for part in line.strip().split(","):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        key = key.strip().upper()
        try:
            result[key] = int(value.strip())
        except ValueError:
            # 串口偶尔出现乱码或半截数据时，不让游戏崩溃。
            continue
    return result


class EEGSerialReader:
    """非阻塞串口读取器，在后台线程中持续更新 EEGState。"""

    def __init__(self, port: str, baudrate: int):
        self.port = port
        self.baudrate = baudrate
        self._state = EEGState()
        self._lock = threading.Lock()
        self._thread = None
        self._running = False
        self._serial = None
        self._simulate = SIMULATE_EEG

    def start(self):
        """启动后台串口读取线程。"""
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """停止线程并关闭串口。"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
        with self._lock:
            self._state.connected = False

    def get_state(self) -> EEGState:
        """返回最新 EEGState 的副本，避免外部直接改共享状态。"""
        with self._lock:
            return EEGState(**self._state.__dict__)

    def consume_blink(self) -> bool:
        """消费一次眨眼事件，保证一次 BLINK 只触发一次跳跃。"""
        with self._lock:
            if self._state.blink:
                self._state.blink = False
                return True
            return False

    def _run(self):
        if self._simulate:
            self._run_simulator()
            return

        if serial is None:
            with self._lock:
                self._state.connected = False
            return

        try:
            self._serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=0.05,
            )
            with self._lock:
                self._state.connected = True
        except Exception:
            with self._lock:
                self._state.connected = False
            return

        while self._running:
            try:
                raw_line = self._serial.readline()
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8", errors="ignore")
                self._update_from_fields(parse_line(line))
            except Exception:
                # 串口断开或读取异常时，关闭脑电控制但保留键盘控制。
                with self._lock:
                    self._state.connected = False
                time.sleep(0.2)

    def _run_simulator(self):
        """无硬件调试模式：定期生成 ATT/MED/SIG/BLINK 测试数据。"""
        blink_count = 0
        last_blink = time.time()
        while self._running:
            now = time.time()
            blink = now - last_blink > random.uniform(2.0, 4.0)
            if blink:
                blink_count += 1
                last_blink = now

            fields = {
                "ATT": random.randint(35, 90),
                "MED": random.randint(35, 85),
                "SIG": 0,
                "BLINK": 1 if blink else 0,
                "COUNT": blink_count,
            }
            self._update_from_fields(fields, connected=True)
            time.sleep(1.0)

    def _update_from_fields(self, fields: dict, connected: bool = True):
        """只更新存在的字段，允许 STM32 偶尔丢字段。"""
        if not fields:
            return

        with self._lock:
            self._state.connected = connected
            if "ATT" in fields:
                self._state.attention = fields["ATT"]
            if "MED" in fields:
                self._state.meditation = fields["MED"]
            if "SIG" in fields:
                self._state.signal = fields["SIG"]
            if "COUNT" in fields:
                self._state.blink_count = fields["COUNT"]
            if fields.get("BLINK", 0) == 1:
                self._state.blink = True
            self._state.last_update = time.time()
