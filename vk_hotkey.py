"""
Windows VK Code (虛擬鍵碼) 熱鍵監聽系統
使用 Windows API 的 VK Code 精確識別每個物理按鍵，
完全區分數字鍵盤和主鍵盤。
"""

import ctypes
import threading
import time

# Windows VK Code 定義
VK_CODES = {
    # 功能鍵
    0x70: "F1", 0x71: "F2", 0x72: "F3", 0x73: "F4",
    0x74: "F5", 0x75: "F6", 0x76: "F7", 0x77: "F8",
    0x78: "F9", 0x79: "F10", 0x7A: "F11", 0x7B: "F12",

    # 數字鍵（主鍵盤）
    0x30: "0", 0x31: "1", 0x32: "2", 0x33: "3", 0x34: "4",
    0x35: "5", 0x36: "6", 0x37: "7", 0x38: "8", 0x39: "9",

    # 字母鍵
    0x41: "A", 0x42: "B", 0x43: "C", 0x44: "D", 0x45: "E",
    0x46: "F", 0x47: "G", 0x48: "H", 0x49: "I", 0x4A: "J",
    0x4B: "K", 0x4C: "L", 0x4D: "M", 0x4E: "N", 0x4F: "O",
    0x50: "P", 0x51: "Q", 0x52: "R", 0x53: "S", 0x54: "T",
    0x55: "U", 0x56: "V", 0x57: "W", 0x58: "X", 0x59: "Y",
    0x5A: "Z",

    # 數字鍵盤（與主鍵盤完全不同的 VK Code）
    0x60: "NumPad0", 0x61: "NumPad1", 0x62: "NumPad2", 0x63: "NumPad3",
    0x64: "NumPad4", 0x65: "NumPad5", 0x66: "NumPad6", 0x67: "NumPad7",
    0x68: "NumPad8", 0x69: "NumPad9",

    # 數字鍵盤運算符
    0x6A: "NumPad*",
    0x6B: "NumPad+",
    0x6D: "NumPad-",
    0x6E: "NumPad.",
    0x6F: "NumPad/",

    # 主鍵盤特殊符號
    0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-",
    0xBE: ".", 0xBF: "/", 0xC0: "`",
    0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'",

    # 控制鍵
    0x08: "Backspace", 0x09: "Tab", 0x0D: "Enter",
    0x10: "Shift", 0x11: "Ctrl", 0x12: "Alt",
    0x13: "Pause", 0x14: "CapsLock",
    0x1B: "Escape", 0x20: "Space",

    # 方向鍵
    0x21: "PageUp", 0x22: "PageDown", 0x23: "End", 0x24: "Home",
    0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down",

    # 編輯鍵
    0x2D: "Insert", 0x2E: "Delete",

    # 其他
    0x90: "NumLock", 0x91: "ScrollLock",
}

# 反向映射：從名稱到 VK Code
VK_NAME_TO_CODE = {v: k for k, v in VK_CODES.items()}


class VKHotkeyListener:
    """基於 Windows VK Code 的全局熱鍵監聽器"""

    def __init__(self, callback):
        """
        Args:
            callback: 回調函數，接收 vk_code (int) 和 vk_name (str)
        """
        self.callback = callback
        self.running = False
        self.thread = None
        try:
            self.user32 = ctypes.windll.user32
            self.GetAsyncKeyState = self.user32.GetAsyncKeyState
            self.GetAsyncKeyState.argtypes = [ctypes.c_int]
            self.GetAsyncKeyState.restype = ctypes.c_short
        except Exception as e:
            print(f"VK 熱鍵系統初始化失敗: {e}")
            self.user32 = None

    def start(self):
        if not self.user32:
            return False
        if self.running:
            return True
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

    def _listen_loop(self):
        pressed_keys = set()
        while self.running:
            try:
                for vk_code, vk_name in VK_CODES.items():
                    state = self.GetAsyncKeyState(vk_code)
                    if state & 0x8000:
                        if vk_code not in pressed_keys:
                            pressed_keys.add(vk_code)
                            try:
                                self.callback(vk_code, vk_name)
                            except Exception as e:
                                print(f"熱鍵回調錯誤: {e}")
                    else:
                        pressed_keys.discard(vk_code)
                time.sleep(0.01)
            except Exception as e:
                print(f"VK 監聽循環錯誤: {e}")
                time.sleep(0.1)

    def is_running(self):
        return self.running


class VKCaptureSingleKey:
    """一次性按鍵捕獲器，用於設定熱鍵時偵測使用者按下的鍵"""

    def __init__(self, callback):
        """
        Args:
            callback: 接收 (vk_code, vk_name) 的回調函數
        """
        self.callback = callback
        self.running = False
        self.thread = None
        try:
            self.user32 = ctypes.windll.user32
            self.GetAsyncKeyState = self.user32.GetAsyncKeyState
            self.GetAsyncKeyState.argtypes = [ctypes.c_int]
            self.GetAsyncKeyState.restype = ctypes.c_short
        except Exception:
            self.user32 = None

    def start_capture(self):
        if not self.user32:
            return False
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.running = False

    def _capture_loop(self):
        # 等待所有鍵都放開後再開始監聽
        time.sleep(0.3)
        while self.running:
            try:
                for vk_code, vk_name in VK_CODES.items():
                    state = self.GetAsyncKeyState(vk_code)
                    if state & 0x8001:  # 剛按下
                        self.running = False
                        try:
                            self.callback(vk_code, vk_name)
                        except Exception as e:
                            print(f"捕獲回調錯誤: {e}")
                        return
                time.sleep(0.01)
            except Exception as e:
                print(f"捕獲循環錯誤: {e}")
                time.sleep(0.1)


def get_vk_display_name(vk_name: str) -> str:
    """將 VK 名稱轉換為使用者友好的顯示名稱"""
    if not vk_name:
        return ""
    if vk_name.startswith("NumPad"):
        return "Num" + vk_name[6:]
    return vk_name


def get_vk_code_from_name(vk_name: str):
    return VK_NAME_TO_CODE.get(vk_name)


def get_vk_name_from_code(vk_code: int):
    return VK_CODES.get(vk_code)
