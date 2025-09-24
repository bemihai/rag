import base64

import pandas as pd
import streamlit as st
from google.api_core.exceptions import InternalServerError

from helper import NO_DATA_ANSWERS
from model.llm import run_llm
from utils import logger


def process_user_prompt(model, prompt: str, human_messages: list) -> dict:
    """Process a user prompt"""
    content = {"initial": False}
    error_msg = "Can't generate an answer, please try again."

    # Generate the query and schema used
    try:
        query = run_llm(prompt, model, human_messages)
        logger.info(f"Query generated for prompt: '{prompt}'")
        logger.info(f"Query: {query}")
    except Exception as err:
        query = None
        error_msg = err.default_answer

    content["query"] = query
    return content


def load_local_img(pth: str) -> str:
    """Load a local image to display."""
    file_ = open(pth, "rb")
    contents = file_.read()
    data_url = base64.b64encode(contents).decode("utf-8")
    file_.close()
    return data_url


def format_user_message(message: dict) -> str:
    """Format a user message"""
    message_text = message["question"]
    data_url = load_local_img("src/ui/img/human.jpg")
    return f"""
    <div style="display:flex; align-items:flex-start; justify-content:flex-end; margin:0; padding:0; margin-bottom:10px;">
        <div style="background:#006AFF; color:white; border-radius:20px; padding:10px; margin-right:5px; max-width:75%; margin:0; line-height:1.2; word-wrap:break-word;">
            {message_text}
        </div>
        <img src="data:image/gif;base64,{data_url}" class="user-avatar" alt="avatar" style="width:40px; height:40px; margin:0;" />
    </div>
    """


def format_assistant_message(message: dict) -> str:
    """Format a assistant message"""
    message_text = message["answer"]
    data_url = load_local_img("src/ui/img/bot.png")
    return f"""
    <div style="display:flex; align-items:flex-start; justify-content:flex-start; margin:0; padding:0; margin-bottom:10px;">
        <img src="data:image/gif;base64,{data_url}" class="bot-avatar" alt="avatar" style="width:30px; height:30px; margin:0; margin-right:5px; margin-top:5px;" />
        <div style="background:#71797E; color:white; border-radius:20px; padding:10px; margin-left:5px; max-width:75%; font-size:14px; margin:0; line-height:1.2; word-wrap:break-word;">
            {message_text}
        </div>
    </div>
    """


def display_message(message: dict):
    """Display a message in the UI."""

    if message["role"] == "human":
        container_html = format_user_message(message)
        st.markdown(container_html, unsafe_allow_html=True)

    if message["role"] == "ai":
        container_html = format_assistant_message(message)
        st.write(container_html, unsafe_allow_html=True)


