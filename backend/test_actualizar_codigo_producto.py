"""
Test de PUT /productos/{id}/codigo. Cubre la regresion encontrada al
habilitar la edicion de codigo desde Inventario para productos que ya
tenian codigo_proveedor: mandar {"codigo": null} para limpiar un codigo
tiraba 500 (None.strip()) en vez de guardar.
    pytest backend/test_actualizar_codigo_producto.py
"""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from database import get_db
from rutas.productos import router as productos_router
from rutas.usuarios import require_admin


@pytest.fixture()
def ctx():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)

    def _get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(productos_router)
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[require_admin] = lambda: {"rol": "admin"}

    db = TestingSession()
    p1 = models.Producto(nombre="Producto Uno", codigo="ABC-001")
    p2 = models.Producto(nombre="Producto Dos", codigo=None)
    db.add_all([p1, p2])
    db.commit()
    db.refresh(p1); db.refresh(p2)
    ids = SimpleNamespace(p1=p1.id, p2=p2.id)
    db.close()

    return SimpleNamespace(client=TestClient(app), ids=ids)


def test_asignar_codigo_nuevo(ctx):
    res = ctx.client.put(f"/productos/{ctx.ids.p2}/codigo", json={"codigo": "XYZ-002"})
    assert res.status_code == 200
    assert res.json()["codigo"] == "XYZ-002"


def test_limpiar_codigo_existente_con_null_no_rompe(ctx):
    # Antes de la fix, mandar codigo=null (en vez de omitir la clave) tiraba
    # 500 por None.strip(). La UI de Inventario ahora manda null explicito
    # cuando el usuario vacia el input para liberar un codigo.
    res = ctx.client.put(f"/productos/{ctx.ids.p1}/codigo", json={"codigo": None})
    assert res.status_code == 200
    assert res.json()["codigo"] is None


def test_rechaza_codigo_duplicado(ctx):
    res = ctx.client.put(f"/productos/{ctx.ids.p2}/codigo", json={"codigo": "ABC-001"})
    assert res.status_code == 400
    assert "ya está en uso" in res.json()["detail"]
