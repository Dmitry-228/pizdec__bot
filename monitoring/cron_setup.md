# 📅 Настройка автоматического мониторинга воронки

## 🚀 Автоматический запуск мониторинга

### **1. Настройка cron для ежедневного мониторинга**

Откройте crontab для редактирования:
```bash
crontab -e
```

Добавьте следующие строки:

```bash
# Мониторинг воронки онбординга - каждый день в 11:20 (после отправки сообщений)
20 11 * * * /Users/aleksandrsim/AXIDI/update/axidi_project/monitoring/run_monitoring.sh

# Дополнительный мониторинг в 18:00 для проверки дневной активности
0 18 * * * /Users/aleksandrsim/AXIDI/update/axidi_project/monitoring/run_monitoring.sh
```

### **2. Проверка настроек cron**

Посмотреть текущие настройки:
```bash
crontab -l
```

### **3. Ручной запуск мониторинга**

```bash
# Запуск мониторинга вручную
python monitoring/onboarding_monitor.py

# Или через bash-скрипт
./monitoring/run_monitoring.sh
```

### **4. Просмотр логов мониторинга**

```bash
# Последние записи в логе мониторинга
tail -f logs/monitoring/onboarding_monitor_$(date +%Y%m%d).log

# Лог cron-запусков
tail -f logs/monitoring/monitoring_cron.log

# Все логи мониторинга
ls -la logs/monitoring/
```

### **5. Структура логов**

```
logs/monitoring/
├── onboarding_monitor_YYYYMMDD.log  # Основной лог мониторинга
└── monitoring_cron.log              # Лог cron-запусков
```

### **6. Примеры cron-выражений**

```bash
# Каждый день в 11:20
20 11 * * * /path/to/script.sh

# Каждый час
0 * * * * /path/to/script.sh

# Каждые 30 минут
*/30 * * * * /path/to/script.sh

# Только по будням в 9:00
0 9 * * 1-5 /path/to/script.sh
```

### **7. Мониторинг статистики**

Система автоматически собирает статистику:
- ✅ Количество отправленных сообщений
- ❌ Количество неудачных отправок
- 🔒 Количество заблокированных пользователей
- ⏭️ Количество пропущенных пользователей
- 📊 Процент успешных отправок

### **8. Уведомления админов**

При необходимости можно добавить уведомления в Telegram:
```bash
# Добавить в run_monitoring.sh
curl -s "https://api.telegram.org/bot<BOT_TOKEN>/sendMessage" \
  -d "chat_id=<ADMIN_ID>" \
  -d "text=Мониторинг воронки завершен"
```
