docker:
	docker build --tag stefapi/docker-mdns-helper:latest --platform linux/amd64 .
	docker push stefapi/docker-mdns-helper:latest
