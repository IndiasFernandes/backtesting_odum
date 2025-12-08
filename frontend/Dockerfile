FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY frontend/package.json frontend/package-lock.json* ./

# Install dependencies (will be overwritten by volume mount, but ensures they're available)
RUN npm ci || npm install

# Copy frontend code
COPY frontend/ ./

# Expose port
EXPOSE 5173

# Install dependencies and start dev server
# This ensures dependencies are installed even when volume mount overwrites them
CMD sh -c "npm install && npm run dev -- --host 0.0.0.0"

