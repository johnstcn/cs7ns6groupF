#!/usr/bin/env bash
set -euo pipefail

DOCKER_COMPOSE_FILE="docker-compose.demo1.yml"
#TOXCLI=".bin/toxiproxy-cli"
#TOX_VERSION="v2.1.4"
#KERNEL=$(uname -s | tr '[:upper:]' '[:lower:]')
#TOXCLI_URL="https://github.com/Shopify/toxiproxy/releases/download/${TOX_VERSION}/toxiproxy-cli-${KERNEL}-amd64"

#function fetch_toxiproxy {
#    if [ ! -x "${TOXCLI}" ]; then
#        echo "Fetching toxiproxy-cli"
#        mkdir -p ".bin"
#        wget -q "${TOXCLI_URL}" -O $TOXCLI
#    fi
#}

function setup {
    docker-compose -f "${DOCKER_COMPOSE_FILE}" up --build --force-recreate --detach
}

function dump_cluster_state {
  echo "--- cluster state ---"
  for n in $(seq 0 2); do
    echo "node${n} state:"
    echo state | nc localhost $((9000 + n))
  done
}

function dump_raft_disk_state {
  echo "--- raft persistent state ---"
  for n in $(seq 0 2); do
    echo "data/state_$n.json"
    jq < "data/state_$n.json"
  done
}

function dump_room_state {
  echo "--- room $1 booking state ---"
    for n in $(seq 0 2); do
      echo "data/test_$n.db"
      sqlite3 "data/test_$n.db" "select RoomID, RoomState, BookTime from room where RoomID = $1;"
  done
}

function teardown {
    docker-compose -f "${DOCKER_COMPOSE_FILE}" down -t 1
    docker-compose -f "${DOCKER_COMPOSE_FILE}" rm -f
}

function wait_for_user {
  read -p "Press enter to continue"
}

trap teardown EXIT
setup

echo -n "waiting for leader election"
for i in $(seq 0 4); do
  echo -n '.'
  sleep 1
done
echo
dump_cluster_state
dump_raft_disk_state
leader_id=$(echo state | nc localhost 9000 | grep LEADER | awk '{print $2}' | awk -F ':' '{print $1}')
leader_http_port=$((5000+leader_id))
dump_room_state 101
echo "booking state: "
curl "http://localhost:${leader_http_port}/api/bookings" | jq '.'
wait_for_user
echo -n "booking room 101 via localhost:${leader_http_port} -> "
#echo "db 101" | nc localhost "$leader_port"
curl -XPOST "http://localhost:${leader_http_port}/api/bookings" --data "room_id=101"
echo
echo -n "waiting for replication"
for i in $(seq 0 4); do
  echo -n '.'
  sleep 1
done
echo
dump_raft_disk_state
dump_room_state 101
curl "http://localhost:${leader_http_port}/api/bookings" | jq '.'
wait_for_user
echo -n "trying to double-book room 101 via localhost:${leader_http_port} -> "
curl -XPOST "http://localhost:${leader_http_port}/api/bookings" --data "room_id=101"
echo
dump_raft_disk_state
dump_room_state 101
curl "http://localhost:${leader_http_port}/api/bookings" | jq '.'