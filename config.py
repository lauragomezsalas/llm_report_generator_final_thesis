import os
from dotenv import load_dotenv
from agent_framework.azure import AzureOpenAIChatClient

load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = (
    os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
    or os.getenv("AZURE_OPENAI_DEPLOYMENT")
)

AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")


def validate_env() -> None:
    required = {
        "AZURE_OPENAI_API_KEY": AZURE_OPENAI_API_KEY,
        "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
        "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
        "SERPER_API_KEY": SERPER_API_KEY,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")


def build_chat_client() -> AzureOpenAIChatClient:
    validate_env()
    return AzureOpenAIChatClient(
        api_key=AZURE_OPENAI_API_KEY,
        endpoint=AZURE_OPENAI_ENDPOINT,
        deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
        api_version=AZURE_OPENAI_API_VERSION,
    )

from openai import AzureOpenAI

GOVERNANCE_AZURE_OPENAI_API_KEY = (
    os.getenv("GOVERNANCE_AZURE_OPENAI_API_KEY") or AZURE_OPENAI_API_KEY
)
GOVERNANCE_AZURE_OPENAI_ENDPOINT = (
    os.getenv("GOVERNANCE_AZURE_OPENAI_ENDPOINT") or AZURE_OPENAI_ENDPOINT
)
GOVERNANCE_AZURE_OPENAI_DEPLOYMENT_NAME = (
    os.getenv("GOVERNANCE_AZURE_OPENAI_DEPLOYMENT_NAME")
    or AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
)
GOVERNANCE_AZURE_OPENAI_API_VERSION = os.getenv(
    "GOVERNANCE_AZURE_OPENAI_API_VERSION",
    AZURE_OPENAI_API_VERSION,
)


def build_governance_client() -> AzureOpenAI:
    validate_env()
    if not GOVERNANCE_AZURE_OPENAI_DEPLOYMENT_NAME:
        raise ValueError("Missing GOVERNANCE_AZURE_OPENAI_DEPLOYMENT_NAME")

    return AzureOpenAI(
        api_key=GOVERNANCE_AZURE_OPENAI_API_KEY,
        azure_endpoint=GOVERNANCE_AZURE_OPENAI_ENDPOINT,
        api_version=GOVERNANCE_AZURE_OPENAI_API_VERSION,
    )
