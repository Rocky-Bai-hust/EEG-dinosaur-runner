# -*- coding: utf-8 -*-
"""Chrome 小恐龙脑电控制配置。

# 这个文件只放“可调参数”，不写游戏逻辑。
# 修改这里的数值后，重新运行 main.py 即可生效。
# 注意：时间单位凡是以 _MS 结尾，都是毫秒。
"""

# 是否启用串口脑电控制。
# True  = 游戏启动后会打开 SERIAL_PORT，从 Arduino/STM32 读取脑电文本数据。
# False = 完全禁用脑电串口，只用键盘控制，适合没有接硬件时玩原版游戏。
SERIAL_ENABLED = True

# 是否使用软件模拟脑电数据。
# True  = 不打开真实串口，由 eeg_serial_reader.py 随机生成 ATT/MED/SIG/BLINK。
# False = 使用真实硬件串口。
# 调试电脑端游戏逻辑时可设为 True；连接 Arduino 实测时应设为 False。
SIMULATE_EEG = False

# 调试模式开关。
# 1 = 调试状态，碰到障碍物也不会死亡；
# 0 = 正常状态，碰到障碍物会死亡。
DEBUG_MODE = 0

# 电脑端连接 Arduino/STM32 的串口号。
# Windows 一般是 "COM3"、"COM7" 这种格式；实际端口可在设备管理器或 Arduino IDE 中查看。
SERIAL_PORT = "COM7"

# 电脑端读取 Arduino/STM32 的波特率。
# 当前 Arduino 使用同一个硬件串口接 TGAM 并转发到 USB，所以这里必须和 TGAM 一样是 57600。
SERIAL_BAUD = 57600

# 信号质量阈值。
# TGAM 的 SIG/Signal/PoorSignal 数值越小越好：
#   0   表示信号很好；
#   200 通常表示未佩戴、接触差或无有效信号。
# 游戏只在 signal <= GOOD_SIGNAL_MAX 时接受脑电控制，避免坏信号误触发。
GOOD_SIGNAL_MAX = 10

# 专注度分级阈值，ATTENTION 的常见范围是 0-100。
# 这些值会被 eeg_control.py 用来计算速度加成：
#   ATTENTION_LOW  以上：轻微加速；
#   ATTENTION_MID  以上：中等加速；
#   ATTENTION_HIGH 以上：明显加速。
ATTENTION_LOW = 50
ATTENTION_MID = 65
ATTENTION_HIGH = 80

# 冥想/放松度护盾阈值，MEDITATION 的常见范围是 0-100。
# 当信号质量良好且 meditation >= MEDITATION_SHIELD 时，游戏进入 RELAX 模式：
#   1. 游戏速度会乘以 0.75，整体变慢；
#   2. 如果护盾冷却结束，会生成一个可抵消一次碰撞的护盾。
MEDITATION_SHIELD = 65

# 护盾冷却时间。
# 护盾被障碍物消耗后，需要等待这么久才能再次生成。
SHIELD_COOLDOWN_MS = 8000

# Demo assist: keep EEG-triggered jumps reliable without moving the dinosaur or changing global speed.
ENABLE_MIN_JUMP_CLEARANCE = True
MIN_JUMP_CLEAR_DISTANCE_PX = 280
MAX_ASSIST_JUMP_VEL = 10.5
JUMP_GRAVITY = 0.8

# Demo start gate: wait for real EEG hardware and good signal before entering a run.
START_REQUIRE_EEG_READY = True
START_REQUIRE_SIGNAL_ZERO = True
START_SIGNAL_STABLE_MS = 2000

# Demo fallback: when signal is bad in-game, auto-jump nearby obstacles to keep the demo flowing.
IN_GAME_BAD_SIGNAL_AUTOPILOT = True
AUTO_JUMP_TRIGGER_MIN_X = 120
AUTO_JUMP_TRIGGER_MAX_X = 360

# Theme switching: 1 enables score-based black/white day-night switching, 0 keeps original theme.
AUTO_THEME_SWITCH = 1
THEME_SWITCH_SCORE_INTERVAL = 500

# Pause control for live demos.
ENABLE_PAUSE = True

# Focus-success assist: reward clean obstacle passes with temporary effective attention.
ENABLE_FOCUS_SUCCESS_ASSIST = True
FOCUS_SUCCESS_BONUS_STEP = 5
FOCUS_SUCCESS_BONUS_MAX = 50

# PC-only test hotkeys for exercising EEG conditions without hardware.
ENABLE_EEG_TEST_HOTKEYS = False

# 专注冲刺配置。
# 当信号质量良好且 attention >= SPRINT_ATTENTION 时，触发一次短暂冲刺。
# 冲刺期间：
#   1. 小恐龙额外加速 SPRINT_SPEED_BONUS；
#   2. 碰到障碍物不会死亡，而是直接撞碎/穿过；
#   3. 冲刺结束后进入冷却，冷却结束前不会再次触发。
SPRINT_ATTENTION = 80

# 每次冲刺持续时间。
SPRINT_DURATION_MS = 2500

# 两次冲刺之间的冷却时间。
SPRINT_COOLDOWN_MS = 7000

# 冲刺期间额外增加的游戏速度。
# 数值越大，冲刺越快，也越有“爆发感”。
SPRINT_SPEED_BONUS = 8

# 游戏速度配置。
# BASE_GAME_SPEED 是基础速度；实际速度会根据专注度、冥想度和冲刺状态动态变化。
BASE_GAME_SPEED = 20

# 游戏最低速度限制。
# 冥想模式会让速度变慢，但不会低于这个值。
MIN_GAME_SPEED = 5

# 游戏最高速度限制。
# 专注度和冲刺会让速度变快，但不会超过这个值，避免速度失控。
MAX_GAME_SPEED = 30
