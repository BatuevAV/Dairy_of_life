-- Миграция БД для добавления AI-функционала и мультиюзера
-- Выполнить в pgAdmin4 для базы dairy_of_life

-- 1. Добавление полей мультиюзера в таблицу users
ALTER TABLE users
ADD COLUMN IF NOT EXISTS is_owner BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_allowed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS allowed_by BIGINT,
ADD COLUMN IF NOT EXISTS ai_requests_today INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS ai_requests_limit INTEGER DEFAULT 30,
ADD COLUMN IF NOT EXISTS last_ai_request TIMESTAMP WITHOUT TIME ZONE;

-- 2. Добавление полей AI-оценки в таблицу day_entries
ALTER TABLE day_entries
ADD COLUMN IF NOT EXISTS food_ai_estimated BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS food_ai_model VARCHAR(50),
ADD COLUMN IF NOT EXISTS food_ai_confidence FLOAT,
ADD COLUMN IF NOT EXISTS food_items_json TEXT;

-- 3. Установка текущего пользователя как owner
UPDATE users
SET is_owner = TRUE, is_allowed = TRUE
WHERE telegram_id = 997743143;

-- 4. Проверка изменений
SELECT 
    telegram_id,
    username,
    is_owner,
    is_allowed,
    ai_requests_today,
    ai_requests_limit
FROM users;

-- 5. Проверка новых полей в day_entries
SELECT 
    id,
    user_id,
    date,
    food_ai_estimated,
    food_ai_model,
    food_ai_confidence
FROM day_entries
LIMIT 5;

COMMIT;
