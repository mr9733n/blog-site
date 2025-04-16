# Blog-site 0.0.1.8

1. Базовые улучшения безопасности
- [x] Улучшить защиту от XSS в функции renderMarkdown
- [x] Улучшить валидацию пользовательского ввода в компонентах форм
- [x] Систематизировать добавление CSRF-токенов
2. Исправление производительности
- [x] Оптимизировать DOM-манипуляции в BlogPost.svelte
- [ ] Устранить повторяющиеся API-запросы
3. Улучшение архитектуры
- [x] Выделить общие функции форматирования в утилиты
- [x] Разделить компоненты на презентационные и контейнеры
- [x] Устранить дублирование кода загрузки изображений
4. Улучшение UX
- [ ] Добавить более информативные сообщения об ошибках
- [ ] Улучшить индикаторы загрузки для асинхронных операций

## Bugs:
- [x] Fix profile theme: night mode is not applied.
- [x] Fix input styling in night mode.
- [x] Fix styles in the CreatePost module.
- [x] Fix redirect and error message for failed image uploads.
- [x] Fix check token on post and upload
- [x] Check token on open Create Post
- [x] Fix inactive state visibility in Admin-post tab link (Admin-panel).
- [ ] Fix production deployment setup.
- [ ] ...

## Features:
- [x] Add a new screen in Profile: "Admin-users" (rename appropriately) for user list management.
- [x] Create a new route and model for managing users.
- [x] Add a new route and model for blocking users.
- [x] Update the image list screen to allow navigation from the user list.
- [x] Allow users to edit their profile data (name, email, password).
- [x] Allow users to edit their posts.
- [ ] Enhance Markdown renderer to support text justification
- [ ] Implement server-side pagination.
- [ ] Add lazy loading on the frontend with server pagination.
- [ ] Enable lazy load pagination for posts, comments, users, and images.
- [ ] Add support for custom CSS in user profiles.
- [ ] Implement multilingual title switching (EN/RU).
- [ ] Улучшить систему локализации
- [ ] ...

## Security:
- [ ] Enhance database security.
- [ ] Implement additional security measures.
- [ ] ...

## Infrastructure:
- [ ] Document production deployment (Docker, Compose, logs, SSL, secure proxy configuration).
- [ ] ...

## Refactoring:
- [x] Optimize route structure.
- [ ] Improve Svelte module organization.
- [ ] Рассмотреть переход на TypeScript
- [ ] ...

## Tests:
- [ ] Add automated tests for core functionality.
- [ ] Добавить юнит-тесты для критической логики
- [ ] ...

---
