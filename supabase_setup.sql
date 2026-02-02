-- Создание таблицы для хранения JSON данных (имитация файловой системы)
CREATE TABLE IF NOT EXISTS json_storage (
    key TEXT PRIMARY KEY,
    data JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Вставка начальных пустых значений, если их нет
INSERT INTO json_storage (key, data) VALUES 
('users', '{}'),
('links', '{}'),
('transactions', '[]'),
('promocodes', '{}'),
('domains', '{}')
ON CONFLICT (key) DO NOTHING;

-- Функция для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = now(); 
   RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_json_storage_modtime BEFORE UPDATE
ON json_storage FOR EACH ROW EXECUTE PROCEDURE  update_updated_at_column();
