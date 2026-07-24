"""
Motor de reparto de pagos a proveedores.

Un PagoProveedor se reparte contra RecepcionCompra concretas via
PagoProveedorAplicacion (cascada FIFO por defecto, o reparto manual).
estado_pago de una recepción nunca se setea a mano: siempre se deriva
de recalcular_estado_pago().
"""
from datetime import datetime
from sqlalchemy.orm import Session
from models import (
    PagoProveedor, PagoProveedorAplicacion, SaldoFavorProveedorMovimiento,
    RecepcionCompra,
)

TIPOS_PAGO_VALIDOS = {"pago", "ajuste_manual", "legacy_sin_movimiento"}


class ErrorMotorPagos(Exception):
    pass


def recalcular_estado_pago(db: Session, recepcion: RecepcionCompra) -> str:
    """Única fuente de verdad para RecepcionCompra.estado_pago. La setea y la devuelve."""
    if recepcion.devuelta:
        recepcion.estado_pago = "anulada"
        return recepcion.estado_pago

    if not recepcion.monto_factura:
        # Recepción de contado (sin crédito) — nunca entra al circuito de pagos.
        return recepcion.estado_pago

    aplicado = sum(
        float(a.monto_aplicado_usd or 0)
        for a in db.query(PagoProveedorAplicacion)
        .join(PagoProveedor, PagoProveedorAplicacion.pago_id == PagoProveedor.id)
        .filter(
            PagoProveedorAplicacion.recepcion_id == recepcion.id,
            PagoProveedor.estado == "registrado",
        )
        .all()
    )

    monto_factura = float(recepcion.monto_factura or 0)
    if aplicado >= monto_factura - 0.01:
        recepcion.estado_pago = "pagado"
    elif aplicado > 0.01:
        recepcion.estado_pago = "pago_parcial"
    elif recepcion.fecha_vencimiento_pago and datetime.now().date() > recepcion.fecha_vencimiento_pago:
        recepcion.estado_pago = "vencido"
    else:
        recepcion.estado_pago = "pendiente"

    return recepcion.estado_pago


def pendiente_recepcion(db: Session, recepcion: RecepcionCompra) -> float:
    aplicado = sum(
        float(a.monto_aplicado_usd or 0)
        for a in db.query(PagoProveedorAplicacion)
        .join(PagoProveedor, PagoProveedorAplicacion.pago_id == PagoProveedor.id)
        .filter(
            PagoProveedorAplicacion.recepcion_id == recepcion.id,
            PagoProveedor.estado == "registrado",
        )
        .all()
    )
    return round(max(float(recepcion.monto_factura or 0) - aplicado, 0), 2)


def recepciones_credito_proveedor(db: Session, proveedor_id: int):
    from models import OrdenCompra
    orden_ids = [
        o.id for o in db.query(OrdenCompra.id).filter(OrdenCompra.proveedor_id == proveedor_id).all()
    ]
    if not orden_ids:
        return []
    return (
        db.query(RecepcionCompra)
        .filter(
            RecepcionCompra.orden_id.in_(orden_ids),
            RecepcionCompra.monto_factura.isnot(None),
            RecepcionCompra.devuelta == False,  # noqa: E712
        )
        .order_by(RecepcionCompra.fecha_recepcion.asc(), RecepcionCompra.id.asc())
        .all()
    )


def aplicar_pago(db: Session, pago: PagoProveedor, aplicaciones_manuales: list | None = None) -> dict:
    """
    Reparte pago.monto_usd contra las recepciones pendientes del proveedor.

    aplicaciones_manuales: lista opcional de {"recepcion_id": int, "monto": float}.
    Si no se pasa, cascada automática FIFO (recepción más antigua primero).
    Sobrante -> saldo a favor del proveedor.
    """
    disponible = round(float(pago.monto_usd or 0), 2)
    recepciones_tocadas = []

    if aplicaciones_manuales is not None:
        total_manual = round(sum(float(a["monto"]) for a in aplicaciones_manuales), 2)
        if total_manual > disponible + 0.01:
            raise ErrorMotorPagos(
                f"Las aplicaciones manuales suman {total_manual} pero el pago es de {disponible}"
            )
        for item in aplicaciones_manuales:
            recepcion = db.query(RecepcionCompra).filter(RecepcionCompra.id == item["recepcion_id"]).first()
            if not recepcion:
                raise ErrorMotorPagos(f"Recepción {item['recepcion_id']} no existe")
            monto = round(float(item["monto"]), 2)
            pendiente = pendiente_recepcion(db, recepcion)
            if monto > pendiente + 0.01:
                raise ErrorMotorPagos(
                    f"Recepción {recepcion.id} tiene pendiente {pendiente} pero se intenta aplicar {monto}"
                )
            db.add(PagoProveedorAplicacion(
                pago_id=pago.id, recepcion_id=recepcion.id,
                monto_aplicado_usd=monto, tipo_aplicacion="manual",
            ))
            disponible = round(disponible - monto, 2)
            recepciones_tocadas.append(recepcion)
    else:
        cola = recepciones_credito_proveedor(db, pago.proveedor_id)
        for recepcion in cola:
            if disponible <= 0.01:
                break
            pendiente = pendiente_recepcion(db, recepcion)
            if pendiente <= 0.01:
                continue
            monto = round(min(pendiente, disponible), 2)
            db.add(PagoProveedorAplicacion(
                pago_id=pago.id, recepcion_id=recepcion.id,
                monto_aplicado_usd=monto, tipo_aplicacion="cascada_automatica",
            ))
            disponible = round(disponible - monto, 2)
            recepciones_tocadas.append(recepcion)

    if disponible > 0.01:
        db.add(SaldoFavorProveedorMovimiento(
            proveedor_id=pago.proveedor_id, monto_usd=disponible,
            tipo="generado", pago_origen_id=pago.id,
            nota="Sobrante de pago aplicado en cascada",
        ))

    db.flush()
    for recepcion in recepciones_tocadas:
        recalcular_estado_pago(db, recepcion)

    return {"aplicado": round(float(pago.monto_usd or 0) - disponible, 2), "sobrante_saldo_favor": disponible}


def anular_pago(db: Session, pago: PagoProveedor, motivo: str, usuario: str) -> None:
    """Anula un pago, revierte sus aplicaciones y libera el saldo a favor que haya generado
    (solo la parte todavía no consumida; si ya se consumió en otro lado, bloquea con error)."""
    if pago.estado == "anulado":
        raise ErrorMotorPagos("El pago ya está anulado")

    aplicaciones = db.query(PagoProveedorAplicacion).filter(PagoProveedorAplicacion.pago_id == pago.id).all()
    recepciones_ids = [a.recepcion_id for a in aplicaciones]

    generado = sum(
        float(m.monto_usd) for m in db.query(SaldoFavorProveedorMovimiento).filter(
            SaldoFavorProveedorMovimiento.pago_origen_id == pago.id,
            SaldoFavorProveedorMovimiento.tipo == "generado",
        ).all()
    )
    if generado > 0.01:
        saldo_actual_proveedor = sum(
            float(m.monto_usd) for m in db.query(SaldoFavorProveedorMovimiento).filter(
                SaldoFavorProveedorMovimiento.proveedor_id == pago.proveedor_id,
            ).all()
        )
        if saldo_actual_proveedor < generado - 0.01:
            raise ErrorMotorPagos(
                f"Este pago generó ${generado:.2f} de saldo a favor, pero el proveedor ya solo tiene "
                f"${saldo_actual_proveedor:.2f} disponible — parte de ese saldo ya se consumió en otro pago/"
                f"recepción. Resolvé eso manualmente antes de anular."
            )
        db.add(SaldoFavorProveedorMovimiento(
            proveedor_id=pago.proveedor_id, monto_usd=-generado,
            tipo="liberado", pago_origen_id=pago.id,
            nota=f"Liberado por anulación de pago {pago.id}: {motivo}",
        ))

    for a in aplicaciones:
        db.delete(a)

    pago.estado = "anulado"
    pago.anulado_motivo = motivo
    pago.anulado_por = usuario
    pago.anulado_fecha = datetime.now()

    db.flush()
    for recepcion_id in recepciones_ids:
        recepcion = db.query(RecepcionCompra).filter(RecepcionCompra.id == recepcion_id).first()
        if recepcion:
            recalcular_estado_pago(db, recepcion)


def saldo_favor_disponible(db: Session, proveedor_id: int) -> float:
    total = sum(
        float(m.monto_usd) for m in db.query(SaldoFavorProveedorMovimiento).filter(
            SaldoFavorProveedorMovimiento.proveedor_id == proveedor_id,
        ).all()
    )
    return round(total, 2)


def resumen_deuda_proveedor(db: Session, proveedor_id: int) -> dict:
    """Deuda real de un proveedor: recepciones a crédito activas (no devueltas) menos lo
    aplicado, neto del saldo a favor acumulado. saldo_pendiente negativo = a favor nuestro."""
    recepciones = recepciones_credito_proveedor(db, proveedor_id)
    total_facturado = round(sum(float(r.monto_factura or 0) for r in recepciones), 2)
    pendientes = [(r, pendiente_recepcion(db, r)) for r in recepciones]
    pendiente_bruto = round(sum(p for _, p in pendientes), 2)
    saldo_favor = saldo_favor_disponible(db, proveedor_id)
    return {
        "total_facturado":          total_facturado,
        "total_aplicado":           round(total_facturado - pendiente_bruto, 2),
        "saldo_favor":              saldo_favor,
        "saldo_pendiente":          round(pendiente_bruto - saldo_favor, 2),
        "recepciones_pendientes":   sum(1 for _, p in pendientes if p > 0.01),
        "recepcion_mas_antigua_pendiente": next(
            (r.fecha_recepcion for r, p in pendientes if p > 0.01), None
        ),
    }
