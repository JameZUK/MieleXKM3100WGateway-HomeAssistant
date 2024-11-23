# Use the official Node.js 18 image based on Alpine Linux
FROM node:18-alpine

COPY ["MieleXKM3100WGateway/package.json", "MieleXKM3100WGateway/package-lock.json*", "./"]

# Set environment variables
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV NODE_ENV=production

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install app dependencies
RUN npm install --only=production

# Copy the rest of the application source code
COPY . .

# Expose the port your app runs on (assuming 3000)
EXPOSE 3000

COPY run.sh /
RUN chmod a+x /run.sh

# Start the Node.js application
CMD [ "/run.sh" ]
