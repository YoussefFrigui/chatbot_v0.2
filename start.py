#!/usr/bin/env python
"""Quick start script - loads .env and starts the server."""

import os
import sys

# Load .env file if it exists
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    print(f"Loading environment from {env_file}")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key and value and not os.environ.get(key):
                    os.environ[key] = value
                    print(f"  Set {key}")

# Check for required API key
if not os.environ.get("OPENROUTER_API_KEY"):
    print("\n⚠️  WARNING: OPENROUTER_API_KEY not set!")
    print("   Set it in .env or run: $env:OPENROUTER_API_KEY='your-key'")
    print("   Get a free key at: https://openrouter.ai/keys\n")

# Start server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "webapp.server:app",
        host="127.0.0.1",
        port=1111,
        reload=True,
    )