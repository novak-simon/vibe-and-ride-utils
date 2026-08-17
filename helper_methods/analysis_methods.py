import os
from typing import Any

def save_in_downloads_as(content: Any = "empty", name: str = "unnamed_exported_file") -> None:
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    file_path = os.path.join(downloads_path, name + ".txt")
    with open(file_path, "w") as f:
        f.write(str(content))