# -*- coding: utf-8 -*-
"""脑电状态到游戏控制量的映射函数。"""

from config import (
    ATTENTION_HIGH,
    ATTENTION_LOW,
    ATTENTION_MID,
    GOOD_SIGNAL_MAX,
    MAX_GAME_SPEED,
    MIN_GAME_SPEED,
)


def is_signal_good(signal: int) -> bool:
    """判断 TGAM/STM32 上报的信号质量是否可用于控制游戏。"""
    return signal <= GOOD_SIGNAL_MAX


def attention_speed_bonus(attention: int) -> int:
    """根据专注度分档增加速度，避免每一帧速度剧烈抖动。"""
    if attention >= ATTENTION_HIGH:
        return 0
    if attention >= ATTENTION_MID:
        return 0
    if attention >= ATTENTION_LOW:
        return 0
    return 0


def clamp_game_speed(speed: float) -> int:
    """把最终速度限制在可玩的范围内。"""
    return max(MIN_GAME_SPEED, min(MAX_GAME_SPEED, int(speed)))
