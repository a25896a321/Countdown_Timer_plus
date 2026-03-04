"""
Windows 原生音效播放器
使用 winmm.dll MCI 命令，支援多聲道播放
完全相容 pygame.mixer.Channel 的多聲道功能
"""
import ctypes
import os
import time
from threading import Thread


class WindowsAudioPlayer:
    """
    Windows 原生音效播放器
    使用 MCI (Media Control Interface) 實現多聲道播放
    """

    def __init__(self):
        try:
            self.winmm = ctypes.windll.winmm
            self.available = True
        except Exception as e:
            print(f"[ERROR] winmm 初始化失敗: {e}")
            self.available = False

        self.active_channels = {}

    def get_channel(self, channel_id):
        if channel_id not in self.active_channels:
            self.active_channels[channel_id] = AudioChannel(self, channel_id)
        return self.active_channels[channel_id]


class AudioChannel:
    """
    音效聲道類別 — 模擬 pygame.mixer.Channel
    多個聲道可同時播放，互不干擾
    """

    def __init__(self, player, channel_id):
        self.player = player
        self.channel_id = channel_id
        self.is_busy = False
        self.current_alias = None
        self.stop_flag = False

    def play(self, sound, loops=0):
        if not self.player.available:
            return
        self.stop()

        def play_thread():
            self.is_busy = True
            self.stop_flag = False
            total_plays = loops + 1
            try:
                for i in range(total_plays):
                    if self.stop_flag:
                        break
                    timestamp = int(time.time() * 1000000)
                    alias = f"ch{self.channel_id}_s{timestamp}_i{i}"
                    self.current_alias = alias
                    sound_path = os.path.abspath(sound.file_path)
                    cmd_open = f'open "{sound_path}" type mpegvideo alias {alias}'
                    result = self.player.winmm.mciSendStringW(cmd_open, None, 0, None)
                    if result != 0:
                        cmd_open = f'open "{sound_path}" type waveaudio alias {alias}'
                        result = self.player.winmm.mciSendStringW(cmd_open, None, 0, None)
                    if result == 0:
                        cmd_play = f'play {alias} wait'
                        self.player.winmm.mciSendStringW(cmd_play, None, 0, None)
                        cmd_close = f'close {alias}'
                        self.player.winmm.mciSendStringW(cmd_close, None, 0, None)
                    else:
                        print(f"無法開啟音效檔案: {sound_path}")
                    if i < total_plays - 1 and not self.stop_flag:
                        time.sleep(0.1)
            except Exception as e:
                print(f"播放音效錯誤 (channel {self.channel_id}): {e}")
            finally:
                self.is_busy = False
                self.current_alias = None

        Thread(target=play_thread, daemon=True).start()

    def stop(self):
        self.stop_flag = True
        if self.current_alias and self.player.available:
            try:
                self.player.winmm.mciSendStringW(f'stop {self.current_alias}', None, 0, None)
                self.player.winmm.mciSendStringW(f'close {self.current_alias}', None, 0, None)
            except Exception:
                pass
        self.is_busy = False
        self.current_alias = None

    def get_busy(self):
        return self.is_busy


class AudioSound:
    """音效物件類別 — 模擬 pygame.mixer.Sound"""

    def __init__(self, file_path):
        self.file_path = file_path

    def play(self):
        player = get_player()
        if player.available:
            channel = player.get_channel(99)
            channel.play(self)


_global_player = WindowsAudioPlayer()


def get_player():
    return _global_player
