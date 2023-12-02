# NOTE: Matches default Python version of Ubuntu 22.04
ARG PYTHON_VERSION=3.11.6
ARG POETRY_VERSION=1.6
FROM python:${PYTHON_VERSION} as production

RUN apt-get update  && \
    DEBIAN_FRONTEND=noninteractive  \
    DEBCONF_NONINTERACTIVE_SEEN=true  \
    apt-get install -y  file  \
                        less  \
                        librdkafka-dev  \
                        python3-pip

RUN export POETRY_HOME=/opt/poetry  && \
    export POETRY_VERSION=${POETRY_VERSION}  && \
    curl -sSL https://install.python-poetry.org | python3 -  && \
    install -o root -g root -m 555 /opt/poetry/bin/poetry /usr/local/bin/poetry  && \
    /opt/poetry/bin/poetry completions bash >> /etc/profile.d/poetry.sh

ENV WORKDIR=/opt/boids-utils
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PYTHONPATH=${WORKDIR}/src:/usr/local/lib/python3.11/site-packages

WORKDIR ${WORKDIR}
COPY * ${WORKDIR}/

RUN /opt/poetry/bin/poetry install --only=main

RUN addgroup --gid 1000 python  && \
    adduser  --gid 1000 --uid 1000 python

USER python
RUN mkdir ~/.ssh  && \
    chmod -R a+rwX ~/

CMD ["--verbose"]

# ============================================================================
FROM production as development

USER root

# Add Docker's official GPG key:
RUN apt-get update  && \
    apt-get install -y  ca-certificates  \
                        curl  \
                        gnupg  && \
    install -m 0755 -d /etc/apt/keyrings  && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg  && \
    chmod a+r /etc/apt/keyrings/docker.gpg  && \
    export ARCH=$(dpkg --print-architecture)  && \
    export SIGNED_BY=/etc/apt/keyrings/docker.gpg  && \
    export DOCKER_APT_URL=https://download.docker.com/linux/debian  && \
    set -a; . /etc/os-release  && \
    echo "deb [arch=${ARCH} signed-by=${SIGNED_BY}] ${DOCKER_APT_URL} ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list  && \
    cat /etc/apt/sources.list.d/docker.list  && \
    apt-get update  && \
    apt-get install -y  docker-ce  \
                        docker-ce-cli  \
                        containerd.io  \
                        docker-buildx-plugin  \
                        docker-compose-plugin

RUN usermod --append --groups docker python

# Above, we only installed 'production' dependencies... here, we
# install the remaining dependencies (test, dev, etc.)
RUN /opt/poetry/bin/poetry install

USER python
