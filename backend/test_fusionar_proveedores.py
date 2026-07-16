"""
Tests del endpoint POST /compras/proveedores/fusionar, con TestClient de
FastAPI y SQLite en memoria aislado (no toca ferreteria.db ni Railway).
    pytest backend/test_fusionar_proveedores.py
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
from rutas.compras import router as compras_router
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
    app.include_router(compras_router)
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[require_admin] = lambda: {"rol": "admin"}

    db = TestingSession()
    canonico  = models.Proveedor(nombre="CINDU DE VENEZUELA, S.A.", codigo="CIN")
    dup1      = models.Proveedor(nombre="cindu de venezuela")
    dup2      = models.Proveedor(nombre="CINDU")
    otro      = models.Proveedor(nombre="Otro proveedor sin relación")
    productos = [models.Producto(nombre=f"Producto {i}", codigo=f"FUS-{i:03d}", stock=5) for i in range(2)]
    db.add_all([canonico, dup1, dup2, otro, *productos])
    db.commit()
    for obj in (canonico, dup1, dup2, otro, *productos):
        db.refresh(obj)

    # producto[0]: solo dup1 lo provee (caso simple de repunte)
    db.add(models.ProductoProveedor(producto_id=productos[0].id, proveedor_id=dup1.id, prioridad=1))
    # producto[1]: dup2 Y canonico ya lo proveen ambos (caso de conflicto/dedup)
    db.add(models.ProductoProveedor(producto_id=productos[1].id, proveedor_id=canonico.id, prioridad=1))
    db.add(models.ProductoProveedor(producto_id=productos[1].id, proveedor_id=dup2.id, prioridad=2))
    orden = models.OrdenCompra(numero="OC-9001", proveedor_id=dup1.id, estado="borrador")
    db.add(orden)
    db.commit()

    ctx_ns = SimpleNamespace(
        client=TestClient(app),
        canonico_id=canonico.id,
        dup1_id=dup1.id,
        dup2_id=dup2.id,
        otro_id=otro.id,
        producto_simple_id=productos[0].id,
        producto_conflicto_id=productos[1].id,
        orden_id=orden.id,
        Session=TestingSession,
    )
    db.close()
    return ctx_ns


def test_fusionar_exitosa(ctx):
    res = ctx.client.post("/compras/proveedores/fusionar", json={
        "canonico_id": ctx.canonico_id,
        "duplicados_ids": [ctx.dup1_id, ctx.dup2_id],
    })
    assert res.status_code == 200
    body = res.json()
    assert sorted(body["fusionados"]) == sorted([ctx.dup1_id, ctx.dup2_id])

    db = ctx.Session()
    try:
        # Los duplicados quedan desactivados, no borrados
        dup1 = db.get(models.Proveedor, ctx.dup1_id)
        dup2 = db.get(models.Proveedor, ctx.dup2_id)
        assert dup1.activo is False
        assert dup2.activo is False

        # La orden de compra que apuntaba a dup1 ahora apunta al canónico
        orden = db.get(models.OrdenCompra, ctx.orden_id)
        assert orden.proveedor_id == ctx.canonico_id

        # producto_simple: la fila de dup1 se repuntó al canónico (no se duplicó)
        filas = db.query(models.ProductoProveedor).filter(
            models.ProductoProveedor.producto_id == ctx.producto_simple_id
        ).all()
        assert len(filas) == 1
        assert filas[0].proveedor_id == ctx.canonico_id
    finally:
        db.close()


def test_fusionar_dedup_cuando_canonico_ya_provee_el_mismo_producto(ctx):
    res = ctx.client.post("/compras/proveedores/fusionar", json={
        "canonico_id": ctx.canonico_id,
        "duplicados_ids": [ctx.dup2_id],
    })
    assert res.status_code == 200

    db = ctx.Session()
    try:
        filas = db.query(models.ProductoProveedor).filter(
            models.ProductoProveedor.producto_id == ctx.producto_conflicto_id
        ).all()
        # Antes había 2 filas (canonico y dup2) para el mismo producto; la de
        # dup2 se descarta en vez de crear un segundo registro del canónico.
        assert len(filas) == 1
        assert filas[0].proveedor_id == ctx.canonico_id
    finally:
        db.close()


def test_fusionar_conflicto_maximo_tres_duplicados(ctx):
    db = ctx.Session()
    extra = models.Proveedor(nombre="Cuarto duplicado")
    db.add(extra)
    db.commit()
    db.refresh(extra)
    extra_id = extra.id
    db.close()

    res = ctx.client.post("/compras/proveedores/fusionar", json={
        "canonico_id": ctx.canonico_id,
        "duplicados_ids": [ctx.dup1_id, ctx.dup2_id, ctx.otro_id, extra_id],
    })
    assert res.status_code == 400
    assert "3" in res.json()["detail"]

    # Nada debe haber cambiado: los 4 proveedores siguen activos
    db = ctx.Session()
    try:
        activos = db.query(models.Proveedor.id, models.Proveedor.activo).filter(
            models.Proveedor.id.in_([ctx.dup1_id, ctx.dup2_id, ctx.otro_id, extra_id])
        ).all()
        assert all(a for _, a in activos)
    finally:
        db.close()


def test_fusionar_descarta_y_reporta_cuando_producto_ya_esta_al_maximo_de_proveedores(ctx):
    # producto_conflicto_id ya tiene canonico@1 y dup2@2 (fixture base). Lo
    # llevamos al máximo de 3 filas agregando a dup1 también como proveedor
    # de ese mismo producto: escenario "el canónico ya tiene proveedores en
    # este producto y el duplicado también aporta uno".
    db = ctx.Session()
    db.add(models.ProductoProveedor(producto_id=ctx.producto_conflicto_id, proveedor_id=ctx.dup1_id, prioridad=3))
    db.commit()
    db.close()

    res = ctx.client.post("/compras/proveedores/fusionar", json={
        "canonico_id": ctx.canonico_id,
        "duplicados_ids": [ctx.dup1_id, ctx.dup2_id],
    })
    assert res.status_code == 200
    body = res.json()
    descartes = body["filas_descartadas_por_conflicto"]
    # Tanto dup1@3 como dup2@2 chocan con el canónico ya presente en @1:
    # la fusión no falla, descarta ambas filas redundantes y lo reporta.
    assert len(descartes) == 2
    assert {d["proveedor_duplicado_id"] for d in descartes} == {ctx.dup1_id, ctx.dup2_id}
    assert all(d["producto_id"] == ctx.producto_conflicto_id for d in descartes)

    db = ctx.Session()
    try:
        filas = db.query(models.ProductoProveedor).filter(
            models.ProductoProveedor.producto_id == ctx.producto_conflicto_id
        ).all()
        assert len(filas) == 1
        assert filas[0].proveedor_id == ctx.canonico_id
    finally:
        db.close()


def test_fusionar_rollback_si_canonico_no_existe(ctx):
    res = ctx.client.post("/compras/proveedores/fusionar", json={
        "canonico_id": 999999,
        "duplicados_ids": [ctx.dup1_id],
    })
    assert res.status_code == 404

    db = ctx.Session()
    try:
        dup1 = db.get(models.Proveedor, ctx.dup1_id)
        assert dup1.activo is True   # no se tocó nada

        orden = db.get(models.OrdenCompra, ctx.orden_id)
        assert orden.proveedor_id == ctx.dup1_id   # sigue apuntando al duplicado original
    finally:
        db.close()
