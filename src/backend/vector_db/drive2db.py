import csv
import io
import re
from pathlib import Path
from typing import Any, Dict

import pdfplumber
import requests

try:
    from .vector_db_helper import create_doc_upsert, get_pgvector_client, ensure_schema
except ImportError:
    from vector_db_helper import create_doc_upsert, get_pgvector_client, ensure_schema  # type: ignore


def classify_file_type(link: str) -> str:
    if re.search(r"docs\.google\.com/document/d/", link):
        return "word"
    if re.search(r"drive\.google\.com/file/d/", link):
        return "pdf"
    return "unknown"


def drive2db(date: str, link: str, doc_id: int) -> Dict[str, Any]:
    full_text = []
    file_type = classify_file_type(link)

    if file_type == "pdf":
        link_id = re.search(r"/d/([a-zA-Z0-9_-]+)", link)
        if not link_id:
            return {"date": date, "link": link, "content": "INVALID DRIVE LINK", "id": doc_id}

        file_id = link_id.group(1)
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        try:
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            file_stream = io.BytesIO(response.content)
        except requests.RequestException as e:
            return {"date": date, "link": link, "content": f"DOWNLOAD ERROR: {e}", "id": doc_id}

        try:
            with pdfplumber.open(file_stream) as pdf:
                for page_index, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        lines = page_text.split("\n")
                        for line in lines:
                            cleaned_line = " ".join(line.strip().split())
                            cleaned_line = re.sub(r"[^0-9A-Za-z가-힣\s.,!?\-()]", "", cleaned_line)
                            if cleaned_line:
                                full_text.append(cleaned_line)

                    if page.images:
                        full_text.append("<IMAGE>")
                    full_text.append(f"<PAGE_BREAK:{page_index}>")
        except Exception as e:
            return {"date": date, "link": link, "content": f"PARSING ERROR: {e}", "id": doc_id}

    elif file_type == "word":
        return {"date": date, "link": link, "content": "WORD TYPE IS NOT SUPPORTED YET", "id": doc_id}
    else:
        return {"date": date, "link": link, "content": "UNKNOWN FILE TYPE", "id": doc_id}

    return {
        "date": f"{date}T00:00:00Z",
        "link": link,
        "content": " ".join(full_text).strip(),
        "id": str(doc_id),
    }


def drive_upsert_all(client, file_path: str) -> None:
    try:
        with open(file_path, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            row_count = 1

            for row in reader:
                if "date" not in row or "link" not in row:
                    print(f"Warning: row {row_count} has invalid columns.")
                    row_count += 1
                    continue

                data = drive2db(row["date"], row["link"], row_count)
                create_doc_upsert(client, "drive", data)
                row_count += 1
    except FileNotFoundError:
        print(f"Error: file not found: {file_path}")
    except Exception as e:
        print(f"Error: failed to process CSV: {e}")


if __name__ == "__main__":
    client = get_pgvector_client()
    ensure_schema(client)
    drive_upsert_all(client, str((Path(__file__).resolve().parent / "drive_list").resolve()))
