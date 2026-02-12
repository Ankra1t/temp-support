
# Запуск Docker Compose
run_step "docker-compose build" "Запуск Docker Compose"

# 🔹 Запуск приложения (app) первым
run_step "docker compose up -d app" "Запуск контейнера app"

# 🔹 Ждем, пока app будет готов (можно через healthcheck или простой sleep)
echo "⏳ Ждем 10 секунд, чтобы контейнер app полностью стартовал..."
sleep 10

# Обновление зависимостей Composer
run_step "docker compose exec app bash -c 'composer update'" "Обновление зависимостей PHP через Composer"

# Миграции базы данных
run_step "docker compose exec app bash -c 'php artisan migrate'" "Применение миграций базы данных"

# Генерация ключа Laravel
run_step "docker compose exec app bash -c 'php artisan key:generate'" "Генерация ключа приложения Laravel"

# 🔹 Запуск остальных сервисов
run_step "docker compose down" "Отключение сервисов"
run_step "docker compose up -d" "Перезапуск сервисов"