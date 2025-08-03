# Анализ работы генерации видео в боте

## 🎬 Общий процесс генерации видео

### 1. Начальная точка - Главное меню
Пользователь видит главное меню с кнопками:
- 📸 **Генерация фото**
- 🎬 **Генерация видео**
- 👤 **Мой профиль**
- 💰 **Подписка**
- 🆘 **Поддержка**

### 2. Выбор "Генерация видео"
**Кнопка:** `🎬 Генерация видео` → `callback_data: "video_generate_menu"`

**Результат:** Открывается меню видеогенерации с кнопками:
- 🎬 **AI-видео (Kling 2.1)** → `callback_data: "ai_video_v2_1"`
- 🔙 **Главное меню** → `callback_data: "back_to_menu"`

### 3. Выбор модели видео
**Кнопка:** `🎬 AI-видео (Kling 2.1)` → `callback_data: "ai_video_v2_1"`

**Что происходит:**
- Проверка ресурсов пользователя (стоимость: 20 печенек)
- Если ресурсов достаточно → показывается меню выбора стилей
- Если недостаточно → показывается сообщение о пополнении баланса

### 4. Выбор стиля видео
После нажатия на `ai_video_v2_1` показывается клавиатура со стилями:

#### Доступные стили видео:
```
🏃‍♂️ Динамичное действие
🐢 Замедленное движение
🎥 Кинематографический панорамный вид
😊 Выразительная мимика
⏳ Движение объекта
💃 Танцевальная последовательность
🌊 Естественное течение
🏙 Городская атмосфера
✨ Фантастическое движение
📼 Ретро-волна
```

#### Промпты для каждого стиля:
- **🏃‍♂️ Динамичное действие:** "A person performing dynamic action, energetic movement, athletic pose, action sequence, dynamic motion, vibrant energy, active movement, powerful gesture, dynamic pose, energetic action"
- **🐢 Замедленное движение:** "A person in slow motion, graceful movement, elegant motion, smooth transition, gentle movement, flowing motion, serene movement, peaceful motion, calm action, slow graceful pose"
- **🎥 Кинематографический панорамный вид:** "Cinematic panning shot, professional camera movement, smooth camera transition, film-like motion, cinematic quality, professional videography, smooth pan, camera movement, cinematic shot, professional video"
- **😊 Выразительная мимика:** "A person with expressive facial features, emotional expression, animated face, lively expression, dynamic facial movement, expressive eyes, animated features, emotional face, lively eyes, expressive pose"
- **⏳ Движение объекта:** "A person interacting with objects, hand movement, object manipulation, hand gesture, object interaction, manual action, hand motion, object handling, manual movement, hand action"
- **💃 Танцевальная последовательность:** "A person dancing, dance movement, rhythmic motion, dance pose, choreographed movement, dance sequence, rhythmic action, dance gesture, choreographed pose, dance motion"
- **🌊 Естественное течение:** "A person in natural environment, flowing movement, natural motion, organic movement, natural pose, flowing action, natural gesture, organic motion, natural flow, environmental movement"
- **🏙 Городская атмосфера:** "A person in urban setting, city environment, urban atmosphere, street scene, city background, urban pose, street environment, city motion, urban action, street atmosphere"
- **✨ Фантастическое движение:** "A person in fantasy setting, magical movement, fantasy environment, mystical motion, magical pose, fantasy action, mystical movement, magical gesture, fantasy motion, enchanted movement"
- **📼 Ретро-волна:** "A person in retro style, vintage atmosphere, retro aesthetic, nostalgic motion, vintage pose, retro action, nostalgic movement, vintage gesture, retro motion, nostalgic action"

#### Дополнительные опции:
- ✍️ **Свой промпт (вручную)** → `callback_data: "enter_custom_prompt_manual"`
- 🤖 **Свой промпт (Помощник AI)** → `callback_data: "enter_custom_prompt_llama"`
- 🔙 **Назад** → `callback_data: "video_generate_menu"`

### 5. Выбор стиля или ввод промпта

#### А) Выбор готового стиля
**Кнопка:** Любой из стилей → `callback_data: "video_style_{style_key}"`

**Что происходит:**
- Система автоматически подставляет промпт для выбранного стиля
- Пользователю предлагается загрузить фото или пропустить
- Состояние: `VideoStates.AWAITING_VIDEO_PHOTO`

#### Б) Свой промпт вручную
**Кнопка:** `✍️ Свой промпт (вручную)` → `callback_data: "enter_custom_prompt_manual"`

**Что происходит:**
- Пользователь вводит текстовое описание видео
- Состояние: `VideoStates.AWAITING_VIDEO_PROMPT`

#### В) Свой промпт с помощью AI
**Кнопка:** `🤖 Свой промпт (Помощник AI)` → `callback_data: "enter_custom_prompt_llama"`

**Что происходит:**
- AI-помощник помогает составить промпт
- Пользователь может редактировать предложенный промпт

### 6. Загрузка фото (опционально)

#### А) Если пользователь загружает фото:
- Фото сохраняется в папку `generated/{user_id}/`
- Имя файла: `video_photo_{uuid}.jpg`
- Показывается подтверждение с параметрами

#### Б) Если пользователь пропускает фото:
- Команда `/skip`
- Генерация происходит без стартового изображения

### 7. Подтверждение и запуск генерации

**Показывается сообщение с параметрами:**
```
✅ Подтверждение генерации видео

🎬 Модель: AI-видео (Kling 2.1)
📝 Промпт: [описание видео]
📸 Стартовое фото: [есть/нет]
💰 Стоимость: 20 печенек

[Кнопки:]
✅ Подтвердить → callback_data: "confirm_video_generation"
✏️ Изменить промпт → callback_data: "edit_video_prompt"
📷 Изменить фото → callback_data: "edit_video_photo"
🔙 Назад → callback_data: "ai_video_v2_1"
```

### 8. Процесс генерации

#### А) Запуск:
- Создается задача в БД (`video_tasks` таблица)
- Статус: `pending_submission`
- Отправляется уведомление о начале генерации

#### Б) Прогресс:
- Система отправляет уведомления каждые 30-60 секунд
- Примерные сообщения:
  ```
  🎬 Генерация видео в процессе...
  ⏱ Прошло: 2 минуты из ~5 минут
  📊 Статус: Обработка кадров...
  ```

#### В) Завершение:
- Видео сохраняется в `generated/video_{user_id}_{uuid}.mp4`
- Статус обновляется на `completed`
- Пользователь получает готовое видео

## 💰 Стоимость и ресурсы

### Стоимость генерации видео:
- **AI-видео (Kling 2.1):** 20 печенек
- **Длительность:** 3-5 секунд
- **Качество:** Высокое (Kling 2.1 модель)

### Проверка ресурсов:
- Проверяется баланс пользователя перед генерацией
- Если недостаточно печенек → показывается сообщение о пополнении
- Списываются ресурсы только при успешном запуске

## 🔧 Технические детали

### Модель:
- **ID:** `kwaivgi/kling-v2.1`
- **API:** Replicate
- **Стоимость API:** 0.0028 * 5 = 0.014 за генерацию

### Состояния FSM:
- `VideoStates.AWAITING_VIDEO_PROMPT` - ожидание ввода промпта
- `VideoStates.AWAITING_VIDEO_PHOTO` - ожидание загрузки фото
- `VideoStates.AWAITING_VIDEO_CONFIRMATION` - ожидание подтверждения

### База данных:
- Таблица `video_tasks` - хранение задач генерации
- Поля: `user_id`, `video_path`, `status`, `prediction_id`, `model_key`, `style_name`

## 🎯 Пошаговая инструкция для пользователя

### Для создания видео:

1. **Откройте бота** → Главное меню
2. **Нажмите** `🎬 Генерация видео`
3. **Выберите** `🎬 AI-видео (Kling 2.1)`
4. **Выберите стиль** или введите свой промпт:
   - Готовые стили: нажмите на любой стиль
   - Свой промпт: нажмите `✍️ Свой промпт (вручную)`
5. **Загрузите фото** (опционально) или нажмите `/skip`
6. **Подтвердите** параметры и нажмите `✅ Подтвердить`
7. **Дождитесь** завершения генерации (3-5 минут)
8. **Получите** готовое видео

### Для отмены:
- На любом этапе можно нажать `🔙 Назад`
- Или использовать команду `/cancel`

## ⚠️ Возможные проблемы

### Ошибки ресурсов:
- Недостаточно печенек → пополните баланс
- Ошибка модели → попробуйте позже

### Ошибки генерации:
- Слишком длинный промпт → сократите описание
- Неподходящее фото → загрузите другое изображение
- Технические ошибки → обратитесь в поддержку

## 📊 Статистика

### Время генерации:
- **Обычно:** 3-5 минут
- **Максимум:** 10 минут
- **Уведомления:** каждые 30-60 секунд

### Размер файлов:
- **Видео:** 3-5 секунд, высокое качество
- **Формат:** MP4
- **Разрешение:** Зависит от модели

### Ограничения:
- **Длина промпта:** до 500 символов
- **Размер фото:** до 10 МБ
- **Частота генерации:** не более 1 видео в 5 минут
