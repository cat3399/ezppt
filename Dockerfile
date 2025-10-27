FROM astral/uv:bookworm-slim
WORKDIR /work
COPY . .

RUN uv venv
RUN uv sync
RUN uv run setup.py
RUN rm -rf ~/.cache
EXPOSE 8000
CMD ["uv", "run", "main.py"]
