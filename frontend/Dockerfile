FROM node:20-alpine
WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Start the development server instead of preview
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"] 