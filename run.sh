#!/usr/bin/with-contenv bashio
GROUPID=$(bashio::config 'GROUPID')
GROUPKEY=$(bashio::config 'GROUPKEY')
export GROUP_ID=$GROUPID
export GROUP_KEY=$GROUPKEY
echo "ID: $GROUP_ID"
echo "KEY: $GROUP_KEY"
echo "Starting mileGateway..."
while true
do 
  python3 miele_gateway.py
  sleep 2
  echo "Restarting..."
done
