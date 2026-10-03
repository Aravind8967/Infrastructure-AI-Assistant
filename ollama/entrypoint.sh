#!/bin/sh
set -e

echo "=================================================="
echo "          STARTING OLLAMA SERVICE (inc_ollama)    "
echo "=================================================="

# Start Ollama server in background
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama server daemon to become ready
echo "Waiting for Ollama server daemon to start..."
until ollama list > /dev/null 2>&1; do
    sleep 2
done
echo "Ollama server is up and running!"

# Model 1: gemma3:4b-it-q4_K_M
MODEL_LLM="gemma3:4b-it-q4_K_M"
echo "Checking if model '$MODEL_LLM' is present in ollama_data volume..."
if ollama list | grep -q "gemma3"; then
    echo "✅ Model '$MODEL_LLM' already exists in ollama_data volume. Skipping download."
else
    echo "📥 Model '$MODEL_LLM' NOT found in ollama_data. Downloading model now..."
    ollama pull "$MODEL_LLM"
    echo "✅ Model '$MODEL_LLM' downloaded successfully!"
fi

# Model 2: nomic-embed-text:latest
MODEL_EMBED="nomic-embed-text:latest"
echo "Checking if model '$MODEL_EMBED' is present in ollama_data volume..."
if ollama list | grep -q "nomic-embed-text"; then
    echo "✅ Model '$MODEL_EMBED' already exists in ollama_data volume. Skipping download."
else
    echo "📥 Model '$MODEL_EMBED' NOT found in ollama_data. Downloading model now..."
    ollama pull "$MODEL_EMBED"
    echo "✅ Model '$MODEL_EMBED' downloaded successfully!"
fi

echo "=================================================="
echo "Ollama setup complete! Models ready in ollama_data."
echo "=================================================="

# Keep Ollama server process running in foreground
wait $OLLAMA_PID
