import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

load_dotenv()


def upload_text(path: str, text: str) -> str:
    """Upload text to ADLS at <filesystem>/<path>, overwriting if it exists."""
    account = os.getenv("STORAGE_ACCOUNT")
    service = DataLakeServiceClient(
        account_url=f"https://{account}.dfs.core.windows.net",
        credential=DefaultAzureCredential(),
    )
    fs = service.get_file_system_client(os.getenv("STORAGE_FILESYSTEM"))
    fs.get_file_client(path).upload_data(text.encode("utf-8"), overwrite=True)
    return f"https://{account}.dfs.core.windows.net/{os.getenv('STORAGE_FILESYSTEM')}/{path}"


if __name__ == "__main__":
    with open("dictionary/DimSavingsAccount.csv", encoding="utf-8") as f:
        url = upload_text("dictionary/DimSavingsAccount.csv", f.read())
    print("Uploaded to", url)