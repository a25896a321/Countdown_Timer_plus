"""
倒數計時器 主程式
Countdown_Timer_plus - Main Application
作者：oo_jump　協作：巴哈_波菜菜菜
版本：v1.3.1
"""

import tkinter as tk
from tkinter import ttk, messagebox
import platform
import os
import sys
import threading
import webbrowser

from translations import get_text, TRANSLATIONS
from config_manager import ConfigManager
from timer_engine import TimerEngine
from settings_window import ProfileWindow, TimerMgrWindow, OverlaySettingsWindow
from overlay_window import OverlayWindow

try:
    from vk_hotkey import VKHotkeyListener, get_vk_display_name
    VK_AVAILABLE = True
except ImportError:
    VK_AVAILABLE = False


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


# ── 顏色主題 ──────────────────────────────────────────────────────────────────

BG_MAIN    = "#1e2130"
BG_PANEL   = "#2d3250"
BG_BTN     = "#3a4170"
BG_ACCENT  = "#5a6bcc"
BG_SUCCESS = "#2d6a4f"
BG_DANGER  = "#8b1a1a"
FG_TEXT    = "#e8eaf6"
FG_SUB     = "#9199cc"
BORDER     = "#3d4571"


class CountdownTimerApp:
    """倒數計時器主應用程式"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.os_type = platform.system()
        self.font_family = "Microsoft JhengHei" if self.os_type == "Windows" else "PingFang SC"

        # 圖示路徑
        self.icon_path = resource_path("ico_timer.ico")
        if os.path.exists(self.icon_path):
            try:
                root.iconbitmap(self.icon_path)
            except Exception:
                pass

        # 設定管理器
        self.config_manager = ConfigManager()

        # 語言
        self.lang = self.config_manager.get("language", "zh_TW")

        # 計時引擎
        self.engine = TimerEngine(self.config_manager)
        self.engine.on_update = self._schedule_ui_update
        self.engine.on_toggle_overlay = lambda: self.root.after(0, self._toggle_overlay)

        # 狀態
        self._overlay: OverlayWindow = None
        self._overlay_mode = False
        self._settings_open = False
        self._ui_update_pending = False

        # 子視窗（唯一性限制）
        self._profile_win: ProfileWindow = None
        self._timer_mgr_win: TimerMgrWindow = None
        self._overlay_settings_win: OverlaySettingsWindow = None

        # VK 熱鍵監聽器
        self._vk_listener = None

        self._build_main_ui()
        self._apply_config_to_ui()
        self._setup_global_hotkeys()
        self.engine.start_engine()

        root.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ── 翻譯 ──────────────────────────────────────────────────────────────────

    def t(self, key: str) -> str:
        return get_text(self.lang, key)

    # ── UI 建構 ───────────────────────────────────────────────────────────────

    def _build_main_ui(self):
        self.root.title(self.t("app_title"))
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(False, False)

        style = ttk.Style()
        style.theme_use("clam")

        # ── hint_frame：頂部提示文字 ──────────────────────────────────────
        hint_frame = tk.Frame(self.root, bg=BG_PANEL, pady=4)
        hint_frame.pack(fill=tk.X, padx=0, pady=0)
        self.hint_label = tk.Label(
            hint_frame,
            text=self.t("hint_no_profile"),
            font=(self.font_family, 9),
            bg=BG_PANEL, fg=FG_SUB,
        )
        self.hint_label.pack(padx=10)

        # ── top_frame：控制按鈕列 ─────────────────────────────────────────
        top_frame = tk.Frame(self.root, bg=BG_MAIN, pady=6)
        top_frame.pack(fill=tk.X, padx=8)

        btn_defs = [
            # (attr, text_key, command, bg)
            ("topmost_btn", "btn_topmost_on", self._toggle_topmost, BG_SUCCESS),
            ("save_btn",    "btn_save_settings", self._open_profiles,  BG_BTN),
            ("settings_btn","btn_settings",   self._open_timer_mgr, BG_BTN),
            ("overlay_settings_btn","btn_overlay_settings", self._open_overlay_settings, BG_BTN),
            ("sponsor_btn", "btn_sponsor",    self._open_sponsor,   "#6a2d8b"),
        ]
        for attr, key, cmd, bg in btn_defs:
            btn = tk.Button(
                top_frame, text=self.t(key),
                command=cmd,
                bg=bg, fg=FG_TEXT,
                activebackground=BG_ACCENT, activeforeground=FG_TEXT,
                relief=tk.FLAT, bd=0, padx=8, pady=3,
                font=(self.font_family, 9),
                cursor="hand2",
            )
            btn.pack(side=tk.LEFT, padx=3)
            setattr(self, attr, btn)

        # 右側：語言 + 開關 + 懸浮框切換
        right = tk.Frame(top_frame, bg=BG_MAIN)
        right.pack(side=tk.RIGHT)

        self.lang_zh_btn = tk.Button(
            right, text="中文", command=lambda: self._change_lang("zh_TW"),
            bg=BG_BTN, fg=FG_TEXT, activebackground=BG_ACCENT,
            relief=tk.FLAT, bd=0, padx=6, pady=3,
            font=(self.font_family, 9), cursor="hand2",
        )
        self.lang_zh_btn.pack(side=tk.LEFT, padx=2)

        self.lang_en_btn = tk.Button(
            right, text="EN", command=lambda: self._change_lang("en_US"),
            bg=BG_BTN, fg=FG_TEXT, activebackground=BG_ACCENT,
            relief=tk.FLAT, bd=0, padx=6, pady=3,
            font=(self.font_family, 9), cursor="hand2",
        )
        self.lang_en_btn.pack(side=tk.LEFT, padx=2)

        self.switch_btn = tk.Button(
            right, text=self.t("btn_switch_on"),
            command=self._toggle_all_disabled,
            bg=BG_SUCCESS, fg=FG_TEXT, activebackground=BG_ACCENT,
            relief=tk.FLAT, bd=0, padx=8, pady=3,
            font=(self.font_family, 9), cursor="hand2",
        )
        self.switch_btn.pack(side=tk.LEFT, padx=3)

        self.timer_switch_btn = tk.Button(
            right, text=self.t("btn_overlay_open"),
            command=self._toggle_overlay,
            bg=BG_BTN, fg=FG_TEXT, activebackground=BG_ACCENT,
            relief=tk.FLAT, bd=0, padx=8, pady=3,
            font=(self.font_family, 9), cursor="hand2",
        )
        self.timer_switch_btn.pack(side=tk.LEFT, padx=3)

        # ── 計時器顯示區 ──────────────────────────────────────────────────
        self.timer_display_frame = tk.Frame(self.root, bg=BG_PANEL, pady=8)
        self.timer_display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 0))
        self._build_timer_displays()

        # ── opacity_frame：透明度拉條 ─────────────────────────────────────
        opacity_frame = tk.Frame(self.root, bg=BG_MAIN, pady=4)
        opacity_frame.pack(fill=tk.X, padx=10, pady=(4, 8))

        tk.Label(opacity_frame, text=self.t("opacity_label"),
                 font=(self.font_family, 8),
                 bg=BG_MAIN, fg=FG_SUB).pack(side=tk.LEFT, padx=4)

        self.opacity_scale = tk.Scale(
            opacity_frame,
            from_=0.1, to=1.0, resolution=0.05,
            orient=tk.HORIZONTAL,
            command=self._on_opacity_change,
            bg=BG_PANEL, fg=FG_TEXT,
            troughcolor=BG_BTN,
            highlightthickness=0,
            length=160,
            showvalue=False,
        )
        self.opacity_scale.set(self.config_manager.get("window_opacity", 0.95))
        self.opacity_scale.pack(side=tk.LEFT, padx=4)

        tk.Label(
            opacity_frame,
            text=self.t("hint_run_as_admin"),
            font=(self.font_family, 9),
            bg=BG_MAIN, fg="#ffffff",
            anchor="e",
        ).pack(side=tk.RIGHT, padx=6)

        # 延遲模式：標籤 + 切換按鈕
        # 按鈕永遠顯示「目前正在使用的模式」，顏色也區分狀態
        # 高延遲 0.3s = 灰藍（預設）  低延遲 0.1s = 綠色（效能模式）
        self._delay_btn = tk.Button(
            opacity_frame,
            text=self.t("btn_delay_high"),
            font=(self.font_family, 8),
            bg=BG_BTN, fg=FG_TEXT,
            activebackground=BG_ACCENT,
            activeforeground=FG_TEXT,
            relief=tk.FLAT, bd=0,
            padx=6, pady=2,
            cursor="hand2",
            command=self._toggle_delay,
        )
        self._delay_btn.pack(side=tk.RIGHT, padx=2)

        self._delay_label = tk.Label(
            opacity_frame,
            text=self.t("delay_label"),
            font=(self.font_family, 8),
            bg=BG_MAIN, fg=FG_SUB,
        )
        self._delay_label.pack(side=tk.RIGHT, padx=(6, 0))

    def _build_timer_displays(self):
        """建立計時器顯示行（含標題列，grid 對齊）"""
        for w in self.timer_display_frame.winfo_children():
            w.destroy()
        self.timer_rows = []
        ff = self.font_family

        timers = self.engine.get_timers()
        if not timers:
            tk.Label(
                self.timer_display_frame,
                text="← 請先設定計時組（⚙️ 計時管理）",
                font=(ff, 10),
                bg=BG_PANEL, fg=FG_SUB,
            ).pack(pady=20)
            return

        # ── 外層容器（grid 佈局）────────────────────────────────────────
        container = tk.Frame(self.timer_display_frame, bg=BG_PANEL)
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 4))

        # 欄位索引
        COL_NAME  = 0
        COL_KEY   = 1
        COL_TIME  = 2
        COL_MODE  = 3
        COL_ROUND = 4

        container.columnconfigure(COL_NAME,  weight=0, minsize=160)
        container.columnconfigure(COL_KEY,   weight=0, minsize=120)
        container.columnconfigure(COL_TIME,  weight=0, minsize=120)
        container.columnconfigure(COL_MODE,  weight=0, minsize=100)
        container.columnconfigure(COL_ROUND, weight=0, minsize=60)

        # ── 標題列 ──────────────────────────────────────────────────────
        header_cols = [
            (COL_NAME,  self.t("col_timer_name"), "w"),
            (COL_KEY,   self.t("col_hotkey"),     "center"),
            (COL_TIME,  self.t("col_time_sec"),   "center"),
            (COL_MODE,  self.t("col_mode"),       "center"),
            (COL_ROUND, "",                        "center"),
        ]
        for col, text, anchor in header_cols:
            tk.Label(
                container, text=text,
                font=(ff, 10, "bold"), bg=BG_PANEL, fg=FG_TEXT,
                anchor=anchor, padx=4, pady=3,
            ).grid(row=0, column=col, sticky="ew")

        # 標題下分隔線
        tk.Frame(container, bg=BORDER, height=1).grid(
            row=1, column=0, columnspan=5, sticky="ew", padx=2, pady=(0, 2))

        # ── 計時行 ──────────────────────────────────────────────────────
        for i, timer in enumerate(timers):
            row_ref = self._make_timer_row(container, timer, i, grid_row=i + 2)
            self.timer_rows.append(row_ref)

    def _make_timer_row(self, container: tk.Frame, timer, idx: int, grid_row: int):
        """在 grid 容器中建立單個計時器顯示行，回傳標籤參考物件"""
        import types
        ff = self.font_family

        # 初始倒數顯示值：未停用時顯示設定時間，停用中顯示 --
        time1 = int(timer.config.get("time1", 0))
        if self.engine.all_disabled or time1 == 0:
            init_text  = "--"
            init_color = FG_SUB
        else:
            init_text  = str(time1)
            init_color = FG_SUB

        # Col 0：計時名稱（不設 wraplength，永遠單行）
        name = timer.config.get("timer_name", f"計時 {idx+1}")
        tk.Label(
            container, text=name, font=(ff, 9),
            bg=BG_PANEL, fg=FG_SUB, anchor="w", padx=4,
        ).grid(row=grid_row, column=0, sticky="w", pady=2)

        # Col 1：快捷鍵
        key = timer.config.get("key") or self.t("hotkey_none")
        tk.Label(
            container, text=f"{key}",
            font=(ff, 8), bg=BG_PANEL, fg=FG_SUB, anchor="center",
        ).grid(row=grid_row, column=1, sticky="ew", pady=2)

        # Col 2：倒數時間（大字體，可動態更新）
        time_lbl = tk.Label(
            container, text=init_text,
            font=(ff, 22, "bold"),
            bg=BG_PANEL, fg=init_color, anchor="center",
        )
        time_lbl.grid(row=grid_row, column=2, sticky="ew", pady=2)

        # Col 3：倒數模式文字
        mode_key_map = {"loop": "mode_loop", "stop": "mode_stop", "dual": "mode_dual"}
        mode = timer.config.get("mode", "loop")
        tk.Label(
            container, text=self.t(mode_key_map.get(mode, "mode_loop")),
            font=(ff, 9), bg=BG_PANEL, fg=FG_SUB, anchor="center",
        ).grid(row=grid_row, column=3, sticky="ew", pady=2)

        # Col 4：回合標示（雙回合模式用，可動態更新）
        round_lbl = tk.Label(
            container, text="",
            font=(ff, 8), bg=BG_PANEL, fg=FG_SUB, anchor="center",
        )
        round_lbl.grid(row=grid_row, column=4, sticky="ew", pady=2)

        # 回傳輕量參考物件（_update_timer_displays 所需的三個欄位）
        r = types.SimpleNamespace()
        r._timer_idx = idx
        r._time_lbl  = time_lbl
        r._round_lbl = round_lbl
        return r

    def _update_timer_displays(self):
        """更新所有計時器顯示（在 Tkinter 主線程中執行）"""
        timers = self.engine.get_timers()
        from timer_engine import STATE_RUNNING, STATE_FINISHED, STATE_IDLE

        for row in self.timer_rows:
            idx = row._timer_idx
            if idx >= len(timers):
                continue
            timer = timers[idx]

            if self.engine.all_disabled:
                # 全停用：一律顯示 --
                text  = "--"
                color = FG_SUB
            elif timer.state == STATE_IDLE:
                # 啟用但未啟動：顯示設定的初始時間（time1）
                time1 = int(timer.time1)
                text  = str(time1) if time1 > 0 else "--"
                color = FG_SUB
            elif timer.state == STATE_FINISHED:
                text  = "0"
                color = BG_DANGER
            else:
                # STATE_RUNNING：顯示即時倒數
                secs = timer.get_display_seconds()
                text = str(secs)
                if secs <= 3:
                    color = "#ff6b6b" if timer.flash_visible else "#ff9999"
                elif secs <= 10:
                    color = "#ffd93d"
                else:
                    color = "#7c83e0"

            row._time_lbl.config(text=text, fg=color)

            # 回合標示（雙回合模式，倒數中才顯示）
            mode = timer.config.get("mode", "loop")
            if mode == "dual" and timer.state == STATE_RUNNING:
                round_txt = self.t("timer_round1") if timer.current_round == 1 \
                    else self.t("timer_round2")
                row._round_lbl.config(text=round_txt)
            else:
                row._round_lbl.config(text="")

        # 更新 hint
        self._update_hint()

    def _update_hint(self):
        profile = self.config_manager.get_active_profile()
        if profile is None:
            self.hint_label.config(text=self.t("hint_no_profile"))
            return
        name = profile.get("name", "")
        status = ""
        if self.engine.all_disabled:
            status = " " + self.t("hint_disabled")
        elif self.engine.all_paused:
            status = " " + self.t("hint_paused")
        self.hint_label.config(text=self.t("hint_profile") + name + status)

    # ── 設定套用 ──────────────────────────────────────────────────────────────

    def _apply_config_to_ui(self):
        """從設定檔套用 UI 狀態"""
        # 透明度
        opacity = self.config_manager.get("window_opacity", 0.95)
        self.root.attributes("-alpha", opacity)
        self.opacity_scale.set(opacity)

        # 置頂
        always_top = self.config_manager.get("always_on_top", True)
        self.root.attributes("-topmost", always_top)
        self._update_topmost_btn(always_top)

        # hint
        self._update_hint()

    def _update_topmost_btn(self, is_top: bool):
        if is_top:
            self.topmost_btn.config(text=self.t("btn_topmost_on"), bg=BG_SUCCESS)
        else:
            self.topmost_btn.config(text=self.t("btn_topmost_off"), bg=BG_DANGER)

    # ── 按鈕回調 ──────────────────────────────────────────────────────────────

    def _toggle_topmost(self):
        current = self.config_manager.get("always_on_top", True)
        new_val = not current
        self.config_manager.set("always_on_top", new_val)
        self.root.attributes("-topmost", new_val)
        self._update_topmost_btn(new_val)
        self.config_manager.save()

    def _on_opacity_change(self, val):
        opacity = float(val)
        self.config_manager.set("window_opacity", opacity)
        self.root.attributes("-alpha", opacity)

    def _toggle_delay(self):
        """切換計時引擎更新間隔：高延遲 0.3s ⇄ 低延遲 0.1s
        按鈕文字與顏色永遠反映「目前正在使用的模式」：
          高延遲 0.3s → 灰藍（BG_BTN，預設一般模式）
          低延遲 0.1s → 綠色（BG_SUCCESS，效能/精確模式）
        """
        if self.engine.update_interval == 0.3:
            self.engine.update_interval = 0.1
            self._delay_btn.config(text=self.t("btn_delay_low"), bg=BG_SUCCESS)
        else:
            self.engine.update_interval = 0.3
            self._delay_btn.config(text=self.t("btn_delay_high"), bg=BG_BTN)

    def _change_lang(self, lang: str):
        self.lang = lang
        self.config_manager.set("language", lang)
        self.config_manager.save()
        self._refresh_ui_language()

    def _refresh_ui_language(self):
        """重新套用所有 UI 文字（不重建視窗）"""
        self.root.title(self.t("app_title"))
        self.save_btn.config(text=self.t("btn_save_settings"))
        self.settings_btn.config(text=self.t("btn_settings"))
        self.overlay_settings_btn.config(text=self.t("btn_overlay_settings"))
        self.sponsor_btn.config(text=self.t("btn_sponsor"))
        self.switch_btn.config(
            text=self.t("btn_switch_off") if self.engine.all_disabled
            else self.t("btn_switch_on")
        )
        self.timer_switch_btn.config(
            text=self.t("btn_overlay_close") if self._overlay_mode
            else self.t("btn_overlay_open")
        )
        self._update_topmost_btn(self.config_manager.get("always_on_top", True))
        self._update_hint()
        # 更新延遲標籤與按鈕文字
        if hasattr(self, "_delay_label"):
            self._delay_label.config(text=self.t("delay_label"))
        if hasattr(self, "_delay_btn"):
            key = "btn_delay_low" if self.engine.update_interval == 0.1 else "btn_delay_high"
            self._delay_btn.config(text=self.t(key))
        # 重建計時列（含翻譯標題）
        self._build_timer_displays()

    def _toggle_all_disabled(self):
        self.engine.toggle_all_disabled()
        disabled = self.engine.all_disabled
        self.switch_btn.config(
            text=self.t("btn_switch_off") if disabled else self.t("btn_switch_on"),
            bg=BG_DANGER if disabled else BG_SUCCESS,
        )
        self._update_hint()
        # 停用後 _tick 不再呼叫 on_update，需在主線程強制刷新一次 UI
        self._do_ui_update()

    def _toggle_overlay(self):
        if self._overlay_mode:
            self.show_main()
        else:
            self.show_overlay()

    def show_overlay(self):
        """切換到懸浮框模式"""
        if self._overlay is None or not self._overlay.is_alive():
            self._overlay = OverlayWindow(self)
        self._overlay_mode = True
        self.root.withdraw()
        self.timer_switch_btn.config(text=self.t("btn_overlay_close"))

    def show_main(self):
        """從懸浮框返回主視窗"""
        self._overlay_mode = False
        if self._overlay:
            self._overlay.destroy()
            self._overlay = None
        self.root.deiconify()
        self.timer_switch_btn.config(text=self.t("btn_overlay_open"))

    # ── 設定視窗（唯一性保護） ────────────────────────────────────────────────

    def _open_profiles(self):
        if self._settings_open:
            return
        self._settings_open = True
        if self._profile_win is None:
            self._profile_win = ProfileWindow(self)
        self._profile_win.open()

    def _open_timer_mgr(self):
        if self._settings_open:
            return
        self._settings_open = True
        self.engine.all_paused = True
        if self._timer_mgr_win is None:
            self._timer_mgr_win = TimerMgrWindow(self)
        self._timer_mgr_win.open()

    def _open_overlay_settings(self):
        if self._settings_open:
            return
        self._settings_open = True
        self.engine.all_paused = True
        if self._overlay_settings_win is None:
            self._overlay_settings_win = OverlaySettingsWindow(self)
        self._overlay_settings_win.open()

    # ── 設定視窗回調 ──────────────────────────────────────────────────────────

    def on_settings_closed(self):
        """任意設定視窗關閉時呼叫"""
        self._settings_open = False
        self.engine.all_paused = False
        self._profile_win = None
        self._timer_mgr_win = None
        self._overlay_settings_win = None

    def on_profile_applied(self):
        """設定檔被套用後更新引擎和 UI"""
        self.engine.reload()
        self._build_timer_displays()
        self._update_hint()
        if self._overlay and self._overlay.is_alive():
            self._overlay.rebuild_timers()

    def on_timers_changed(self):
        """計時組更動後更新引擎和 UI"""
        self.engine.reload()
        self._build_timer_displays()
        if self._overlay and self._overlay.is_alive():
            self._overlay.rebuild_timers()

    def on_overlay_settings_changed(self):
        """懸浮窗設定變更後重建懸浮窗"""
        if self._overlay and self._overlay.is_alive():
            self._overlay.refresh()

    def reload_global_hotkeys(self):
        """重新載入全域熱鍵設定"""
        # 熱鍵在 engine.handle_vk_key 中動態讀取 config，無需重啟監聽器

    # ── VK 全域熱鍵監聽 ───────────────────────────────────────────────────────

    def _setup_global_hotkeys(self):
        if not VK_AVAILABLE:
            return
        if self._vk_listener:
            try:
                self._vk_listener.stop()
            except Exception:
                pass
        self._vk_listener = VKHotkeyListener(callback=self.engine.handle_vk_key)
        self._vk_listener.start()

    # ── UI 更新排程 ───────────────────────────────────────────────────────────

    def _schedule_ui_update(self):
        """從計時引擎線程觸發 UI 更新（線程安全）"""
        if not self._ui_update_pending:
            self._ui_update_pending = True
            try:
                self.root.after(0, self._do_ui_update)
            except Exception:
                self._ui_update_pending = False

    def _do_ui_update(self):
        self._ui_update_pending = False
        try:
            self._update_timer_displays()
            # 同步 switch_btn 狀態（VK 熱鍵從背景線程觸發時也能正確更新）
            disabled = self.engine.all_disabled
            self.switch_btn.config(
                text=self.t("btn_switch_off") if disabled else self.t("btn_switch_on"),
                bg=BG_DANGER if disabled else BG_SUCCESS,
            )
        except Exception:
            pass

    # ── 贊助視窗 ──────────────────────────────────────────────────────────────

    def _open_sponsor(self):
        win = tk.Toplevel(self.root)
        win.title(self.t("sponsor_title"))
        win.configure(bg=BG_MAIN)
        win.attributes("-topmost", True)
        if os.path.exists(self.icon_path):
            try:
                win.iconbitmap(self.icon_path)
            except Exception:
                pass

        frame = tk.Frame(win, bg=BG_MAIN, padx=24, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text=self.t("sponsor_msg"),
                 font=(self.font_family, 11),
                 bg=BG_MAIN, fg=FG_TEXT).pack(pady=(0, 12))

        tk.Button(
            frame, text=self.t("sponsor_youtube"),
            command=lambda: webbrowser.open("https://www.youtube.com/@oo_jump_game"),
            bg="#c0392b", fg="#ffffff",
            relief=tk.FLAT, padx=12, pady=6,
            font=(self.font_family, 10, "bold"),
            cursor="hand2",
        ).pack(pady=4)

        tk.Button(
            frame, text=self.t("btn_close"),
            command=win.destroy,
            bg=BG_BTN, fg=FG_TEXT,
            relief=tk.FLAT, padx=12, pady=4,
            font=(self.font_family, 10),
            cursor="hand2",
        ).pack(pady=(8, 0))

        win.update_idletasks()
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

    # ── 關閉程序 ──────────────────────────────────────────────────────────────

    def _on_closing(self):
        # 儲存設定
        self.config_manager.set("window_opacity", self.opacity_scale.get())
        self.config_manager.save()

        # 停止引擎
        self.engine.stop_engine()

        # 停止 VK 監聽
        if self._vk_listener:
            try:
                self._vk_listener.stop()
            except Exception:
                pass

        # 關閉懸浮窗
        if self._overlay:
            try:
                self._overlay.destroy()
            except Exception:
                pass

        self.root.destroy()


# ─────────────────────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    app = CountdownTimerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
