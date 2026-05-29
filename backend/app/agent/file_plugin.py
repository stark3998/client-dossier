# app/agent/file_plugin.py
import json
import os
from semantic_kernel.functions import kernel_function
from app.config import get_settings


class FilePlugin:
    @kernel_function(
        name="list_files",
        description="List files available for a client in the document store."
    )
    async def list_files(self, path: str = "") -> str:
        settings = get_settings()
        target = os.path.join(settings.ONEDRIVE_SYNC_PATH, path)
        if not os.path.isdir(target):
            return json.dumps({"error": "Directory not found"})

        files = []
        for entry in os.listdir(target):
            full = os.path.join(target, entry)
            files.append({
                "name": entry,
                "type": "folder" if os.path.isdir(full) else "file",
                "size": os.path.getsize(full) if os.path.isfile(full) else None,
            })
        return json.dumps(files, indent=2)

    @kernel_function(
        name="read_file_preview",
        description="Get a text preview of a document by file path."
    )
    async def read_file_preview(self, file_path: str) -> str:
        settings = get_settings()
        full_path = os.path.join(settings.ONEDRIVE_SYNC_PATH, file_path)
        if not os.path.isfile(full_path):
            return json.dumps({"error": "File not found"})

        try:
            from app.ingestion.parser import parse_document
            parsed = parse_document(full_path)
            text = "\n\n".join(s.text for s in parsed.sections)
            return text[:3000]
        except Exception as e:
            return json.dumps({"error": str(e)})
