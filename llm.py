import os
from getpass import getpass
from pathlib import Path

from langchain_community.llms.llamacpp import LlamaCpp
from langchain_google_genai import ChatGoogleGenerativeAI


class LlamaCppModel:
    """
    Load a local llm with langchain and llama cpp.
    Models can be downloaded from huggingface, e.g. https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf

    Args:
        model_path: The path to the model file.
        max_tokens: The maximum number of tokens to generate.
        n_ctx: The context length of the model.
        kwargs: Additional keyword arguments to pass to `LLamaCpp`.
    """

    def __init__(self, model_path: str | Path, max_tokens: int = 500, n_ctx: int = 2048, **kwargs):
        self.llm = LlamaCpp(
            model_path=model_path,
            n_gpu_layers=-1,
            max_tokens=max_tokens,
            n_ctx=n_ctx,
            seed=42,
        )

    def invoke(self, prompt: str):
        """Invoke the model with a prompt."""
        return self.llm.invoke(prompt)


class GeminiModel:
    """
    Load a Google AI model with langchain.

    Args:
        model_name: The name of the model to load.
        max_tokens: The maximum number of tokens to generate.
        kwargs: Additional keyword arguments to pass to `ChatGoogleGenerativeAI`.
    """

    def __init__(self, model_name: str = "gemini-2.0-flash", max_tokens: int = 500, **kwargs):
        if "GOOGLE_API_KEY" not in os.environ:
            os.environ["GOOGLE_API_KEY"] = getpass("To use Gemini, enter your Google AI API key: ")

        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            max_retries=2,
            max_tokens=max_tokens,
            **kwargs,
        )

    def invoke(self, prompt: str):
        """Invoke the model with a prompt."""
        return self.llm.invoke(prompt).content