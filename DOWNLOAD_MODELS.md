# 📥 Скачивание моделей SAM 2.1 / Download SAM 2.1 Models

## 🇷🇺 Русская версия

⚠️ **ВАЖНО**: Модели НЕ включены в репозиторий (слишком большие для git).

Вы должны скачать их вручную **ПОСЛЕ** клонирования репозитория.

### Какие модели скачать?

**Рекомендуется для начала**: `sam2.1_hiera_base_plus.pt` (314 MB)

**Все модели**:
- `sam2.1_hiera_base_plus.pt` - **314 MB** (рекомендуется для RTX 4090)
- `sam2.1_hiera_large.pt` - 894 MB (лучшее качество, но медленнее)
- `sam2.1_hiera_small.pt` - 184 MB (быстрее, но хуже качество)
- `sam2.1_hiera_tiny.pt` - 155 MB (самая быстрая, базовое качество)

### Как скачать?

#### Вариант 1: Через браузер

1. Перейдите: https://github.com/facebookresearch/sam2/releases

2. Скачайте нужные модели

3. Поместите в:
   ```
   %USERPROFILE%\.nuke\NukeSamurai\sam2_repo\checkpoints\
   ```

#### Вариант 2: Через командную строку

```cmd
cd %USERPROFILE%\.nuke\NukeSamurai\sam2_repo\checkpoints

:: Base+ (рекомендуется)
curl -L -o sam2.1_hiera_base_plus.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt

:: Large (опционально)
curl -L -o sam2.1_hiera_large.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt

:: Small (опционально)
curl -L -o sam2.1_hiera_small.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_small.pt

:: Tiny (опционально)
curl -L -o sam2.1_hiera_tiny.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt
```

### Проверка установки

После скачивания проверьте:

```cmd
dir %USERPROFILE%\.nuke\NukeSamurai\sam2_repo\checkpoints
```

Должны видеть файлы `.pt`.

---

## 🇬🇧 English Version

⚠️ **IMPORTANT**: Models are NOT included in the repository (too large for git).

You must download them manually **AFTER** cloning the repository.

### Which models to download?

**Recommended for start**: `sam2.1_hiera_base_plus.pt` (314 MB)

**All models**:
- `sam2.1_hiera_base_plus.pt` - **314 MB** (recommended for RTX 4090)
- `sam2.1_hiera_large.pt` - 894 MB (best quality, but slower)
- `sam2.1_hiera_small.pt` - 184 MB (faster, but lower quality)
- `sam2.1_hiera_tiny.pt` - 155 MB (fastest, basic quality)

### How to download?

#### Option 1: Via browser

1. Go to: https://github.com/facebookresearch/sam2/releases

2. Download needed models

3. Place in:
   ```
   %USERPROFILE%\.nuke\NukeSamurai\sam2_repo\checkpoints\
   ```

#### Option 2: Via command line

```cmd
cd %USERPROFILE%\.nuke\NukeSamurai\sam2_repo\checkpoints

:: Base+ (recommended)
curl -L -o sam2.1_hiera_base_plus.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt

:: Large (optional)
curl -L -o sam2.1_hiera_large.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt

:: Small (optional)
curl -L -o sam2.1_hiera_small.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_small.pt

:: Tiny (optional)
curl -L -o sam2.1_hiera_tiny.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt
```

### Verify installation

After downloading, check:

```cmd
dir %USERPROFILE%\.nuke\NukeSamurai\sam2_repo\checkpoints
```

You should see `.pt` files.

