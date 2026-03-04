
> 版本：v1.3.0 | 作者：oo_jump | 協作：巴哈_波菜菜菜 | 平台：Windows

# 倒數計時器 Plus (Countdown_Timer_plus_v1.3.0)

---

## 📋 專案簡介

為遊戲實況/副本挑戰設計的多組倒數計時器，支援懸浮窗顯示、全域快捷鍵、音效提示、圖示閃爍等功能。

---

## 🗂 檔案結構

```
New_Countdown_Timer/
├── main.py                 主程式入口
├── translations.py         多語言翻譯文字（zh_TW / en_US）
├── config_manager.py       設定檔讀寫管理（10 個插槽）
├── timer_engine.py         計時器核心邏輯（多線程）
├── overlay_window.py       懸浮窗 UI
├── settings_window.py      設定視窗 UI（設定檔/計時管理/懸浮窗設定）
├── audio_player.py         Windows 原生音效播放（winmm.dll MCI）
├── vk_hotkey.py            Windows VK Code 全域熱鍵監聽
├── countdown_config.json   執行時自動產生的設定檔
├── requirements.txt        Python 依賴套件（開發用）
├── sound_type/             音效資料夾（使用者可自行放入 .mp3/.wav）
│   └── *_sq.mp3            檔名含 _sq 的音效才會顯示於列表
└── png_type/               圖片資料夾（使用者可自行放入 .png/.jpg）
    ├── *_on.png            含 _on 字尾者為「倒數中」圖示
    └── Set_*.png           Set_ 開頭者為系統保留圖示（拖曳把手、齒輪等）

```

---

## 🚀 功能列表

### 1. 主視窗 (main_frame)

| 元件 | 說明 |
|------|------|
| hint_frame | 頂部顯示當前設定檔名稱、狀態 |
| 📌 置頂按鈕 | 切換視窗置頂 |
| 💾 設定檔 | 開啟設定檔管理視窗 |
| ⚙️ 計時管理 | 開啟多組計時管理視窗 |
| 🖥 懸浮窗 | 開啟懸浮窗設定視窗 |
| ❤️ 贊助 | 贊助資訊連結 |
| 中文/EN | 切換介面語言 |
| ✅/⛔ 開關 | 全部啟用/停用 |
| 🗔 懸浮框 | 切換懸浮框模式（隱藏主視窗） |
| opacity | 視窗透明度拉條 |
| 更新延遲 | 切換計時引擎更新間隔（高延遲 0.3s / 低延遲 0.1s） |

### 2. 計時器顯示

- 每個計時器以一行顯示：名稱、快捷鍵、倒數秒數、模式文字（自動循環 / 倒數後停止 / 雙回合切換）、回合標示
- 顏色：正常 → 紫藍、≤10秒 → 黃色、≤3秒 → 紅色閃爍

### 3. 設定檔管理（💾）

- 最多 10 個設定檔插槽，插槽 1（`[1]`）固定為預設設定檔
- 功能：套用、匯入 JSON、匯出 JSON、清空、編輯名稱
- 空插槽亦可直接套用或命名（自動建立空設定檔）
- 3 個程序快捷鍵設定：
  - 全部暫停
  - 啟用/停用
  - 懸浮框開關

### 4. 多組計時管理（⚙️）

- 新增、上移、下移、刪除計時組
- 每個計時組可設定：
  - **名稱**
  - **快捷鍵**（VK 全域監聽）
  - **倒數模式**：
    - `自動循環` — 歸零後自動重新開始
    - `倒數後停止` — 歸零後停留在 0
    - `雙回合切換` — 回合一結束→回合二→回合一...
  - **快捷鍵功能**：重置並開始 / 重置並停止
  - **圖片顯示**（png_type 資料夾中的圖片）
  - **音效管理**（sound_type 資料夾中的音效檔案）
    - 播放方式：單次播放 / 分段播放
    - 提前幾秒播放
    - 分段次數

### 5. 懸浮窗（🗔）

- 全域置頂透明浮動視窗
- 可拖曳移動（Set_Arrow_keys 圖示，退回 ⊹ 文字符號）
- 齒輪按鈕（Set_gear 圖示，退回 ⚙ 文字符號）返回主視窗
- 橫向排列顯示所有計時組
- 圖示上方顯示倒數秒數

### 6. 懸浮窗設定（🖥）

- 起始座標 X, Y
- 圖示大小、間距
- 透明度
- 是否顯示圖片（顯示圖片 / 僅顯示數字+名稱）
- 是否顯示背景底色
- 背景顏色、數字顏色、名稱顏色
- 名稱顯示位置（圖片上/下/中疊加）與對齊方式

---

## 🔧 技術細節

### 計時精度（Epoch 絕對計時）
- 核心：`_epoch_start` 起始時間戳，在整個運行期間永不更改
- 計算公式：
  - `MODE_LOOP` → `remaining = time1 - (total_elapsed % time1)`
  - `MODE_DUAL` → 依 `total_elapsed % (time1+time2)` 決定回合與 remaining
  - `MODE_STOP` → `remaining = time1 - total_elapsed`
- 保證：10 秒迴圈第 20 輪結束時，total_elapsed == 200 秒（牆鐘絕對值），零累積誤差
- 阻塞容錯：電腦阻塞恢復後，計時器自動補位至正確週期位置，不連鎖觸發
- NTP 防禦：`total_elapsed = max(0.0, now - _epoch_start)` 防止系統時鐘回撥造成異常

### 熱鍵系統
- VK Code 全域監聽（`GetAsyncKeyState`）
- 完整區分數字鍵盤（NumPad/）和主鍵盤（/）
- 支援 CapsLock、反引號（`）等特殊鍵
- 所有 VK 熱鍵觸發均透過 `root.after(0, ...)` 在主線程排程，避免 Tkinter 線程衝突

### 音效分段播放邏輯
```python
interval = advance / frequency
for i in range(frequency):
    trigger_time = advance - (i * interval)
    trigger_rounded = int(trigger_time + 0.5)
    if current_second == trigger_rounded and trigger_rounded > 0:
        play_sound()
```

### 圖示閃爍
- 倒數最後 3 秒：圖示在原圖與灰階之間每 0.4 秒切換
- 倒數結束：固定顯示灰階圖示
- 使用 PIL（Pillow）進行灰階轉換

### 音效播放
- 使用 Windows `winmm.dll` MCI 命令
- 多聲道機制（每個計時器獨立聲道，互不干擾）
- 支援 .mp3 和 .wav 格式

---

## 📦 打包說明

```bash
pip install pyinstaller Pillow
pyinstaller --onefile --windowed --name Countdown_Timer_plus_v1.3.0 \
    --add-data "sound_type;sound_type" \
    --add-data "png_type;png_type" \
    main.py
```

打包後結構：
```
dist/Countdown_Timer_plus_v1.3.0/
├── Countdown_Timer_plus_v1.3.0.exe
├── sound_type/
└── png_type/
```

---

## 📥 依賴安裝

```bash
pip install -r requirements.txt
```

| 套件 | 版本 | 用途 |
|------|------|------|
| Pillow | ≥10.0 | 圖片處理（灰階、縮放） |
| pyinstaller | ≥6.0 | 打包為 exe |

標準庫（無需安裝）：
- `tkinter` — UI 框架
- `ctypes` — Windows API（winmm.dll, GetAsyncKeyState）
- `threading` — 多線程
- `json` — 設定檔讀寫

---

## 🗓 開發進度紀錄

### v1.0.0（2026-03-02）
- [x] 建立專案基礎架構
- [x] `translations.py`：繁中/英文翻譯
- [x] `audio_player.py`：Windows winmm 多聲道音效播放
- [x] `vk_hotkey.py`：VK Code 全域熱鍵監聽，支援一次性捕獲
- [x] `config_manager.py`：10 插槽設定檔管理，匯入/匯出
- [x] `timer_engine.py`：三種計時模式、音效觸發、圖示閃爍邏輯
- [x] `overlay_window.py`：懸浮窗，可拖曳，PIL 圖示顯示
- [x] `settings_window.py`：設定檔管理、多組計時管理、懸浮窗設定三個視窗
- [x] `main.py`：主視窗 UI，引擎整合，線程安全 UI 更新

### v1.1.0（2026-03-03）
- [x] 移除首次開啟的管理員身分提示框；全域監聽預設啟用，不再提示
- [x] `TimerMgrWindow` 初始高度提升（`max(500→620)`），避免下方按鈕遮擋
- [x] `OverlaySettingsWindow` 初始高度提升（`min(620→700)`），避免下方按鈕遮擋
- [x] 設定檔管理視窗（💾）開啟時不再設 `all_paused=True`，個別計時快捷鍵持續有效

### v1.2.0（2026-03-04）
- [x] 移除「設為預設」按鈕；插槽 1 固定為預設，簡化操作流程
- [x] 空插槽（profile = None）允許被選取並套用，自動建立空設定檔
- [x] `_save_name()` 支援對空插槽直接建立設定檔並命名
- [x] `apply_profile()` 移除插槽為空時的攔截，無條件套用指定插槽
- [x] 設定檔列表選中後固定選項（`_pinned_slot`），防止編輯名稱時意外切換
- [x] 名稱輸入框 `<FocusIn>` 綁定 `_reassert_selection()`，確保操作一致性
- [x] README.md 新增「模組與資安說明」章節，完整揭露使用 API 與資安評估
- [x] 計時器核心改為 **Epoch 絕對計時**（`_epoch_start`）：零累積誤差、阻塞自動補位
- [x] `timer_engine.py` 新增 `update_interval` 可切換（高延遲 0.3s / 低延遲 0.1s）
- [x] 主視窗新增「更新延遲」切換按鈕，清楚標示目前使用的延遲模式
- [x] `total_elapsed = max(0.0, ...)` 防禦 NTP 時鐘回撥

### v1.3.0（2026-03-04）
- [x] 專案更名：`Countdown_Timer_plus_v1.3.0`，協作者：巴哈_波菜菜菜
- [x] 懸浮窗設定新增「顯示圖片」勾選框（預設開啟），關閉後僅顯示數字與名稱
- [x] 新增齒輪按鈕並且支援自訂圖檔（`Set_Arrow_keys` / `Set_gear`），找不到圖檔時退回文字符號
- [x] 主視窗計時列「模式」欄改為文字顯示（自動循環 / 倒數後停止 / 雙回合切換）

---

## 🔒 模組與資安說明

### 使用模組總覽

| 分類 | 模組 | 用途 |
|------|------|------|
| GUI | `tkinter` / `ttk` / `messagebox` / `filedialog` / `colorchooser` | 所有視窗、按鈕、對話框 |
| 多執行緒 | `threading` | 計時器引擎、熱鍵監聽、音效播放各自獨立 |
| 時間 | `time` | 計時精度控制（`time.time()` Epoch 差值） |
| 檔案系統 | `os` / `sys` / `json` / `copy` | 本地路徑操作、設定檔讀寫 |
| 環境偵測 | `platform` | 判斷 Windows 以啟用 Windows 專屬功能 |
| 瀏覽器 | `webbrowser` | 僅用於贊助按鈕，固定開啟作者 YouTube 頻道 |
| Windows API | `ctypes` | 呼叫 `user32.dll`、`winmm.dll`（詳見下方） |
| 圖片處理 | `Pillow (PIL)` | 懸浮窗圖示縮放、灰階轉換（閃爍效果） |

### Windows 系統 API 呼叫說明

**`user32.dll` — `GetAsyncKeyState`（`vk_hotkey.py`）**
- 用途：全域輪詢使用者是否按下已設定的快捷鍵（F6/F7/F8 等）
- 行為範圍：僅輪詢 `VK_CODES` 字典定義的約 80 個常用鍵，不記錄、不儲存、不傳送任何按鍵資料
- 備註：此 API 與鍵盤記錄器（keylogger）所用相同，**PyInstaller 打包後可能觸發防毒軟體誤報**，屬正常現象

**`winmm.dll` — MCI 音效播放（`audio_player.py`）**
- 用途：播放 `sound_type/` 資料夾中的本地音效（`.mp3` / `.wav`）
- 行為範圍：純本地音效輸出，無任何網路行為

### 資安評估

| 項目 | 行為 | 評估 |
|------|------|------|
| 鍵盤監聽（`GetAsyncKeyState`） | 全域輪詢按鍵狀態 | 低風險（本地操作，不記錄不傳送） |
| 音效播放（`winmm MCI`） | 讀取本地音效檔 | 無風險 |
| 設定檔讀寫 | 讀寫同目錄 JSON | 無風險 |
| 網路連線 | 僅贊助按鈕開啟 YouTube | 無風險（固定 URL，不傳送使用者資料） |
| 圖片處理（Pillow） | 讀取本地 PNG | 無風險 |
| 管理員權限 | 執行時可要求 | 必要（全域熱鍵需要），不用於其他操作 |

**結論：本程序不具備任何主動網路通訊、遠端控制、資料回傳機制。所有操作均限於本機。**

> PyInstaller 打包時會一併拉入 `socket`、`http`、`urllib`、`subprocess`、`asyncio` 等標準函式庫，這些均為 `webbrowser` 或 Pillow 的間接靜態依賴，**程式碼中並未主動呼叫**，不影響資安。

---

## ❓ 常見問題

**Q: 全域熱鍵沒有反應？**
> A: 請以系統管理員身分執行程式。部分系統需要管理員權限才能使用 `GetAsyncKeyState` 全域監聽。

**Q: 音效沒有聲音？**
> A: 確認 `sound_type/` 資料夾中有音效檔案，且檔名含有 `_sq`（如 `炎-中文-女-瀟瀟1-固定魔方_sq.mp3`），才會顯示於清單中。

**Q: 圖示不顯示？**
> A: 確認已安裝 `Pillow`（`pip install Pillow`），且圖片放在 `png_type/` 資料夾中。懸浮窗設定中「顯示圖片」需勾選。
