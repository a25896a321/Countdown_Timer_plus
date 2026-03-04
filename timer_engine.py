"""
計時器引擎模組
負責多組計時器的核心邏輯：倒數、模式切換、音效觸發、圖片閃爍
"""

import time
import threading
import os

try:
    from audio_player import get_player, AudioSound, AudioChannel
    _audio_player = get_player()
    AUDIO_AVAILABLE = _audio_player.available
except Exception:
    AUDIO_AVAILABLE = False
    _audio_player = None


# 計時器模式常數
MODE_LOOP = "loop"       # 自動循環倒數
MODE_STOP = "stop"       # 倒數後停止
MODE_DUAL = "dual"       # 雙回合切換

# 快捷鍵功能常數
ACTION_RESET_START = "reset_start"
ACTION_TOGGLE      = "toggle"       # 開關：未啟動→開始，倒數中→重置並停止

# 計時器狀態常數
STATE_IDLE = "idle"
STATE_RUNNING = "running"
STATE_FINISHED = "finished"


class TimerInstance:
    """
    單個計時器實例
    管理一組計時器的完整狀態
    """

    def __init__(self, config: dict, channel_id: int, data_dir: str = "."):
        self.config = config
        self.channel_id = channel_id
        self.data_dir = data_dir

        self.state = STATE_IDLE
        self.current_round = 1          # 1 或 2（雙回合模式）
        self.remaining = float(config.get("time1", 60))

        # 單一起始時間戳：reset_and_start() 設定後整個運行期間不再更改，
        # 所有 remaining 均由 (now - _epoch_start) 絕對計算，確保零累積誤差。
        self._epoch_start: float = None
        self._pause_remaining = float(config.get("time1", 60))

        self._last_second = -1
        self._last_cycle_idx: int = -1  # 上一 tick 的週期索引（用於偵測週期邊界）
        self._last_round: int = 0       # 上一 tick 的回合（0=未開始；用於 DUAL 切換偵測）
        self._sound1_played = False
        self._sound2_played = False

        self._lock = threading.Lock()

        # 圖片閃爍狀態
        self.flash_visible = True       # True=原圖, False=灰階
        self._flash_thread = None
        self._flash_running = False

    # ── 屬性存取 ────────────────────────────────────────────────────────────

    @property
    def mode(self) -> str:
        return self.config.get("mode", MODE_LOOP)

    @property
    def time1(self) -> float:
        return float(self.config.get("time1", 60))

    @property
    def time2(self) -> float:
        return float(self.config.get("time2", 30))

    @property
    def current_total_time(self) -> float:
        if self.mode == MODE_DUAL and self.current_round == 2:
            return self.time2
        return self.time1

    @property
    def is_running(self) -> bool:
        return self.state == STATE_RUNNING

    @property
    def is_finished(self) -> bool:
        return self.state == STATE_FINISHED

    @property
    def is_idle(self) -> bool:
        return self.state == STATE_IDLE

    # ── 控制方法 ────────────────────────────────────────────────────────────

    def trigger_hotkey(self):
        """觸發快捷鍵（根據設定的 hotkey_action 執行）"""
        action = self.config.get("hotkey_action", ACTION_RESET_START)
        if action == ACTION_RESET_START:
            self.reset_and_start()
        elif action == ACTION_TOGGLE:
            self.toggle_start_stop()
        else:
            # 向後相容舊設定值 "reset_stop"
            self.toggle_start_stop()

    def reset_and_start(self):
        """重置並開始倒數（雙回合模式回到回合一）"""
        with self._lock:
            self.current_round = 1
            self.remaining = self.time1
            self._pause_remaining = self.time1
            self._epoch_start = time.time()   # 唯一起始時間戳，整輪不變
            self.state = STATE_RUNNING
            self._last_second = -1
            self._last_cycle_idx = -1
            self._last_round = 0
            self._sound1_played = False
            self._sound2_played = False
            self._stop_flash()

    def reset_and_stop(self):
        """重置並停止（回到起始時間、狀態設為 IDLE）"""
        with self._lock:
            self.current_round = 1
            self.remaining = self.time1
            self._pause_remaining = self.time1
            self._epoch_start = None
            self.state = STATE_IDLE
            self._last_second = -1
            self._last_cycle_idx = -1
            self._last_round = 0
            self._sound1_played = False
            self._sound2_played = False
            self._stop_flash()

    def toggle_start_stop(self):
        """
        開關模式（關閉會重置）：
        - 若計時器「未在倒數」（IDLE / FINISHED）→ 重置並開始倒數
        - 若計時器「倒數中」（RUNNING）→ 重置回起始時間並停止
        """
        if self.state == STATE_RUNNING:
            self.reset_and_stop()
        else:
            self.reset_and_start()

    def stop(self):
        """停止計時"""
        with self._lock:
            if self.state == STATE_RUNNING:
                self._pause_remaining = self.remaining
            self._epoch_start = None
            self.state = STATE_IDLE
            self._stop_flash()

    def pause(self):
        """暫停（外部呼叫，用於全域暫停）"""
        self.stop()

    # ── 計時更新 ─────────────────────────────────────────────────────────────

    def update(self):
        """
        更新計時器狀態（應每 update_interval 秒呼叫一次）。
        返回需要觸發音效的資訊 (round, sound_config) 或 None。

        ── 核心設計：單一 Epoch 絕對計時 ──────────────────────────────────────
        _epoch_start 在整個倒數運行期間永不更改（只由 reset_and_start 設定一次）。
        remaining 直接由 (now - _epoch_start) 絕對計算，無任何累積誤差：
          MODE_LOOP  → remaining = time1 - (total_elapsed % time1)
          MODE_DUAL  → 依 (total_elapsed % (time1+time2)) 決定回合與 remaining
          MODE_STOP  → remaining = time1 - total_elapsed，歸零後設 FINISHED
        保證：10 秒迴圈第 20 輪結束時，total_elapsed == 200 秒（牆鐘絕對值）。
        """
        if self.state != STATE_RUNNING:
            return None

        now = time.time()
        mode = self.mode
        sound_trigger = None

        with self._lock:
            # max(0.0, ...) 防禦 NTP 回撥導致 total_elapsed 暫時為負
            total_elapsed = max(0.0, now - self._epoch_start)

            if mode == MODE_LOOP:
                cycle_time = self.time1
                if cycle_time <= 0:
                    return None
                cycle_idx     = int(total_elapsed / cycle_time)
                offset        = total_elapsed - cycle_idx * cycle_time
                new_remaining = max(0.0, cycle_time - offset)

                # 偵測週期邊界 → 重設音效旗標與秒數追蹤
                if cycle_idx != self._last_cycle_idx:
                    self._last_cycle_idx = cycle_idx
                    self._last_round     = 1
                    self._sound1_played  = False
                    self._last_second    = -1
                    self._stop_flash()
                    self.flash_visible   = True

                self.remaining = new_remaining

            elif mode == MODE_DUAL:
                period = self.time1 + self.time2
                if period <= 0:
                    return None
                cycle_idx = int(total_elapsed / period)
                offset    = total_elapsed - cycle_idx * period

                if offset < self.time1:
                    new_round     = 1
                    new_remaining = max(0.0, self.time1 - offset)
                else:
                    new_round     = 2
                    new_remaining = max(0.0, self.time2 - (offset - self.time1))

                # 偵測新週期或回合切換 → 重設音效旗標與秒數追蹤
                if cycle_idx != self._last_cycle_idx or new_round != self._last_round:
                    self._last_cycle_idx = cycle_idx
                    self._last_round     = new_round
                    self._sound1_played  = False
                    self._sound2_played  = False
                    self._last_second    = -1
                    self._stop_flash()
                    self.flash_visible   = True

                self.current_round = new_round
                self.remaining     = new_remaining

            elif mode == MODE_STOP:
                new_remaining  = max(0.0, self.time1 - total_elapsed)
                self.remaining = new_remaining
                if new_remaining <= 0:
                    self._stop_flash()
                    self.flash_visible = False   # 顯示灰階
                    self.state         = STATE_FINISHED
                    self._epoch_start  = None
                    return None

            current_second = int(self.remaining + 0.5)

        # ── 音效觸發（鎖外執行，避免長時間持鎖）────────────────────────────
        if current_second != self._last_second:
            self._last_second = current_second
            sound_trigger = self._check_sound_trigger(current_second)

        # ── 閃爍控制（最後 3 秒）────────────────────────────────────────────
        if 0 < self.remaining <= 3.0:
            if not self._flash_running:
                self._start_flash()
        else:
            if self._flash_running:
                self._stop_flash()
                self.flash_visible = True

        return sound_trigger

    def _check_sound_trigger(self, current_second: int):
        """
        檢查是否需要觸發音效
        返回 (round_num, sound_config) 或 None
        """
        round_num = self.current_round

        if round_num == 1 or self.mode != MODE_DUAL:
            sound_cfg = self.config.get("sound1")
        else:
            sound_cfg = self.config.get("sound2")

        if not sound_cfg or not sound_cfg.get("file"):
            return None

        advance = int(sound_cfg.get("advance", 2))
        play_mode = sound_cfg.get("mode", "once")
        frequency = int(sound_cfg.get("frequency", 1))

        if play_mode == "once":
            # 在提前 advance 秒時觸發一次
            if current_second == advance and current_second > 0:
                flag_attr = f"_sound{round_num}_played"
                if not getattr(self, flag_attr, False):
                    setattr(self, flag_attr, True)
                    return (round_num, sound_cfg)
        else:
            # 分段播放邏輯
            total_time = self.current_total_time
            if frequency > 0 and advance > 0:
                interval = advance / frequency
                for i in range(frequency):
                    trigger_time = advance - (i * interval)
                    trigger_rounded = int(trigger_time + 0.5)
                    if current_second == trigger_rounded and trigger_rounded > 0:
                        return (round_num, sound_cfg)

        return None

    # ── 圖片閃爍 ─────────────────────────────────────────────────────────────

    def _start_flash(self):
        """開始閃爍（前3秒）"""
        if self._flash_running:
            return
        self._flash_running = True

        def flash_loop():
            while self._flash_running:
                self.flash_visible = not self.flash_visible
                time.sleep(0.4)

        self._flash_thread = threading.Thread(target=flash_loop, daemon=True)
        self._flash_thread.start()

    def _stop_flash(self):
        """停止閃爍"""
        self._flash_running = False
        if self._flash_thread:
            self._flash_thread = None

    # ── 顯示輔助 ─────────────────────────────────────────────────────────────

    def get_display_seconds(self) -> int:
        """取得顯示用的秒數（四捨五入）"""
        return int(self.remaining + 0.5)

    def get_current_image_name(self) -> str:
        """取得當前應顯示的圖片名稱"""
        if self.mode == MODE_DUAL and self.current_round == 2:
            base = self.config.get("image2") or self.config.get("image1") or ""
        else:
            base = self.config.get("image1") or ""
        return base

    def get_image_state(self) -> str:
        """
        返回圖片應顯示的狀態（依 image_mode 決定顯示邏輯）：
        image_mode = "default"（預設）：
            倒數中=on，最後3秒閃爍，結束=gray
        image_mode = "cooldown"（冷卻模式）：
            倒數中=gray（冷卻中），最後3秒閃爍（提示即將完成），結束=on（準備好了）
        image_mode = "original_only"（僅用原圖）：
            永遠顯示原圖，不啟用灰階效果
        """
        image_mode = self.config.get("image_mode", "default")

        if image_mode == "original_only":
            # 永遠顯示原圖，不使用灰階
            if self.state == STATE_RUNNING:
                return "on"
            if self.state == STATE_FINISHED:
                return "on"
            return "normal"

        if image_mode == "cooldown":
            # 倒數中=灰階（冷卻中），結束=原圖（準備好了）
            if self.state == STATE_FINISHED or self.remaining <= 0:
                return "on"
            if self.state == STATE_RUNNING:
                if self._flash_running:
                    # 閃爍時：在灰階與原圖間切換，提示冷卻即將結束
                    return "flash_off" if self.flash_visible else "flash_on"
                return "gray"
            return "normal"

        # default（預設）
        if self.state == STATE_FINISHED or self.remaining <= 0:
            return "gray"
        if self.state == STATE_RUNNING:
            if self._flash_running:
                return "flash_on" if self.flash_visible else "flash_off"
            return "on"
        return "normal"


class TimerEngine:
    """
    多組計時器引擎
    管理所有計時器實例的建立、更新和熱鍵路由
    """

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.timers: list[TimerInstance] = []
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

        # 全域狀態
        self.all_disabled = False
        self.all_paused = False

        # 更新間隔：0.3 = 高延遲（預設），0.1 = 低延遲（較精確，適合短迴圈）
        self.update_interval: float = 0.3

        # 音效觸發回調（由外部設定）
        self.on_sound_trigger = None  # Callable[(timer_idx, round_num, sound_cfg)]
        # UI 更新回調
        self.on_update = None  # Callable[()]

        self.load_timers()

    def load_timers(self):
        """從當前啟用的設定檔載入計時器"""
        with self._lock:
            self.timers.clear()
            profile = self.config_manager.get_active_profile()
            if not profile:
                return
            data_dir = self.config_manager.data_dir
            for i, timer_cfg in enumerate(profile.get("timers", [])):
                inst = TimerInstance(timer_cfg, channel_id=i, data_dir=data_dir)
                self.timers.append(inst)

    def reload(self):
        """重新載入計時器（切換設定檔後呼叫）"""
        self.load_timers()

    # ── 引擎控制 ─────────────────────────────────────────────────────────────

    def start_engine(self):
        """啟動更新循環"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()

    def stop_engine(self):
        """停止更新循環"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _update_loop(self):
        """計時器更新主循環（間隔由 update_interval 控制）"""
        while self._running:
            try:
                self._tick()
            except Exception as e:
                print(f"計時器更新錯誤: {e}")
            time.sleep(self.update_interval)

    def _tick(self):
        """單次更新所有計時器"""
        if self.all_disabled or self.all_paused:
            return

        with self._lock:
            for i, timer in enumerate(self.timers):
                result = timer.update()
                if result is not None:
                    round_num, sound_cfg = result
                    self._trigger_sound(i, round_num, sound_cfg)

        if self.on_update:
            try:
                self.on_update()
            except Exception:
                pass

    def _trigger_sound(self, timer_idx: int, round_num: int, sound_cfg: dict):
        """觸發音效播放"""
        if not AUDIO_AVAILABLE or not _audio_player:
            return
        sound_file = sound_cfg.get("file")
        if not sound_file:
            return

        sound_folder = self.config_manager.get_sound_folder()
        # 尋找實際檔案
        for ext in (".mp3", ".wav"):
            full_path = os.path.join(sound_folder, sound_file + ext)
            if os.path.exists(full_path):
                try:
                    sound = AudioSound(full_path)
                    channel = _audio_player.get_channel(timer_idx * 2 + round_num)
                    channel.play(sound)
                except Exception as e:
                    print(f"播放音效失敗: {e}")
                break

        if self.on_sound_trigger:
            try:
                self.on_sound_trigger(timer_idx, round_num, sound_cfg)
            except Exception:
                pass

    # ── 熱鍵路由 ─────────────────────────────────────────────────────────────

    def handle_vk_key(self, vk_code: int, vk_name: str):
        """
        處理全局按鍵事件
        全域熱鍵（reset_all / toggle_all / toggle_overlay）永遠有效，
        個別計時器熱鍵只在啟用且非設定暫停狀態下有效。
        """
        # ── 全域熱鍵（停用狀態下仍可觸發） ────────────────────────────────
        global_hk = self.config_manager.get_global_hotkeys()
        if vk_name == global_hk.get("reset_all"):
            self.reset_all()
            return
        if vk_name == global_hk.get("toggle_all"):
            self.toggle_all_disabled()
            return
        if vk_name == global_hk.get("toggle_overlay"):
            if self.on_toggle_overlay:
                self.on_toggle_overlay()
            return

        # ── 個別計時器熱鍵（停用或設定暫停時不觸發） ─────────────────────
        if self.all_disabled or self.all_paused:
            return
        with self._lock:
            for timer in self.timers:
                if timer.config.get("key") == vk_name:
                    timer.trigger_hotkey()

    # 外部可設定的回調
    on_toggle_overlay = None

    # ── 全域控制 ─────────────────────────────────────────────────────────────

    def reset_all(self):
        """
        重置所有計時器至起始倒數時間並停止倒數。
        不改變 all_disabled / all_paused 狀態，保持當前啟用狀態。
        """
        with self._lock:
            for timer in self.timers:
                timer.reset_and_stop()
        # 通知 UI 更新（執行緒安全）
        if self.on_update:
            try:
                self.on_update()
            except Exception:
                pass

    def toggle_all_disabled(self):
        """
        切換啟用/停用。
        停用時：同時重置所有計時器至起始時間並停止倒數。
        啟用時：計時器保持在起始時間待命，由個別熱鍵觸發。
        """
        self.all_disabled = not self.all_disabled
        if self.all_disabled:
            # 停用時重置所有計時器
            with self._lock:
                for timer in self.timers:
                    timer.reset_and_stop()
        # 通知 UI 更新
        if self.on_update:
            try:
                self.on_update()
            except Exception:
                pass

    def resume_all(self):
        """取消設定視窗暫停"""
        self.all_paused = False

    def stop_all(self):
        """停止所有計時器"""
        with self._lock:
            for timer in self.timers:
                timer.stop()

    def get_timers(self) -> list:
        """取得計時器列表（唯讀）"""
        return list(self.timers)

    def play_sound_test(self, sound_file: str):
        """測試播放音效"""
        if not AUDIO_AVAILABLE or not _audio_player:
            return
        sound_folder = self.config_manager.get_sound_folder()
        for ext in (".mp3", ".wav"):
            full_path = os.path.join(sound_folder, sound_file + ext)
            if os.path.exists(full_path):
                try:
                    sound = AudioSound(full_path)
                    channel = _audio_player.get_channel(99)
                    channel.play(sound)
                except Exception as e:
                    print(f"測試音效失敗: {e}")
                break
