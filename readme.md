# Configuration Management Service

Сервис управления конфигурациями для распределённых сервисов, реализованный с использованием Python, Twisted, PostgreSQL и Docker.

## Возможности

- **REST API** для управления конфигурациями сервисов
- **Версионирование** конфигураций с автоматическим инкрементом
- **Валидация** YAML конфигураций с проверкой обязательных полей
- **Шаблонизация** с использованием Jinja2
- **История изменений** для каждого сервиса
- **Асинхронная обработка** запросов с Twisted
- **PostgreSQL** для надежного хранения данных

## Архитектура

```
src/
├── main.py                 # Точка входа приложения
├── api/                    # REST API
│   ├── server.py          # Веб-сервер и маршрутизация
│   └── handlers.py        # Обработчики HTTP запросов
├── database/              # Работа с базой данных
│   └── connection.py      # Менеджер подключений PostgreSQL
└── models/                # Модели данных и валидация
    └── configuration.py   # Валидация и обработка конфигураций
```

## Быстрый старт

### Требования

- Docker и docker-compose
- Порты 8080 (API) и 5432 (PostgreSQL) должны быть свободны

### Запуск

1. Склонируйте проект и перейдите в директорию
2. Запустите сервисы:

```bash
docker-compose up --build
```

3. Сервис будет доступен по адресу `http://localhost:8080`

## API Документация

### 1. Загрузка конфигурации

**POST** `/config/{service}`

Загружает новую конфигурацию для сервиса.

**Пример запроса:**

```bash
curl -X POST http://localhost:8080/config/my_service \
  -H "Content-Type: application/x-yaml" \
  -d '
version: 1
database:
  host: "db.local"
  port: 5432
features:
  enable_auth: true
  enable_cache: false
'
```

**Для Windows PowerShell:**

```powershell
curl.exe -X POST http://localhost:8080/config/my_service `
  -H "Content-Type: application/x-yaml" `
  -d @"
version: 1
database:
  host: "db.local"
  port: 5432
features:
  enable_auth: true
  enable_cache: false
"@
```

**Пример ответа:**

```json
{
	"service": "my_service",
	"version": 1,
	"status": "saved"
}
```

### 2. Получение конфигурации

**GET** `/config/{service}[?version=N&template=1]`

Получает актуальную или конкретную версию конфигурации.

**Параметры:**

- `version` (необязательный) - номер версии конфигурации
- `template` (необязательный) - обработка через Jinja2 (значение: 1)

**Примеры запросов:**

```bash
# Получить последнюю версию
curl http://localhost:8080/config/my_service

# Получить конкретную версию
curl http://localhost:8080/config/my_service?version=1

# Получить с обработкой шаблона
curl http://localhost:8080/config/my_service?template=1
```

### 3. История конфигураций

**GET** `/config/{service}/history`

Получает историю версий конфигураций для сервиса.

**Пример запроса:**

```bash
curl http://localhost:8080/config/my_service/history
```

**Пример ответа:**

```json
[
	{
		"version": 3,
		"created_at": "2025-08-19T13:00:00"
	},
	{
		"version": 2,
		"created_at": "2025-08-19T12:15:00"
	},
	{
		"version": 1,
		"created_at": "2025-08-19T12:00:00"
	}
]
```

## Валидация конфигураций

Сервис проверяет наличие обязательных полей:

- `version` (integer)
- `database.host` (string)
- `database.port` (integer)

## Шаблонизация Jinja2

При использовании параметра `?template=1` конфигурации обрабатываются через Jinja2.

**Пример шаблона:**

```yaml
version: 2
welcome_message: 'Hello {{ user }}!'
database:
  host: "{{ db_host | default('localhost') }}"
```

Переменные шаблона можно передать в теле запроса в формате JSON:

```bash
curl "http://localhost:8080/config/my_service?template=1" \

```

**Для Windows PowerShell:**

```powershell
# Вариант 1: Используя Invoke-WebRequest (нативный PowerShell)
Invoke-WebRequest -Uri "http://localhost:8080/config/my_service?template=1&user=Alice&db_host=prod.db.local" `
  -Method GET

# Вариант 2: Используя curl.exe (если установлен)
curl.exe "http://localhost:8080/config/my_service?template=1&user=Alice&db_host=prod.db.local"
```

**Для Windows Command Prompt:**

```cmd
curl.exe "http://localhost:8080/config/my_service?template=1&user=Alice&db_host=prod.db.local"
```

````

## Структура базы данных

```sql
CREATE TABLE configurations (
    id SERIAL PRIMARY KEY,
    service TEXT NOT NULL,
    version INTEGER NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(service, version)
);
````

## Тестирование

Запуск тестов:

```bash
# Внутри контейнера приложения
docker-compose exec app pytest

# Или локально (если установлены зависимости)
pytest tests/
```

## Коды ошибок

- **400 Bad Request** - Невалидный YAML или неверные параметры
- **404 Not Found** - Сервис или версия не найдены
- **409 Conflict** - Версия уже существует
- **422 Unprocessable Entity** - Не прошла валидация конфигурации
- **500 Internal Server Error** - Внутренняя ошибка сервера

## Примеры использования

### Полный цикл работы с конфигурацией

```bash
# 1. Загрузить первую конфигурацию
curl -X POST http://localhost:8080/config/web_service \
  -H "Content-Type: application/x-yaml" \
  -d '
version: 1
database:
  host: "localhost"
  port: 5432
features:
  enable_auth: true
'

# 2. Получить конфигурацию
curl http://localhost:8080/config/web_service

# 3. Загрузить новую версию с шаблоном
curl -X POST http://localhost:8080/config/web_service \
  -H "Content-Type: application/x-yaml" \
  -d '
version: 2
database:
  host: "{{ db_host }}"
  port: 5432
welcome_message: "Hello {{ user }}!"
'

# 4. Получить с обработкой шаблона
curl "http://localhost:8080/config/web_service?template=1" \
  -H "Content-Type: application/json" \
  -d '{"db_host": "prod.db.com", "user": "Admin"}'

# 5. Посмотреть историю
curl http://localhost:8080/config/web_service/history
```

## Разработка

### Структура проекта

- Код организован по модулям (API, Database, Models)
- Используется типизация Python
- Асинхронная обработка с Twisted
- Тесты с pytest и pytest-twisted

### Расширение функциональности

- Добавление новых валидаторов в `models/configuration.py`
- Расширение API через `api/handlers.py`
- Модификация схемы БД через `init.sql`
