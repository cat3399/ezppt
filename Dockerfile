FROM astral/uv:bookworm-slim

RUN apt-get update && \
    apt-get install -y locales && \
    sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales 

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8
ENV PYTHONUTF8=1

WORKDIR /work
COPY . .

RUN uv venv
RUN uv sync
RUN uv run setup.py

EXPOSE 8000
CMD ["uv", "run", "main.py"]

