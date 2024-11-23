# Use the official Node.js 18 image based on Alpine Linux
FROM node:18-alpine

COPY ["MieleXKM3100WGateway/package.json", "MieleXKM3100WGateway/package-lock.json*", "./"]

# Set environment variables
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV NODE_ENV=production

# Install app dependencies
RUN npm install --only=production

# Set the working directory inside the container
WORKDIR /app

ENV NODE_ENV=production

# Expose the port your app runs on (assuming 3000)
EXPOSE 3000/tcp

COPY run.sh /
RUN chmod a+x /run.sh

COPY MieleXKM3100WGateway/mieleGateway.js ./

# Start the Node.js application
CMD [ "/run.sh" ]
