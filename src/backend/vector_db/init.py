try:
    from .vector_db_helper import ensure_schema, initialize_col, upsert_folder
    from .config import FORMATS
except ImportError:
    from vector_db_helper import ensure_schema, initialize_col, upsert_folder  # type: ignore
    from config import FORMATS  # type: ignore


def init_recreate_collections(client) -> None:
    ensure_schema(client)
    for col_name in FORMATS.keys():
        initialize_col(client, col_name)


def init_upsertall(client, path: str) -> None:
    for col_name in FORMATS.keys():
        if col_name == "drive":
            # drive는 drive_list CSV 기반으로 별도 적재한다.
            continue
        folder_name = col_name.split(".")[0] + "/" + col_name.split(".")[1]
        upsert_folder(client, path + folder_name, col_name)
    
