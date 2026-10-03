FROM ollama/ollama:latest

# Install curl and ca-certificates for healthcheck and model pulling
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy entrypoint script that conditionally downloads gemma3 and nomic-embed-text models
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose Ollama default port
EXPOSE 11434

ENTRYPOINT ["/entrypoint.sh"]
