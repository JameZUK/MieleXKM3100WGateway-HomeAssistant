# syntax=docker/dockerfile:1
ARG BUILD_FROM
FROM $BUILD_FROM

COPY ["MieleXKM3100WGateway/package.json", "MieleXKM3100WGateway/package-lock.json*", "./"]

RUN \
     apk add --no-cache \
        nodejs=18.17.1-r0 \
        npm=9.6.6-r0\
    \
    && npm install

WORKDIR /app

ENV NODE_ENV=production

EXPOSE 3000/tcp

COPY run.sh /
RUN chmod a+x /run.sh

COPY MieleXKM3100WGateway/mieleGateway.js ./

#CMD [ "node", "mieleGateway.js" ]
CMD [ "/run.sh" ]
