import pygame
import os
import random
import sys
import math

from config import *
from eeg_control import attention_speed_bonus, clamp_game_speed, is_signal_good
from eeg_serial_reader import EEGSerialReader, EEGState

pygame.init()

# 游戏窗口和资源路径配置。
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREEN_HEIGHT = 600
SCREEN_WIDTH = 1100
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

# 加载小恐龙、障碍物和背景素材。
RUNNING = [pygame.image.load(os.path.join(BASE_DIR, "Assets/Dino", "DinoRun1.png")),
           pygame.image.load(os.path.join(BASE_DIR, "Assets/Dino", "DinoRun2.png"))]
JUMPING = pygame.image.load(os.path.join(BASE_DIR, "Assets/Dino", "DinoJump.png"))
DUCKING = [pygame.image.load(os.path.join(BASE_DIR, "Assets/Dino", "DinoDuck1.png")),
           pygame.image.load(os.path.join(BASE_DIR, "Assets/Dino", "DinoDuck2.png"))]

SMALL_CACTUS = [pygame.image.load(os.path.join(BASE_DIR, "Assets/Cactus", "SmallCactus1.png")),
                pygame.image.load(os.path.join(BASE_DIR, "Assets/Cactus", "SmallCactus2.png")),
                pygame.image.load(os.path.join(BASE_DIR, "Assets/Cactus", "SmallCactus3.png"))]
LARGE_CACTUS = [pygame.image.load(os.path.join(BASE_DIR, "Assets/Cactus", "LargeCactus1.png")),
                pygame.image.load(os.path.join(BASE_DIR, "Assets/Cactus", "LargeCactus2.png")),
                pygame.image.load(os.path.join(BASE_DIR, "Assets/Cactus", "LargeCactus3.png"))]

BIRD = [pygame.image.load(os.path.join(BASE_DIR, "Assets/Bird", "Bird1.png")),
        pygame.image.load(os.path.join(BASE_DIR, "Assets/Bird", "Bird2.png"))]

# 飞鸟高度
BIRD_LOW_Y = 300
BIRD_HIGH_Y = 205

CLOUD = pygame.image.load(os.path.join(BASE_DIR, "Assets/Other", "Cloud.png"))

BG = pygame.image.load(os.path.join(BASE_DIR, "Assets/Other", "Track.png"))
GAME_OVER = pygame.image.load(os.path.join(BASE_DIR, "Assets/Other", "GameOver.png"))
RESET = pygame.image.load(os.path.join(BASE_DIR, "Assets/Other", "Reset.png"))

SHIELD_BREAK_DURATION_MS = 450
SPRINT_IMPACT_DURATION_MS = 300

# 全局只创建一个串口读取器，避免每次从菜单重开游戏时重复创建线程。
eeg_reader = None
inverted_frame = None


def get_dark_theme(current_points):
    if not AUTO_THEME_SWITCH:
        return False
    interval = max(1, THEME_SWITCH_SCORE_INTERVAL)
    return (current_points // interval) % 2 == 1


def themed_surface(surface, dark_theme):
    return surface


def invert_current_frame(surface):
    """Invert the whole frame, matching Chromium Dino's page-level night mode."""
    global inverted_frame
    if inverted_frame is None or inverted_frame.get_size() != surface.get_size():
        inverted_frame = pygame.Surface(surface.get_size())
    inverted_frame.fill((255, 255, 255))
    inverted_frame.blit(surface, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
    surface.blit(inverted_frame, (0, 0))


def theme_colors(dark_theme):
    if dark_theme:
        return {
            "background": (0, 0, 0),
            "text": (245, 245, 245),
            "muted": (185, 185, 185),
            "panel": (20, 20, 20, 220),
            "panel_border": (235, 235, 235, 180),
            "bar_bg": (60, 60, 60, 230),
        }
    return {
        "background": (255, 255, 255),
        "text": (0, 0, 0),
        "muted": (80, 80, 80),
        "panel": (255, 255, 255, 210),
        "panel_border": (45, 45, 45, 180),
        "bar_bg": (225, 225, 225, 230),
    }


def get_default_test_eeg_state():
    return EEGState(attention=50, meditation=40, signal=0, connected=True)


def apply_eeg_test_key(key, test_state):
    if not ENABLE_EEG_TEST_HOTKEYS:
        return False, False

    blink_triggered = False
    handled = True
    if key == pygame.K_z:
        test_state.connected = True
        test_state.signal = 0
    elif key == pygame.K_x:
        test_state.connected = True
        test_state.signal = 200
    elif key == pygame.K_c:
        test_state.attention = 40
    elif key == pygame.K_v:
        test_state.attention = 70
    elif key == pygame.K_b:
        test_state.attention = 90
    elif key == pygame.K_n:
        test_state.meditation = 75
    elif key == pygame.K_m:
        test_state.blink_count += 1
        blink_triggered = True
    elif key == pygame.K_r:
        reset_state = get_default_test_eeg_state()
        test_state.attention = reset_state.attention
        test_state.meditation = reset_state.meditation
        test_state.signal = reset_state.signal
        test_state.blink = reset_state.blink
        test_state.blink_count = reset_state.blink_count
        test_state.connected = reset_state.connected
        test_state.last_update = reset_state.last_update
    elif key == pygame.K_o:
        test_state.connected = False
        test_state.signal = 200
    else:
        handled = False

    return handled, blink_triggered


def merge_test_eeg_state(real_state, test_state):
    if not ENABLE_EEG_TEST_HOTKEYS:
        return real_state
    merged = EEGState(**real_state.__dict__)
    merged.attention = test_state.attention
    merged.meditation = test_state.meditation
    merged.signal = test_state.signal
    merged.connected = test_state.connected
    merged.blink_count = test_state.blink_count
    merged.last_update = pygame.time.get_ticks() / 1000
    return merged


def eeg_test_help_lines():
    return [
        "EEG TEST: Z NORMAL(SIG=0)  X BAD SIG AUTO(SIG=200)",
        "C ATT=40  V ATT=70  B ATT=90(SPRINT)  N MED=75",
        "M BLINK  R RESET  O OFFLINE",
    ]


def get_eeg_reader():
    """按需启动脑电串口读取线程。"""
    global eeg_reader
    if not SERIAL_ENABLED:
        return None
    if eeg_reader is None:
        eeg_reader = EEGSerialReader(SERIAL_PORT, SERIAL_BAUD)
        eeg_reader.start()
    return eeg_reader


def shutdown_game():
    """退出程序前关闭串口线程，避免后台线程残留。"""
    global eeg_reader
    if eeg_reader is not None:
        eeg_reader.stop()
        eeg_reader = None
    pygame.quit()
    sys.exit()


def wait_for_eeg_ready_screen(reader):
    """Wait until EEG hardware is connected and signal quality is ready for a demo run."""
    if not START_REQUIRE_EEG_READY or not SERIAL_ENABLED:
        return True

    font = pygame.font.Font('freesansbold.ttf', 30)
    status_font = pygame.font.Font('freesansbold.ttf', 20)
    clock = pygame.time.Clock()
    test_state = EEGState(attention=50, meditation=40, signal=200, connected=False)
    ready_start_ms = None

    if SIMULATE_EEG:
        start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start < 800:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    shutdown_game()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return False

            SCREEN.fill((255, 255, 255))
            title = font.render("SIMULATION MODE", True, (0, 0, 0))
            hint = status_font.render("EEG simulator enabled; starting demo run", True, (80, 80, 80))
            SCREEN.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 25)))
            SCREEN.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20)))
            pygame.display.update()
            clock.tick(30)
        return True

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                shutdown_game()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
            if event.type == pygame.KEYDOWN:
                apply_eeg_test_key(event.key, test_state)

        eeg_state = reader.get_state() if reader is not None else EEGState()
        eeg_state = merge_test_eeg_state(eeg_state, test_state)
        signal_ready = eeg_state.signal == 0 if START_REQUIRE_SIGNAL_ZERO else is_signal_good(eeg_state.signal)
        now = pygame.time.get_ticks()
        if eeg_state.connected and signal_ready:
            if ready_start_ms is None:
                ready_start_ms = now
            if now - ready_start_ms >= START_SIGNAL_STABLE_MS:
                return True
        else:
            ready_start_ms = None

        stable_elapsed_ms = 0 if ready_start_ms is None else now - ready_start_ms
        stable_remaining_ms = max(0, START_SIGNAL_STABLE_MS - stable_elapsed_ms)

        SCREEN.fill((255, 255, 255))
        title = font.render("Connecting EEG Device", True, (0, 0, 0))
        SCREEN.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 160)))

        lines = [
            f"SIG: {eeg_state.signal}",
            f"ATT: {eeg_state.attention}",
            f"MED: {eeg_state.meditation}",
            f"connected: {eeg_state.connected}",
            f"Keep SIG=0 for {START_SIGNAL_STABLE_MS / 1000:.1f}s before start",
            f"stable: {stable_elapsed_ms / 1000:.1f}s  remaining: {stable_remaining_ms / 1000:.1f}s",
            "Press ESC to return",
        ]
        if ENABLE_EEG_TEST_HOTKEYS:
            lines.extend(["", "PC test: press Z to force connected + SIG=0"])
        for index, line in enumerate(lines):
            color = (0, 0, 0) if index < 4 else (80, 80, 80)
            text = status_font.render(line, True, color)
            SCREEN.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 230 + index * 34)))

        pygame.display.update()
        clock.tick(30)


def needs_bad_signal_auto_jump(obstacle):
    if isinstance(obstacle, Bird):
        return obstacle.rect.y == BIRD_LOW_Y
    return isinstance(obstacle, (SmallCactus, LargeCactus))


def get_nearest_right_obstacle(player, obstacle_list, jumpable_only=False):
    nearest = None
    nearest_distance = None
    for obstacle in obstacle_list:
        if jumpable_only and not needs_bad_signal_auto_jump(obstacle):
            continue
        distance = obstacle.rect.x - player.dino_rect.right
        if distance < 0:
            continue
        if nearest_distance is None or distance < nearest_distance:
            nearest = obstacle
            nearest_distance = distance
    return nearest, nearest_distance


def should_auto_jump_for_bad_signal(player, obstacle_list, signal_good, current_game_speed):
    if not IN_GAME_BAD_SIGNAL_AUTOPILOT or signal_good:
        return False

    nearest, distance = get_nearest_right_obstacle(player, obstacle_list, jumpable_only=True)
    if nearest is None:
        return False

    trigger_max = min(AUTO_JUMP_TRIGGER_MAX_X, max(AUTO_JUMP_TRIGGER_MIN_X, current_game_speed * 8))
    return 0 <= distance <= trigger_max


class Dinosaur:
    """玩家控制的小恐龙，负责跑、跳、下蹲三种状态。"""

    X_POS = 80
    Y_POS = 310
    Y_POS_DUCK = 340
    JUMP_VEL = 8.5

    def __init__(self):
        self.duck_img = DUCKING
        self.run_img = RUNNING
        self.jump_img = JUMPING

        self.dino_duck = False
        self.dino_run = True
        self.dino_jump = False

        self.step_index = 0
        self.jump_vel = self.JUMP_VEL
        self.jump_initial_vel = self.JUMP_VEL
        self.image = self.run_img[0]
        self.dino_rect = self.image.get_rect()
        self.dino_rect.x = self.X_POS
        self.dino_rect.y = self.Y_POS

    def start_jump(self, current_game_speed):
        """Start one jump, optionally assisting hang time for EEG demo latency."""
        jump_initial_vel = self.JUMP_VEL
        if ENABLE_MIN_JUMP_CLEARANCE and current_game_speed > 0:
            required_frames = MIN_JUMP_CLEAR_DISTANCE_PX / current_game_speed
            calculated_vel = (required_frames * JUMP_GRAVITY) / 2
            jump_initial_vel = min(MAX_ASSIST_JUMP_VEL, max(self.JUMP_VEL, calculated_vel))

        self.jump_initial_vel = jump_initial_vel
        self.jump_vel = jump_initial_vel
        self.dino_duck = False
        self.dino_run = False
        self.dino_jump = True

    def update(self, userInput, eeg_jump=False, current_game_speed=None):
        if self.dino_duck:
            self.duck()
        if self.dino_run:
            self.run()
        if self.dino_jump:
            self.jump()

        if self.step_index >= 10:
            self.step_index = 0

        # 键盘上方向键、空格键、脑电眨眼事件都可以触发一次跳跃。
        jump_pressed = userInput[pygame.K_UP] or userInput[pygame.K_SPACE] or eeg_jump

        if jump_pressed and not self.dino_jump:
            if current_game_speed is None:
                current_game_speed = game_speed
            self.start_jump(current_game_speed)
        elif userInput[pygame.K_DOWN] and not self.dino_jump:
            self.dino_duck = True
            self.dino_run = False
            self.dino_jump = False
        elif not (self.dino_jump or userInput[pygame.K_DOWN]):
            self.dino_duck = False
            self.dino_run = True
            self.dino_jump = False

    def duck(self):
        self.image = self.duck_img[self.step_index // 5]
        self.dino_rect = self.image.get_rect()
        self.dino_rect.x = self.X_POS
        self.dino_rect.y = self.Y_POS_DUCK
        self.step_index += 1

    def run(self):
        self.image = self.run_img[self.step_index // 5]
        self.dino_rect = self.image.get_rect()
        self.dino_rect.x = self.X_POS
        self.dino_rect.y = self.Y_POS
        self.step_index += 1

    def jump(self):
        self.image = self.jump_img
        if self.dino_jump:
            self.dino_rect.y -= self.jump_vel * 4
            self.jump_vel -= JUMP_GRAVITY
        if self.jump_vel < -self.jump_initial_vel:
            self.dino_jump = False
            self.jump_initial_vel = self.JUMP_VEL
            self.jump_vel = self.JUMP_VEL

    def draw(self, SCREEN, dark_theme=False):
        SCREEN.blit(themed_surface(self.image, dark_theme), (self.dino_rect.x, self.dino_rect.y))


class Cloud:
    """背景云朵，只做横向滚动和随机重置位置。"""

    def __init__(self):
        self.x = SCREEN_WIDTH + random.randint(800, 1000)
        self.y = random.randint(50, 100)
        self.image = CLOUD
        self.width = self.image.get_width()

    def update(self):
        self.x -= game_speed
        if self.x < -self.width:
            self.x = SCREEN_WIDTH + random.randint(2500, 3000)
            self.y = random.randint(50, 100)

    def draw(self, SCREEN, dark_theme=False):
        SCREEN.blit(themed_surface(self.image, dark_theme), (self.x, self.y))


class Obstacle:
    """障碍物基类，仙人掌和飞鸟共用移动、绘制逻辑。"""

    def __init__(self, image, type):
        self.image = image
        self.type = type
        self.rect = self.image[self.type].get_rect()
        self.rect.x = SCREEN_WIDTH
        self.counted = False
        self.autopilot_assisted = False

    def update(self):
        self.rect.x -= game_speed
        if self.rect.x < -self.rect.width:
            obstacles.pop()

    def draw(self, SCREEN, dark_theme=False):
        SCREEN.blit(themed_surface(self.image[self.type], dark_theme), self.rect)


class SmallCactus(Obstacle):
    def __init__(self, image):
        self.type = random.randint(0, 2)
        super().__init__(image, self.type)
        self.rect.y = 325


class LargeCactus(Obstacle):
    def __init__(self, image):
        self.type = random.randint(0, 2)
        super().__init__(image, self.type)
        self.rect.y = 300


class Bird(Obstacle):
    def __init__(self, image, y_pos=BIRD_LOW_Y):
        self.type = 0
        super().__init__(image, self.type)
        self.rect.y = y_pos
        self.index = 0

    def draw(self, SCREEN, dark_theme=False):
        if self.index >= 9:
            self.index = 0
        SCREEN.blit(themed_surface(self.image[self.index//5], dark_theme), self.rect)
        self.index += 1


def draw_shield(surface, dino_rect, now):
    """绘制冥想值触发的护盾效果。"""
    center = dino_rect.center
    radius = max(dino_rect.width, dino_rect.height) // 2 + 18
    pulse = int(math.sin(now / 120) * 4)
    shield_size = (radius + 10 + abs(pulse)) * 2
    shield_surface = pygame.Surface((shield_size, shield_size), pygame.SRCALPHA)
    shield_center = (shield_size // 2, shield_size // 2)

    pygame.draw.circle(shield_surface, (80, 190, 255, 45), shield_center, radius + pulse)
    pygame.draw.circle(shield_surface, (40, 150, 255, 160), shield_center, radius + pulse, 4)
    pygame.draw.circle(shield_surface, (220, 245, 255, 190), shield_center, radius + pulse - 6, 2)
    surface.blit(
        shield_surface,
        (center[0] - shield_size // 2, center[1] - shield_size // 2),
    )


def draw_shield_break(surface, dino_rect, break_start, now):
    """护盾抵消碰撞后，播放短暂破碎动画。"""
    if break_start is None:
        return False

    elapsed = now - break_start
    if elapsed >= SHIELD_BREAK_DURATION_MS:
        return False

    progress = elapsed / SHIELD_BREAK_DURATION_MS
    center = dino_rect.center
    radius = max(dino_rect.width, dino_rect.height) // 2 + 18
    alpha = max(0, int(210 * (1 - progress)))
    spread = int(radius + progress * 45)
    break_size = (spread + 20) * 2
    break_surface = pygame.Surface((break_size, break_size), pygame.SRCALPHA)
    break_center = (break_size // 2, break_size // 2)

    pygame.draw.circle(break_surface, (80, 190, 255, alpha // 3), break_center, spread, 3)
    for index in range(12):
        angle = (math.tau / 12) * index + 0.35
        crack_start = radius + int(progress * 10)
        crack_end = radius + 16 + int(progress * 38)
        start = (
            break_center[0] + int(math.cos(angle) * crack_start),
            break_center[1] + int(math.sin(angle) * crack_start),
        )
        end = (
            break_center[0] + int(math.cos(angle) * crack_end),
            break_center[1] + int(math.sin(angle) * crack_end),
        )
        pygame.draw.line(break_surface, (30, 140, 255, alpha), start, end, 3)

    surface.blit(
        break_surface,
        (center[0] - break_size // 2, center[1] - break_size // 2),
    )
    return True


def draw_sprint_effect(surface, dino_rect, now):
    """绘制专注冲刺时小恐龙身后的速度拖尾。"""
    center_y = dino_rect.centery
    trail_surface = pygame.Surface((260, 150), pygame.SRCALPHA)
    base_x = 225
    base_y = 75

    for index in range(10):
        offset = (now // 28 + index * 19) % 190
        alpha = max(35, 215 - index * 17)
        y_wave = int(math.sin((now / 65) + index * 0.9) * 15)
        start = (base_x - offset, base_y + y_wave)
        end = (base_x - offset - 54 - index * 5, base_y + y_wave)
        pygame.draw.line(trail_surface, (255, 45, 35, alpha), start, end, 8)
        pygame.draw.line(trail_surface, (255, 120, 25, alpha), start, end, 5)
        pygame.draw.line(trail_surface, (255, 235, 75, max(40, alpha - 30)), start, end, 2)
        pygame.draw.line(
            trail_surface,
            (60, 210, 255, max(55, alpha - 80)),
            (start[0], start[1] + 13),
            (end[0] - 24, end[1] + 13),
            2,
        )

    for index in range(6):
        spark_x = base_x - 35 - ((now // 22 + index * 37) % 185)
        spark_y = base_y - 42 + ((index * 23 + now // 18) % 88)
        spark_len = 16 + index * 3
        pygame.draw.line(
            trail_surface,
            (255, 245, 130, 185),
            (spark_x, spark_y),
            (spark_x - spark_len, spark_y + 4),
            2,
        )

    aura_alpha = 100 + int(math.sin(now / 45) * 35)
    pygame.draw.ellipse(
        trail_surface,
        (255, 45, 35, aura_alpha),
        (base_x - 116, base_y - 50, 178, 100),
        7,
    )
    pygame.draw.ellipse(
        trail_surface,
        (255, 135, 30, aura_alpha),
        (base_x - 96, base_y - 43, 145, 86),
        4,
    )
    pygame.draw.ellipse(
        trail_surface,
        (50, 210, 255, 145),
        (base_x - 130, base_y - 58, 205, 116),
        2,
    )

    surface.blit(trail_surface, (dino_rect.left - 205, center_y - 75))


def draw_sprint_impacts(surface, impacts, now):
    """绘制冲刺撞碎障碍物时的爆裂效果，并清理过期动画。"""
    active_impacts = []
    for center, start_time in impacts:
        elapsed = now - start_time
        if elapsed >= SPRINT_IMPACT_DURATION_MS:
            continue

        progress = elapsed / SPRINT_IMPACT_DURATION_MS
        alpha = max(0, int(220 * (1 - progress)))
        radius = int(8 + progress * 34)
        pygame.draw.circle(surface, (255, 55, 35, alpha), center, radius + 8, 4)
        pygame.draw.circle(surface, (255, 190, 40, alpha), center, radius, 3)
        for index in range(12):
            angle = math.tau * index / 12
            end = (
                center[0] + int(math.cos(angle) * (radius + 22)),
                center[1] + int(math.sin(angle) * (radius + 22)),
            )
            color = (255, 70, 35, alpha) if index % 2 == 0 else (55, 195, 255, alpha)
            pygame.draw.line(surface, color, center, end, 3)
        active_impacts.append((center, start_time))

    return active_impacts


def draw_sprint_hud(surface, font, active, ready, now, sprint_start, cooldown_start, dark_theme=False):
    """右上角显示冲刺状态：可用、持续中或冷却中。"""
    width = 210
    height = 44
    x = SCREEN_WIDTH - width - 20
    y = 70
    colors = theme_colors(dark_theme)

    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(panel, colors["panel"], (0, 0, width, height), border_radius=6)
    pygame.draw.rect(panel, colors["panel_border"], (0, 0, width, height), 2, border_radius=6)

    if active:
        remaining = max(0, SPRINT_DURATION_MS - (now - sprint_start))
        label = f"SPRINT {remaining / 1000:.1f}s"
        fill_ratio = remaining / SPRINT_DURATION_MS
        fill_color = (255, 70, 35)
    elif ready:
        label = "SPRINT READY"
        fill_ratio = 1.0
        fill_color = (40, 190, 255)
    else:
        remaining = max(0, SPRINT_COOLDOWN_MS - (now - cooldown_start))
        label = f"SPRINT CD {remaining / 1000:.1f}s"
        fill_ratio = 1 - (remaining / SPRINT_COOLDOWN_MS)
        fill_color = (120, 120, 120)

    pygame.draw.rect(panel, colors["bar_bg"], (12, 27, width - 24, 8), border_radius=4)
    pygame.draw.rect(
        panel,
        fill_color,
        (12, 27, int((width - 24) * fill_ratio), 8),
        border_radius=4,
    )
    text = font.render(label, True, colors["text"])
    panel.blit(text, (12, 7))
    surface.blit(panel, (x, y))


def get_pause_button_rect():
    return pygame.Rect(SCREEN_WIDTH - 200, 24, 30, 30)


def draw_pause_button(surface, dark_theme=False, paused=False):
    if not ENABLE_PAUSE:
        return

    rect = get_pause_button_rect()
    colors = theme_colors(dark_theme)
    pygame.draw.rect(surface, colors["panel"], rect, border_radius=4)
    pygame.draw.rect(surface, colors["panel_border"], rect, 2, border_radius=4)

    icon_color = colors["text"]
    if paused:
        points_icon = [
            (rect.left + 11, rect.top + 8),
            (rect.left + 11, rect.bottom - 8),
            (rect.right - 8, rect.centery),
        ]
        pygame.draw.polygon(surface, icon_color, points_icon)
    else:
        pygame.draw.rect(surface, icon_color, (rect.left + 9, rect.top + 8, 4, 14))
        pygame.draw.rect(surface, icon_color, (rect.right - 13, rect.top + 8, 4, 14))


def draw_pause_overlay(surface, font, small_font, dark_theme=False):
    if not ENABLE_PAUSE:
        return

    panel_width = 360
    panel_height = 150
    panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    pygame.draw.rect(panel, (255, 255, 255, 215), (0, 0, panel_width, panel_height), border_radius=6)
    pygame.draw.rect(panel, (45, 45, 45, 210), (0, 0, panel_width, panel_height), 2, border_radius=6)

    title = font.render("PAUSED", True, (35, 35, 35))
    resume_hint = small_font.render("Press Q to Resume", True, (55, 55, 55))
    restart_hint = small_font.render("Press R to Restart", True, (55, 55, 55))
    panel.blit(title, title.get_rect(center=(panel_width // 2, 38)))
    panel.blit(resume_hint, resume_hint.get_rect(center=(panel_width // 2, 82)))
    panel.blit(restart_hint, restart_hint.get_rect(center=(panel_width // 2, 112)))
    surface.blit(panel, panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
    draw_pause_button(surface, dark_theme, paused=True)


def main():
    """一局游戏的主循环。"""
    global game_speed, base_game_speed, x_pos_bg, y_pos_bg, points, obstacles
    run = True
    clock = pygame.time.Clock()
    player = Dinosaur()
    cloud = Cloud()
    reader = get_eeg_reader()
    base_game_speed = BASE_GAME_SPEED
    game_speed = BASE_GAME_SPEED
    x_pos_bg = 0
    y_pos_bg = 380
    points = 0
    font = pygame.font.Font('freesansbold.ttf', 20)
    hud_font = pygame.font.Font('freesansbold.ttf', 16)
    obstacles = []
    death_count = 0
    shield_active = False
    shield_cooldown_start = -SHIELD_COOLDOWN_MS
    shield_break_start = None
    sprint_active = False
    sprint_start = 0
    sprint_cooldown_start = -SPRINT_COOLDOWN_MS
    sprint_impacts = []
    paused = False
    pause_started = 0
    paused_frame = None
    consecutive_success_count = 0
    attention_assist_bonus = 0
    focus_assist_paused_by_sprint = False
    was_sprint_active = False
    test_eeg_state = get_default_test_eeg_state()
    test_blink_pending = False

    def score(dark_theme):
        """更新分数，并每 100 分提高基础速度。"""
        global points, base_game_speed
        points += 1
        if points % 100 == 0:
            base_game_speed += 1

        colors = theme_colors(dark_theme)
        text = font.render("Points: " + str(points), True, colors["text"])
        textRect = text.get_rect()
        textRect.center = (1000, 40)
        SCREEN.blit(text, textRect)

    def draw_eeg_hud(
        eeg_state,
        signal_good,
        mode_text,
        shield_ready,
        dark_theme,
        effective_attention,
        assist_bonus,
        success_count,
        sprint_ready,
    ):
        """在左上角显示脑电状态，方便联调 STM32 数据。"""
        if ENABLE_EEG_TEST_HOTKEYS:
            eeg_status = "EEG: TEST HOTKEYS"
        elif reader is None:
            eeg_status = "EEG: DISABLED"
        elif not eeg_state.connected:
            eeg_status = "EEG: OFFLINE"
        elif not signal_good:
            eeg_status = "EEG: BAD SIGNAL"
        else:
            eeg_status = "EEG: OK"

        if assist_bonus > 0:
            att_text = f"ATT: {eeg_state.attention}(+{assist_bonus})={effective_attention}"
        else:
            att_text = f"ATT: {eeg_state.attention}"

        hud_lines = [
            f"{att_text}  MED: {eeg_state.meditation}  SIG: {eeg_state.signal}",
            f"BLINK: {eeg_state.blink_count}  {eeg_status}",
            f"MODE: {mode_text}  SHIELD: {'ON' if shield_ready else 'OFF'}",
        ]
        if ENABLE_EEG_TEST_HOTKEYS:
            hud_lines.append(
                f"FOCUS PASS: {success_count}  BONUS: +{assist_bonus}  SPRINT: {'READY' if sprint_ready else 'CD'}"
            )
            hud_lines.extend(eeg_test_help_lines())
        colors = theme_colors(dark_theme)
        for index, line in enumerate(hud_lines):
            text = hud_font.render(line, True, colors["text"])
            SCREEN.blit(text, (20, 20 + index * 22))

    def background(dark_theme):
        """滚动地面背景，形成小恐龙向前奔跑的效果。"""
        global x_pos_bg, y_pos_bg
        image_width = BG.get_width()
        bg_image = themed_surface(BG, dark_theme)
        SCREEN.blit(bg_image, (x_pos_bg, y_pos_bg))
        SCREEN.blit(bg_image, (image_width + x_pos_bg, y_pos_bg))
        if x_pos_bg <= -image_width:
            SCREEN.blit(bg_image, (image_width + x_pos_bg, y_pos_bg))
            x_pos_bg = 0
        x_pos_bg -= game_speed

    def resume_from_pause():
        nonlocal paused, pause_started, paused_frame, sprint_start, sprint_cooldown_start
        nonlocal shield_cooldown_start, shield_break_start, sprint_impacts
        duration = pygame.time.get_ticks() - pause_started
        sprint_start += duration
        sprint_cooldown_start += duration
        shield_cooldown_start += duration
        if shield_break_start is not None:
            shield_break_start += duration
        sprint_impacts = [(center, start_time + duration) for center, start_time in sprint_impacts]
        paused = False
        paused_frame = None

    while run:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                shutdown_game()
            if event.type == pygame.KEYDOWN:
                if paused and event.key == pygame.K_r:
                    if wait_for_eeg_ready_screen(reader):
                        main()
                        return
                    continue
                handled, blink_triggered = apply_eeg_test_key(event.key, test_eeg_state)
                if handled:
                    test_blink_pending = test_blink_pending or blink_triggered
            if ENABLE_PAUSE and event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                if paused:
                    resume_from_pause()
                else:
                    paused = True
                    pause_started = pygame.time.get_ticks()
                    paused_frame = SCREEN.copy()
            if ENABLE_PAUSE and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if get_pause_button_rect().collidepoint(event.pos):
                    if paused:
                        resume_from_pause()
                    else:
                        paused = True
                        pause_started = pygame.time.get_ticks()
                        paused_frame = SCREEN.copy()

        if paused:
            dark_theme = get_dark_theme(points)
            if paused_frame is not None:
                SCREEN.blit(paused_frame, (0, 0))
            draw_pause_overlay(SCREEN, font, hud_font, dark_theme)
            pygame.display.update()
            clock.tick(30)
            continue

        dark_theme = get_dark_theme(points)
        draw_dark_theme = False
        colors = theme_colors(draw_dark_theme)
        SCREEN.fill(colors["background"])
        userInput = pygame.key.get_pressed()

        # 每一帧读取一次脑电快照；读取器在后台线程中工作，不阻塞游戏循环。
        if reader is not None:
            eeg_state = reader.get_state()
        else:
            eeg_state = EEGState()
        eeg_state = merge_test_eeg_state(eeg_state, test_eeg_state)
        signal_good = eeg_state.connected and is_signal_good(eeg_state.signal)

        eeg_jump = False
        if signal_good and reader is not None:
            # BLINK 是一次性事件，consume_blink() 读取后会自动清除。
            eeg_jump = reader.consume_blink()
        if signal_good and test_blink_pending:
            eeg_jump = True
            test_blink_pending = False

        now = pygame.time.get_ticks()

        # 脑电控制规则：
        # Attention 提高速度，Meditation 触发减速/护盾，高 Attention 触发冲刺。
        if ENABLE_FOCUS_SUCCESS_ASSIST:
            attention_assist_bonus = min(
                FOCUS_SUCCESS_BONUS_MAX,
                consecutive_success_count * FOCUS_SUCCESS_BONUS_STEP,
            )
        else:
            attention_assist_bonus = 0
        effective_attention = min(100, eeg_state.attention + attention_assist_bonus)
        attention_bonus = attention_speed_bonus(effective_attention) if signal_good else 0
        relax_mode = signal_good and eeg_state.meditation >= MEDITATION_SHIELD
        meditation_factor = 0.75 if relax_mode else 1.0

        # 专注度达到阈值且冷却结束时，进入短时间冲刺。
        sprint_ready = now - sprint_cooldown_start >= SPRINT_COOLDOWN_MS
        if signal_good and effective_attention >= SPRINT_ATTENTION and not sprint_active and sprint_ready:
            sprint_active = True
            sprint_start = now
            consecutive_success_count = 0
            attention_assist_bonus = 0
            focus_assist_paused_by_sprint = True
            effective_attention = eeg_state.attention

        if sprint_active and now - sprint_start >= SPRINT_DURATION_MS:
            sprint_active = False
            sprint_cooldown_start = now
            sprint_ready = False
            focus_assist_paused_by_sprint = False
            consecutive_success_count = 0
            attention_assist_bonus = 0

        if was_sprint_active and not sprint_active:
            focus_assist_paused_by_sprint = False
            consecutive_success_count = 0
            attention_assist_bonus = 0

        if ENABLE_FOCUS_SUCCESS_ASSIST:
            attention_assist_bonus = min(
                FOCUS_SUCCESS_BONUS_MAX,
                consecutive_success_count * FOCUS_SUCCESS_BONUS_STEP,
            )
        else:
            attention_assist_bonus = 0
        effective_attention = min(100, eeg_state.attention + attention_assist_bonus)
        attention_bonus = attention_speed_bonus(effective_attention) if signal_good else 0

        sprint_speed_bonus = SPRINT_SPEED_BONUS if sprint_active else 0
        game_speed = clamp_game_speed((base_game_speed + attention_bonus + sprint_speed_bonus) * meditation_factor)
        auto_jump = should_auto_jump_for_bad_signal(player, obstacles, signal_good, game_speed)
        if auto_jump:
            nearest_obstacle, _ = get_nearest_right_obstacle(player, obstacles, jumpable_only=True)
            if nearest_obstacle is not None:
                nearest_obstacle.autopilot_assisted = True

        # Meditation 达标且冷却结束时，生成一个可抵消碰撞的护盾。
        if relax_mode and not shield_active:
            if now - shield_cooldown_start >= SHIELD_COOLDOWN_MS:
                shield_active = True

        if sprint_active:
            mode_text = "SPRINT"
        elif relax_mode:
            mode_text = "RELAX"
        elif attention_bonus > 0:
            mode_text = "FOCUS"
        else:
            mode_text = "NORMAL"

        player.update(userInput, eeg_jump=eeg_jump or auto_jump, current_game_speed=game_speed)
        if sprint_active:
            draw_sprint_effect(SCREEN, player.dino_rect, now)
        if shield_active:
            draw_shield(SCREEN, player.dino_rect, now)
        player.draw(SCREEN, draw_dark_theme)
        if shield_break_start is not None:
            if not draw_shield_break(SCREEN, player.dino_rect, shield_break_start, now):
                shield_break_start = None

        if len(obstacles) == 0:
            # 屏幕上没有障碍物时，随机生成一种新的障碍。
            # 飞鸟分为低位和高位两种：高位飞鸟需要下蹲，跳跃会撞上。
            obstacle_type = random.randint(0, 3)
            if obstacle_type == 0:
                obstacles.append(SmallCactus(SMALL_CACTUS))
            elif obstacle_type == 1:
                obstacles.append(LargeCactus(LARGE_CACTUS))
            elif obstacle_type == 2:
                obstacles.append(Bird(BIRD, BIRD_LOW_Y))
            else:
                obstacles.append(Bird(BIRD, BIRD_HIGH_Y))

        for obstacle in obstacles[:]:
            obstacle.draw(SCREEN, draw_dark_theme)
            obstacle.update()
            if (
                ENABLE_FOCUS_SUCCESS_ASSIST
                and not obstacle.counted
                and obstacle.rect.right < player.dino_rect.left
            ):
                obstacle.counted = True
                if (
                    signal_good
                    and not sprint_active
                    and not focus_assist_paused_by_sprint
                    and not auto_jump
                    and not obstacle.autopilot_assisted
                ):
                    consecutive_success_count += 1
                    attention_assist_bonus = min(
                        FOCUS_SUCCESS_BONUS_MAX,
                        consecutive_success_count * FOCUS_SUCCESS_BONUS_STEP,
                    )
            if player.dino_rect.colliderect(obstacle.rect):
                if sprint_active:
                    # 冲刺状态下碰撞不会死亡，障碍物被移除并播放撞击特效。
                    sprint_impacts.append((obstacle.rect.center, pygame.time.get_ticks()))
                    obstacles.remove(obstacle)
                elif shield_active:
                    # 护盾状态下抵消一次碰撞，然后进入冷却。
                    obstacles.remove(obstacle)
                    shield_active = False
                    shield_break_start = pygame.time.get_ticks()
                    shield_cooldown_start = pygame.time.get_ticks()
                    consecutive_success_count = 0
                    attention_assist_bonus = 0
                elif DEBUG_MODE == 1:
                    # 调试状态下保留碰撞判定，但不会进入死亡菜单。
                    pass
                else:
                    consecutive_success_count = 0
                    attention_assist_bonus = 0
                    death_count += 1
                    menu(death_count)

        background(draw_dark_theme)

        cloud.draw(SCREEN, draw_dark_theme)
        cloud.update()
        sprint_impacts = draw_sprint_impacts(SCREEN, sprint_impacts, now)

        score(draw_dark_theme)
        draw_eeg_hud(
            eeg_state,
            signal_good,
            mode_text,
            shield_active,
            draw_dark_theme,
            effective_attention,
            attention_assist_bonus,
            consecutive_success_count,
            sprint_ready,
        )
        draw_sprint_hud(SCREEN, hud_font, sprint_active, sprint_ready, now, sprint_start, sprint_cooldown_start, draw_dark_theme)
        draw_pause_button(SCREEN, draw_dark_theme, paused=False)

        was_sprint_active = sprint_active
        if dark_theme:
            invert_current_frame(SCREEN)
        clock.tick(30)
        pygame.display.update()


def menu(death_count):
    """开始菜单和死亡后的重新开始界面。"""
    global points
    run = True
    while run:
        SCREEN.fill((255, 255, 255))
        font = pygame.font.Font('freesansbold.ttf', 30)
        score_font = pygame.font.Font('freesansbold.ttf', 20)

        if death_count == 0:
            text = font.render("Press any Key to Start", True, (0, 0, 0))
            textRect = text.get_rect()
            textRect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            SCREEN.blit(text, textRect)
            SCREEN.blit(RUNNING[0], (SCREEN_WIDTH // 2 - 20, SCREEN_HEIGHT // 2 - 140))
        else:
            # 死亡后显示原版 Chrome Dino 风格的 Game Over、Reset 和本局分数。
            game_over_rect = GAME_OVER.get_rect()
            game_over_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60)
            SCREEN.blit(GAME_OVER, game_over_rect)

            reset_rect = RESET.get_rect()
            reset_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            SCREEN.blit(RESET, reset_rect)

            score = font.render("Your Score: " + str(points), True, (0, 0, 0))
            scoreRect = score.get_rect()
            scoreRect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)
            SCREEN.blit(score, scoreRect)

            hint = score_font.render("Press any Key to Restart", True, (80, 80, 80))
            hint_rect = hint.get_rect()
            hint_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 90)
            SCREEN.blit(hint, hint_rect)

        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                shutdown_game()
            if event.type == pygame.KEYDOWN:
                reader = get_eeg_reader()
                if wait_for_eeg_ready_screen(reader):
                    main()


if __name__ == "__main__":
    try:
        menu(death_count=0)
    finally:
        if eeg_reader is not None:
            eeg_reader.stop()
