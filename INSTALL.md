# 📥 Детальная инструкция по установке / Detailed Installation Guide

---

## ⚠️ НЕТ папки `python_libs`!

Этот плагин использует **subprocess архитектуру** - torch работает в **отдельном процессе**!  
**НЕ** копируйте библиотеки в папку плагина - это старый подход, который **не работал**.

📖 Подробнее: [README.md - Архитектура](./README.md#-архитектура--architecture)

---

## 🆕 ДЛЯ ТЕСТИРОВЩИКОВ: Пошаговая Инструкция

**Если вы устанавливаете плагин впервые**, используйте максимально подробную инструкцию:

📖 **[INSTALLATION_STEP_BY_STEP.md](./INSTALLATION_STEP_BY_STEP.md)** ← Начните здесь!

Там есть:
- ✅ Точные команды для установки Python 3.10
- ✅ Установка PyTorch с CUDA (с проверками!)
- ✅ Все зависимости с версиями
- ✅ Загрузка моделей SAM 2.1 (прямые ссылки)
- ✅ Настройка Nuke init.py и menu.py
- ✅ Тестовый запуск
- ✅ Решение проблем

---

## 🇷🇺 Русская версия (Краткая)

### Предварительные требования

#### 1. NVIDIA GPU с CUDA
- **Минимум**: GTX 1060 6GB или выше
- **Рекомендуется**: RTX 3060 12GB или выше
- **Оптимально**: RTX 4090 24GB

#### 2. Windows 10/11 64-bit

#### 3. Nuke 16.0v4 или выше

#### 4. 20 GB свободного места на диске

---

### Шаг 1: Установка Python 3.10

1. **Скачайте Python 3.10.11**:
   - https://www.python.org/downloads/release/python-31011/
   - Выберите: "Windows installer (64-bit)"

2. **Запустите установщик**:
   - ✅ **ОБЯЗАТЕЛЬНО отметьте**: "Add Python 3.10 to PATH"
   - ✅ **ОБЯЗАТЕЛЬНО отметьте**: "Install for all users"
   - Нажмите "Install Now"

3. **Проверьте установку**:
   ```cmd
   python --version
   ```
   Должно вывести: `Python 3.10.11`

---

### Шаг 2: Определение версии CUDA

Откройте командную строку и выполните:

```cmd
nvidia-smi
```

Найдите строку:
```
CUDA Version: 12.1
```

**Если CUDA Version:**
- **12.x** → используйте cu121
- **11.x** → используйте cu118

---

### Шаг 3: Установка PyTorch с CUDA

#### Для CUDA 12.1 (RTX 4090, RTX 4080, RTX 4070 и новее):

```cmd
pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 --index-url https://download.pytorch.org/whl/cu121
```

#### Для CUDA 11.8 (RTX 3090, RTX 3080, RTX 3070):

```cmd
pip install torch==2.5.1+cu118 torchvision==0.20.1+cu118 --index-url https://download.pytorch.org/whl/cu118
```

**Проверьте установку**:
```cmd
python -c "import torch; print('torch:', torch.__version__); print('CUDA:', torch.cuda.is_available())"
```

Должно вывести:
```
torch: 2.5.1+cu121
CUDA: True
```

⚠️ **Если CUDA: False** - переустановите PyTorch с правильной версией CUDA!

---

### Шаг 4: Установка зависимостей для System Python

**Автоматически (рекомендуется):**
```cmd
cd %USERPROFILE%\.nuke\NukeSamurai
pip install -r requirements.txt
```

**Или вручную:**
```cmd
pip install numpy opencv-python pillow tqdm hydra-core omegaconf iopath timm einops loguru
```

⚠️ **Важно:** Все зависимости должны быть установлены в system Python, где установлен PyTorch!

**Проверьте**:
```cmd
pip list | findstr "opencv numpy pillow tqdm hydra loguru timm einops"
```

### Шаг 4.5: Установка OpenCV для Nuke Python (для Bounding Box)

⚠️ **КРИТИЧЕСКИ ВАЖНО:** Для работы "Create Bounding Box" нужен opencv-python в **Nuke Python**!

**Откройте CMD/PowerShell как Администратор:**

Для Nuke 16.0v4:
```cmd
"C:\Program Files\Nuke16.0v4\python.exe" -m pip install --force-reinstall opencv-python numpy
```

Для Nuke 15.1:
```cmd
"C:\Program Files\Nuke15.1v5\python.exe" -m pip install --force-reinstall opencv-python numpy
```

💡 **`--force-reinstall`** гарантирует установку именно в Nuke Python!

**Проверка (ВАЖНО!):**
```cmd
"C:\Program Files\Nuke15.1v5\python.exe" -c "import cv2; print('Path:', cv2.__file__)"
```

⚠️ Путь ДОЛЖЕН содержать `Nuke15.1v5\lib\site-packages`, **НЕ** `AppData\Roaming\Python\Python310`!

---

### Шаг 5: Клонирование плагина

```cmd
cd %USERPROFILE%\.nuke
git clone https://github.com/YOUR_USERNAME/NukeSamurai-Windows.git NukeSamurai
cd NukeSamurai
```

---

### Шаг 6: Скачивание моделей SAM 2.1

#### Вариант 1: Через браузер

1. Перейдите: https://github.com/facebookresearch/sam2/releases
2. Скачайте модели:
   - `sam2.1_hiera_base_plus.pt` (рекомендуется, ~314 MB)
   - `sam2.1_hiera_large.pt` (опционально, ~894 MB)
   - `sam2.1_hiera_small.pt` (опционально, ~184 MB)
   - `sam2.1_hiera_tiny.pt` (опционально, ~155 MB)

3. Поместите в:
   ```
   %USERPROFILE%\.nuke\NukeSamurai\sam2_repo\checkpoints\
   ```

#### Вариант 2: Через командную строку

```cmd
cd %USERPROFILE%\.nuke\NukeSamurai\sam2_repo\checkpoints

curl -L -o sam2.1_hiera_base_plus.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt
```

---

### Шаг 7: Настройка Nuke (если плагин не загружается автоматически)

**Nuke автоматически загружает** `init.py` и `menu.py` из всех поддиректорий `.nuke/`.

Но если у вас УЖЕ есть свой `.nuke/init.py` или `.nuke/menu.py`, добавьте туда:

#### В `.nuke/init.py` (создайте, если нет):

```python
# NukeSamurai Plugin
nuke.pluginAddPath('./NukeSamurai')
```

#### В `.nuke/menu.py` (создайте, если нет):

```python
# NukeSamurai Plugin
import nuke
nuke.pluginAddPath('./NukeSamurai')
```

**ИЛИ** просто ничего не делайте - Nuke загрузит плагин автоматически из `NukeSamurai/init.py`!

---

### Шаг 8: Проверка установки

Откройте **Nuke**.

В консоли (F8) должно появиться:
```
[NukeSamurai] Plugin loaded (GPU via subprocess)
```

✅ Если видите это сообщение - установка прошла успешно!

---

### Шаг 9: Первый запуск

1. В Nuke нажмите **Tab**
2. Введите **SAMURAI**
3. Создайте узел

Должен появиться узел SAMURAI с кнопками:
- Update Path
- Create Bounding Box
- Generate Mask

---

## Устранение проблем

### "Plugin not found"

**Проверьте структуру**:
```
%USERPROFILE%\.nuke\
└── NukeSamurai\
    ├── init.py
    ├── menu.py
    ├── scripts\
    │   ├── nuke_samurai.py
    │   ├── sam2_worker.py
    │   └── demo.py
    └── sam2_repo\
        └── checkpoints\
            └── sam2.1_hiera_base_plus.pt
```

### "torch not found"

```cmd
python -c "import torch"
```

Если ошибка - переустановите PyTorch (Шаг 3).

### "CUDA: False"

1. Проверьте NVIDIA драйвера:
   ```cmd
   nvidia-smi
   ```

2. Переустановите PyTorch с правильной версией CUDA.

3. Проверьте CUDA Toolkit:
   ```cmd
   nvcc --version
   ```

---

## 🇬🇧 English Version

### Prerequisites

#### 1. NVIDIA GPU with CUDA
- **Minimum**: GTX 1060 6GB or higher
- **Recommended**: RTX 3060 12GB or higher
- **Optimal**: RTX 4090 24GB

#### 2. Windows 10/11 64-bit

#### 3. Nuke 16.0v4 or higher

#### 4. 20 GB free disk space

---

### Step 1: Install Python 3.10

1. **Download Python 3.10.11**:
   - https://www.python.org/downloads/release/python-31011/
   - Choose: "Windows installer (64-bit)"

2. **Run installer**:
   - ✅ **CHECK**: "Add Python 3.10 to PATH"
   - ✅ **CHECK**: "Install for all users"
   - Click "Install Now"

3. **Verify installation**:
   ```cmd
   python --version
   ```
   Should output: `Python 3.10.11`

---

### Step 2: Determine CUDA Version

Open command prompt and run:

```cmd
nvidia-smi
```

Find line:
```
CUDA Version: 12.1
```

**If CUDA Version:**
- **12.x** → use cu121
- **11.x** → use cu118

---

### Step 3: Install PyTorch with CUDA

#### For CUDA 12.1 (RTX 4090, RTX 4080, RTX 4070 and newer):

```cmd
pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 --index-url https://download.pytorch.org/whl/cu121
```

#### For CUDA 11.8 (RTX 3090, RTX 3080, RTX 3070):

```cmd
pip install torch==2.5.1+cu118 torchvision==0.20.1+cu118 --index-url https://download.pytorch.org/whl/cu118
```

**Verify installation**:
```cmd
python -c "import torch; print('torch:', torch.__version__); print('CUDA:', torch.cuda.is_available())"
```

Should output:
```
torch: 2.5.1+cu121
CUDA: True
```

⚠️ **If CUDA: False** - reinstall PyTorch with correct CUDA version!

---

### Step 4: Install Dependencies

**Automatic (recommended):**
```cmd
cd %USERPROFILE%\.nuke\NukeSamurai
pip install -r requirements.txt
```

**Or manually:**
```cmd
pip install numpy opencv-python pillow tqdm hydra-core omegaconf iopath timm einops loguru
```

⚠️ **Important:** All dependencies must be installed in the same system Python where PyTorch is installed!

**Verify**:
```cmd
pip list | findstr "opencv numpy pillow tqdm hydra loguru timm einops"
```

---

### Step 5: Clone Plugin

```cmd
cd %USERPROFILE%\.nuke
git clone https://github.com/YOUR_USERNAME/NukeSamurai-Windows.git NukeSamurai
cd NukeSamurai
```

---

### Step 6: Download SAM 2.1 Models

#### Option 1: Via Browser

1. Go to: https://github.com/facebookresearch/sam2/releases
2. Download models:
   - `sam2.1_hiera_base_plus.pt` (recommended, ~314 MB)
   - `sam2.1_hiera_large.pt` (optional, ~894 MB)
   - `sam2.1_hiera_small.pt` (optional, ~184 MB)
   - `sam2.1_hiera_tiny.pt` (optional, ~155 MB)

3. Place in:
   ```
   %USERPROFILE%\.nuke\NukeSamurai\sam2_repo\checkpoints\
   ```

#### Option 2: Via Command Line

```cmd
cd %USERPROFILE%\.nuke\NukeSamurai\sam2_repo\checkpoints

curl -L -o sam2.1_hiera_base_plus.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt
```

---

### Step 7: Configure Nuke (if plugin doesn't load automatically)

**Nuke automatically loads** `init.py` and `menu.py` from all subdirectories in `.nuke/`.

But if you ALREADY have your own `.nuke/init.py` or `.nuke/menu.py`, add there:

#### In `.nuke/init.py` (create if doesn't exist):

```python
# NukeSamurai Plugin
nuke.pluginAddPath('./NukeSamurai')
```

#### In `.nuke/menu.py` (create if doesn't exist):

```python
# NukeSamurai Plugin
import nuke
nuke.pluginAddPath('./NukeSamurai')
```

**OR** just do nothing - Nuke will load the plugin automatically from `NukeSamurai/init.py`!

---

### Step 8: Verify Installation

Open **Nuke**.

In console (F8) you should see:
```
[NukeSamurai] Plugin loaded (GPU via subprocess)
```

✅ If you see this message - installation successful!

---

### Step 9: First Run

1. In Nuke press **Tab**
2. Type **SAMURAI**
3. Create node

SAMURAI node should appear with buttons:
- Update Path
- Create Bounding Box
- Generate Mask

---

## Troubleshooting

### "Plugin not found"

**Check structure**:
```
%USERPROFILE%\.nuke\
└── NukeSamurai\
    ├── init.py
    ├── menu.py
    ├── scripts\
    │   ├── nuke_samurai.py
    │   ├── sam2_worker.py
    │   └── demo.py
    └── sam2_repo\
        └── checkpoints\
            └── sam2.1_hiera_base_plus.pt
```

### "torch not found"

```cmd
python -c "import torch"
```

If error - reinstall PyTorch (Step 3).

### "CUDA: False"

1. Check NVIDIA drivers:
   ```cmd
   nvidia-smi
   ```

2. Reinstall PyTorch with correct CUDA version.

3. Check CUDA Toolkit:
   ```cmd
   nvcc --version
   ```

---

✅ **Installation complete! Enjoy GPU-accelerated masking in Nuke!** 🚀

