import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'

const LABELS_METODO = {
  efectivo_usd:    'Efectivo $',
  zelle:           'Zelle',
  binance:         'Binance',
  efectivo_bs:     'Efectivo Bs',
  transferencia_bs:'Transferencia Bs',
  pago_movil:      'Pago Móvil',
  punto_banesco:   'Punto Banesco',
  punto_provincial:'Punto Provincial',
}

export function exportarFacturaPDF(data) {
  const { venta, detalles, pagos } = data
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })

  const AZUL   = [22, 33, 62]       // #16213e
  const ROJO   = [233, 69, 96]      // #e94560
  const GRIS   = [168, 168, 179]
  const BLANCO = [255, 255, 255]
  const NEGRO  = [30, 30, 30]

  const ancho = 210
  const margen = 15

  // ── Encabezado ─────────────────────────────────────────────────────────────
  doc.setFillColor(...AZUL)
  doc.rect(0, 0, ancho, 32, 'F')

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(22)
  doc.setTextColor(...ROJO)
  doc.text('FERREUTIL', margen, 14)

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(9)
  doc.setTextColor(...GRIS)
  doc.text('Ferretería · Ciudad Ojeda, Venezuela', margen, 21)
  doc.text('Documento no fiscal — solo para uso interno', margen, 27)

  // Número de factura
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(11)
  doc.setTextColor(...BLANCO)
  doc.text(`Factura #${venta.id}`, ancho - margen, 14, { align: 'right' })
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(9)
  doc.setTextColor(...GRIS)
  const fecha = venta.fecha ? new Date(venta.fecha).toLocaleString('es-VE') : ''
  doc.text(fecha, ancho - margen, 21, { align: 'right' })
  doc.text(`Atendió: ${venta.usuario || ''}`, ancho - margen, 27, { align: 'right' })

  let y = 40

  // ── Datos de venta ──────────────────────────────────────────────────────────
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(9)
  doc.setTextColor(...NEGRO)

  const moneda      = venta.moneda_venta || 'USD'
  const tipoPrecio  = venta.tipo_precio_usado || 'referencial'
  const tasaBcv     = venta.tasa_bcv ? `Bs. ${Number(venta.tasa_bcv).toFixed(2)}` : '—'
  const tasaBin     = venta.tasa_binance ? `Bs. ${Number(venta.tasa_binance).toFixed(2)}` : '—'

  const infoLeft  = [`Moneda: ${moneda}`, `Tipo de precio: ${tipoPrecio}`]
  const infoRight = [`Tasa BCV: ${tasaBcv}`, `Tasa Binance: ${tasaBin}`]

  infoLeft.forEach((t, i)  => doc.text(t, margen,         y + i * 5))
  infoRight.forEach((t, i) => doc.text(t, ancho - margen, y + i * 5, { align: 'right' }))
  y += 14

  // ── Tabla de productos ──────────────────────────────────────────────────────
  const sym = moneda === 'USD' ? '$' : 'Bs.'

  autoTable(doc, {
    startY: y,
    head: [['Producto', 'Cant.', 'Precio unit.', 'Subtotal']],
    body: detalles.map(d => {
      let nombre = d.nombre
      if (d.variante_label) {
        nombre += `\n  ${d.variante_label}`
        if (d.variante_codigo) nombre += `  [${d.variante_codigo}]`
      } else if (d.codigo) {
        nombre += `  [${d.codigo}]`
      }
      return [
        nombre,
        d.cantidad,
        `${sym} ${Number(d.precio_unitario).toFixed(2)}`,
        `${sym} ${Number(d.subtotal).toFixed(2)}`,
      ]
    }),
    styles: { fontSize: 9, cellPadding: 3, textColor: NEGRO },
    headStyles: { fillColor: AZUL, textColor: BLANCO, fontStyle: 'bold' },
    alternateRowStyles: { fillColor: [245, 245, 250] },
    columnStyles: {
      0: { cellWidth: 'auto' },
      1: { halign: 'center', cellWidth: 18 },
      2: { halign: 'right',  cellWidth: 32 },
      3: { halign: 'right',  cellWidth: 32 },
    },
    margin: { left: margen, right: margen },
  })

  y = doc.lastAutoTable.finalY + 6

  // ── Totales ─────────────────────────────────────────────────────────────────
  const subtotal  = Number(venta.subtotal  || 0).toFixed(2)
  const descuento = Number(venta.descuento || 0).toFixed(2)
  const total     = Number(venta.total     || 0).toFixed(2)
  const abonado   = Number(venta.total_abonado || 0).toFixed(2)
  const exceso    = Number(venta.exceso    || 0).toFixed(2)

  const totalesX = ancho - margen - 60
  const filasTotales = [
    ['Subtotal:', `${sym} ${subtotal}`],
    ...(Number(descuento) > 0 ? [['Descuento:', `- ${sym} ${descuento}`]] : []),
    ['TOTAL:', `${sym} ${total}`],
    ['Total abonado:', `${sym} ${abonado}`],
    ...(Number(exceso) > 0 ? [['Vuelto/Exceso:', `${sym} ${exceso}`]] : []),
  ]

  doc.setFontSize(9)
  filasTotales.forEach((fila, i) => {
    const esTotal = fila[0] === 'TOTAL:'
    if (esTotal) {
      doc.setFont('helvetica', 'bold')
      doc.setTextColor(...ROJO)
    } else {
      doc.setFont('helvetica', 'normal')
      doc.setTextColor(...NEGRO)
    }
    doc.text(fila[0], totalesX, y + i * 6)
    doc.text(fila[1], ancho - margen, y + i * 6, { align: 'right' })
  })

  y += filasTotales.length * 6 + 8

  // ── Pagos ───────────────────────────────────────────────────────────────────
  if (pagos && pagos.length > 0) {
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(10)
    doc.setTextColor(...AZUL)
    doc.text('Formas de pago', margen, y)
    y += 4

    autoTable(doc, {
      startY: y,
      head: [['Método', 'Moneda', 'Monto recibido', 'Equivalente']],
      body: pagos.map(p => [
        LABELS_METODO[p.metodo_pago] || p.metodo_pago,
        p.moneda_pago,
        `${p.moneda_pago === 'USD' ? '$' : 'Bs.'} ${Number(p.monto_original).toFixed(2)}`,
        `${sym} ${Number(p.monto_equivalente).toFixed(2)}`,
      ]),
      styles: { fontSize: 8.5, cellPadding: 2.5, textColor: NEGRO },
      headStyles: { fillColor: [15, 52, 96], textColor: BLANCO, fontStyle: 'bold' },
      margin: { left: margen, right: margen },
    })

    y = doc.lastAutoTable.finalY + 6
  }

  // ── Observación ─────────────────────────────────────────────────────────────
  if (venta.observacion) {
    doc.setFont('helvetica', 'italic')
    doc.setFontSize(8.5)
    doc.setTextColor(...GRIS)
    doc.text(`Obs: ${venta.observacion}`, margen, y)
    y += 6
  }

  // ── Pie de página ────────────────────────────────────────────────────────────
  const altoPagina = 297
  doc.setFillColor(...AZUL)
  doc.rect(0, altoPagina - 12, ancho, 12, 'F')
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(7.5)
  doc.setTextColor(...GRIS)
  doc.text('DOCUMENTO NO FISCAL — USO INTERNO', ancho / 2, altoPagina - 4.5, { align: 'center' })

  doc.save(`Factura-${venta.id}.pdf`)
}
