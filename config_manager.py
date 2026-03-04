"""
設定檔管理模組
負責讀取、儲存、匯入、匯出設定檔
支援最多 12 個設定檔插槽
"""

import json
import os
import sys
import copy


def resource_path(relative_path: str) -> str:
    """取得資源路徑（支援 PyInstaller onefile / onedir 打包）"""
    try:
        base_path = sys._MEIPASS              # onefile 模式：解壓暫存目錄
    except AttributeError:
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)  # onedir 模式：exe 旁
        else:
            base_path = os.path.abspath(".")  # 開發模式：腳本旁
    return os.path.join(base_path, relative_path)


def get_data_dir() -> str:
    """取得資料目錄（exe 旁或腳本旁）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_FILE = "countdown_config.json"
MAX_PROFILES = 12


def make_default_sound_config():
    return {"file": None, "mode": "once", "advance": 1, "frequency": 1}


def make_default_timer():
    return {
        "timer_name": "新計時",
        "key": None,
        "mode": "loop",          # loop / stop / dual
        "time1": 60,
        "time2": 30,
        "hotkey_action": "reset_start",   # reset_start / toggle
        "image_mode": "default",          # default / cooldown / original_only
        "image1": None,
        "image2": None,
        "sound1": make_default_sound_config(),
        "sound2": make_default_sound_config(),
    }


def make_default_profile(name="新設定檔"):
    return {
        "name": name,
        "timers": []
    }


def make_default_overlay_settings():
    return {
        "x": 500,
        "y": 700,
        "icon_size": 48,
        "spacing": 1,
        "opacity": 0.9,
        "show_bg": False,
        "bg_color": "#1a1a2e",
        "text_color": "#ffffff",
        # 控制列顯示
        "show_drag": True,          # 顯示拖曳手把圖示
        "show_gear": True,          # 顯示齒輪設定按鈕
        # 數字背景
        "show_num_bg": False,       # 顯示數字背景底色
        "num_bg_color": "#1a1a2e",  # 數字背景顏色
        # 計時名稱
        "show_name_bg": True,           # 顯示計時名稱背景底色
        "name_bg_color": "#1a1a2e",     # 計時名稱背景顏色
        "name_color": "#ffffff",         # 計時名稱字體顏色
        "name_position": "below_img",   # above_img / below_img / center_img / top_img / bottom_img
        "name_align": "center",          # left / center / right
        # 顯示控制
        "hide_idle_timers": False,       # 隱藏未倒數中的計時器
    }


def make_default_global_hotkeys():
    return {
        "reset_all":      "F6",
        "toggle_all":     "F7",
        "toggle_overlay": "F8",
    }


def make_default_config():
    """建立預設完整設定"""
    profiles = [None] * MAX_PROFILES

    # 預設檔1
    profiles[0] = {
        "name": "炎計時1",
        "timers": [
            {
                "timer_name": "固定魔方",
                "key": "NumPad/",
                "mode": "loop",
                "time1": 150,
                "hotkey_action": "reset_start",
                "image1": "Zakum_Green square",
                "image2": None,
                "sound1": {"file": "炎-中文-女-瀟瀟1_固定魔方", "mode": "once", "advance": 2, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "魔方/黑水(雙回合)",
                "key": "Tab",
                "mode": "dual",
                "time1": 40,
                "time2": 40,
                "hotkey_action": "reset_start",
                "image1": "Zakum_Poison pit",
                "image2": "Zakum_Green square",
                "sound1": {"file": "炎-中文-女-瀟瀟1_黑水", "mode": "once", "advance": 2, "frequency": 1},
                "sound2": {"file": "炎-中文-女-瀟瀟1_機制魔方", "mode": "once", "advance": 2, "frequency": 1},
            },
        ]
    }
    # 預設檔2
    profiles[1] = {
        "name": "炎計時2",
        "timers": [
            {
                "timer_name": "固定魔方",
                "key": "NumPad/",
                "mode": "loop",
                "time1": 150,
                "hotkey_action": "reset_start",
                "image1": "Zakum_Green square",
                "image2": None,
                "sound1": {"file": "炎-中文-女-瀟瀟1_固定魔方", "mode": "once", "advance": 2, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "黑水(單計時)",
                "key": "`",
                "mode": "stop",
                "time1": 40,
                "hotkey_action": "reset_start",
                "image1": "Zakum_Poison pit",
                "image2": None,
                "sound1": {"file": "炎-中文-女-瀟瀟1_黑水", "mode": "once", "advance": 2, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
        ]
    }
    # 預設檔3
    profiles[2] = {
        "name": "困拉計時1（物理推薦）",
        "timers": [
            {
                "timer_name": "69%困拉黑水",
                "key": "`",
                "mode": "loop",
                "time1": 60,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_Poison pit",
                "image2": None,
                "sound1": {"file": "困拉-中文-女-瀟瀟1_黑水", "mode": "once", "advance": 2, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "84%玩家炸彈",
                "key": "Tab",
                "mode": "loop",
                "time1": 25,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_boom alarm",
                "image2": None,
                "sound1": {"file": "困拉-中文-女-瀟瀟1_頭頂炸彈", "mode": "once", "advance": 1, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "84%反盾鬧鐘",
                "key": "CapsLock",
                "mode": "loop",
                "time1": 80,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_alarm time",
                "image2": None,
                "sound1": {"file": "困拉-中文-女-瀟瀟1_反盾鬧鐘", "mode": "once", "advance": 1, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
        ]
    }
    # 預設檔4
    profiles[3] = {
        "name": "困拉計時2（物理推薦）",
        "timers": [
            {
                "timer_name": "69%困拉黑水",
                "key": "`",
                "mode": "loop",
                "time1": 60,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_Poison pit",
                "image2": None,
                "sound1": {"file": "困拉-中文-女-瀟瀟1_黑水", "mode": "once", "advance": 2, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "84%反盾鬧鐘",
                "key": "CapsLock",
                "mode": "loop",
                "time1": 80,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_alarm time",
                "image2": None,
                "sound1": {"file": "困拉-中文-女-瀟瀟1_反盾鬧鐘", "mode": "once", "advance": 1, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
        ]
    }

    # 預設檔5
    profiles[4] = {
        "name": "困拉計時3（計時推薦）",
        "timers": [
            {
                "timer_name": "69%困拉黑水",
                "key": "`",
                "mode": "loop",
                "time1": 60,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_Poison pit",
                "image2": None,
                "sound1": {"file": "困拉-中文-女-瀟瀟1_黑水", "mode": "once", "advance": 2, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "89%增傷時鐘",
                "key": "NumPad+",
                "mode": "loop",
                "time1": 10,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_clock",
                "image2": None,
                "sound1": {"file": "困拉-中文-女-瀟瀟1_扣時", "mode": "once", "advance": 1, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "84%小怪(單計時)",
                "key": "NumPad*",
                "mode": "stop",
                "time1": 45,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_little monster",
                "image2": None,
                "sound1": {"file": "困拉-中文-女-瀟瀟1_小怪消失", "mode": "once", "advance": 3, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
        ]
    }

        # 預設檔6
    profiles[5] = {
        "name": "困拉計時4（計時推薦）",
        "timers": [
            {
                "timer_name": "69%困拉黑水",
                "key": "`",
                "mode": "loop",
                "time1": 60,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_Poison pit",
                "image2": None,
                "sound1": {"file": "困拉-中文-女-瀟瀟1_黑水", "mode": "once", "advance": 2, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "89%增傷時鐘",
                "key": "NumPad+",
                "mode": "loop",
                "time1": 10,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_clock",
                "image2": None,
                "sound1": {"file": "困拉-中文-女-瀟瀟1_扣時", "mode": "once", "advance": 1, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "84%小怪/消失(雙回合)",
                "key": "NumPad-",
                "mode": "dual",
                "time1": 45,
                "time2": 5,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_little monster",
                "image2": "Papulatus(Hard)_little monster disappears",
                "sound1": {"file": "困拉-中文-女-瀟瀟1_小怪消失", "mode": "once", "advance": 3, "frequency": 1},
                "sound2": {"file": "困拉-中文-女-瀟瀟1_召喚小怪", "mode": "once", "advance": 1, "frequency": 1},
            },
        ]
    }
        # 預設檔7
    profiles[6] = {
        "name": "困拉計時5（全部）",
        "timers": [
            {
                "timer_name": "69%困拉黑水",
                "key": "`",
                "mode": "loop",
                "time1": 60,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_Poison pit",
                "image2": None,
                "sound1": {"file": "困拉-中文-女-瀟瀟1_黑水", "mode": "once", "advance": 2, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "84%反盾鬧鐘",
                "key": "CapsLock",
                "mode": "loop",
                "time1": 80,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_alarm time",
                "image2": None,
                "sound1": {"file": "困拉-中文-女-瀟瀟1_反盾鬧鐘", "mode": "once", "advance": 1, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "89%增傷時鐘",
                "key": "NumPad+",
                "mode": "loop",
                "time1": 10,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_clock",
                "image2": None,
                "sound1": {"file": "困拉-中文-女-瀟瀟1_扣時", "mode": "once", "advance": 1, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "84%小怪(單計時)",
                "key": "NumPad*",
                "mode": "stop",
                "time1": 45,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_little monster",
                "image2": None,
                "sound1": {"file": "困拉-中文-女-瀟瀟1_小怪消失", "mode": "once", "advance": 3, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "84%小怪/消失(雙回合)",
                "key": "NumPad-",
                "mode": "dual",
                "time1": 45,
                "time2": 5,
                "hotkey_action": "reset_start",
                "image1": "Papulatus(Hard)_little monster",
                "image2": "Papulatus(Hard)_little monster disappears",
                "sound1": {"file": "困拉-中文-女-瀟瀟1_小怪消失", "mode": "once", "advance": 3, "frequency": 1},
                "sound2": {"file": "困拉-中文-女-瀟瀟1_召喚小怪", "mode": "once", "advance": 1, "frequency": 1},
            },
        ]
    }

    # 預設檔8
    profiles[7] = {
        "name": "buff機（全部）",
        "timers": [
            {
                "timer_name": "祈禱",
                "key": "1",
                "mode": "stop",
                "time1": 300,
                "hotkey_action": "reset_start",
                "image1": "holySymbol",
                "image2": None,
                "sound1": {"file": "技能_祈禱", "mode": "once", "advance": 10, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "速激",
                "key": "2",
                "mode": "stop",
                "time1": 300,
                "hotkey_action": "reset_start",
                "image1": "haste",
                "image2": None,
                "sound1": {"file": "技能_速度激發", "mode": "once", "advance": 10, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "幸運",
                "key": "3",
                "mode": "stop",
                "time1": 300,
                "hotkey_action": "reset_start",
                "image1": "mesoUP",
                "image2": None,
                "sound1": {"file": "技能_幸運術", "mode": "once", "advance": 10, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "聖火",
                "key": "4",
                "mode": "stop",
                "time1": 300,
                "hotkey_action": "reset_start",
                "image1": "holyFire",
                "image2": None,
                "sound1": {"file": "技能_聖火", "mode": "once", "advance": 10, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "會心",
                "key": "5",
                "mode": "stop",
                "time1": 300,
                "hotkey_action": "reset_start",
                "image1": "sharpEyes",
                "image2": None,
                "sound1": {"file": "技能_會心之眼", "mode": "once", "advance": 10, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "雪花",
                "key": "6",
                "mode": "stop",
                "time1": 600,
                "hotkey_action": "reset_start",
                "image1": "Snowflakes",
                "image2": None,
                "sound1": {"file": "補品_雪花", "mode": "once", "advance": 3, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "章魚燒",
                "key": "7",
                "mode": "stop",
                "time1": 600,
                "hotkey_action": "reset_start",
                "image1": "TakoyakiJumbo",
                "image2": None,
                "sound1": {"file": "補品_章魚燒", "mode": "once", "advance": 3, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "迴避藥丸",
                "key": "8",
                "mode": "stop",
                "time1": 600,
                "hotkey_action": "reset_start",
                "image1": "dexterity-pill",
                "image2": None,
                "sound1": {"file": "補品_迴避藥丸", "mode": "once", "advance": 3, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "止痛劑",
                "key": "9",
                "mode": "stop",
                "time1": 1800,
                "hotkey_action": "reset_start",
                "image1": "pain-reliever",
                "image2": None,
                "sound1": {"file": "補品_止痛劑", "mode": "once", "advance": 3, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "海盜船冷卻",
                "key": "NumPad0",
                "mode": "stop",
                "time1": 90,
                "hotkey_action": "reset_start",
                "image_mode": "cooldown",
                "image1": "battleship",
                "image2": None,
                "sound1": {"file": "技能_cd結束", "mode": "once", "advance": 1, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "60分鐘",
                "key": "F1",
                "mode": "stop",
                "time1": 3600,
                "hotkey_action": "reset_start",
                "image1": "60min",
                "image2": None,
                "sound1": {"file": "計時_60分鐘了", "mode": "once", "advance": 1, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "加倍",
                "key": "Delete",
                "mode": "stop",
                "time1": 1800,
                "hotkey_action": "reset_start",
                "image1": "DoubleEXP",
                "image2": None,
                "sound1": {"file": "計時_加倍結束", "mode": "once", "advance": 1, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
        ]
    }


    # 預設檔9
    profiles[8] = {
        "name": "槍手日常使用（個人配置）",
        "timers": [
            {
                "timer_name": "祈禱",
                "key": "1",
                "mode": "stop",
                "time1": 300,
                "hotkey_action": "reset_start",
                "image1": "holySymbol",
                "image2": None,
                "sound1": {"file": "技能_祈禱", "mode": "once", "advance": 10, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "雪花",
                "key": "Insert",
                "mode": "stop",
                "time1": 600,
                "hotkey_action": "reset_start",
                "image1": "Snowflakes",
                "image2": None,
                "sound1": {"file": "補品_雪花", "mode": "once", "advance": 2, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "章魚燒",
                "key": "F12",
                "mode": "stop",
                "time1": 600,
                "hotkey_action": "reset_start",
                "image1": "TakoyakiJumbo",
                "image2": None,
                "sound1": {"file": "補品_章魚燒", "mode": "once", "advance": 2, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "迴避藥丸",
                "key": "=",
                "mode": "stop",
                "time1": 600,
                "hotkey_action": "reset_start",
                "image1": "dexterity-pill",
                "image2": None,
                "sound1": {"file": "補品_迴避藥丸", "mode": "once", "advance": 2, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "止痛劑",
                "key": "-",
                "mode": "stop",
                "time1": 1800,
                "hotkey_action": "reset_start",
                "image1": "pain-reliever",
                "image2": None,
                "sound1": {"file": "補品_止痛劑", "mode": "once", "advance": 2, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "海盜船冷卻",
                "key": "CapsLock",
                "mode": "stop",
                "time1": 90,
                "hotkey_action": "reset_start",
                "image_mode": "cooldown",
                "image1": "battleship",
                "image2": None,
                "sound1": {"file": "技能_cd結束", "mode": "once", "advance": 1, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "章魚",
                "key": "Space",
                "mode": "stop",
                "time1": 10,
                "hotkey_action": "reset_start",
                "image1": "octopus",
                "image2": None,
                "sound1": {"file": "技能_章魚", "mode": "once", "advance": 1, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
            {
                "timer_name": "加倍",
                "key": "Delete",
                "mode": "stop",
                "time1": 1800,
                "hotkey_action": "reset_start",
                "image1": "DoubleEXP",
                "image2": None,
                "sound1": {"file": "計時_加倍結束", "mode": "once", "advance": 1, "frequency": 1},
                "sound2": make_default_sound_config(),
            },
        ]
    }


    return {
        "language": "zh_TW",
        "active_profile": 0,
        "default_profile": 0,
        "always_on_top": True,
        "window_opacity": 0.95,
        "global_hotkeys": make_default_global_hotkeys(),
        "overlay": make_default_overlay_settings(),
        "profiles": profiles,
    }


class ConfigManager:
    """設定檔管理器"""

    def __init__(self):
        self.data_dir = get_data_dir()
        self.config_path = os.path.join(self.data_dir, CONFIG_FILE)
        self.config = {}
        self.load()

    def load(self):
        """從檔案載入設定"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self.config = self._merge_with_defaults(loaded)
            except Exception as e:
                print(f"載入設定失敗，使用預設值: {e}")
                self.config = make_default_config()
        else:
            self.config = make_default_config()
        self._ensure_profiles_length()

    def _merge_with_defaults(self, loaded: dict) -> dict:
        """將載入的設定與預設值合併，確保所有欄位存在"""
        default = make_default_config()
        result = copy.deepcopy(default)

        for key, val in loaded.items():
            if key == "profiles":
                continue
            if key in result:
                if isinstance(result[key], dict) and isinstance(val, dict):
                    result[key].update(val)
                else:
                    result[key] = val

        # 合併 profiles
        loaded_profiles = loaded.get("profiles", [])
        for i in range(MAX_PROFILES):
            if i < len(loaded_profiles):
                result["profiles"][i] = loaded_profiles[i]

        return result

    def _ensure_profiles_length(self):
        """確保 profiles 列表長度為 MAX_PROFILES"""
        profiles = self.config.get("profiles", [])
        while len(profiles) < MAX_PROFILES:
            profiles.append(None)
        self.config["profiles"] = profiles[:MAX_PROFILES]

    def save(self):
        """儲存設定到檔案"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"儲存設定失敗: {e}")
            return False

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value

    # ── 設定檔操作 ──────────────────────────────────────────────────────────

    def get_profile(self, slot: int):
        """取得指定插槽的設定檔（可能為 None）"""
        profiles = self.config.get("profiles", [])
        if 0 <= slot < len(profiles):
            return profiles[slot]
        return None

    def set_profile(self, slot: int, profile: dict):
        """設定指定插槽的設定檔"""
        self._ensure_profiles_length()
        self.config["profiles"][slot] = profile

    def clear_profile(self, slot: int):
        """清空指定插槽"""
        self._ensure_profiles_length()
        self.config["profiles"][slot] = None

    def get_active_profile(self):
        """取得當前啟用的設定檔"""
        slot = self.config.get("active_profile", 0)
        return self.get_profile(slot)

    def apply_profile(self, slot: int):
        """套用指定插槽的設定檔（空插槽亦可套用）"""
        self.config["active_profile"] = slot
        return True

    def get_profile_name(self, slot: int) -> str:
        p = self.get_profile(slot)
        if p is None:
            return ""
        return p.get("name", f"設定檔 {slot + 1}")

    def export_profile(self, slot: int, filepath: str) -> bool:
        """匯出指定插槽的設定檔到 JSON 檔案"""
        profile = self.get_profile(slot)
        if profile is None:
            return False
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"匯出失敗: {e}")
            return False

    def import_profile(self, slot: int, filepath: str) -> tuple:
        """匯入 JSON 檔案到指定插槽，返回 (success, error_msg)"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                profile = json.load(f)
            if not isinstance(profile, dict):
                return False, "無效的設定檔格式"
            if "name" not in profile or "timers" not in profile:
                return False, "設定檔缺少必要欄位 (name, timers)"
            self.set_profile(slot, profile)
            return True, ""
        except json.JSONDecodeError as e:
            return False, f"JSON 格式錯誤: {e}"
        except Exception as e:
            return False, str(e)

    # ── 全域熱鍵 ─────────────────────────────────────────────────────────────

    def get_global_hotkeys(self) -> dict:
        return self.config.get("global_hotkeys", make_default_global_hotkeys())

    def set_global_hotkey(self, action: str, vk_name):
        hk = self.config.setdefault("global_hotkeys", make_default_global_hotkeys())
        hk[action] = vk_name

    # ── 懸浮窗設定 ────────────────────────────────────────────────────────────

    def get_overlay_settings(self) -> dict:
        return self.config.get("overlay", make_default_overlay_settings())

    def update_overlay_settings(self, new_settings: dict):
        overlay = self.config.setdefault("overlay", make_default_overlay_settings())
        overlay.update(new_settings)

    # ── 資源路徑輔助 ──────────────────────────────────────────────────────────

    def get_sound_folder(self) -> str:
        return os.path.join(self.data_dir, "sound_type")

    def get_png_folder(self) -> str:
        return os.path.join(self.data_dir, "png_type")

    def get_sound_files(self) -> list:
        """掃描音效資料夾，返回 sound_type 資料夾中所有 .mp3 / .wav 檔案名稱（不含副檔名）"""
        folder = self.get_sound_folder()
        result = []
        if not os.path.exists(folder):
            return result
        for fname in sorted(os.listdir(folder)):
            name, ext = os.path.splitext(fname)
            if ext.lower() in (".mp3", ".wav"):
                result.append(name)
        return result

    def get_png_files(self) -> list:
        """掃描圖片資料夾，返回圖片名稱（不含副檔名和 _on/_off 後綴）"""
        folder = self.get_png_folder()
        result = []
        seen = set()
        if not os.path.exists(folder):
            return result
        for fname in sorted(os.listdir(folder)):
            name, ext = os.path.splitext(fname)
            if ext.lower() not in (".png", ".jpg", ".jpeg", ".gif"):
                continue
            base = name
            for suffix in ("_on", "_off"):
                if name.endswith(suffix):
                    base = name[:-len(suffix)]
                    break
            if base not in seen:
                seen.add(base)
                result.append(base)
        return result
