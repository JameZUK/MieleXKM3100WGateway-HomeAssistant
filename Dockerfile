# Use the official Node.js 18 image based on Alpine Linux
FROM node:18-alpine

# Set environment variables
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    NODE_ENV=production

# Set the working directory inside the container
WORKDIR /app

# Copy application files
COPY . .

# Install app dependencies
RUN npm install --only=production

# Make the startup script executable
RUN chmod +x ./run.sh

# Expose the port
EXPOSE 3000

# Start the application using the startup script
CMD ["./run.sh"]
