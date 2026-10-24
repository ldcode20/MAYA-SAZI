"""Start the Maya website on the port the host gives (Render sets PORT; Hugging
Face Spaces uses 7860). One worker: demo rooms live in memory.

Proxy trust is deliberately narrow: uvicorn keeps its default (trust forwarding
headers only from 127.0.0.1), and the rate limits read just the right-most
X-Forwarded-For entry, the one the host's proxy appended (MAYA_TRUST_PROXY=1).
Nothing here trusts every forwarding source."""

import os

import uvicorn

if __name__ == "__main__":
    os.environ.setdefault("MAYA_TRUST_PROXY", "1")
    uvicorn.run("api:app", app_dir="src", host="0.0.0.0", port=int(os.environ.get("PORT", "7860")),
                workers=1, log_level="info")
