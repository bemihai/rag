from typing import Any

import streamlit as st
from dotenv import load_dotenv

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from src.utils import logger
from .prompts import SYSTEM_PROMPT, USER_PROMPT
from .exceptions import ModelInternalError

load_dotenv()


def load_base_model(model_provider: str, model_name: str, **kwargs) -> BaseChatModel:
    """
    Loads the base LLM model based on the provider.

    Args:
        model_provider (str): The model provider, e.g., "google", "openai".
        model_name (str): The name of the model to load.
        **kwargs: Additional keyword arguments to pass to the model constructor.

    Returns: An instance of the loaded chat model.
    """
    match model_provider.lower():
        case "google":
            api_key = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else None
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in Streamlit secrets.")
            model = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0.0,
                max_retries=2,
                google_api_key=api_key,
                **kwargs,
            )
            logger.info(f"Loaded Google model successfully: {model_name}")
            return model
        case "openai":
            api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else None
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in Streamlit secrets.")
            model = ChatOpenAI(
                model=model_name,
                temperature=0.0,
                max_retries=2,
                api_key=api_key,
                **kwargs,
            )
            logger.info(f"Loaded OpenAI model successfully: {model_name}")
            return model
        case _:
            raise ValueError(f"Unsupported model provider: {model_provider}")


def invoke_llm(question: str, model: BaseChatModel, human_messages: list) -> str:
    """
    Invoke the LLM model with the provided question and human messages.

    Args:
        question (str): The user's question to be answered by the model.
        model (BaseChatModel): The loaded LLM model instance.
        human_messages (list): A list of tuples containing previous human messages in the format (role, content).

    Returns: The model's answer as a string.
    """
    if human_messages:
        messages = [("system", SYSTEM_PROMPT), *human_messages, ("human", USER_PROMPT)]
        prompt = ChatPromptTemplate.from_messages(messages)
    else:
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT)
        ])

    tagging_chain = prompt | model

    try:
        model_output = tagging_chain.invoke({"question": f"{question}"})
        if hasattr(model_output, "content"):
            return model_output.content
        elif isinstance(model_output, dict) and "content" in model_output:
            return model_output["content"]
        else:
            return str(model_output)
    except Exception as e:
        raise ModelInternalError() from e