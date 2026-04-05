import os
import logging
import warnings

import dspy
import litellm
from dotenv import load_dotenv

load_dotenv()


def configure_dspy():
    deployment = (
        os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT")
    )
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

    missing = []
    if not deployment:
        missing.append("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME or AZURE_OPENAI_DEPLOYMENT")
    if not api_key:
        missing.append("AZURE_OPENAI_API_KEY")
    if not endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")

    if missing:
        raise ValueError(f"Missing environment variables for DSPy: {', '.join(missing)}")

    # Disable LiteLLM callback-based background logging
    litellm.callbacks = []
    litellm.success_callback = []
    litellm.failure_callback = []

    # Reduce noisy LiteLLM logger output in console
    logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
    logging.getLogger("litellm").setLevel(logging.CRITICAL)
    warnings.filterwarnings("ignore", module="litellm")

    lm = dspy.LM(
        model=f"azure/{deployment}",
        api_key=api_key,
        api_base=endpoint,
        api_version=api_version,
        temperature=0,
    )

    dspy.configure(
        lm=lm,
        track_usage=True,
    )

    return lm