"""
Tests de los endpoints GET/PUT /productos/{id}/reposicion, con TestClient
de FastAPI y SQLite en memoria aislado (no toca ferreteria.db ni Railway).
    pytest backend/test_reposicion_endpoints.py
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
from rutas.reposicion import router as reposicion_router
from rutas.usuarios import require_admin_o_gestionador


@pytest.fixture()
def ctx():
    # StaticPool: todas las conexiones (creación de tablas + cada request del
    # TestClient) comparten la MISMA base en memoria — sin esto, sqlite crea
    # una base nueva y vacía por cada conexión y las tablas "desaparecen".
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
    app.include_router(reposicion_router)
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[require_admin_o_gestionador] = lambda: {"rol": "admin"}

    db = TestingSession()
    producto = models.Producto(nombre="Producto Test", codigo="RT-001", stock=20)
    db.add(producto)
    proveedores = [
        models.Proveedor(nombre="Proveedor Uno",   dias_credito=30, lead_time_dias_default=7),
        models.Proveedor(nombre="Proveedor Dos",   dias_credito=15, lead_time_dias_default=5),
        models.Proveedor(nombre="Proveedor Tres"),
        models.Proveedor(nombre="Proveedor Cuatro"),
    ]
    db.add_all(proveedores)
    db.commit()
    db.refresh(producto)
    for p in proveedores:
        db.refresh(p)
    ids = [p.id for p in proveedores]
    db.close()

    return SimpleNamespace(
        client=TestClient(app),
        producto_id=producto.id,
        proveedor_ids=ids,
    )


def test_get_ficha_vacia(ctx):
    res = ctx.client.get(f"/productos/{ctx.producto_id}/reposicion")
    assert res.status_code == 200
    assert res.json()["ficha_cargada"] is False


def test_put_crea_ficha(ctx):
    payload = {
        "modo_reposicion": "stock_continuo",
        "stock_min_objetivo": 5,
        "stock_max_objetivo": 30,
        "unidades_exhibicion": 2,
        "colchon_dias": 3,
        "activo": True,
        "proveedores": [
            {"proveedor_id": ctx.proveedor_ids[0], "prioridad": 1,
             "precio_actual_usd": 10.0, "minimo_compra": 5},
        ],
    }
    res = ctx.client.put(f"/productos/{ctx.producto_id}/reposicion", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["ficha_cargada"] is True
    assert body["modo_reposicion"] == "stock_continuo"
    assert len(body["proveedores"]) == 1
    assert body["proveedores"][0]["proveedor_nombre"] == "Proveedor Uno"
    assert body["existencia_disponible"] == 18   # C17: stock(20) - exhibicion(2)


def test_put_actualiza_ficha(ctx):
    base = {
        "modo_reposicion": "stock_continuo",
        "stock_min_objetivo": 5, "stock_max_objetivo": 30,
        "unidades_exhibicion": 0, "colchon_dias": 3,
        "proveedores": [{"proveedor_id": ctx.proveedor_ids[0], "prioridad": 1}],
    }
    ctx.client.put(f"/productos/{ctx.producto_id}/reposicion", json=base)

    actualizado = dict(base, modo_reposicion="pedido_bajo_demanda", stock_min_objetivo=99)
    res = ctx.client.put(f"/productos/{ctx.producto_id}/reposicion", json=actualizado)
    assert res.status_code == 200
    body = res.json()
    assert body["modo_reposicion"] == "pedido_bajo_demanda"
    assert body["stock_min_objetivo"] == 99


def test_put_rechaza_modo_invalido(ctx):
    payload = {"modo_reposicion": "modo_que_no_existe", "proveedores": []}
    res = ctx.client.put(f"/productos/{ctx.producto_id}/reposicion", json=payload)
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "modo_reposicion inválido" in detail
    assert "stock_continuo" in detail   # mensaje concreto: lista los valores validos


def test_put_rechaza_cuarto_proveedor(ctx):
    payload = {
        "modo_reposicion": "stock_continuo",
        "proveedores": [
            {"proveedor_id": ctx.proveedor_ids[0], "prioridad": 1},
            {"proveedor_id": ctx.proveedor_ids[1], "prioridad": 2},
            {"proveedor_id": ctx.proveedor_ids[2], "prioridad": 3},
            {"proveedor_id": ctx.proveedor_ids[3], "prioridad": 1},
        ],
    }
    res = ctx.client.put(f"/productos/{ctx.producto_id}/reposicion", json=payload)
    assert res.status_code == 400
    assert "3 proveedores" in res.json()["detail"]


def test_put_sin_stock_declarado_setea_fecha_automatica(ctx):
    payload = {
        "modo_reposicion": "stock_continuo",
        "proveedores": [
            {"proveedor_id": ctx.proveedor_ids[0], "prioridad": 1, "sin_stock_declarado": True},
        ],
    }
    res = ctx.client.put(f"/productos/{ctx.producto_id}/reposicion", json=payload)
    body = res.json()
    assert body["proveedores"][0]["sin_stock_declarado"] is True
    assert body["proveedores"][0]["sin_stock_fecha"] is not None   # C24: se asienta sola

    # Al volver a false, se limpia sola
    payload2 = dict(payload)
    payload2["proveedores"][0]["sin_stock_declarado"] = False
    res2 = ctx.client.put(f"/productos/{ctx.producto_id}/reposicion", json=payload2)
    body2 = res2.json()
    assert body2["proveedores"][0]["sin_stock_declarado"] is False
    assert body2["proveedores"][0]["sin_stock_fecha"] is None


def _crear_cinco_productos(ctx):
    productos = [
        models.Producto(nombre=f"Producto Bulk {i}", codigo=f"BLK-{i:03d}", stock=10 + i)
        for i in range(5)
    ]
    # StaticPool comparte la misma conexión en memoria, así que una sesión
    # abierta acá es visible para las requests posteriores del TestClient.
    db = next(ctx.client.app.dependency_overrides[get_db]())
    db.add_all(productos)
    db.commit()
    for p in productos:
        db.refresh(p)
    ids = [p.id for p in productos]
    db.close()
    return ids


def test_put_bulk_exito_cinco_productos(ctx):
    producto_ids = _crear_cinco_productos(ctx)
    fichas = [
        {
            "producto_id": pid,
            "modo_reposicion": "stock_continuo",
            "stock_min_objetivo": 5,
            "stock_max_objetivo": 20,
            "unidades_exhibicion": 0,
            "colchon_dias": 3,
            "proveedores": [{"proveedor_id": ctx.proveedor_ids[0], "prioridad": 1}],
        }
        for pid in producto_ids
    ]
    res = ctx.client.put("/productos/reposicion/bulk", json={"fichas": fichas})
    assert res.status_code == 200
    body = res.json()
    assert len(body["actualizadas"]) == 5
    assert all(f["ficha_cargada"] for f in body["actualizadas"])

    # Confirmamos que efectivamente quedó persistido (no solo en la respuesta)
    verificacion = ctx.client.get(f"/productos/{producto_ids[0]}/reposicion")
    assert verificacion.json()["ficha_cargada"] is True


def test_put_bulk_rollback_si_tercero_invalido(ctx):
    producto_ids = _crear_cinco_productos(ctx)
    fichas = []
    for i, pid in enumerate(producto_ids):
        ficha = {
            "producto_id": pid,
            "modo_reposicion": "stock_continuo",
            "proveedores": [{"proveedor_id": ctx.proveedor_ids[0], "prioridad": 1}],
        }
        if i == 2:
            ficha["modo_reposicion"] = "modo_que_no_existe"   # el 3ro es inválido
        fichas.append(ficha)

    res = ctx.client.put("/productos/reposicion/bulk", json={"fichas": fichas})
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert len(detail["errores"]) == 1
    assert detail["errores"][0]["producto_id"] == producto_ids[2]

    # Nada debe haberse guardado, ni siquiera las 4 fichas válidas (rollback total)
    for pid in producto_ids:
        verificacion = ctx.client.get(f"/productos/{pid}/reposicion")
        assert verificacion.json()["ficha_cargada"] is False
