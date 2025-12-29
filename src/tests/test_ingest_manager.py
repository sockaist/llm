import types

from llm_backend.vectorstore import ingest_manager


class FakePointStruct:
    def __init__(self, id, vector, payload):
        self.id = id
        self.vector = vector
        self.payload = payload


class FakeClient:
    def __init__(self):
        self.collections = {"col": True}
        self.upserts = []
        self.payloads = {}

    def get_collection(self, collection_name):
        if collection_name not in self.collections:
            raise RuntimeError("missing collection")

    def upsert(self, collection_name, points):
        self.upserts.extend(points)

    def retrieve(self, collection_name, ids, with_payload=True):
        if not ids:
            return []
        pid = ids[0]
        payload = self.payloads.get(pid)
        if payload is None:
            return []
        return [types.SimpleNamespace(payload=payload)]

    def set_payload(self, collection_name, payload, points):
        for pid in points:
            self.payloads[pid] = payload

    def delete(self, collection_name, points_selector):
        return types.SimpleNamespace(result={"num_points": 1})

    def scroll(self, collection_name, scroll_filter, limit, with_payload, with_vectors):
        return [], None


class FakeManager:
    def __init__(self):
        self.client = FakeClient()
        self.dense_model = types.SimpleNamespace(encode=lambda text: [0.1, 0.2])


def test_upsert_document_validates_collection_and_content(monkeypatch):
    mgr = FakeManager()
    data = {"content": "hello", "id": "doc1"}
    ingest_manager.upsert_document(mgr, "col", data, None)
    assert mgr.client.upserts, "upsert should happen"


def test_upsert_document_skips_missing_collection(monkeypatch):
    mgr = FakeManager()
    data = {"content": "hello"}
    mgr.client.collections = {}  # make collection missing
    ingest_manager.upsert_document(mgr, "missing", data, None)
    assert not mgr.client.upserts


def test_update_payload_sets_payload(monkeypatch):
    mgr = FakeManager()
    mgr.client.payloads["doc"] = {"foo": "bar"}
    ok = ingest_manager.update_payload(mgr, "col", "doc", {"x": 1}, merge=True)
    assert ok is True
    assert mgr.client.payloads["doc"]["x"] == 1


def test_delete_by_filter_returns_count():
    mgr = FakeManager()
    cnt = ingest_manager.delete_by_filter(mgr, "col", "field", "v")
    assert cnt == 1
