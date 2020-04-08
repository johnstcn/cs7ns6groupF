#!/usr/bin/env bash
set -euo pipefail

DOCKER_COMPOSE_FILE="docker-compose.demo2.yml"
TOXCLI=".bin/toxiproxy-cli"
TOX_VERSION="v2.1.4"
KERNEL=$(uname -s | tr '[:upper:]' '[:lower:]')
TOXCLI_URL="https://github.com/Shopify/toxiproxy/releases/download/${TOX_VERSION}/toxiproxy-cli-${KERNEL}-amd64"

function fetch_toxiproxy {
    if [ ! -x "${TOXCLI}" ]; then
        echo "Fetching toxiproxy-cli"
        mkdir -p ".bin"
        wget -q "${TOXCLI_URL}" -O $TOXCLI
    fi
}

function setup {
    docker-compose -f "${DOCKER_COMPOSE_FILE}" up --detach
}

function teardown {
    echo "--- BEGIN CONTAINER LOGS ---"
    docker-compose -f "${DOCKER_COMPOSE_FILE}" logs -t
    echo "--- END CONTAINER LOGS ---"
    docker-compose -f "${DOCKER_COMPOSE_FILE}" down -t 1
}

trap teardown EXIT
fetch_toxiproxy
setup
# create proxy configurations
$TOXCLI create peer0 -l toxiproxy:19000 -u peer0:9000
$TOXCLI create peer1 -l toxiproxy:19001 -u peer1:9001

# we need to wait for a second
sleep 1

# do a leader election
echo -n "performing leader election: "
echo vote | nc localhost 9000
echo
for i in $(seq 1 10); do
    LDR=$(echo ldr? | nc localhost 9000)
    if [ ! -z "${LDR}" ]; then
        echo "leader: ${LDR}"
        break
    fi
    sleep 1
done