# Google Search MCP Server

This repository contains a Model Context Protocol (MCP) server that provides a tool-based interface to Google's Custom Search Engine (CSE) API. It is designed for use with MCP-compatible clients, such as those found in IDEs like Visual Studio Code, allowing developers and models to perform Google searches programmatically.

## Features

-   **Google Search Integration:** Perform Google searches using the CSE API.
-   **Flexible Configuration:** Configure the server via environment variables or a `.env` file.
-   **User-Friendly Tools:** Provides a clear `google_search` tool with support for various search parameters.
-   **Conversational Outputs:** Returns search results in a conversational format, making it easy for clients to use the results.
-   **Standalone and Asynchronous:** The server runs as a standalone script and uses an asynchronous architecture for better performance.

## Prerequisites

Before running the server, you need to have Python 3.12+ and `uv` installed. You will also need a Google API key and a Programmable Search Engine (CSE) ID. You will also need Node.js and `npx` to run the MCP Inspector tool for testing.

## Installation

1.  **Clone the repository.**

```bash
# Use gh cli to clone repository
gh repo clone fvanevski/google_search_mcp

# Use git to clone repository
git clone https://github.com/fvanevski/google_search_mcp.git

# Enter the repository directory
cd google_search_mcp
```

2.  **Create a virtual environment and install the required dependencies:**

```bash
# Create a virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate

# Install the dependencies
uv pip install mcp requests pydantic python-dotenv
```

## Running and Testing the Server

The MCP server is a command-line application that communicates over standard I/O. To use it, a client (like an IDE, a coding agent, or an inspector tool) must launch the server process.

### Running for Diagnostics

You can try to run the script directly from your terminal to see if it starts without errors. This is a quick way to validate your Python environment and the script's basic syntax.

```bash
python google_search_mcp.py
```

However, the server will simply start and wait for input, so you won't be able to interact with it directly from your terminal.

### Testing with MCP Inspector

The recommended way to test the server interactively is with **MCP Inspector**. It runs as a command-line tool and provides an interactive shell for sending requests to your server.

1.  **Launch the Inspector:**
    You can run the inspector without a permanent installation using `npx`. The inspector will launch your MCP server script for you. From your project directory, run:

```bash
# Run the inspector with `uv run --with <dependencies> -- python3 <script>`
npx @modelcontextprotocol/inspector uv run --with requests,python-dotenv,pydantic,mcp -- python3 google_search_mcp.py
```

    Even if you have your virtual environment active, the `python` command as executed by the inspector will not correctly point to the interpreter with the necessary dependencies, thus we use uv instead with the `--with` flag.

2.  **Interact with the Server:**
    Once the inspector starts, you can click the "Connect" button to establish a session with your server. You can then use commands like `list_tools` and `call_tool` to interact with it.

    **Example session:**

```
# List all available tools
> list_tools

# Call the 'google_search' tool with arguments
> call_tool google_search '''{"query": "What is the capital of France?"}'''
```

This provides a reliable way to test all the tools and verify that the server is working as expected.

## Configuration

The server is configured using environment variables or a `.env` file in your project's root directory.

### Environment Variables

-   `GOOGLE_API_KEY`: Your Google API key.
-   `GOOGLE_CSE_ID`: Your Programmable Search Engine (CSE) ID.

**Example `.env` file:**

```
GOOGLE_API_KEY=your-secret-api-key
GOOGLE_CSE_ID=your-cse-id
```

## Usage with an MCP Client (VS Code Example)

You can connect to this server from any standard MCP client. Here’s how to do it in a VS Code environment that supports MCP:

1.  **Configure Your MCP Client:** In your IDE's MCP client settings (e.g., in `mcp.json` for VS Code), configure a new MCP server that points to the script.

    **Example `mcp.json` entry for VS Code:**

    ```json
    {
      "servers": {
        "google_search": {
          "command": "uv",
          "args": [
            "run",
            "--with",
            "requests,python-dotenv,pydantic,mcp",
            "--",
            "python",
            "/path/to/your/project/google_search_mcp.py"
          ]
        }
      }
    }
    ```

    *Note: Replace `/path/to/your/project` with the actual path to the project directory.*

2.  **Use the Tools:** Once connected, you can use the exposed tools in your chat or agent interactions with natural language queries or structured calls. For example, to perform a Google search, you could send the following structured tool call:

    ```json
    {
      "tool": "google_search",
      "arguments": {
        "query": "What is the weather in London?"
      }
    }
    ```

    The server will execute the query and return the search results.