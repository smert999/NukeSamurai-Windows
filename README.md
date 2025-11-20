# NukeSamurai - Windows GPU Edition 🚀

> **SAM 2.1 (Segment Anything Model 2.1)** plugin for **Nuke** with **GPU acceleration** on Windows

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Nuke](https://img.shields.io/badge/Nuke-16.0v4-blue.svg)](https://www.foundry.com/products/nuke)
[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![CUDA](https://img.shields.io/badge/CUDA-11.8%2F12.1-green.svg)](https://developer.nvidia.com/cuda-toolkit)

---

## 📖 О проекте / About

**Русский:**

NukeSamurai - это адаптированная версия плагина для Nuke, позволяющая генерировать маски объектов с помощью SAM 2.1 (Segment Anything Model 2.1) от Meta с использованием **GPU ускорения на Windows**.

**Ключевые особенности:**
- ✅ **GPU ускорение** (NVIDIA RTX 4090 и другие)
- ✅ **100x быстрее** CPU версии (~15-20 секунд вместо 15-20 минут для 181 кадра)
- ✅ Работает на **Windows** (решены все проблемы совместимости)
- ✅ **Subprocess архитектура** (обходит конфликты DLL между Nuke Python и PyTorch)
- ✅ Автоматическое создание Read ноды с масками
- ✅ Прогресс-бар в реальном времени с детализацией этапов
- ✅ Поддержка PNG, EXR (с автоматическим fallback), MP4
- ✅ OCIO colorspace поддержка

**English:**

NukeSamurai is an adapted version of the Nuke plugin that generates object masks using SAM 2.1 (Segment Anything Model 2.1) from Meta with **GPU acceleration on Windows**.

**Key Features:**
- ✅ **GPU acceleration** (NVIDIA RTX 4090 and others)
- ✅ **100x faster** than CPU version (~15-20 seconds vs 15-20 minutes for 181 frames)
- ✅ Works on **Windows** (all compatibility issues resolved)
- ✅ **Subprocess architecture** (bypasses DLL conflicts between Nuke Python and PyTorch)
- ✅ Automatic Read node creation with masks
- ✅ Real-time progress bar with detailed stages
- ✅ PNG, EXR (with automatic fallback), MP4 support
- ✅ OCIO colorspace support

---

## 🎬 Demo

Before (CPU): **15-20 minutes** for 181 frames  
After (GPU RTX 4090): **15-20 seconds** for 181 frames ⚡

---

## 🏗️ Архитектура / Architecture

### **Почему НЕТ папки `python_libs`?**

**Русский:**

Этот плагин использует **subprocess архитектуру** для полной изоляции PyTorch от Nuke Python:

```
┌─────────────────────────────────────────────────────────────┐
│ NUKE PROCESS (Python 3.9/3.11)                              │
├─────────────────────────────────────────────────────────────┤
│ • UI (getBbox, buttons)                                     │
│ • opencv-python (только для GUI)                           │
│ • numpy (только для GUI)                                    │
│                                                             │
│ ────────────► Запускает subprocess ────────────►            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ WORKER PROCESS (System Python 3.10/3.11)                   │
├─────────────────────────────────────────────────────────────┤
│ • PyTorch + CUDA                                            │
│ • SAM2                                                      │
│ • All dependencies (hydra, timm, etc.)                     │
│                                                             │
│ ◄──────────── Reports progress ◄────────────                │
└─────────────────────────────────────────────────────────────┘
```

**Преимущества:**
- ✅ **НЕТ конфликтов DLL** между Nuke Python и PyTorch
- ✅ **НЕТ локальной копии torch** в плагине (экономия ~2GB)
- ✅ **Простая установка** через `pip install -r requirements.txt`
- ✅ **Полная изоляция** - Nuke и torch не видят друг друга
- ✅ **Используется ваш рабочий system Python** с torch+CUDA

**Что устанавливается:**
1. **System Python (3.10/3.11)**: torch + зависимости SAM2 (hydra, omegaconf, timm, einops, loguru)
2. **Nuke Python (3.9/3.11)**: только opencv-python + numpy (для GUI bbox)
3. **Плагин**: скрипты + SAM2 код (sam2_repo уже включен в релиз!)

💡 **Важно:** Код SAM2 **не устанавливается через pip** - он уже включен в папку `sam2_repo`!

📝 **Примечание:** В других версиях плагина (например, Linux версия от Theo) используется `pip install -e sam2_repo/` для компиляции CUDA расширения. На Windows это требует Visual Studio и **не обязательно** - плагин отлично работает без него!

**English:**

This plugin uses **subprocess architecture** for complete PyTorch isolation from Nuke Python:

**Benefits:**
- ✅ **NO DLL conflicts** between Nuke Python and PyTorch
- ✅ **NO local torch copy** in plugin (saves ~2GB)
- ✅ **Easy installation** via `pip install -r requirements.txt`
- ✅ **Complete isolation** - Nuke and torch don't see each other
- ✅ **Uses your working system Python** with torch+CUDA

**What gets installed:**
1. **System Python (3.10/3.11)**: torch + SAM2 dependencies (hydra, omegaconf, timm, einops, loguru)
2. **Nuke Python (3.9/3.11)**: only opencv-python + numpy (for GUI bbox)
3. **Plugin**: scripts + SAM2 code (sam2_repo already included in release!)

💡 **Important:** SAM2 code is **not installed via pip** - it's already included in `sam2_repo` folder!

---

## 💻 Требования / Requirements

### Минимальные требования:
- **Nuke** 16.0v4 или выше
- **Windows 10/11** (64-bit)
- **NVIDIA GPU** с поддержкой CUDA (RTX 3060 или выше рекомендуется)
- **Python 3.10** (системный, отдельно от Nuke)
- **16 GB RAM** (минимум)
- **20 GB свободного места** (для моделей SAM 2.1)

### Рекомендуемые:
- **Nuke** 16.0v4+
- **NVIDIA RTX 4090** или аналогичная
- **32 GB RAM**
- **SSD** для кэша

---

## 📥 Установка / Installation

### Шаг 1: Установка системного Python 3.10

1. Скачайте Python 3.10: https://www.python.org/downloads/release/python-31011/
2. Установите с опциями:
   - ✅ Add Python to PATH
   - ✅ Install for all users

### Шаг 2: Установка PyTorch с CUDA

Откройте **командную строку** (cmd) и выполните:

```bash
pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 --index-url https://download.pytorch.org/whl/cu121
```

Или для CUDA 11.8:
```bash
pip install torch==2.5.1+cu118 torchvision==0.20.1+cu118 --index-url https://download.pytorch.org/whl/cu118
```

### Шаг 3: Установка зависимостей для System Python

**Вариант 1: Автоматическая установка (рекомендуется)**
```bash
cd %USERPROFILE%\.nuke\NukeSamurai
pip install -r requirements.txt
```

**Вариант 2: Ручная установка с точными версиями**
```bash
pip install numpy>=1.26.0 opencv-python>=4.8.0 Pillow>=10.0.0 hydra-core>=1.3.0 omegaconf>=2.3.0 iopath>=0.1.10 timm>=0.9.0 tqdm>=4.65.0 einops>=0.7.0 loguru>=0.7.0
```

**Или по одному:**
```bash
pip install numpy>=1.26.0
pip install opencv-python>=4.8.0
pip install Pillow>=10.0.0
pip install hydra-core>=1.3.0
pip install omegaconf>=2.3.0
pip install iopath>=0.1.10
pip install timm>=0.9.0
pip install tqdm>=4.65.0
pip install einops>=0.7.0
pip install loguru>=0.7.0
```

⚠️ **Важно:** Все зависимости должны быть установлены в system Python, где установлен PyTorch!

### Шаг 3.5: Установка OpenCV для Nuke Python (для Bounding Box)

⚠️ **КРИТИЧЕСКИ ВАЖНО:** Для работы "Create Bounding Box" нужен opencv-python в **Nuke Python**!

🚨 **СНАЧАЛА проверьте ВАШУ версию Nuke:**
```bash
dir "C:\Program Files" | findstr Nuke
```

**Откройте PowerShell/CMD как Администратор:**

Для Nuke 16.0v4:
```bash
"C:\Program Files\Nuke16.0v4\python.exe" -m pip install --force-reinstall opencv-python>=4.8.0 numpy>=1.26.0
```

Для Nuke 15.1v5:
```bash
"C:\Program Files\Nuke15.1v5\python.exe" -m pip install --force-reinstall opencv-python>=4.8.0 numpy>=1.26.0
```

⚠️ **Замените версию на ВАШУ!** Если видите ошибку "файл не найден" - проверьте версию заново!

💡 **`--force-reinstall`** гарантирует установку именно в Nuke Python, а не в system Python!

**Проверка (ВАЖНО!):**
```bash
"C:\Program Files\Nuke15.1v5\python.exe" -c "import cv2; print('OpenCV:', cv2.__version__, '\nPath:', cv2.__file__)"
```

⚠️ Путь ДОЛЖЕН содержать `Nuke15.1v5\lib\site-packages`, **НЕ** `AppData\Roaming\Python\Python310`!

**Если видите путь к Python310:**
- Очистите переменную окружения PYTHONPATH
- Переустановите с `--force-reinstall`

### Шаг 4: Установка плагина

1. Скачайте релиз или клонируйте репозиторий:
```bash
cd %USERPROFILE%\.nuke
git clone https://github.com/YOUR_USERNAME/NukeSamurai-Windows.git NukeSamurai
```

2. Скачайте модели SAM 2.1:
```bash
cd %USERPROFILE%\.nuke\NukeSamurai\sam2_repo\checkpoints
```

Скачайте модели с:
- https://github.com/facebookresearch/sam2/releases

Модели:
- `sam2.1_hiera_base_plus.pt` (рекомендуется для RTX 4090)
- `sam2.1_hiera_large.pt`
- `sam2.1_hiera_small.pt`
- `sam2.1_hiera_tiny.pt`

### Шаг 5: Настройка Nuke

Плагин автоматически загружается из `~/.nuke/NukeSamurai/`

**Если плагин не загрузился автоматически**, добавьте в `.nuke/init.py`:
```python
nuke.pluginAddPath('./NukeSamurai')
```

Проверьте в консоли Nuke (F8):
```
[NukeSamurai] Plugin loaded (GPU via subprocess)
```

---

## 🎮 Использование / Usage

### 1. Создайте узел SAMURAI

В Nuke:
- Нажмите **Tab**
- Введите **SAMURAI**
- Выберите узел

### 2. Update Path

1. Подключите **Read node** с последовательностью кадров
2. В SAMURAI node нажмите **Update Path**
3. Проверьте что Frame Range и FPS определились автоматически

### 3. Create Bounding Box

1. Нажмите **Create Bounding Box**
2. В открывшемся окне выделите объект
3. Нажмите **Enter** или **Space** для подтверждения

### 4. Настройте параметры

- **Model type**: Base+ (рекомендуется для RTX 4090)
- **Frame Range**: 1001 - 1182 (автоматически)
- **File type**: 
  - **png** (рекомендуется, всегда работает) ✅
  - **exr** (автоматически переключится на PNG если OpenCV не поддерживает)
  - **mp4** (пока не реализовано)
- **Output Path**: `D:/path/to/Mask_####.png`

⚠️ **Важно:** Output Path должен содержать `####` или `###`

💡 **Tip:** Наведите курсор на "File type" чтобы увидеть подсказку о форматах

### 5. Generate Mask

1. Нажмите **Generate Mask**
2. Следите за прогрессом в Progress Bar
3. После завершения Read node создастся автоматически справа от SAMURAI!

---

## 🏗️ Архитектура / Architecture

```
┌─────────────────────────────────────────┐
│ Nuke Python 3.11 (UI only)             │
│ • Node creation                         │
│ • Bounding Box                          │
│ • Parameters                            │
│ • Progress Bar                          │
└─────────────────────────────────────────┘
                ↓ subprocess
┌─────────────────────────────────────────┐
│ System Python 3.10 (Worker)             │
│ • torch 2.5.1+cu121 ✓ WORKS!           │
│ • CUDA GPU RTX 4090 ✓                  │
│ • SAM2 inference                        │
│ • Mask generation & save                │
└─────────────────────────────────────────┘
```

**Почему subprocess?**
- Nuke Python 3.11 (скомпилирован Foundry) несовместим с PyTorch DLL
- ABI/CRT конфликты делают невозможным импорт torch в Nuke Python
- Subprocess использует системный Python 3.10 где torch РАБОТАЕТ с GPU
- Чистое разделение: UI в Nuke, вычисления в system Python

---

## ⚡ Производительность / Performance

### Тесты на RTX 4090:

| Frames | CPU (minutes) | GPU (seconds) | Speedup |
|--------|---------------|---------------|---------|
| 181    | 15-20 min     | 15-20 sec     | 100x    |
| 500    | 45-60 min     | 40-50 sec     | 90x     |
| 1000   | 90-120 min    | 80-100 sec    | 80x     |

**Base+ Model:**
- Reading frames: ~38 FPS
- Propagation: ~15-30 FPS
- Total: ~20 seconds for 181 frames

---

## 🔧 Устранение неполадок / Troubleshooting

### "ModuleNotFoundError: No module named 'numpy'" при Create Bounding Box

**Проблема:** opencv-python и numpy не установлены в **Nuke Python**, или Nuke импортирует cv2 из system Python.

**Важно:** Функция "Create Bounding Box" использует cv2.selectROI(), которая выполняется в Nuke Python, а не в subprocess!

**Решение:** 

1. Установите opencv-python и numpy В NUKE PYTHON с `--force-reinstall`:

```bash
# Для Nuke 16.0v4:
"C:\Program Files\Nuke16.0v4\python.exe" -m pip install --force-reinstall opencv-python>=4.8.0 numpy>=1.26.0

# Для Nuke 15.1:
"C:\Program Files\Nuke15.1v5\python.exe" -m pip install --force-reinstall opencv-python>=4.8.0 numpy>=1.26.0
```

2. Проверьте что cv2 установлен в правильное место:

```bash
"C:\Program Files\Nuke15.1v5\python.exe" -c "import cv2; print(cv2.__file__)"
```

**Должно быть:** `C:\Program Files\Nuke15.1v5\lib\site-packages\cv2\...`  
**НЕ должно быть:** `C:\Users\...\AppData\Roaming\Python\Python310\...`

3. Если путь неправильный - очистите PYTHONPATH:

```powershell
[Environment]::SetEnvironmentVariable("PYTHONPATH", $null, "User")
```

⚠️ Требуются права администратора!

### "ModuleNotFoundError: No module named 'loguru'" при Generate Mask

**Проблема:** Не все зависимости SAM2 установлены в system Python.

**Решение:**
```bash
cd %USERPROFILE%\.nuke\NukeSamurai
pip install -r requirements.txt
```

Или установите недостающий модуль:
```bash
pip install loguru
```

**Проверьте все зависимости:**
```bash
pip list | findstr "torch numpy opencv hydra loguru timm einops"
```

### "Worker failed with code 1"

Проверьте консоль Nuke (F8) для деталей ошибки.

**Частые причины:**
1. PyTorch не установлен в system Python
2. CUDA Toolkit не установлен
3. Неправильная версия torch (нужна +cu118 или +cu121)
4. Не установлены зависимости SAM2 (loguru, timm, einops и др.)

**Решение:**
```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```
Должно быть: `2.5.1+cu121 True`

Если проблема с зависимостями:
```bash
cd %USERPROFILE%\.nuke\NukeSamurai
pip install -r requirements.txt
```

### "Frame range error"

- Убедитесь что input frames существуют (1001-1182)
- Output Path должен содержать `####` или `###`

### "OpenCV cannot write EXR"

OpenCV на Windows не поддерживает EXR по умолчанию.

**Решение:**
- Плагин **автоматически** переключится на PNG при выборе EXR
- Вы увидите предупреждение: `WARNING: EXR not supported by OpenCV, using PNG`
- Read нода создастся с правильным PNG путём
- **Рекомендация:** Используйте PNG сразу (идеально для масок)

### Медленная генерация

- Проверьте что используется GPU: `Device: cuda:0`
- Закройте другие GPU-приложения
- Уменьшите модель: Large → Base+ → Small

### Предупреждение "NumPy 1.x cannot be run in NumPy 2.2.6" при запуске Nuke

**Это НЕ проблема плагина!**

- Предупреждение идёт от **самого Nuke** (PySide2/shiboken2)
- Наш плагин использует **subprocess** с отдельным Python
- Worker полностью **изолирован** от NumPy проблем Nuke
- Предупреждение **не влияет** на работу плагина

**Можно игнорировать!** Плагин работает нормально. ✅

---

## 📝 Changelog

### [1.1.0] - 2025-01-21

#### Added
- ✅ **EXR automatic fallback** to PNG when OpenCV doesn't support EXR
- ✅ **Tooltip in UI** explaining file format support
- ✅ **Detailed progress stages** (Loading Model, Reading Frames, Detecting Object, Propagating)
- ✅ **OCIO colorspace support** for Read node (Linear/Utility - Linear - sRGB)
- ✅ **OpenEXR environment variable** support (OPENCV_IO_ENABLE_OPENEXR=1)

#### Fixed
- ✅ **Read node creation context issue** (nuke.thisNode() in executeInMainThread)
- ✅ **EXR fallback path reporting** (worker now sends correct PNG path to Nuke)
- ✅ **Read node frame range** auto-configuration (first/last/origfirst/origlast)
- ✅ **Read node file existence check** before creation
- ✅ **Progress bar accuracy** (correct total_frames calculation)
- ✅ **cv2 import error** on Nuke startup (moved to local import in getBbox)

### [1.0.0] - 2025-01-20

#### Added
- ✅ GPU acceleration через subprocess architecture
- ✅ Automatic Read node creation
- ✅ PNG support (8-bit, OpenCV compatible)
- ✅ Real-time progress bar
- ✅ Clean startup (minimal logs)
- ✅ Auto-detection of CUDA version

#### Fixed
- ✅ PyTorch DLL compatibility with Nuke Python 3.11
- ✅ OpenEXR → PNG conversion (OpenCV limitation on Windows)
- ✅ Frame range calculation (inclusive range)
- ✅ Encoding errors (emoji in Windows console)
- ✅ Config path resolution
- ✅ Model path resolution
- ✅ SAM2 conditional nuke imports

#### Changed
- Default file type: EXR → **PNG**
- Architecture: In-process → **Subprocess**
- init.py: 94 lines → **16 lines**

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Credits

- **Original NukeSamurai**: [Theo-SAMINADIN-td](https://github.com/Theo-SAMINADIN-td/NukeSamurai)
- **SAM 2.1**: [Meta AI Research](https://github.com/facebookresearch/sam2)
- **Windows GPU Adaptation**: Ostrix

---

## 📧 Contact

- **Author**: Ostrix
- **Email**: nfsprostreet2007@mail.ru
- **GitHub**: [Your GitHub Profile]

---

## ⚠️ Disclaimer

This is an unofficial adaptation of NukeSamurai for Windows with GPU support. Use at your own risk.

---

## 🌟 Show Your Support

If this project helped you, please give it a ⭐️!

---

**Made with ❤️ for the Nuke community**
