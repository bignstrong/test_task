#!/bin/bash

# Скрипт для тестирования API сервиса конфигураций

BASE_URL="http://localhost:8080"
SERVICE_NAME="test_service"

echo "=== Тестирование API сервиса конфигураций ==="
echo "Базовый URL: $BASE_URL"
echo "Сервис: $SERVICE_NAME"
echo

# 1. Загрузка первой конфигурации
echo "1. Загрузка первой конфигурации..."
curl -X POST "$BASE_URL/config/$SERVICE_NAME" \
  -H "Content-Type: application/x-yaml" \
  -d '
version: 1
database:
  host: "localhost"
  port: 5432
features:
  enable_auth: true
  enable_cache: false
' | jq '.'
echo -e "\n"

# 2. Получение актуальной конфигурации
echo "2. Получение актуальной конфигурации..."
curl -s "$BASE_URL/config/$SERVICE_NAME" | jq '.'
echo -e "\n"

# 3. Загрузка конфигурации с шаблоном
echo "3. Загрузка конфигурации с шаблоном..."
curl -X POST "$BASE_URL/config/$SERVICE_NAME" \
  -H "Content-Type: application/x-yaml" \
  -d '
version: 2
database:
  host: "{{ db_host | default(\"localhost\") }}"
  port: 5432
welcome_message: "Hello {{ user }}!"
environment: "{{ env }}"
' | jq '.'
echo -e "\n"

# 4. Получение конфигурации с обработкой шаблона
echo "4. Получение конфигурации с обработкой шаблона..."
curl -s "$BASE_URL/config/$SERVICE_NAME?template=1" \
  -H "Content-Type: application/json" \
  -d '{"db_host": "prod.db.local", "user": "Alice", "env": "production"}' | jq '.'
echo -e "\n"

# 5. Получение конкретной версии
echo "5. Получение версии 1..."
curl -s "$BASE_URL/config/$SERVICE_NAME?version=1" | jq '.'
echo -e "\n"

# 6. Получение истории конфигураций
echo "6. Получение истории конфигураций..."
curl -s "$BASE_URL/config/$SERVICE_NAME/history" | jq '.'
echo -e "\n"

# 7. Попытка загрузки дублирующей версии (должна вернуть ошибку)
echo "7. Попытка загрузки дублирующей версии (ошибка 409)..."
curl -X POST "$BASE_URL/config/$SERVICE_NAME" \
  -H "Content-Type: application/x-yaml" \
  -d '
version: 1
database:
  host: "duplicate.local"
  port: 5432
' | jq '.'
echo -e "\n"

# 8. Попытка получения несуществующего сервиса
echo "8. Попытка получения несуществующего сервиса (ошибка 404)..."
curl -s "$BASE_URL/config/nonexistent_service" | jq '.'
echo -e "\n"

# 9. Попытка загрузки невалидного YAML
echo "9. Попытка загрузки невалидного YAML (ошибка 400)..."
curl -X POST "$BASE_URL/config/$SERVICE_NAME" \
  -H "Content-Type: application/x-yaml" \
  -d '
version: 3
database:
  host: "test.local"
  invalid_yaml: [
  unclosed_bracket
' | jq '.'
echo -e "\n"

# 10. Попытка загрузки конфигурации без обязательных полей
echo "10. Попытка загрузки без обязательных полей (ошибка 422)..."
curl -X POST "$BASE_URL/config/$SERVICE_NAME" \
  -H "Content-Type: application/x-yaml" \
  -d '
# version отсутствует
database:
  host: "test.local"
  # port отсутствует
' | jq '.'
echo -e "\n"

echo "=== Тестирование завершено ==="