"""
設定視窗模組
包含：
  1. ProfileWindow  - 設定檔管理（選擇、應用、匯入、匯出、清空、全域熱鍵）
  2. TimerMgrWindow - 多組時間管理（新增、排序、刪除、設定各計時器參數）
  3. OverlaySettingsWindow - 懸浮窗設定
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
import os
import copy

from translations import get_text
from config_manager import (
    ConfigManager, MAX_PROFILES,
    make_default_timer, make_default_profile, make_default_sound_config
)
from vk_hotkey import VKCaptureSingleKey, get_vk_display_name

# ── 通用顏色主題 ──────────────────────────────────────────────────────────────

THEME = {
    "bg":       "#1e2130",
    "panel":    "#2d3250",
    "btn":      "#3a4170",
    "btn_hl":   "#5a6bcc",
    "accent":   "#7c83e0",
    "danger":   "#e05050",
    "success":  "#50c878",
    "text":     "#e8eaf6",
    "sub_text": "#9199cc",
    "border":   "#3d4571",
    "entry_bg": "#252a45",
}


def make_btn(parent, text, cmd, **kw):
    """建立統一風格的按鈕"""
    btn = tk.Button(
        parent, text=text, command=cmd,
        bg=kw.pop("bg", THEME["btn"]),
        fg=kw.pop("fg", THEME["text"]),
        activebackground=THEME["btn_hl"],
        activeforeground=THEME["text"],
        relief=tk.FLAT,
        bd=0,
        padx=kw.pop("padx", 10),
        pady=kw.pop("pady", 4),
        cursor="hand2",
        **kw
    )
    return btn


def make_label(parent, text, **kw):
    return tk.Label(
        parent, text=text,
        bg=kw.pop("bg", THEME["bg"]),
        fg=kw.pop("fg", THEME["text"]),
        **kw
    )


def make_entry(parent, textvariable=None, width=12, **kw):
    e = tk.Entry(
        parent,
        textvariable=textvariable,
        bg=THEME["entry_bg"],
        fg=THEME["text"],
        insertbackground=THEME["text"],
        relief=tk.FLAT,
        bd=2,
        highlightthickness=1,
        highlightbackground=THEME["border"],
        width=width,
        **kw
    )
    return e


# ─────────────────────────────────────────────────────────────────────────────
# 1. 設定檔管理視窗
# ─────────────────────────────────────────────────────────────────────────────

class ProfileWindow:
    """設定檔管理視窗（💾）"""

    def __init__(self, parent_app):
        self.app = parent_app
        self.config_manager: ConfigManager = parent_app.config_manager
        self.lang = parent_app.lang
        self._win = None
        self._hotkey_captures = {}   # action -> VKCaptureSingleKey
        self._hk_btns = {}           # action -> Button widget
        self._pinned_slot = None     # 當前鎖定的設定檔插槽索引

    def t(self, key):
        return get_text(self.lang, key)

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            return
        self._build()

    def _build(self):
        win = tk.Toplevel()
        win.title(self.t("profile_window_title"))
        win.configure(bg=THEME["bg"])
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.protocol("WM_DELETE_WINDOW", self._on_close)
        self._win = win

        if hasattr(self.app, 'icon_path') and os.path.exists(self.app.icon_path):
            win.iconbitmap(self.app.icon_path)

        font_family = self.app.font_family

        # ── 左側：設定檔列表 ──────────────────────────────────────────────
        left = tk.Frame(win, bg=THEME["bg"], padx=10, pady=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        make_label(left, self.t("profile_list_label"),
                   font=(font_family, 11, "bold")).pack(anchor="w", pady=(0, 6))

        lb_frame = tk.Frame(left, bg=THEME["panel"], bd=1, relief=tk.FLAT)
        lb_frame.pack(fill=tk.BOTH, expand=True)

        self.profile_listbox = tk.Listbox(
            lb_frame,
            bg=THEME["panel"], fg=THEME["text"],
            selectbackground=THEME["accent"],
            selectforeground="#ffffff",
            font=(font_family, 10),
            relief=tk.FLAT, bd=0,
            activestyle="none",
            width=20, height=12,
        )
        self.profile_listbox.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.profile_listbox.bind("<<ListboxSelect>>", self._on_profile_select)

        self._populate_profile_list()

        # ── 操作按鈕 ──────────────────────────────────────────────────────
        btn_frame = tk.Frame(left, bg=THEME["bg"])
        btn_frame.pack(fill=tk.X, pady=(8, 0))

        actions = [
            ("btn_apply_profile", THEME["success"], self._apply),
            ("btn_import_profile", THEME["btn"], self._import),
            ("btn_export_profile", THEME["btn"], self._export),
            ("btn_clear_profile", THEME["danger"], self._clear),
        ]
        for key, color, cmd in actions:
            b = make_btn(btn_frame, self.t(key), cmd, bg=color, font=(font_family, 9))
            b.pack(fill=tk.X, pady=2)

        # ── 右側：設定檔詳情 ──────────────────────────────────────────────
        right = tk.Frame(win, bg=THEME["bg"], padx=10, pady=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)

        make_label(right, self.t("profile_detail_label"),
                   font=(font_family, 11, "bold")).pack(anchor="w", pady=(0, 6))

        # 設定檔名稱編輯
        name_row = tk.Frame(right, bg=THEME["bg"])
        name_row.pack(fill=tk.X, pady=4)
        make_label(name_row, self.t("profile_name_label"),
                   font=(font_family, 9)).pack(side=tk.LEFT)
        self._name_var = tk.StringVar()
        self._name_entry = make_entry(name_row, textvariable=self._name_var, width=22)
        self._name_entry.pack(side=tk.LEFT, padx=4)
        # 取得焦點時重新確認 listbox 選擇，防止雙擊導致誤切換
        self._name_entry.bind("<FocusIn>", self._reassert_selection)
        make_btn(name_row, self.t("btn_edit_profile_name"), self._save_name,
                 font=(font_family, 9)).pack(side=tk.LEFT)

        # 詳情文字
        detail_frame = tk.Frame(right, bg=THEME["panel"], bd=1, relief=tk.FLAT)
        detail_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.detail_text = tk.Text(
            detail_frame,
            bg=THEME["panel"], fg=THEME["text"],
            font=(font_family, 9),
            relief=tk.FLAT, bd=0,
            state=tk.DISABLED,
            wrap=tk.WORD,
            width=34, height=10,
        )
        self.detail_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ── 程序快捷鍵 ────────────────────────────────────────────────────
        sep = tk.Frame(right, bg=THEME["border"], height=1)
        sep.pack(fill=tk.X, pady=8)

        make_label(right, self.t("global_hotkeys_label"),
                   font=(font_family, 10, "bold")).pack(anchor="w")

        hk_frame = tk.Frame(right, bg=THEME["bg"])
        hk_frame.pack(fill=tk.X, pady=4)

        hk_defs = [
            ("reset_all", "hotkey_reset_all"),
            ("toggle_all", "hotkey_toggle_all"),
            ("toggle_overlay", "hotkey_toggle_overlay"),
        ]
        self._hk_btns = {}
        for action, label_key in hk_defs:
            row = tk.Frame(hk_frame, bg=THEME["bg"])
            row.pack(fill=tk.X, pady=2)
            make_label(row, self.t(label_key),
                       font=(font_family, 9), width=16, anchor="w").pack(side=tk.LEFT)
            vk_name = self.config_manager.get_global_hotkeys().get(action)
            btn_text = get_vk_display_name(vk_name) if vk_name else self.t("hotkey_none")
            btn = make_btn(
                row, btn_text,
                lambda a=action: self._start_hotkey_capture(a),
                font=(font_family, 9), width=10
            )
            btn.pack(side=tk.LEFT, padx=4)
            clear_btn = make_btn(
                row, "✕",
                lambda a=action: self._clear_hotkey(a),
                bg=THEME["danger"], font=(font_family, 9), padx=4
            )
            clear_btn.pack(side=tk.LEFT)
            self._hk_btns[action] = btn

        win.update_idletasks()
        # 置中顯示
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

        self._update_detail(None)

    def _populate_profile_list(self):
        self.profile_listbox.delete(0, tk.END)
        default_slot = 0   # 固定第一個插槽為預設
        active_slot = self.config_manager.config.get("active_profile", 0)
        for i in range(MAX_PROFILES):
            p = self.config_manager.get_profile(i)
            if p:
                name = p.get("name", f"設定檔 {i+1}")
                badges = []
                if i == default_slot:
                    badges.append(self.t("default_badge"))
                if i == active_slot:
                    badges.append("▶")
                badge_str = " ".join(badges)
                label = f"[{i+1}] {name} {badge_str}".strip()
            else:
                label = f"[{i+1}] {self.t('profile_empty')}"
            self.profile_listbox.insert(tk.END, label)

    def _on_profile_select(self, event=None):
        sel = self.profile_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self._pinned_slot = idx   # 鎖定當前選中插槽
        p = self.config_manager.get_profile(idx)
        if p:
            self._name_var.set(p.get("name", ""))
        else:
            self._name_var.set("")
        self._update_detail(idx)

    def _update_detail(self, slot):
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        if slot is None or self.config_manager.get_profile(slot) is None:
            self.detail_text.insert(tk.END, self.t("timer_detail_none"))
        else:
            p = self.config_manager.get_profile(slot)
            lines = [f"📋 {p.get('name', '')}"]
            timers = p.get("timers", [])
            lines.append(f"{self.t('timer_count_info')}{len(timers)}")
            for i, t in enumerate(timers):
                lines.append(f"\nNo.{i+1} {t.get('timer_name','')}")
                lines.append(f"  鍵：{t.get('key','無')}")
                mode_map = {"loop": "自動循環", "stop": "倒數停止", "dual": "雙回合"}
                lines.append(f"  模式：{mode_map.get(t.get('mode','loop'),'')}")
                lines.append(f"  時間：{t.get('time1', 0)}s")
                if t.get("mode") == "dual":
                    lines.append(f"  回合二：{t.get('time2', 0)}s")
            self.detail_text.insert(tk.END, "\n".join(lines))
        self.detail_text.config(state=tk.DISABLED)

    def _reassert_selection(self, event=None):
        """名稱輸入框取得焦點時，重新確認 listbox 選擇維持在鎖定插槽"""
        if self._pinned_slot is not None:
            self.profile_listbox.selection_clear(0, tk.END)
            self.profile_listbox.selection_set(self._pinned_slot)
            self.profile_listbox.see(self._pinned_slot)

    def _get_selected_slot(self):
        sel = self.profile_listbox.curselection()
        if not sel:
            # 若 listbox 無選取但有鎖定插槽，回傳鎖定插槽
            if self._pinned_slot is not None:
                return self._pinned_slot
            messagebox.showwarning(self.t("warning_title"), self.t("no_profile_selected"),
                                   parent=self._win)
            return None
        return sel[0]

    def _apply(self):
        slot = self._get_selected_slot()
        if slot is None:
            return
        # 若插槽為空，自動建立空設定檔再套用
        if self.config_manager.get_profile(slot) is None:
            empty = make_default_profile(f"設定檔 {slot + 1}")
            self.config_manager.set_profile(slot, empty)
        if messagebox.askyesno(self.t("confirm_title"), self.t("confirm_apply_profile"),
                                parent=self._win):
            self.config_manager.apply_profile(slot)
            self.config_manager.save()
            self.app.on_profile_applied()
            self._populate_profile_list()

    def _import(self):
        slot = self._get_selected_slot()
        if slot is None:
            return
        if self.config_manager.get_profile(slot) is not None:
            if not messagebox.askyesno(self.t("confirm_title"), self.t("confirm_import"),
                                        parent=self._win):
                return
        filepath = filedialog.askopenfilename(
            parent=self._win,
            title=self.t("btn_import_profile"),
            filetypes=[("JSON 設定檔", "*.json"), ("所有檔案", "*.*")]
        )
        if not filepath:
            return
        ok, err = self.config_manager.import_profile(slot, filepath)
        if ok:
            self.config_manager.save()
            messagebox.showinfo(self.t("info_title"), self.t("import_success"), parent=self._win)
            self._populate_profile_list()
            self._update_detail(slot)
        else:
            messagebox.showerror(self.t("error_title"),
                                 self.t("import_error") + err, parent=self._win)

    def _export(self):
        slot = self._get_selected_slot()
        if slot is None:
            return
        if self.config_manager.get_profile(slot) is None:
            messagebox.showwarning(self.t("warning_title"), self.t("no_profile_selected"),
                                   parent=self._win)
            return
        name = self.config_manager.get_profile_name(slot)
        filepath = filedialog.asksaveasfilename(
            parent=self._win,
            title=self.t("btn_export_profile"),
            defaultextension=".json",
            initialfile=f"{name}.json",
            filetypes=[("JSON 設定檔", "*.json")]
        )
        if not filepath:
            return
        ok = self.config_manager.export_profile(slot, filepath)
        if ok:
            messagebox.showinfo(self.t("info_title"),
                                self.t("export_success") + filepath, parent=self._win)
        else:
            messagebox.showerror(self.t("error_title"), self.t("export_error"), parent=self._win)

    def _clear(self):
        slot = self._get_selected_slot()
        if slot is None:
            return
        if not messagebox.askyesno(self.t("confirm_title"), self.t("confirm_clear_profile"),
                                    parent=self._win):
            return
        self.config_manager.clear_profile(slot)
        self.config_manager.save()
        self._populate_profile_list()
        self._update_detail(slot)

    def _set_default(self):
        slot = self._get_selected_slot()
        if slot is None:
            return
        if self.config_manager.get_profile(slot) is None:
            messagebox.showwarning(self.t("warning_title"), self.t("no_profile_selected"),
                                   parent=self._win)
            return
        self.config_manager.config["default_profile"] = slot
        self.config_manager.save()
        self._populate_profile_list()

    def _save_name(self):
        slot = self._get_selected_slot()
        if slot is None:
            return
        p = self.config_manager.get_profile(slot)
        if p is None:
            # 插槽為空時，自動建立空設定檔
            p = make_default_profile(f"設定檔 {slot + 1}")
        new_name = self._name_var.get().strip()
        if not new_name:
            messagebox.showwarning(self.t("warning_title"), self.t("profile_name_empty"),
                                   parent=self._win)
            return
        p["name"] = new_name
        self.config_manager.set_profile(slot, p)
        self.config_manager.save()
        self._populate_profile_list()
        self._update_detail(slot)

    # ── 全域熱鍵捕獲 ──────────────────────────────────────────────────────

    def _start_hotkey_capture(self, action: str):
        btn = self._hk_btns.get(action)
        if btn:
            btn.config(text=self.t("hotkey_press_key"), bg=THEME["accent"])

        cap = VKCaptureSingleKey(lambda code, name: self._on_hotkey_captured(action, name))
        self._hotkey_captures[action] = cap
        cap.start_capture()

    def _on_hotkey_captured(self, action: str, vk_name: str):
        self.config_manager.set_global_hotkey(action, vk_name)
        self.config_manager.save()
        self.app.reload_global_hotkeys()
        btn = self._hk_btns.get(action)
        if btn:
            try:
                btn.config(text=get_vk_display_name(vk_name), bg=THEME["btn"])
            except Exception:
                pass

    def _clear_hotkey(self, action: str):
        self.config_manager.set_global_hotkey(action, None)
        self.config_manager.save()
        self.app.reload_global_hotkeys()
        btn = self._hk_btns.get(action)
        if btn:
            btn.config(text=self.t("hotkey_none"))

    def _on_close(self):
        for cap in self._hotkey_captures.values():
            try:
                cap.stop()
            except Exception:
                pass
        self._hotkey_captures.clear()
        if self._win:
            self._win.destroy()
            self._win = None
        self.app.on_settings_closed()


# ─────────────────────────────────────────────────────────────────────────────
# 2. 多組時間管理視窗
# ─────────────────────────────────────────────────────────────────────────────

class TimerMgrWindow:
    """多組時間管理視窗（⚙️）"""

    # 快捷鍵輸入框顏色常數
    _KEY_ENTRY_BG         = "#dde0f5"   # 靜止狀態：淺薰衣草底
    _KEY_ENTRY_CAPTURE_BG = "#f5e4a0"   # 捕獲中：淺黃底
    _KEY_ENTRY_FG         = "#000000"   # 黑色字體

    def __init__(self, parent_app):
        self.app = parent_app
        self.config_manager: ConfigManager = parent_app.config_manager
        self.lang = parent_app.lang
        self._win = None
        self._selected_idx = None
        self._editing_timer = None
        self._hk_capture = None
        self._preview_win = None   # 圖片預覽浮窗（同時只存一個）

    def t(self, key):
        return get_text(self.lang, key)

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            return
        self._build()

    def _get_current_timers(self) -> list:
        profile = self.config_manager.get_active_profile()
        if profile is None:
            return []
        return profile.get("timers", [])

    def _save_timers(self, timers: list):
        slot = self.config_manager.config.get("active_profile", 0)
        p = self.config_manager.get_profile(slot)
        if p is None:
            p = make_default_profile()
        p["timers"] = timers
        self.config_manager.set_profile(slot, p)
        self.config_manager.save()

    def _build(self):
        win = tk.Toplevel()
        win.title(self.t("timer_mgr_title"))
        win.configure(bg=THEME["bg"])
        win.resizable(True, True)
        win.attributes("-topmost", True)
        win.protocol("WM_DELETE_WINDOW", self._on_close)
        self._win = win

        if hasattr(self.app, 'icon_path') and os.path.exists(self.app.icon_path):
            win.iconbitmap(self.app.icon_path)

        font_family = self.app.font_family

        # 頂部：設定檔名稱
        profile = self.config_manager.get_active_profile()
        profile_name = profile.get("name", "（無）") if profile else "（無）"
        make_label(win, f"📋 {self.t('hint_profile')}{profile_name}",
                   font=(font_family, 11, "bold"),
                   bg=THEME["bg"]).pack(anchor="w", padx=16, pady=(10, 0))

        main_frame = tk.Frame(win, bg=THEME["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ── 左側：計時組列表 ──────────────────────────────────────────────
        left = tk.Frame(main_frame, bg=THEME["bg"])
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        make_label(left, self.t("timer_list_label"),
                   font=(font_family, 10, "bold")).pack(anchor="w", pady=(0, 4))

        lb_frame = tk.Frame(left, bg=THEME["panel"])
        lb_frame.pack(fill=tk.BOTH, expand=True)
        self.timer_lb = tk.Listbox(
            lb_frame,
            bg=THEME["panel"], fg=THEME["text"],
            selectbackground=THEME["accent"],
            font=(font_family, 10),
            relief=tk.FLAT, bd=0,
            activestyle="none",
            width=26, height=14,
        )
        self.timer_lb.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.timer_lb.bind("<<ListboxSelect>>", self._on_timer_select)

        # 操作按鈕
        op_frame = tk.Frame(left, bg=THEME["bg"])
        op_frame.pack(fill=tk.X, pady=(6, 0))
        btn_defs = [
            ("btn_add_timer", THEME["success"], self._add_timer),
            ("btn_move_up", THEME["btn"], self._move_up),
            ("btn_move_down", THEME["btn"], self._move_down),
            ("btn_delete_timer", THEME["danger"], self._delete_timer),
        ]
        for key, color, cmd in btn_defs:
            make_btn(op_frame, self.t(key), cmd, bg=color,
                     font=(font_family, 9)).pack(fill=tk.X, pady=2)

        # ── 右側：設定面板 ────────────────────────────────────────────────
        right_outer = tk.Frame(main_frame, bg=THEME["bg"])
        right_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        make_label(right_outer, self.t("timer_config_label"),
                   font=(font_family, 10, "bold")).pack(anchor="w", pady=(0, 4))

        canvas = tk.Canvas(right_outer, bg=THEME["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(right_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.cfg_frame = tk.Frame(canvas, bg=THEME["bg"])
        canvas_win = canvas.create_window((0, 0), window=self.cfg_frame, anchor="nw")

        def on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(e):
            canvas.itemconfig(canvas_win, width=e.width)

        self.cfg_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        self._canvas = canvas
        self._font_family = font_family
        self._populate_timer_list()
        self._build_config_panel(None)

        win.update_idletasks()
        w = max(800, win.winfo_reqwidth())
        h = max(620, win.winfo_reqheight())
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _populate_timer_list(self):
        self.timer_lb.delete(0, tk.END)
        timers = self._get_current_timers()
        for i, t in enumerate(timers):
            name = t.get("timer_name", f"計時 {i+1}")
            key = t.get("key", "無")
            self.timer_lb.insert(tk.END, f"[{i+1}] {name} ({key})")

    def _on_timer_select(self, event=None):
        sel = self.timer_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        timers = self._get_current_timers()
        if idx < len(timers):
            self._selected_idx = idx
            self._editing_timer = copy.deepcopy(timers[idx])
            self._build_config_panel(self._editing_timer)

    def _build_config_panel(self, timer_cfg):
        for w in self.cfg_frame.winfo_children():
            w.destroy()

        # 統一設定深色下拉清單樣式（#252a45 底色）
        _style = ttk.Style()
        _style.configure(
            "Dark.TCombobox",
            fieldbackground=THEME["entry_bg"],   # #252a45
            background=THEME["btn"],
            foreground=THEME["text"],
            selectbackground=THEME["accent"],
            selectforeground=THEME["text"],
        )
        _style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", THEME["entry_bg"])],
            foreground=[("readonly", THEME["text"])],
        )

        if timer_cfg is None:
            make_label(self.cfg_frame, "← 請從左側選擇或新增計時組",
                       fg=THEME["sub_text"],
                       font=(self._font_family, 10)).pack(pady=20)
            return

        ff = self._font_family

        def row_frame():
            f = tk.Frame(self.cfg_frame, bg=THEME["bg"])
            f.pack(fill=tk.X, pady=3, padx=6)
            return f

        def lbl(parent, key):
            return make_label(parent, self.t(key), font=(ff, 9), width=18, anchor="w")

        # 計時名稱
        r = row_frame()
        lbl(r, "timer_name_label").pack(side=tk.LEFT)
        self._v_name = tk.StringVar(value=timer_cfg.get("timer_name", ""))
        make_entry(r, textvariable=self._v_name, width=20).pack(side=tk.LEFT, padx=4)

        # 快捷鍵
        r = row_frame()
        lbl(r, "timer_key_label").pack(side=tk.LEFT)
        vk_name = timer_cfg.get("key") or ""
        self._v_key = tk.StringVar(value=get_vk_display_name(vk_name) if vk_name else "")
        self._key_entry = tk.Entry(
            r,
            textvariable=self._v_key,
            state="readonly",
            width=12,
            bg=self._KEY_ENTRY_BG,
            fg=self._KEY_ENTRY_FG,
            readonlybackground=self._KEY_ENTRY_BG,
            disabledforeground=self._KEY_ENTRY_FG,
            insertbackground=self._KEY_ENTRY_FG,
            relief=tk.FLAT,
            bd=2,
            highlightthickness=1,
            highlightbackground=THEME["border"],
            font=(ff, 10, "bold"),
        )
        self._key_entry.pack(side=tk.LEFT, padx=4)
        make_btn(r, self.t("hotkey_click_to_set"),
                 self._start_key_capture, font=(ff, 9)).pack(side=tk.LEFT, padx=2)
        make_btn(r, "✕", self._clear_key,
                 bg=THEME["danger"], font=(ff, 9), padx=4).pack(side=tk.LEFT)

        # 倒數模式
        r = row_frame()
        lbl(r, "timer_mode_label").pack(side=tk.LEFT)
        self._v_mode = tk.StringVar(value=timer_cfg.get("mode", "loop"))
        mode_opts = [("loop", "mode_loop"), ("stop", "mode_stop"), ("dual", "mode_dual")]
        for val, key in mode_opts:
            rb = tk.Radiobutton(
                r, text=self.t(key), value=val,
                variable=self._v_mode,
                bg=THEME["bg"], fg=THEME["text"],
                activebackground=THEME["bg"],
                selectcolor=THEME["entry_bg"],
                font=(ff, 9), command=self._on_mode_change,
            )
            rb.pack(side=tk.LEFT, padx=4)

        # 倒數時間1
        r = row_frame()
        lbl(r, "time1_label").pack(side=tk.LEFT)
        self._v_time1 = tk.StringVar(value=str(timer_cfg.get("time1", 60)))
        make_entry(r, textvariable=self._v_time1, width=8).pack(side=tk.LEFT, padx=4)

        # 倒數時間2（雙回合模式）
        self._r_time2 = row_frame()
        lbl(self._r_time2, "time2_label").pack(side=tk.LEFT)
        self._v_time2 = tk.StringVar(value=str(timer_cfg.get("time2", 30)))
        make_entry(self._r_time2, textvariable=self._v_time2, width=8).pack(side=tk.LEFT, padx=4)

        # 快捷鍵功能
        r = row_frame()
        lbl(r, "hotkey_action_label").pack(side=tk.LEFT)
        self._v_action = tk.StringVar(value=timer_cfg.get("hotkey_action", "reset_start"))
        for val, key in [("reset_start", "action_reset_start"), ("toggle", "action_reset_stop")]:
            rb = tk.Radiobutton(
                r, text=self.t(key), value=val,
                variable=self._v_action,
                bg=THEME["bg"], fg=THEME["text"],
                activebackground=THEME["bg"],
                selectcolor=THEME["entry_bg"],
                font=(ff, 9),
            )
            rb.pack(side=tk.LEFT, padx=4)

        # 圖示效果模式
        r = row_frame()
        lbl(r, "image_mode_label").pack(side=tk.LEFT)
        self._v_image_mode = tk.StringVar(value=timer_cfg.get("image_mode", "default"))
        for val, key in [("default", "image_mode_default"),
                         ("cooldown", "image_mode_cooldown"),
                         ("original_only", "image_mode_original_only")]:
            tk.Radiobutton(
                r, text=self.t(key), value=val,
                variable=self._v_image_mode,
                bg=THEME["bg"], fg=THEME["text"],
                activebackground=THEME["bg"],
                selectcolor=THEME["entry_bg"],
                font=(ff, 9),
            ).pack(side=tk.LEFT, padx=4)

        # 分隔線
        tk.Frame(self.cfg_frame, bg=THEME["border"], height=1).pack(
            fill=tk.X, padx=6, pady=6)

        # 圖片設定（回合一）
        self._build_image_row(timer_cfg, round_num=1)

        # 圖片設定（回合二，僅 dual 模式顯示）
        self._img2_container = tk.Frame(self.cfg_frame, bg=THEME["bg"])
        self._img2_container.pack(fill=tk.X)
        self._build_image_row(timer_cfg, round_num=2, parent=self._img2_container)

        # 分隔線
        tk.Frame(self.cfg_frame, bg=THEME["border"], height=1).pack(
            fill=tk.X, padx=6, pady=6)

        # 音效設定（回合一）
        self._build_sound_row(timer_cfg, round_num=1)

        # 音效設定（回合二，僅 dual 模式顯示）
        self._snd2_container = tk.Frame(self.cfg_frame, bg=THEME["bg"])
        self._snd2_container.pack(fill=tk.X)
        self._build_sound_row(timer_cfg, round_num=2, parent=self._snd2_container)

        # 儲存/取消
        tk.Frame(self.cfg_frame, bg=THEME["border"], height=1).pack(
            fill=tk.X, padx=6, pady=6)
        btn_row = row_frame()
        make_btn(btn_row, self.t("btn_save_timer"), self._save_timer,
                 bg=THEME["success"], font=(ff, 10)).pack(side=tk.LEFT, padx=4)
        make_btn(btn_row, self.t("btn_cancel_timer"), self._cancel_edit,
                 font=(ff, 10)).pack(side=tk.LEFT, padx=4)

        self._on_mode_change()

    def _build_image_row(self, timer_cfg, round_num: int, parent=None):
        p = parent or self.cfg_frame
        ff = self._font_family
        r = tk.Frame(p, bg=THEME["bg"])
        r.pack(fill=tk.X, pady=3, padx=6)
        key = "image1_label" if round_num == 1 else "image2_label"
        make_label(r, self.t(key), font=(ff, 9), width=18, anchor="w").pack(side=tk.LEFT)

        img_files = ["（無）"] + self.config_manager.get_png_files()
        img_field = f"image{round_num}"
        current = timer_cfg.get(img_field) or "（無）"
        var = tk.StringVar(value=current if current in img_files else "（無）")
        if round_num == 1:
            self._v_img1 = var
        else:
            self._v_img2 = var

        cb = ttk.Combobox(r, textvariable=var, values=img_files,
                          state="readonly", width=30,
                          font=(ff, 9), style="Dark.TCombobox")
        cb.bind("<FocusIn>", lambda e, c=cb: c.config(
            values=["（無）"] + self.config_manager.get_png_files()))
        cb.pack(side=tk.LEFT, padx=4)

        # 🔎 瀏覽按鈕：點擊後顯示所選圖片的懸浮預覽
        preview_btn = make_btn(
            r, "🔎 瀏覽",
            lambda v=var, b=None: None,
            bg=THEME["btn"], font=(ff, 9), padx=6,
        )
        preview_btn.pack(side=tk.LEFT, padx=2)
        preview_btn.config(
            command=lambda v=var, btn=preview_btn: self._toggle_image_preview(btn, v)
        )

        # 📂 開啟資料夾按鈕
        make_btn(
            r, self.t("btn_open_folder"),
            lambda: self._open_png_folder(),
            bg=THEME["btn"], font=(ff, 9), padx=6,
        ).pack(side=tk.LEFT, padx=2)

    def _toggle_image_preview(self, btn_widget: tk.Widget, img_var: tk.StringVar):
        """點擊「🔎 瀏覽」按鈕時，切換顯示/關閉圖片預覽浮窗"""
        # 若已有浮窗，先關閉（切換行為）
        if self._preview_win is not None:
            try:
                self._preview_win.destroy()
            except Exception:
                pass
            self._preview_win = None
            btn_widget.config(bg=THEME["btn"])
            return

        img_name = img_var.get()
        if not img_name or img_name == "（無）":
            return

        png_folder = self.config_manager.get_png_folder()

        # 尋找圖片檔案（優先帶 _on 後綴）
        pil_img = None
        try:
            from PIL import Image, ImageTk
            for candidate in (f"{img_name}_on", img_name):
                for ext in (".png", ".jpg", ".jpeg", ".gif"):
                    path = os.path.join(png_folder, candidate + ext)
                    if os.path.exists(path):
                        pil_img = Image.open(path).convert("RGBA")
                        break
                if pil_img:
                    break
        except Exception:
            pil_img = None

        # 計算浮窗位置（按鈕右側）
        btn_widget.update_idletasks()
        bx = btn_widget.winfo_rootx() + btn_widget.winfo_width() + 6
        by = btn_widget.winfo_rooty()

        win = tk.Toplevel(self._win)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=THEME["panel"])
        self._preview_win = win

        if pil_img is not None:
            # 等比縮放，最大 220×220
            max_size = 220
            w, h = pil_img.size
            scale = min(max_size / w, max_size / h, 1.0)
            pw, ph = max(1, int(w * scale)), max(1, int(h * scale))
            pil_img = pil_img.resize((pw, ph), Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(pil_img)
            lbl = tk.Label(win, image=tk_img, bg=THEME["panel"],
                           bd=2, relief=tk.SOLID)
            lbl.image = tk_img  # 防 GC
            lbl.pack(padx=4, pady=4)
            # 圖片名稱標籤
            tk.Label(win, text=img_name, bg=THEME["panel"],
                     fg=THEME["sub_text"],
                     font=(self._font_family, 8)).pack(padx=4, pady=(0, 4))
        else:
            tk.Label(win, text=f"找不到圖片：\n{img_name}",
                     bg=THEME["panel"], fg=THEME["text"],
                     font=(self._font_family, 9),
                     padx=12, pady=12).pack()

        win.geometry(f"+{bx}+{by}")

        # 按鈕高亮提示已開啟
        btn_widget.config(bg=THEME["accent"])

        # 點擊浮窗外部或按 Escape 時關閉
        def _close_on_outside(event):
            try:
                wx, wy = win.winfo_rootx(), win.winfo_rooty()
                ww, wh = win.winfo_width(), win.winfo_height()
                mx, my = event.x_root, event.y_root
                if not (wx <= mx <= wx + ww and wy <= my <= wy + wh):
                    self._toggle_image_preview(btn_widget, img_var)
            except Exception:
                pass

        win.bind("<Escape>", lambda e: self._toggle_image_preview(btn_widget, img_var))
        if self._win:
            self._win.bind("<Button-1>", _close_on_outside, add="+")

        def _on_win_destroy():
            try:
                if self._win:
                    self._win.unbind("<Button-1>")
            except Exception:
                pass
            self._preview_win = None
            try:
                btn_widget.config(bg=THEME["btn"])
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", _on_win_destroy)
        win.bind("<Destroy>", lambda e: _on_win_destroy())

    def _build_sound_row(self, timer_cfg, round_num: int, parent=None):
        p = parent or self.cfg_frame
        ff = self._font_family

        sound_field = f"sound{round_num}"
        sc = timer_cfg.get(sound_field) or make_default_sound_config()

        header = tk.Frame(p, bg=THEME["bg"])
        header.pack(fill=tk.X, pady=2, padx=6)
        key = "sound1_label" if round_num == 1 else "sound2_label"
        make_label(header, self.t(key), font=(ff, 9, "bold"),
                   width=18, anchor="w").pack(side=tk.LEFT)

        # 音效選擇
        r = tk.Frame(p, bg=THEME["bg"])
        r.pack(fill=tk.X, pady=2, padx=22)
        make_label(r, self.t("sound_label"), font=(ff, 9),
                   width=10, anchor="w").pack(side=tk.LEFT)
        snd_files = ["（無）"] + self.config_manager.get_sound_files()
        cur_snd = sc.get("file") or "（無）"
        var_snd = tk.StringVar(value=cur_snd if cur_snd in snd_files else "（無）")
        if round_num == 1:
            self._v_snd1 = var_snd
        else:
            self._v_snd2 = var_snd
        cb_snd = ttk.Combobox(r, textvariable=var_snd, values=snd_files,
                              state="readonly", width=28, font=(ff, 9),
                              style="Dark.TCombobox")
        cb_snd.bind("<FocusIn>", lambda e, c=cb_snd: c.config(
            values=["（無）"] + self.config_manager.get_sound_files()))
        cb_snd.pack(side=tk.LEFT, padx=4)
        make_btn(r, self.t("btn_test_sound"),
                 lambda s=var_snd: self._test_sound(s.get()),
                 font=(ff, 9), padx=6).pack(side=tk.LEFT, padx=2)
        make_btn(r, self.t("btn_open_folder"),
                 lambda: self._open_sound_folder(),
                 bg=THEME["btn"], font=(ff, 9), padx=6).pack(side=tk.LEFT, padx=2)

        # 播放方式
        r2 = tk.Frame(p, bg=THEME["bg"])
        r2.pack(fill=tk.X, pady=2, padx=22)
        make_label(r2, self.t("sound_mode_label"), font=(ff, 9),
                   width=10, anchor="w").pack(side=tk.LEFT)
        var_mode = tk.StringVar(value=sc.get("mode", "once"))
        if round_num == 1:
            self._v_sndmode1 = var_mode
        else:
            self._v_sndmode2 = var_mode
        for val, key in [("once", "sound_mode_once"), ("segmented", "sound_mode_segmented")]:
            tk.Radiobutton(
                r2, text=self.t(key), value=val,
                variable=var_mode,
                bg=THEME["bg"], fg=THEME["text"],
                activebackground=THEME["bg"],
                selectcolor=THEME["entry_bg"],
                font=(ff, 9),
            ).pack(side=tk.LEFT, padx=4)

        # 提前秒數
        r3 = tk.Frame(p, bg=THEME["bg"])
        r3.pack(fill=tk.X, pady=2, padx=22)
        make_label(r3, self.t("sound_advance_label"), font=(ff, 9),
                   width=10, anchor="w").pack(side=tk.LEFT)
        var_adv = tk.StringVar(value=str(sc.get("advance", 2)))
        if round_num == 1:
            self._v_sndadv1 = var_adv
        else:
            self._v_sndadv2 = var_adv
        make_entry(r3, textvariable=var_adv, width=6).pack(side=tk.LEFT, padx=4)

        # 分段次數
        r4 = tk.Frame(p, bg=THEME["bg"])
        r4.pack(fill=tk.X, pady=2, padx=22)
        make_label(r4, self.t("sound_frequency_label"), font=(ff, 9),
                   width=10, anchor="w").pack(side=tk.LEFT)
        var_freq = tk.StringVar(value=str(sc.get("frequency", 1)))
        if round_num == 1:
            self._v_sndfreq1 = var_freq
        else:
            self._v_sndfreq2 = var_freq
        make_entry(r4, textvariable=var_freq, width=6).pack(side=tk.LEFT, padx=4)

    def _on_mode_change(self):
        mode = self._v_mode.get() if hasattr(self, "_v_mode") else "loop"
        is_dual = (mode == "dual")
        # 顯示/隱藏回合二時間
        if hasattr(self, "_r_time2"):
            if is_dual:
                self._r_time2.pack(fill=tk.X, pady=3, padx=6)
            else:
                self._r_time2.pack_forget()
        # 顯示/隱藏回合二圖片和音效
        for attr in ("_img2_container", "_snd2_container"):
            container = getattr(self, attr, None)
            if container:
                if is_dual:
                    container.pack(fill=tk.X)
                else:
                    container.pack_forget()

    def _start_key_capture(self):
        if hasattr(self, "_key_entry"):
            self._key_entry.config(state="normal")
            self._v_key.set(self.t("hotkey_press_key"))
            self._key_entry.config(
                state="readonly",
                bg=self._KEY_ENTRY_CAPTURE_BG,
                readonlybackground=self._KEY_ENTRY_CAPTURE_BG,
                fg=self._KEY_ENTRY_FG,
            )

        cap = VKCaptureSingleKey(self._on_key_captured)
        self._hk_capture = cap
        cap.start_capture()

    def _on_key_captured(self, vk_code, vk_name):
        if self._editing_timer is not None:
            self._editing_timer["key"] = vk_name
        if hasattr(self, "_v_key"):
            try:
                self._v_key.set(get_vk_display_name(vk_name))
                if hasattr(self, "_key_entry"):
                    self._key_entry.config(
                        bg=self._KEY_ENTRY_BG,
                        readonlybackground=self._KEY_ENTRY_BG,
                        fg=self._KEY_ENTRY_FG,
                    )
            except Exception:
                pass

    def _clear_key(self):
        if self._editing_timer is not None:
            self._editing_timer["key"] = None
        if hasattr(self, "_v_key"):
            self._v_key.set("")

    def _save_timer(self):
        if self._editing_timer is None or self._selected_idx is None:
            return

        name = self._v_name.get().strip()
        if not name:
            messagebox.showwarning(self.t("warning_title"), self.t("timer_no_name"),
                                   parent=self._win)
            return

        try:
            t1 = int(self._v_time1.get())
            assert t1 > 0
        except Exception:
            messagebox.showwarning(self.t("warning_title"), self.t("timer_invalid_time"),
                                   parent=self._win)
            return

        mode = self._v_mode.get()
        t2 = 30
        if mode == "dual":
            try:
                t2 = int(self._v_time2.get())
                assert t2 > 0
            except Exception:
                messagebox.showwarning(self.t("warning_title"), self.t("timer_invalid_time"),
                                       parent=self._win)
                return

        def collect_sound(snd_var, mode_var, adv_var, freq_var):
            f = snd_var.get().strip()
            if not f or f == "（無）":
                return make_default_sound_config()
            return {
                "file": f,
                "mode": mode_var.get(),
                "advance": max(0, int(adv_var.get())) if adv_var.get().isdigit() else 2,
                "frequency": max(1, int(freq_var.get())) if freq_var.get().isdigit() else 1,
            }

        img1 = self._v_img1.get() if hasattr(self, "_v_img1") else ""
        img2 = self._v_img2.get() if hasattr(self, "_v_img2") else ""
        img1 = None if img1 in ("（無）", "") else img1
        img2 = None if img2 in ("（無）", "") else img2

        sound1 = collect_sound(self._v_snd1, self._v_sndmode1, self._v_sndadv1, self._v_sndfreq1)
        sound2 = collect_sound(self._v_snd2, self._v_sndmode2, self._v_sndadv2, self._v_sndfreq2) \
            if mode == "dual" else make_default_sound_config()

        timer_data = {
            "timer_name": name,
            "key": self._editing_timer.get("key"),
            "mode": mode,
            "time1": t1,
            "time2": t2,
            "hotkey_action": self._v_action.get(),
            "image_mode": self._v_image_mode.get() if hasattr(self, "_v_image_mode") else "default",
            "image1": img1,
            "image2": img2,
            "sound1": sound1,
            "sound2": sound2,
        }

        timers = self._get_current_timers()
        if self._selected_idx < len(timers):
            timers[self._selected_idx] = timer_data
        else:
            timers.append(timer_data)
        self._save_timers(timers)
        self.app.on_timers_changed()
        self._populate_timer_list()
        messagebox.showinfo(self.t("info_title"), self.t("timer_save_success"), parent=self._win)

    def _cancel_edit(self):
        self._selected_idx = None
        self._editing_timer = None
        self._build_config_panel(None)
        self.timer_lb.selection_clear(0, tk.END)

    def _add_timer(self):
        timers = self._get_current_timers()
        new_timer = make_default_timer()
        new_timer["timer_name"] = f"計時 {len(timers)+1}"
        timers.append(new_timer)
        self._save_timers(timers)
        self._populate_timer_list()
        self.timer_lb.selection_clear(0, tk.END)
        idx = len(timers) - 1
        self.timer_lb.selection_set(idx)
        self.timer_lb.see(idx)
        self._selected_idx = idx
        self._editing_timer = copy.deepcopy(new_timer)
        self._build_config_panel(self._editing_timer)

    def _move_up(self):
        sel = self.timer_lb.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        timers = self._get_current_timers()
        timers[idx-1], timers[idx] = timers[idx], timers[idx-1]
        self._save_timers(timers)
        self._populate_timer_list()
        self.timer_lb.selection_set(idx-1)
        self._selected_idx = idx - 1

    def _move_down(self):
        sel = self.timer_lb.curselection()
        timers = self._get_current_timers()
        if not sel or sel[0] >= len(timers) - 1:
            return
        idx = sel[0]
        timers[idx], timers[idx+1] = timers[idx+1], timers[idx]
        self._save_timers(timers)
        self._populate_timer_list()
        self.timer_lb.selection_set(idx+1)
        self._selected_idx = idx + 1

    def _delete_timer(self):
        sel = self.timer_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if not messagebox.askyesno(self.t("confirm_title"), self.t("timer_delete_confirm"),
                                    parent=self._win):
            return
        timers = self._get_current_timers()
        del timers[idx]
        self._save_timers(timers)
        self.app.on_timers_changed()
        self._selected_idx = None
        self._editing_timer = None
        self._populate_timer_list()
        self._build_config_panel(None)

    def _test_sound(self, sound_name: str):
        if sound_name and sound_name != "（無）":
            self.app.engine.play_sound_test(sound_name)

    def _open_png_folder(self):
        """在檔案總管中開啟 png_type 資料夾"""
        folder = self.config_manager.get_png_folder()
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        os.startfile(folder)

    def _open_sound_folder(self):
        """在檔案總管中開啟 sound_type 資料夾"""
        folder = self.config_manager.get_sound_folder()
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        os.startfile(folder)

    def _on_close(self):
        if self._hk_capture:
            try:
                self._hk_capture.stop()
            except Exception:
                pass
        # 關閉圖片預覽浮窗
        if self._preview_win is not None:
            try:
                self._preview_win.destroy()
            except Exception:
                pass
            self._preview_win = None
        if self._win:
            self._win.destroy()
            self._win = None
        self.app.on_settings_closed()


# ─────────────────────────────────────────────────────────────────────────────
# 3. 懸浮窗設定視窗
# ─────────────────────────────────────────────────────────────────────────────

class OverlaySettingsWindow:
    """懸浮窗設定視窗（🖥）"""

    def __init__(self, parent_app):
        self.app = parent_app
        self.config_manager: ConfigManager = parent_app.config_manager
        self.lang = parent_app.lang
        self._win = None

    def t(self, key):
        return get_text(self.lang, key)

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            return
        self._build()

    def _build(self):
        win = tk.Toplevel()
        win.title(self.t("overlay_settings_title"))
        win.configure(bg=THEME["bg"])
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.protocol("WM_DELETE_WINDOW", self._on_close)
        self._win = win

        if hasattr(self.app, 'icon_path') and os.path.exists(self.app.icon_path):
            win.iconbitmap(self.app.icon_path)

        ff = self.app.font_family
        cfg = self.config_manager.get_overlay_settings()

        # 捲動容器
        outer = tk.Frame(win, bg=THEME["bg"])
        outer.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(outer, bg=THEME["bg"], highlightthickness=0, width=360)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        frame = tk.Frame(canvas, bg=THEME["bg"], padx=20, pady=12)
        frame_id = canvas.create_window((0, 0), window=frame, anchor="nw")

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        frame.bind("<Configure>", _on_frame_configure)

        def _on_canvas_configure(e):
            canvas.itemconfig(frame_id, width=e.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        win.bind("<MouseWheel>", _on_mousewheel)

        # ── 輔助建立列 ────────────────────────────────────────────────────────
        LBL_W = 22

        def sep():
            tk.Frame(frame, bg=THEME["border"], height=1).pack(fill=tk.X, pady=6)

        def row(label_key):
            r = tk.Frame(frame, bg=THEME["bg"])
            r.pack(fill=tk.X, pady=3)
            make_label(r, self.t(label_key), font=(ff, 9),
                       width=LBL_W, anchor="w").pack(side=tk.LEFT)
            return r

        def color_row(label_key, var, attr_name):
            r = row(label_key)
            btn = tk.Button(
                r, bg=var.get(), width=4,
                relief=tk.FLAT, bd=1, cursor="hand2",
            )
            btn.pack(side=tk.LEFT, padx=4)
            hex_lbl = make_label(r, var.get(), fg=THEME["sub_text"], font=(ff, 9))
            hex_lbl.pack(side=tk.LEFT)
            setattr(self, attr_name, btn)
            btn.config(command=lambda v=var, b=btn, l=hex_lbl:
                       self._pick_color_with_label(v, b, l))

        def check_row(label_key, var):
            r = row(label_key)
            tk.Checkbutton(r, variable=var,
                           bg=THEME["bg"], fg=THEME["text"],
                           activebackground=THEME["bg"],
                           selectcolor=THEME["entry_bg"]).pack(side=tk.LEFT, padx=4)

        # ── 數值欄位 ──────────────────────────────────────────────────────────
        r = row("overlay_x_label")
        self._v_x = tk.StringVar(value=str(cfg.get("x", 500)))
        make_entry(r, textvariable=self._v_x, width=8).pack(side=tk.LEFT, padx=4)

        r = row("overlay_y_label")
        self._v_y = tk.StringVar(value=str(cfg.get("y", 700)))
        make_entry(r, textvariable=self._v_y, width=8).pack(side=tk.LEFT, padx=4)

        r = row("overlay_icon_size_label")
        self._v_icon = tk.StringVar(value=str(cfg.get("icon_size", 64)))
        make_entry(r, textvariable=self._v_icon, width=8).pack(side=tk.LEFT, padx=4)

        r = row("overlay_spacing_label")
        self._v_spacing = tk.StringVar(value=str(cfg.get("spacing", 1)))
        make_entry(r, textvariable=self._v_spacing, width=8).pack(side=tk.LEFT, padx=4)

        r = row("overlay_opacity_label")
        self._v_opacity = tk.DoubleVar(value=cfg.get("opacity", 0.9))
        sc = tk.Scale(r, from_=0.1, to=1.0, resolution=0.05,
                      orient=tk.HORIZONTAL, variable=self._v_opacity,
                      bg=THEME["panel"], fg=THEME["text"],
                      troughcolor=THEME["entry_bg"], highlightthickness=0,
                      length=140)
        sc.pack(side=tk.LEFT, padx=4)

        # ── 勾選框群組 ────────────────────────────────────────────────────────
        sep()
        self._v_show_drag = tk.BooleanVar(value=cfg.get("show_drag", True))
        check_row("overlay_show_drag_label", self._v_show_drag)

        self._v_show_gear = tk.BooleanVar(value=cfg.get("show_gear", True))
        check_row("overlay_show_gear_label", self._v_show_gear)

        self._v_show_bg = tk.BooleanVar(value=cfg.get("show_bg", False))
        check_row("overlay_bg_label", self._v_show_bg)

        self._v_show_num_bg = tk.BooleanVar(value=cfg.get("show_num_bg", False))
        check_row("overlay_show_num_bg_label", self._v_show_num_bg)

        self._v_show_name_bg = tk.BooleanVar(value=cfg.get("show_name_bg", True))
        check_row("overlay_show_name_bg_label", self._v_show_name_bg)

        self._v_hide_idle = tk.BooleanVar(value=cfg.get("hide_idle_timers", False))
        check_row("overlay_hide_idle_label", self._v_hide_idle)

        self._v_show_image = tk.BooleanVar(value=cfg.get("show_image", True))
        check_row("overlay_show_image_label", self._v_show_image)

        # ── 顏色選取群組 ──────────────────────────────────────────────────────
        sep()
        self._v_bg_color = tk.StringVar(value=cfg.get("bg_color", "#1a1a2e"))
        color_row("overlay_bg_color_label", self._v_bg_color, "_bg_color_btn")

        self._v_num_bg_color = tk.StringVar(value=cfg.get("num_bg_color", "#1a1a2e"))
        color_row("overlay_num_bg_color_label", self._v_num_bg_color, "_num_bg_color_btn")

        self._v_name_bg_color = tk.StringVar(value=cfg.get("name_bg_color", "#1a1a2e"))
        color_row("overlay_name_bg_color_label", self._v_name_bg_color, "_name_bg_color_btn")

        self._v_text_color = tk.StringVar(value=cfg.get("text_color", "#ffffff"))
        color_row("overlay_text_color_label", self._v_text_color, "_text_color_btn")

        self._v_name_color = tk.StringVar(value=cfg.get("name_color", "#ffffff"))
        color_row("overlay_name_color_label", self._v_name_color, "_name_color_btn")

        # ── 名稱顯示設定 ──────────────────────────────────────────────────────
        sep()
        pos_values = [
            self.t("name_pos_above_img"),
            self.t("name_pos_below_img"),
            self.t("name_pos_center_img"),
            self.t("name_pos_top_img"),
            self.t("name_pos_bottom_img"),
        ]
        pos_keys = ["above_img", "below_img", "center_img", "top_img", "bottom_img"]
        cur_pos = cfg.get("name_position", "below_img")
        cur_pos_label = pos_values[pos_keys.index(cur_pos)] if cur_pos in pos_keys else pos_values[1]
        self._v_name_pos_label = tk.StringVar(value=cur_pos_label)
        self._pos_keys = pos_keys
        self._pos_values = pos_values

        r = row("overlay_name_position_label")
        _style = ttk.Style()
        _style.configure("Dark.TCombobox",
                         fieldbackground=THEME["entry_bg"],
                         background=THEME["btn"],
                         foreground=THEME["text"],
                         selectbackground=THEME["accent"],
                         selectforeground=THEME["text"])
        _style.map("Dark.TCombobox",
                   fieldbackground=[("readonly", THEME["entry_bg"])],
                   foreground=[("readonly", THEME["text"])])
        cb_pos = ttk.Combobox(r, textvariable=self._v_name_pos_label,
                              values=pos_values, state="readonly", width=18,
                              font=(ff, 9), style="Dark.TCombobox")
        cb_pos.pack(side=tk.LEFT, padx=4)

        align_values = [
            self.t("name_align_left"),
            self.t("name_align_center"),
            self.t("name_align_right"),
        ]
        align_keys = ["left", "center", "right"]
        cur_align = cfg.get("name_align", "center")
        cur_align_label = align_values[align_keys.index(cur_align)] if cur_align in align_keys else align_values[1]
        self._v_name_align_label = tk.StringVar(value=cur_align_label)
        self._align_keys = align_keys
        self._align_values = align_values

        r = row("overlay_name_align_label")
        cb_align = ttk.Combobox(r, textvariable=self._v_name_align_label,
                                values=align_values, state="readonly", width=18,
                                font=(ff, 9), style="Dark.TCombobox")
        cb_align.pack(side=tk.LEFT, padx=4)

        # ── 操作按鈕 ──────────────────────────────────────────────────────────
        sep()
        btn_row = tk.Frame(frame, bg=THEME["bg"])
        btn_row.pack(fill=tk.X, pady=(0, 4))
        make_btn(btn_row, self.t("btn_save_overlay"), self._save,
                 bg=THEME["success"], font=(ff, 10)).pack(side=tk.LEFT, padx=4)
        make_btn(btn_row, self.t("btn_apply_overlay"), self._apply,
                 bg=THEME["accent"], font=(ff, 10)).pack(side=tk.LEFT, padx=4)
        make_btn(btn_row, self.t("btn_close"), self._on_close,
                 font=(ff, 10)).pack(side=tk.RIGHT, padx=4)

        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win_w = 400
        win_h = min(700, sh - 60)
        canvas.config(height=win_h - 20)
        win.geometry(f"{win_w}x{win_h}+{(sw - win_w)//2}+{(sh - win_h)//2}")

    def _pick_color(self, var: tk.StringVar, btn: tk.Button):
        color = colorchooser.askcolor(color=var.get(), parent=self._win)
        if color and color[1]:
            var.set(color[1])
            btn.config(bg=color[1])

    def _pick_color_with_label(self, var: tk.StringVar, btn: tk.Button, lbl: tk.Label):
        color = colorchooser.askcolor(color=var.get(), parent=self._win)
        if color and color[1]:
            var.set(color[1])
            btn.config(bg=color[1])
            lbl.config(text=color[1])

    def _collect(self) -> dict:
        def safe_int(v, default):
            try:
                return max(1, int(v))
            except Exception:
                return default

        # 將顯示標籤轉回內部 key
        pos_label = self._v_name_pos_label.get()
        name_position = "below_img"
        for k, v in zip(self._pos_keys, self._pos_values):
            if v == pos_label:
                name_position = k
                break

        align_label = self._v_name_align_label.get()
        name_align = "center"
        for k, v in zip(self._align_keys, self._align_values):
            if v == align_label:
                name_align = k
                break

        return {
            "x": safe_int(self._v_x.get(), 500),
            "y": safe_int(self._v_y.get(), 700),
            "icon_size": safe_int(self._v_icon.get(), 64),
            "spacing": max(0, safe_int(self._v_spacing.get(), 1)),
            "opacity": self._v_opacity.get(),
            "show_bg": self._v_show_bg.get(),
            "bg_color": self._v_bg_color.get(),
            "text_color": self._v_text_color.get(),
            "show_drag": self._v_show_drag.get(),
            "show_gear": self._v_show_gear.get(),
            "show_num_bg": self._v_show_num_bg.get(),
            "num_bg_color": self._v_num_bg_color.get(),
            "show_name_bg": self._v_show_name_bg.get(),
            "name_bg_color": self._v_name_bg_color.get(),
            "name_color": self._v_name_color.get(),
            "name_position": name_position,
            "name_align": name_align,
            "hide_idle_timers": self._v_hide_idle.get(),
            "show_image": self._v_show_image.get(),
        }

    def _save(self):
        self.config_manager.update_overlay_settings(self._collect())
        self.config_manager.save()
        self.app.on_overlay_settings_changed()
        messagebox.showinfo(self.t("info_title"), self.t("overlay_save_success"),
                            parent=self._win)

    def _apply(self):
        self.config_manager.update_overlay_settings(self._collect())
        self.app.on_overlay_settings_changed()
        messagebox.showinfo(self.t("info_title"), self.t("overlay_apply_success"),
                            parent=self._win)

    def _on_close(self):
        if self._win:
            self._win.destroy()
            self._win = None
        self.app.on_settings_closed()
