# Pull-through image so Railway deploys LiteLLM via `railway up`
# like api/web. The tag is the single source of truth for the
# deployed version: the compose services build from this file too
# instead of naming the image again.
FROM docker.litellm.ai/berriai/litellm:v1.104.0

# Gateway-wide settings (reasoning content merge). Models stay
# DB-managed via STORE_MODEL_IN_DB.
COPY docker/litellm/config.yaml /app/config.yaml
CMD ["--port", "4000", "--config", "/app/config.yaml"]
