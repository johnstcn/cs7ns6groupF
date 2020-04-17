# cs7ns6groupF
Repo to hold code for CS7NS6 Group F Project

## What you need to run this

 - Python >= 3.6
 - virtualenv
 - Docker (optional, recommended)
 - Docker-compose (optional, recommended)

If you are unable to use `virtualenv` to create a Python virtual environment for any reason, the requirements for the application are specified in `requirements.txt`.

## Structure
The application's code is contained within the `./booking` folder:
 - File `app.py`  is the main application code.
 - File `views.py` contain the various handlers for HTTP responses within the application.
 - File `operation.py` contains code related to database operations shared across both the frontend application and the Raft middleware.
 - Files`raft-*.py` contains code related to the Raft middleware.
 
 Some other files (`ipc.py`, `multicast.py`, `models.py`) are legacy code and no longer required, but are included for reference. 

## Setup

The below commands will set up a new Python virtual environment and install the required packages:
```shell script
virtualenv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running in Docker (recommended)

It is recommended to use `docker-compose` to run this project.

To run the default setup for the application, simply run:
```shell script
docker-compose -f docker-compose.yml up --build
```

This will perform the following steps:
 - Build the `cs7ns6groupf` container from `./Dockerfile`
 - Create 3 instances of the `cs7ns6groupf` container: `peer0`, `peer1`, and `peer2`, each using different local files for the raft database and SQLite databse.

This will run forever until manually stopped with `Control-C`.

## Demo Scripts
Files `./demo1.sh` and `./demo2.sh` each perform the following:
 - Stand up a cluster of the application using `docker-compose -f docker-compose.demoN.yml up --build`
 - Perform a number of actions on the cluster
 - Query various endpoints of the cluster and display the output.
 
Note: to ensure a clean environment, you may need to remove all of the local data in between demoes. To do this, Run: `sudo rm -f data/*`

The file `./Dockerfile` contains directives to build the `cs7ns6groupf` container with all the dependencies for the application included.
It can be built on its own with the command:
```shell script
docker build -t cs7ns6groupf:latest .
```

## Running without Docker (the hard way)

If you are unable to run Docker for whatever reason, you can instead run the code directly, which requires some initial setup.
To run one instance of the application, first double-check you have performed the above `virtualenv` setup.

Then, run the following command, substituting where appropriate:
 - `DB_PATH`: path to the node's SQLite database
 - `RAFT_STATE_PATH`: path to the node's Raft persistent state
 - `SELF_ID`: node identifier (positive integer)
 - `SELF`: the node identifier, hostname, and port for Raft, separated by a colon. Example: `0:localhost:9000`.
 - `PEERS`: the peers in the node's cluster, specified in the same format as above.

Full example invocation:
```shell script
DB_PATH=./data/0.db RAFT_STATE_PATH=./data/0.json SELF_ID=0 SELF=0:localhost:9000 PEERS='1:localhost:9001 2:localhost:9002' python ./app.py
``` 

Repeat this command multiple times to bring up multiple instances of the application.
