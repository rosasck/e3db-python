FROM python:3.7-alpine

RUN apk add --no-cache gcc musl-dev libffi-dev make openssl-dev
RUN mkdir -p /src
WORKDIR /src/

RUN pip install -U pytest pytest-cov sphinx flake8 magic-wormhole

COPY e3db/ /src/e3db/
COPY ["README.md", "LICENSE.md", "setup.py", "/src/"]
COPY ["sender.py", "receiver.py", "/src/"]

RUN python setup.py bdist_wheel && \
  pip install --find-links=./dist/ e3db

COPY integration.py /src/integration.py

ENTRYPOINT ["/src/integration.py"]
