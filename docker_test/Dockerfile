FROM python:3.12-slim

ARG RELEASE_URL="https://github.com/abhinav054/mate/archive/refs/heads/main.tar.gz"
ARG RELEASE_CACHE_KEY="$RELEASE_URL"

ENV PATH="/opt/mate/bin:${PATH}" \
    MATE_HOME="/opt/mate/app/.mate" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    echo "$RELEASE_CACHE_KEY" > /tmp/mate-release-cache-key; \
    curl -fsSL https://raw.githubusercontent.com/abhinav054/mate/main/scripts/install_mate.sh -o /tmp/install_mate.sh; \
    bash /tmp/install_mate.sh \
      --release-url "$RELEASE_URL" \
      --install-dir /opt/mate/app \
      --bin-dir /opt/mate/bin \
      --api-key test-key \
      --base-url https://api.openai.com/v1 \
      --model gpt-4.1-mini; \
    test -x /opt/mate/bin/mate; \
    /opt/mate/app/.venv/bin/python -c "import agent_terminal"

COPY ["docker_test/docker-entrypoint.sh", "/usr/local/bin/mate-docker-entrypoint"]
RUN chmod +x /usr/local/bin/mate-docker-entrypoint

WORKDIR /workspace

ENTRYPOINT ["mate-docker-entrypoint"]
CMD ["bash", "-lc", "test -x /opt/mate/bin/mate && /opt/mate/app/.venv/bin/python -c 'import agent_terminal' && echo 'Mate tarball install smoke test passed.'"]
