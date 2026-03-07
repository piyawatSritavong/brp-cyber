from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_assurance_proof_index as idx


class _Tenant:
    def __init__(self, tenant_id, tenant_code: str) -> None:
        self.id = tenant_id
        self.tenant_code = tenant_code


class _Query:
    def __init__(self, rows):
        self._rows = rows

    def limit(self, n):
        return self

    def all(self):
        return self._rows


class _DB:
    def __init__(self, rows):
        self._rows = rows

    def query(self, model):
        return _Query(self._rows)


def test_assurance_delivery_proof_index_and_export() -> None:
    rows = [_Tenant(uuid4(), "acb"), _Tenant(uuid4(), "xyz")]
    db = _DB(rows)

    idx.signed_delivery_proof_status = lambda tenant_code, limit=1: {
        "count": 1 if tenant_code == "acb" else 0,
        "rows": [{"id": "1-0", "generated_at": "2026-01-01T00:00:00+00:00", "receipt_status": "delivered"}],
    }
    idx.verify_signed_delivery_proof_chain = lambda tenant_code, limit=1000: {"valid": tenant_code == "acb"}

    report = idx.assurance_delivery_proof_index(db, limit=10)
    assert report["count"] == 2
    assert report["valid_chain_count"] == 1

    exported = idx.export_assurance_delivery_proof_index(db, destination_dir="./tmp/compliance/test_proof_index", limit=10)
    assert exported["status"] == "exported"
