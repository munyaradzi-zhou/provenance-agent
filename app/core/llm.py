"""Shared LLM factory — one place to construct the chat model.

Keeps model choice (`gpt-4o-mini`), temperature, and the key in a single spot so
every agent (supervisor, synthesis, text-to-Cypher) is consistent and swappable.
temperature=0 for reproducible eval.

LLM_PROVIDER=azure_openai uses an Azure OpenAI deployment with Microsoft Entra ID
(DefaultAzureCredential: `az login` locally, a managed identity in Azure): no key.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_openai import AzureChatOpenAI, ChatOpenAI
from pydantic import SecretStr

from app.core.config import get_settings


@lru_cache
def get_llm() -> ChatOpenAI | AzureChatOpenAI:
    s = get_settings()
    if s.llm_provider == "azure_openai":
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider

        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )
        return AzureChatOpenAI(
            azure_endpoint=s.azure_openai_endpoint,
            azure_deployment=s.azure_openai_deployment,
            api_version=s.azure_openai_api_version,
            azure_ad_token_provider=token_provider,
            temperature=0,
        )
    return ChatOpenAI(model=s.llm_model, api_key=SecretStr(s.openai_api_key), temperature=0)
