# cs7ns6groupF
Repo to hold code for CS7NS6 Group F Project

## ipc.py

This module handles inter-process communication (via TCP) and leader election (via Bully algorithm).

It is design to be used by other modules:

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
