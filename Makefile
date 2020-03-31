all: demo

.PHONY: docker-ipc
docker-ipc:
	@docker build -f ipc.Dockerfile -t cs7ns6-groupf-ipc:latest .

.PHONY: demo
demo: docker-ipc demo1

.PHONY: demo1
demo1:
	./demo1.sh
