# Use the base image specified in build.json
ARG BUILD_FROM
FROM ${BUILD_FROM}

# Set environment variables
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    NODE_ENV=production

# Install necessary packages (if any)
# For Node.js base images, Node.js and npm are pre-installed

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install app dependencies using npm ci for a clean install
RUN npm ci --only=production

# Copy the rest of the application source code
COPY . .

# Copy the run.sh script to the root directory
COPY run.sh /run.sh

# Make the run.sh script executable
RUN chmod +x /run.sh

# Expose the port your app runs on (assuming 3000)
EXPOSE 3000

# Start the application using run.sh
CMD ["/run.sh"]
