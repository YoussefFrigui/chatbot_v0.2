from setuptools import setup, find_packages

setup(
    name="activiity-chatbot",
    version="0.2.0",
    description="Conversational RAG agent over the Activiity knowledge base",
    python_requires=">=3.10",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.115",
        "uvicorn>=0.30",
        "httpx>=0.27",
        "pydantic>=2.13",
        "llama-index-core>=0.14",
        "llama-index-llms-openrouter>=0.5",
        "llama-index-embeddings-openai>=0.6",
        "llama-index-embeddings-ollama>=0.4",
        "llama-index-vector-stores-qdrant>=0.10",
        "qdrant-client>=1.17",
        "datasets>=3.0",
        "ragas>=0.2",
        "langchain-openai>=0.2",
        "langchain-community>=0.3",
        "langchain-google-genai>=2.0",
    ],
    entry_points={
        "console_scripts": [
            "activiity-chatbot=chatbot.cli:main",
        ],
    },
)