# 🚀 Быстрая настройка для Nuke / Quick Setup for Nuke

## 🇷🇺 Русская версия

### Nuke загружает плагин автоматически! 👍

Если вы скопировали плагин в `%USERPROFILE%\.nuke\NukeSamurai\`, то **ничего дополнительно делать не нужно**!

Nuke автоматически загружает `init.py` и `menu.py` из всех подпапок `.nuke/`.

---

### Но если плагин НЕ загрузился...

#### Вариант 1: У вас УЖЕ есть `.nuke/init.py`

Откройте файл `%USERPROFILE%\.nuke\init.py` и добавьте в конец:

```python
# ============================================
# NukeSamurai Plugin
# ============================================
nuke.pluginAddPath('./NukeSamurai')
```

#### Вариант 2: У вас НЕТ `.nuke/init.py`

Создайте файл `%USERPROFILE%\.nuke\init.py` с содержимым:

```python
import nuke

# ============================================
# NukeSamurai Plugin
# ============================================
nuke.pluginAddPath('./NukeSamurai')
```

---

### Проверка

1. Перезапустите Nuke
2. Откройте консоль (F8)
3. Вы должны увидеть:

```
[NukeSamurai] Plugin loaded (GPU via subprocess)
```

✅ Если видите это - всё работает!

---

### Использование

1. Нажмите **Tab**
2. Введите **SAMURAI**
3. Создайте узел

Готово! 🎉

---

## 🇬🇧 English Version

### Nuke loads plugin automatically! 👍

If you copied plugin to `%USERPROFILE%\.nuke\NukeSamurai\`, then **no additional setup needed**!

Nuke automatically loads `init.py` and `menu.py` from all subdirectories in `.nuke/`.

---

### But if plugin did NOT load...

#### Option 1: You ALREADY have `.nuke/init.py`

Open file `%USERPROFILE%\.nuke\init.py` and add to the end:

```python
# ============================================
# NukeSamurai Plugin
# ============================================
nuke.pluginAddPath('./NukeSamurai')
```

#### Option 2: You DON'T have `.nuke/init.py`

Create file `%USERPROFILE%\.nuke\init.py` with content:

```python
import nuke

# ============================================
# NukeSamurai Plugin
# ============================================
nuke.pluginAddPath('./NukeSamurai')
```

---

### Verification

1. Restart Nuke
2. Open console (F8)
3. You should see:

```
[NukeSamurai] Plugin loaded (GPU via subprocess)
```

✅ If you see this - it works!

---

### Usage

1. Press **Tab**
2. Type **SAMURAI**
3. Create node

Done! 🎉

