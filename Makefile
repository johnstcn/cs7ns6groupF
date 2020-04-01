all: docker demo

.PHONY: docker
docker: docker-ipc

.PHONY: docker-ipc
docker-ipc:
	@docker build -f ipc.Dockerfile -t cs7ns6-groupf-ipc:latest .

.PHONY: demo
demo: demo1 demo2

.PHONY: demo1
demo1:
	./demo1.sh

.PHONY: demo2
demo2:
	./demo2.sh
