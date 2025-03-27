-- Удаление существующих таблиц (если есть)
DROP TABLE IF EXISTS comments;
DROP TABLE IF EXISTS posts;
DROP TABLE IF EXISTS users;

-- Создание таблицы пользователей
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы постов
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES users (id)
);

-- Создание таблицы комментариев
CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    post_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES users (id)
);

-- Индексы для ускорения поиска
CREATE INDEX idx_posts_author ON posts(author_id);
CREATE INDEX idx_comments_post ON comments(post_id);
CREATE INDEX idx_comments_author ON comments(author_id);

-- Вставка тестовых данных (опционально)
-- INSERT INTO users (username, password, email) VALUES
-- ('test', 'pbkdf2:sha256:150000$test', 'test@test.test');

-- INSERT INTO posts (title, content, author_id) VALUES
-- ('Первый пост', 'Содержание первого поста...', 1),
-- ('Второй пост', 'Содержание второго поста...', 1);

-- Add this to schema.sql
CREATE TABLE user_settings (
    user_id INTEGER PRIMARY KEY,
    token_lifetime INTEGER DEFAULT 1800,  -- 30 minutes in seconds
    refresh_token_lifetime INTEGER DEFAULT 1296000; -- 15 дней по умолчанию
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

