# cs7ns6groupF
Repo to hold code for CS7NS6 Group F Project

## ipc.py

This module handles inter-process communication (via TCP) and leader election (via Bully algorithm).

It is designed to be used by other modules:

```
all_peers = ["10.0.0.1:8000", "10.0.0.2:8000", "10.0.0.3:8000"]
p = ipc.Process(0, all_peers)
p.run() 
```

You can also run `ipc.py` directly for a simple demo:

```bash
./ipc.py --id 0 --peers 10.0.0.1:8000 10.0.0.2:8000 10.0.0.3:8000 &
./ipc.py --id 1 --peers 10.0.0.1:8000 10.0.0.2:8000 10.0.0.3:8000 &
./ipc.py --id 2 --peers 10.0.0.1:8000 10.0.0.2:8000 10.0.0.3:8000 &
# start voting
echo vote | nc 10.0.0.1 8000
# check for a leader
echo ldr? | nc 10.0.0.2 8000
# check health
echo ok? | nc 10.0.0.3 8000
```

A more complete, automated example can also be run via `docker-compose`:

```bash
docker-compose -f docker-compose.demo1.yml up
```

If you have GNU make available, you can also just run `make`.

## sample demo

This is a small demo using `docker-compose` and [toxiproxy](https://github.com/Shopify/toxiproxy) to simulate latency. You can run it via `./demo1.sh`.

This script performs the following:
1. Fetches `toxiproxy-cli` to `.bin/toxiproxy-cli` if not present
2. Brings up `docker-compose.demo1.yml`
3. Sets up the requires toxiproxy ingresses / egresses via `toxiproxy-cli`
4. Triggers a leader election and prints the leader
5. Brings down the `docker-compose` setup

## Combined Flask + IPC [02-04-2020]
- IPC is an instance of class Processor in Flask. 
- Only an instance in /search view
- Still to write full integration
- You can see peers connection and talking when on the /search page
and can see 'ok'/'ack' messages when rooms booked.
