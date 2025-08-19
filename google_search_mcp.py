# google_search_mcp.py
"""
MCP server exposing a Google Programmable Search (CSE) tool.

This version has been refactored to run as a standalone command-line
script that communicates over standard input/output (stdio).

Environment:
  - GOOGLE_API_KEY: Google API key
  - GOOGLE_CSE_ID:  Programmable Search Engine (cx) ID

Run:
  python3 google_search_mcp.py
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict, List, Literal, Tuple

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr
from requests.exceptions import RequestException

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from mcp.types import (
    ErrorData,
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
    INTERNAL_ERROR,
    INVALID_PARAMS,
)

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Load environment variables from .env file
load_dotenv()


# --- Configuration Model ---
class GoogleApiConfig(BaseModel):
    """Configuration for the Google API."""

    api_key: SecretStr = Field(..., description="Google API Key.")
    cse_id: str = Field(..., description="Programmable Search Engine (cx) ID.")

    @classmethod
    def from_env(cls) -> "GoogleApiConfig":
        """Loads configuration from environment variables."""
        api_key = os.getenv("GOOGLE_API_KEY")
        cse_id = os.getenv("GOOGLE_CSE_ID")
        if not api_key or not cse_id:
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS,
                    message="Missing GOOGLE_API_KEY or GOOGLE_CSE_ID.",
                )
            )
        return cls(api_key=SecretStr(api_key), cse_id=cse_id)


# --- Pydantic Model for Tool Input ---
class GoogleSearchInput(BaseModel):
    """Input model for the google_search tool."""

    query: str = Field(..., description="The search query.")
    num: int = Field(
        default=10, ge=1, le=10, description="Number of results to return (1-10)."
    )
    start: int = Field(
        default=1,
        ge=1,
        description="The starting index of the results (1-based). For example, `&start=11` would start at the 11th result.",
    )
    dateRestrict: str | None = Field(
        default=None,
        description="Restricts results to a time period. Format: `d[number]`, `w[number]`, `m[number]`, `y[number]` (days, weeks, months, years). Example: `d7` for the last 7 days.",
    )
    siteSearch: str | None = Field(
        default=None,
        description="Restricts results to a specific site. Example: `wikipedia.org`.",
    )
    siteSearchFilter: Literal["e", "i"] | None = Field(
        default=None,
        description="Whether to include (`i`) or exclude (`e`) results from the `siteSearch` domain.",
    )
    exactTerms: str | None = Field(
        default=None,
        description="A phrase that all search results must contain. Example: `"climate change"`"
    )
    excludeTerms: str | None = Field(
        default=None,
        description="A word or phrase that should not appear in any search results. Example: `politics`"
    )
    fileType: str | None = Field(
        default=None, description="Restricts results to files of a specific extension. Example: `pdf`"
    )
    gl: str | None = Field(
        default=None,
        description="Geolocation of the end user. A two-letter country code. Example: `us` for United States.",
    )
    lr: str | None = Field(
        default=None,
        description="Restricts the search to documents written in a particular language. Example: `lang_en` for English.",
    )
    safe: Literal["active", "off"] | None = Field(
        default="active", description="Search safety level. `active` or `off`."
    )
    searchType: Literal["image"] | None = Field(
        default=None, description="Specifies the search type. Set to `image` for image search."
    )


# --- API Interaction ---
def _make_api_call(
    config: GoogleApiConfig,
    params: dict,
) -> requests.Response:
    """Makes the API call to the Google Custom Search API."""
    api_url = "https://www.googleapis.com/customsearch/v1"
    api_params = {
        "key": config.api_key.get_secret_value(),
        "cx": config.cse_id,
        **params,
    }
    try:
        response = requests.get(api_url, params=api_params, timeout=15)
        response.raise_for_status()
        return response
    except RequestException as e:
        logging.error(f"Google API request failed: {e}")
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Transport error: {e}")
        )


def _parse_api_response(
    response: requests.Response,
) -> Tuple[List[Dict[str, str]], str]:
    """Parses the JSON response from the API."""
    data = response.json()
    items = data.get("items") or []
    if not items:
        return [], "No results found."

    results = [
        {
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        }
        for item in items
    ]
    return results, f"Found {len(results)} results."


def perform_google_search(
    config: GoogleApiConfig,
    args: GoogleSearchInput,
) -> Tuple[List[Dict[str, str]], str]:
    """The actual logic for performing a Google search."""
    logging.info(f"Executing google_search with query: '{args.query}'")
    params = args.model_dump(exclude_none=True)
    params["q"] = args.query

    try:
        response = _make_api_call(config, params)
        return _parse_api_response(response)
    except Exception as e:
        logging.error(
            f"An unexpected error occurred during search: {e}", exc_info=True
        )
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Unexpected error: {e}")
        )


# --- MCP Server Implementation ---
async def serve():
    """Sets up and runs the MCP server using stdio."""
    try:
        config = GoogleApiConfig.from_env()
    except McpError as e:
        logging.error(f"Configuration error: {e.message}")
        return

    server = Server("google_cse")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="google_search",
                description=(
                    "Performs a Google Programmable Search (CSE) query with fine-grained control over search parameters. "
                    "Returns a list of results with titles, links, and snippets. Examples:\n"
                    "- Search for recent news about AI: `google_search(query='AI news', dateRestrict='d7')`\n"
                    "- Find PDF documents about machine learning on .gov sites: `google_search(query='machine learning', siteSearch='gov', fileType='pdf')`\n"
                    "- Search for images of cats: `google_search(query='cats', searchType='image')`"
                ),
                inputSchema=GoogleSearchInput.model_json_schema(),
            )
        ]

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return [
            Prompt(
                name="Web Search",
                description=(
                    "Answers questions and finds information using Google Search. "
                    "Refine searches with `dateRestrict` (e.g., 'd7' for last 7 days) "
                    "and `siteSearch` (e.g., 'site:wikipedia.org')."
                ),
                arguments=[
                    PromptArgument(
                        name="query", description="The search query", required=True
                    )
                ],
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name != "google_search":
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message=f"Unknown tool: {name}")
            )
        try:
            args = GoogleSearchInput(**arguments)
        except ValueError as e:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

        results, summary = perform_google_search(config, args)
        formatted_results = "\n\n".join(
            f"Title: {r['title']}\nLink: {r['link']}\nSnippet: {r['snippet']}"
            for r in results
        )
        return [
            TextContent(type="text", text=f"{summary}\n\n{formatted_results}")
        ]

    @server.get_prompt()
    async def get_prompt(
        name: str,
        arguments: dict | None,
    ) -> GetPromptResult:
        if name != "Web Search":
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message=f"Unknown prompt: {name}")
            )
        if not arguments or "query" not in arguments:
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS, message="Query is required for Web Search"
                )
            )

        query = arguments["query"]
        args = GoogleSearchInput(query=query)

        try:
            results, summary = perform_google_search(config, args)
            content = "\n\n".join(
                f"Title: {r['title']}\nLink: {r['link']}\nSnippet: {r['snippet']}"
                for r in results
            )
            return GetPromptResult(
                description=summary,
                messages=[
                    PromptMessage(
                        role="user", content=TextContent(type="text", text=content)
                    )
                ],
            )
        except McpError as e:
            return GetPromptResult(
                description=f"Failed to search for '{query}'",
                messages=[
                    PromptMessage(
                        role="user", content=TextContent(type="text", text=str(e))
                    )
                ],
            )

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)


if __name__ == "__main__":
    asyncio.run(serve())
