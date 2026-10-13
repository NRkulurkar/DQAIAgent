import os
import re
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from synapse import get_columns

load_dotenv()


def call_agent(name: str, version: str, message: str) -> str:
    """Send one message to a Foundry agent and return its text reply."""
    project = AIProjectClient(
        endpoint=os.getenv("FOUNDRY_ENDPOINT"),
        credential=DefaultAzureCredential(),
    )
    openai_client = project.get_openai_client()
    response = openai_client.responses.create(
        input=[{"role": "user", "content": message}],
        extra_body={"agent_reference": {"name": name, "version": version, "type": "agent_reference"}},
        timeout=150,
    )
    return response.output_text


def extract_code_block(text: str) -> str:
    """Pull the content out of the first ``` code block in the reply."""
    match = re.search(r"```[a-zA-Z]*\s*\n(.*?)```", text, re.S)
    if not match:
        raise ValueError("No code block found in the agent's reply:\n" + text[:500])
    return match.group(1).strip()


def generate_dictionary(schema: str, table: str) -> str:
    """Ask dictionary-builder for one table's dictionary; return the CSV text."""
    columns = get_columns(schema, table)
    message = f"Table: {schema}.{table}\nColumns: {columns}"
    reply = call_agent("dictionary-builder", os.getenv("DICT_AGENT_VERSION"), message)
    return extract_code_block(reply)


if __name__ == "__main__":
    csv_text = generate_dictionary("pres", "DimSavingsAccount")
    os.makedirs("dictionary", exist_ok=True)
    path = "dictionary/DimSavingsAccount.csv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(csv_text + "\n")
    print(csv_text[:600])
    print(f"\nSaved to {path}")