# Use the base image specified in build.json
ARG BUILD_FROM
FROM ${BUILD_FROM}

# Set environment variables
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1

# Install necessary packages
RUN pip install --no-cache-dir flask requests cryptography

# Set the working directory
#WORKDIR /usr/src/app
ENV NODE_ENV=production

# Copy the workout data script
COPY miele_gateway.py /

# Copy the startup script
COPY run.sh /

# Make run.sh executable
RUN chmod a+x /run.sh

# Expose the port
EXPOSE 3000

# Start the application using run.sh
CMD ["/run.sh"]
