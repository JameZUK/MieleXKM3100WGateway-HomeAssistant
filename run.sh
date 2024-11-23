#!/usr/bin/with-contenv bashio
GROUPID=$(bashio::config 'GROUPID')
GROUPKEY=$(bashio::config 'GROUPKEY')
export GROUPID=$GROUPID
export GROUPKEY=$GROUPKEY
echo "ID: $GROUPID"
echo "KEY: $GROUPKEY"
echo "Starting mileGateway..."
while true
do 
  python3 miele_gateway.py
  sleep 2
  echo "Restarting..."
done
