# Build stage
FROM node:16-alpine AS build
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Create directories and set permissions
RUN mkdir -p public/build && \
    chmod -R 777 public

# Copy source code
COPY . .

# Set permissions again after copying
RUN chmod -R 777 public

# Build the app (for initial loading)
RUN npm run build

# Run stage
FROM node:16-alpine
WORKDIR /app
COPY --from=build /app/ ./
EXPOSE 8080
CMD ["npm", "run", "start"]