"""
Test de POST /facturas/importar-catalogo — al crear un producto nuevo desde
el catálogo de un proveedor, el código de proveedor debe quedar en
catalogo_proveedor.codigo_proveedor, NUNCA copiado a productos.codigo (que
es el catálogo interno de Ferre-Util y lo asigna el dueño).
    pytest backend/test_importar_catalogo.py
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
from rutas.facturas import router as facturas_router


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
    app.include_router(facturas_router)
    app.dependency_overrides[get_db] = _get_db

    db = TestingSession()
    prov = models.Proveedor(nombre="Cindu de Venezuela", rif="J-12345678-9")
    db.add(prov)
    db.commit()
    db.refresh(prov)
    proveedor_id = prov.id
    db.close()

    return SimpleNamespace(client=TestClient(app), proveedor_id=proveedor_id, Session=TestingSession)


def test_importar_catalogo_producto_nuevo_no_copia_codigo_de_proveedor(ctx):
    res = ctx.client.post("/facturas/importar-catalogo", json={
        "proveedor_id": ctx.proveedor_id,
        "items": [{
            "codigo_catalogo": "00335386",
            "nombre_final": "Impermeabilizante Novacapa 350",
            "costo_final": 12.5,
            "accion": "nuevo",
        }],
    })
    assert res.status_code == 200
    body = res.json()
    assert body["creados"] == 1
    assert body["errores"] == []

    db = ctx.Session()
    try:
        producto = db.query(models.Producto).filter(
            models.Producto.nombre == "Impermeabilizante Novacapa 350"
        ).first()
        assert producto is not None
        assert producto.codigo is None   # el codigo interno queda libre para que Luis lo asigne

        cat = db.query(models.CatalogoProveedor).filter(
            models.CatalogoProveedor.producto_id == producto.id,
        ).first()
        assert cat is not None
        assert cat.codigo_proveedor == "00335386"   # el codigo del proveedor vive acá
    finally:
        db.close()


def test_importar_catalogo_sin_codigo_de_catalogo_tambien_deja_producto_sin_codigo(ctx):
    res = ctx.client.post("/facturas/importar-catalogo", json={
        "proveedor_id": ctx.proveedor_id,
        "items": [{
            "codigo_catalogo": "",
            "nombre_final": "Producto Sin Codigo De Catalogo",
            "costo_final": 5.0,
            "accion": "nuevo",
        }],
    })
    assert res.status_code == 200
    assert res.json()["creados"] == 1

    db = ctx.Session()
    try:
        producto = db.query(models.Producto).filter(
            models.Producto.nombre == "Producto Sin Codigo De Catalogo"
        ).first()
        assert producto.codigo is None
    finally:
        db.close()
