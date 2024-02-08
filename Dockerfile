FROM debian:11

WORKDIR /
RUN set -eu && \
	mkdir /code && \
	apt-get update && \
	apt-get upgrade --no-install-recommends -y && \
	apt-get install --no-install-recommends -y build-essential && \
	apt-get install --no-install-recommends -y ca-certificates python3 python3-pip && \
	pip3 install --no-cache-dir requests pymongo && \
	apt-get remove -y build-essential && \
	apt-get autoremove -y
CMD ["python3", "/code/scanner.py"]
