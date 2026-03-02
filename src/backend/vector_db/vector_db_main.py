from pathlib import Path

try:
    from .drive2db import drive_upsert_all
    from .vector_db_helper import get_pgvector_client, ensure_schema, search_doc
    from .init import init_recreate_collections, init_upsertall
except ImportError:
    from drive2db import drive_upsert_all  # type: ignore
    from vector_db_helper import get_pgvector_client, ensure_schema, search_doc  # type: ignore
    from init import init_recreate_collections, init_upsertall  # type: ignore


INIT = True
BASE_DIR = Path(__file__).resolve().parent
FOLDER_PATH = (BASE_DIR.parents[2] / "data").resolve()
DRIVE_LIST_PATH = (BASE_DIR / "drive_list").resolve()


def main():
    client = get_pgvector_client()
    ensure_schema(client)

    if INIT:
        init_recreate_collections(client)
        init_upsertall(client, str(FOLDER_PATH) + "/")
        drive_upsert_all(client, str(DRIVE_LIST_PATH))

    results = search_doc(client, "몰입캠프", "notion.marketing", 2)
    for hit in results:
        print(f"ID={hit.id}, 유사도={hit.score:.4f}, payload={hit.payload}")


if __name__ == "__main__":
    main()
