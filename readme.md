# Blog-site 0.0.0.12

## Overview

**Blog-site** is a blogging platform with a modern user experience, featuring dark mode support, user registration, Markdown-based post creation, and image attachments. It includes a commenting system, user profiles with token management, a favorites feature, and an admin panel for content moderation.

## Features

### Core Functionality:

- Light and dark theme support.
- User registration and authentication.
- Markdown-based post creation.
- Image attachments in posts.
- Commenting system for posts.
- Editing and deleting personal posts and comments.
- Viewing and deleting uploaded images in the user profile.
- Adding posts to "Favorites."
- Token expiration and refresh token management.
- All authentication-required routes are secured.
- Protection against XSS and SQL injection.

### Administrative Features:

- Access to all posts and comments.
- Editing and deleting posts and comments, including those created by other users.

## Technology Stack

- **Backend**: Flask
- **Frontend**: Svelte
- **Database**: SQLite
- **Proxying**: Nginx
- **Deployment**: Docker, Docker Compose
- **Authentication**: JWT-based token system

## Deployment with Docker

1. Ensure Docker and Docker Compose are installed.
2. Clone the repository:
   ```sh
   git clone https://github.com/mr9733n/blog-site.git
   cd blog-site
   ```
3. Build and start the containers:
   ```sh
   docker-compose up --build -d
   ```
4. The application will be accessible at `http://localhost:36166`

## Future Plans

### Feature Enhancements:

- User list display in profile.
- User blocking functionality.
- Server-side pagination for posts, comments, and users.
- Profile data editing (name, email, password).
- User-defined post title editing.
- Custom CSS support for user profiles.
- Multi-language support (EN/RU).

### Security Improvements:

- Enhanced database protection.

### Infrastructure:

- Production deployment setup (Docker, Compose, logging, SSL, secure proxy configuration).

### Refactoring:

- Route structure optimization.
- Improved Svelte component architecture.

### Testing:

- Unit tests for core functionality.

## Additional Resources

For a detailed list of planned features and known issues, refer to the [TODO list](https://github.com/mr9733n/blog-site/blob/main/todo.md).

## License

This project is released under the MIT license.

