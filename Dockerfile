# Use the official Node.js 18 image based on Alpine Linux
FROM node:18-alpine

# Set environment variables
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    NODE_ENV=production

# Install app dependencies
RUN npm install --only=production

# Expose the port
EXPOSE 3000

# Copy the workout data script
COPY mieleGateway.js /
COPY package.json /

# Copy the startup script
COPY run.sh /

# Make the startup script executable
RUN chmod a+x /run.sh

# Start the application using the startup script
CMD ["/run.sh"]
