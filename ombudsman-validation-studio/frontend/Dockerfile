# Multi-stage build for production
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Install serve to run the built app
RUN npm install -g serve

# Copy built assets from builder stage
COPY --from=builder /app/dist /app/dist

# Copy serve configuration
COPY serve.json /app/serve.json

# Expose port
EXPOSE 3000

# Serve the built app with configuration
CMD ["serve", "-s", "dist", "-l", "3000", "--no-clipboard", "-c", "/app/serve.json"]
