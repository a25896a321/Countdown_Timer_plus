"""
懸浮窗模組
全域置頂的透明懸浮計時顯示窗
支援拖曳移動、齒輪按鈕返回主視窗
"""

import tkinter as tk
from tkinter import font as tkfont
import os
import threading

try:
    from PIL import Image, ImageTk, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from translations import get_text
from timer_engine import STATE_RUNNING, STATE_FINISHED, STATE_IDLE


class TimerWidget(tk.Frame):
    """
    單個計時器的懸浮顯示小部件
    包含：倒數數字 + 圖示
    """

    def __init__(self, parent, timer_instance, config_manager, icon_size=64,
                 text_color="#ffffff", font_family="Microsoft JhengHei",
                 show_num_bg=False, num_bg_color="#1a1a2e",
                 show_name_bg=True, name_bg_color="#1a1a2e",
                 name_color="#ffffff", name_position="below_img",
                 name_align="center", show_image=True, **kwargs):
        super().__init__(parent, **kwargs)
        self.timer_instance = timer_instance
        self.config_manager = config_manager
        self.icon_size = icon_size
        self.text_color = text_color
        self.font_family = font_family
        self.show_num_bg = show_num_bg
        self.num_bg_color = num_bg_color
        self.show_name_bg = show_name_bg
        self.name_bg_color = name_bg_color
        self.name_color = name_color
        self.name_position = name_position  # above_img/below_img/center_img/top_img/bottom_img
        self.name_align = name_align        # left/center/right
        self.show_image = show_image

        self._image_cache = {}
        self._tk_image_cache = {}

        self._current_img_name = None
        self._current_img_state = None

        self._setup_ui()

    def _setup_ui(self):
        widget_bg = self["bg"] if "bg" in self.keys() else "black"
        self.config(bg=widget_bg)

        font_size = max(10, self.icon_size // 4)
        name_font_size = max(8, self.icon_size // 6)
        pos = self.name_position
        inside = pos in ("center_img", "top_img", "bottom_img")

        # 數字背景色
        num_bg = self.num_bg_color if self.show_num_bg else widget_bg
        # 名稱背景色
        name_bg = self.name_bg_color if self.show_name_bg else widget_bg

        # 對齊方式
        anchor_map = {"left": ("w", "left"), "center": ("center", "center"), "right": ("e", "right")}
        lbl_anchor, lbl_justify = anchor_map.get(self.name_align, ("center", "center"))

        # 數字標籤
        self.time_label = tk.Label(
            self, text="--",
            font=(self.font_family, font_size, "bold"),
            fg=self.text_color, bg=num_bg,
            padx=4 if self.show_num_bg else 0,
            pady=1 if self.show_num_bg else 0,
        )

        timer_name = self.timer_instance.config.get("timer_name", "")

        if inside:
            # ── 圖示容器（固定尺寸，名稱以 place 疊加）────────────────────────
            self._icon_container = tk.Frame(
                self, width=self.icon_size, height=self.icon_size, bg=widget_bg
            )
            self._icon_container.pack_propagate(False)

            self.icon_label = tk.Label(self._icon_container, bg=widget_bg)
            self.icon_label.place(x=0, y=0, width=self.icon_size, height=self.icon_size)

            # 垂直位置
            if pos == "center_img":
                rely, y_part = 0.5, "center"
            elif pos == "top_img":
                rely, y_part = 0.03, "n"
            else:   # bottom_img
                rely, y_part = 0.97, "s"

            # 水平位置 → 組合 place anchor
            if self.name_align == "left":
                relx = 0.03
                place_anchor = {"n": "nw", "center": "w", "s": "sw"}[y_part]
            elif self.name_align == "right":
                relx = 0.97
                place_anchor = {"n": "ne", "center": "e", "s": "se"}[y_part]
            else:
                relx = 0.5
                place_anchor = {"n": "n", "center": "center", "s": "s"}[y_part]

            self.name_label = tk.Label(
                self._icon_container, text=timer_name,
                font=(self.font_family, name_font_size),
                fg=self.name_color, bg=name_bg,
                anchor=lbl_anchor, justify=lbl_justify,
                padx=3 if self.show_name_bg else 0,
                pady=1 if self.show_name_bg else 0,
            )
            self.name_label.place(relx=relx, rely=rely, anchor=place_anchor)

            # 排列：數字 → 圖示容器（不顯示圖片時隱藏容器）
            self.time_label.pack(pady=(2, 0))
            if self.show_image:
                self._icon_container.pack()
        else:
            # ── 圖示標籤（正常 pack 排列）─────────────────────────────────────
            self.icon_label = tk.Label(
                self, width=self.icon_size, height=self.icon_size, bg=widget_bg
            )
            self.name_label = tk.Label(
                self, text=timer_name,
                font=(self.font_family, name_font_size),
                fg=self.name_color, bg=name_bg,
                anchor=lbl_anchor, justify=lbl_justify,
                padx=3 if self.show_name_bg else 0,
                pady=1 if self.show_name_bg else 0,
            )
            if pos == "above_img":
                # 名稱 → 數字 → 圖示（不顯示圖片時跳過 icon_label）
                self.name_label.pack(pady=(2, 0))
                self.time_label.pack()
                if self.show_image:
                    self.icon_label.pack()
            else:
                # below_img（預設）：數字 → 圖示 → 名稱
                self.time_label.pack(pady=(2, 0))
                if self.show_image:
                    self.icon_label.pack()
                self.name_label.pack(pady=(0, 2))

    def update_display(self):
        """更新顯示內容（由主線程呼叫）"""
        timer = self.timer_instance

        # 更新數字
        if timer.state == STATE_IDLE:
            display_text = "--"
        elif timer.state == STATE_FINISHED:
            display_text = "0"
        else:
            display_text = str(timer.get_display_seconds())
        self.time_label.config(text=display_text)

        # 更新圖示（show_image=False 時跳過）
        if self.show_image:
            img_name = timer.get_current_image_name()
            img_state = timer.get_image_state()
            if img_name != self._current_img_name or img_state != self._current_img_state:
                self._current_img_name = img_name
                self._current_img_state = img_state
                self._update_icon(img_name, img_state)

    def _update_icon(self, img_name: str, img_state: str):
        """載入並顯示對應圖示；若找不到圖片則以 Set_None 代替"""
        png_folder = self.config_manager.get_png_folder()

        # 優先嘗試指定圖片；若未指定或找不到，退回 Set_None
        tk_img = None
        if img_name:
            tk_img = self._load_icon(png_folder, img_name, img_state)
        if tk_img is None:
            tk_img = self._load_icon(png_folder, "Set_None", img_state)

        if tk_img:
            self.icon_label.config(image=tk_img, width=self.icon_size, height=self.icon_size)
            self.icon_label.image = tk_img  # 防止 GC
        else:
            self.icon_label.config(image="", width=self.icon_size, height=self.icon_size)

    def _load_icon(self, folder: str, name: str, state: str):
        """載入圖示，依狀態選擇 _on / 灰階版本"""
        if not PIL_AVAILABLE:
            return None

        cache_key = (name, state, self.icon_size)
        if cache_key in self._tk_image_cache:
            return self._tk_image_cache[cache_key]

        # 決定要載入哪個檔案
        if state in ("on", "flash_on"):
            candidates = [f"{name}_on", name]
        elif state == "gray":
            candidates = [name]
        elif state == "flash_off":
            candidates = [name]
        else:
            candidates = [name]

        pil_img = None
        for candidate in candidates:
            for ext in (".png", ".jpg", ".jpeg", ".gif"):
                path = os.path.join(folder, candidate + ext)
                if os.path.exists(path):
                    try:
                        pil_img = Image.open(path).convert("RGBA")
                        break
                    except Exception:
                        pass
            if pil_img:
                break

        if pil_img is None:
            # Set_None 本身也找不到時才真正返回 None
            return None

        # 灰階處理
        if state in ("gray", "flash_off"):
            gray = pil_img.convert("L").convert("RGBA")
            pil_img = gray

        # 調整大小
        pil_img = pil_img.resize((self.icon_size, self.icon_size), Image.LANCZOS)

        tk_img = ImageTk.PhotoImage(pil_img)
        self._tk_image_cache[cache_key] = tk_img
        return tk_img

    def rebuild(self, icon_size, text_color, bg_color, font_family):
        """重建部件（更改尺寸/顏色後）"""
        self.icon_size = icon_size
        self.text_color = text_color
        self.font_family = font_family
        self._tk_image_cache.clear()
        self._image_cache.clear()
        self._current_img_name = None
        self._current_img_state = None

        for widget in self.winfo_children():
            widget.destroy()
        self.config(bg=bg_color)
        self._setup_ui()


class OverlayWindow:
    """
    懸浮窗主類別
    全域置頂、可拖曳、顯示多組計時器
    """

    def __init__(self, parent_app):
        self.app = parent_app
        self.config_manager = parent_app.config_manager
        self.engine = parent_app.engine
        self.lang = parent_app.lang

        self.win = None
        self.timer_widgets: list[TimerWidget] = []
        self._drag_x = 0
        self._drag_y = 0
        self._update_job = None
        self.hide_idle_timers = False   # 由 _build / rebuild_timers 更新
        self.show_image = True

        self._build()

    def t(self, key):
        return get_text(self.lang, key)

    def _build(self):
        overlay_cfg = self.config_manager.get_overlay_settings()
        bg_color = overlay_cfg.get("bg_color", "#1a1a2e")
        show_bg = overlay_cfg.get("show_bg", False)
        opacity = overlay_cfg.get("opacity", 0.9)
        x = overlay_cfg.get("x", 500)
        y = overlay_cfg.get("y", 700)
        icon_size = overlay_cfg.get("icon_size", 64)
        spacing = overlay_cfg.get("spacing", 1)
        text_color = overlay_cfg.get("text_color", "#ffffff")
        show_drag     = overlay_cfg.get("show_drag", True)
        show_gear     = overlay_cfg.get("show_gear", True)
        show_num_bg   = overlay_cfg.get("show_num_bg", False)
        num_bg_color  = overlay_cfg.get("num_bg_color", "#1a1a2e")
        show_name_bg  = overlay_cfg.get("show_name_bg", True)
        name_bg_color = overlay_cfg.get("name_bg_color", "#1a1a2e")
        name_color    = overlay_cfg.get("name_color", "#ffffff")
        name_position = overlay_cfg.get("name_position", "below_img")
        name_align    = overlay_cfg.get("name_align", "center")
        self.hide_idle_timers = overlay_cfg.get("hide_idle_timers", False)
        self.show_image = overlay_cfg.get("show_image", True)

        if self.app.os_type == "Windows":
            font_family = "Microsoft JhengHei"
        else:
            font_family = "PingFang SC"

        win = tk.Toplevel()
        win.title(self.t("overlay_title"))
        win.overrideredirect(True)   # 移除標題列
        win.attributes("-topmost", True)
        win.attributes("-alpha", opacity)

        actual_bg = bg_color if show_bg else "black"
        if not show_bg:
            win.attributes("-transparentcolor", "black")

        win.config(bg=actual_bg)
        win.geometry(f"+{x}+{y}")

        self.win = win

        # 控制列（拖曳＋齒輪），僅在需要時顯示
        drag_lbl = None
        gear_lbl = None
        if show_drag or show_gear:
            ctrl_bar = tk.Frame(win, bg=actual_bg, cursor="fleur")
            ctrl_bar.pack(fill=tk.X, padx=0, pady=0)

            if show_drag:
                drag_lbl = tk.Label(ctrl_bar, bg=actual_bg, cursor="fleur")
                self._load_drag_icon(drag_lbl, actual_bg)
                drag_lbl.pack(side=tk.LEFT, padx=4)

            if show_gear:
                gear_lbl = tk.Label(ctrl_bar, bg=actual_bg, cursor="hand2")
                self._load_gear_icon(gear_lbl, actual_bg)
                gear_lbl.pack(side=tk.LEFT, padx=0)

            # 繫結拖曳事件（整個控制列 + 拖曳手把）
            ctrl_bar.bind("<ButtonPress-1>", self._on_drag_start)
            ctrl_bar.bind("<B1-Motion>", self._on_drag_move)
            if drag_lbl:
                drag_lbl.bind("<ButtonPress-1>", self._on_drag_start)
                drag_lbl.bind("<B1-Motion>", self._on_drag_move)

            if gear_lbl:
                gear_lbl.bind("<Button-1>", lambda e: self.app.show_main())

        # 計時器容器
        timer_container = tk.Frame(win, bg=actual_bg)
        timer_container.pack(padx=0, pady=0)
        self.timer_container = timer_container

        # 建立計時器部件
        self._build_timer_widgets(actual_bg, text_color, icon_size, spacing,
                                   font_family, show_num_bg, num_bg_color,
                                   show_name_bg, name_bg_color, name_color,
                                   name_position, name_align,
                                   show_image=self.show_image)

        # 開始更新
        self._schedule_update()

    def _load_drag_icon(self, label: tk.Label, bg_color: str):
        """載入 Set_Arrow_keys 圖示作為拖曳把手；失敗則顯示文字符號"""
        if PIL_AVAILABLE:
            png_folder = self.config_manager.get_png_folder()
            for ext in (".png", ".jpg", ".jpeg", ".gif"):
                path = os.path.join(png_folder, "Set_Arrow_keys" + ext)
                if os.path.exists(path):
                    try:
                        img = Image.open(path).convert("RGBA")
                        img = img.resize((20, 20), Image.LANCZOS)
                        tk_img = ImageTk.PhotoImage(img)
                        label.config(image=tk_img, width=20, height=20)
                        label.image = tk_img  # 防止 GC
                        return
                    except Exception:
                        pass
        # 退回文字符號
        label.config(text="⊹", font=("", 14), fg="#aaaaaa")

    def _load_gear_icon(self, label: tk.Label, bg_color: str):
        """載入 Set_gear 圖示作為設定按鈕；失敗則顯示文字符號"""
        if PIL_AVAILABLE:
            png_folder = self.config_manager.get_png_folder()
            for ext in (".png", ".jpg", ".jpeg", ".gif"):
                path = os.path.join(png_folder, "Set_gear" + ext)
                if os.path.exists(path):
                    try:
                        img = Image.open(path).convert("RGBA")
                        img = img.resize((20, 20), Image.LANCZOS)
                        tk_img = ImageTk.PhotoImage(img)
                        label.config(image=tk_img, width=20, height=20)
                        label.image = tk_img  # 防止 GC
                        return
                    except Exception:
                        pass
        # 退回文字符號
        label.config(text="⚙", font=("Segoe UI Emoji", 14), fg="#aaaaaa")

    def _build_timer_widgets(self, bg_color, text_color, icon_size, spacing,
                             font_family, show_num_bg=False, num_bg_color="#1a1a2e",
                             show_name_bg=True, name_bg_color="#1a1a2e",
                             name_color="#ffffff", name_position="below_img",
                             name_align="center", show_image=True):
        """建立所有計時器 widget"""
        for w in self.timer_widgets:
            try:
                w.destroy()
            except Exception:
                pass
        self.timer_widgets.clear()

        timers = self.engine.get_timers()
        for i, timer in enumerate(timers):
            widget = TimerWidget(
                self.timer_container,
                timer,
                self.config_manager,
                icon_size=icon_size,
                text_color=text_color,
                font_family=font_family,
                show_num_bg=show_num_bg,
                num_bg_color=num_bg_color,
                show_name_bg=show_name_bg,
                name_bg_color=name_bg_color,
                name_color=name_color,
                name_position=name_position,
                name_align=name_align,
                show_image=show_image,
                bg=bg_color,
            )
            widget.grid(row=0, column=i, padx=spacing, pady=2)
            self.timer_widgets.append(widget)

    def _on_drag_start(self, event):
        self._drag_x = event.x_root - self.win.winfo_x()
        self._drag_y = event.y_root - self.win.winfo_y()

    def _on_drag_move(self, event):
        new_x = event.x_root - self._drag_x
        new_y = event.y_root - self._drag_y
        self.win.geometry(f"+{new_x}+{new_y}")
        # 儲存新位置
        self.config_manager.update_overlay_settings({"x": new_x, "y": new_y})

    def _schedule_update(self):
        """每 100ms 更新顯示"""
        if self.win and self.win.winfo_exists():
            self._update_display()
            self._update_job = self.win.after(100, self._schedule_update)

    def _update_display(self):
        """更新所有計時器顯示，並依據 hide_idle_timers 決定是否顯示"""
        timers = self.engine.get_timers()
        for i, widget in enumerate(self.timer_widgets):
            if i >= len(timers):
                continue
            timer = timers[i]
            if self.hide_idle_timers:
                # 只有 RUNNING 狀態才顯示
                if timer.state == STATE_RUNNING:
                    widget.grid()
                else:
                    widget.grid_remove()
                    continue   # 隱藏中不需要更新內容
            else:
                widget.grid()
            widget.update_display()

    def refresh(self):
        """重新建立整個懸浮窗（設定變更後）"""
        self.destroy()
        self._build()

    def rebuild_timers(self):
        """重新建立計時器部件（切換設定檔後）"""
        overlay_cfg = self.config_manager.get_overlay_settings()
        bg_color = overlay_cfg.get("bg_color", "#1a1a2e")
        show_bg = overlay_cfg.get("show_bg", False)
        actual_bg = bg_color if show_bg else "black"
        text_color = overlay_cfg.get("text_color", "#ffffff")
        icon_size = overlay_cfg.get("icon_size", 64)
        spacing = overlay_cfg.get("spacing", 1)
        show_num_bg   = overlay_cfg.get("show_num_bg", False)
        num_bg_color  = overlay_cfg.get("num_bg_color", "#1a1a2e")
        show_name_bg  = overlay_cfg.get("show_name_bg", True)
        name_bg_color = overlay_cfg.get("name_bg_color", "#1a1a2e")
        name_color    = overlay_cfg.get("name_color", "#ffffff")
        name_position = overlay_cfg.get("name_position", "below_img")
        name_align    = overlay_cfg.get("name_align", "center")
        self.hide_idle_timers = overlay_cfg.get("hide_idle_timers", False)
        self.show_image = overlay_cfg.get("show_image", True)
        if self.app.os_type == "Windows":
            font_family = "Microsoft JhengHei"
        else:
            font_family = "PingFang SC"
        self._build_timer_widgets(actual_bg, text_color, icon_size, spacing,
                                   font_family, show_num_bg, num_bg_color,
                                   show_name_bg, name_bg_color, name_color,
                                   name_position, name_align,
                                   show_image=self.show_image)

    def destroy(self):
        """銷毀懸浮窗"""
        if self._update_job:
            try:
                self.win.after_cancel(self._update_job)
            except Exception:
                pass
            self._update_job = None
        if self.win:
            try:
                self.win.destroy()
            except Exception:
                pass
            self.win = None
        self.timer_widgets.clear()

    def is_alive(self) -> bool:
        return self.win is not None and self.win.winfo_exists()
