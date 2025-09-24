import os
from getpass import getpass
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate

from src.utils import logger
from .prompts import SYSTEM_PROMPT, USER_PROMPT
from .exceptions import ModelInternalError

load_dotenv()


def load_google_ai_model(model_name: str, **kwargs) -> ChatGoogleGenerativeAI:
    """Instantiates a Google Gen AI language model."""

    if "GOOGLE_API_KEY" not in os.environ:
        os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter the Google AI API key: ")

    model = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.0,
        max_retries=2,
        google_api_key=os.environ["GOOGLE_API_KEY"],
        **kwargs,
    )
    logger.info(f"Loaded model successfully: {model_name}")

    return model


def run_llm(
        question: str,
        model: ChatGoogleGenerativeAI,
        human_messages: list,
) -> str:
    """
    Run model.
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
        # Extract the textual answer from the model output
        if hasattr(model_output, "content"):
            return model_output.content
        elif isinstance(model_output, dict) and "content" in model_output:
            return model_output["content"]
        else:
            return str(model_output)
    except Exception as e:
        raise ModelInternalError() from e