from fastapi import APIRouter, UploadFile, File, HTTPException
import anthropic
import base64
import json
import io

import os

router = APIRouter(prefix="/facturas", tags=["facturas"])

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

TIPOS_IMAGEN   = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
MEDIA_TYPE_MAP = {
    "image/jpg":  "image/jpeg",
    "image/jpeg": "image/jpeg",
    "image/png":  "image/png",
    "image/webp": "image/webp",
    "image/gif":  "image/gif",
}


def _pdf_a_imagen_base64(contenido: bytes) -> tuple[str, str]:
    """Convierte la primera página de un PDF a JPEG. Retorna (base64, media_type)."""
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="pdf2image no está instalado. Ejecuta: pip install pdf2image  (y asegúrate de tener poppler instalado en el sistema).",
        )
    try:
        paginas = convert_from_bytes(contenido, first_page=1, last_page=1, dpi=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo convertir el PDF: {e}")

    buffer = io.BytesIO()
    paginas[0].save(buffer, format="JPEG", quality=90)
    imagen_b64 = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
    return imagen_b64, "image/jpeg"


@router.post("/escanear")
async def escanear_factura(archivo: UploadFile = File(...)):
    client       = anthropic.Anthropic(api_key=API_KEY)
    contenido    = await archivo.read()
    content_type = (archivo.content_type or "").lower().split(";")[0].strip()

    # ── Determinar imagen y media_type para Claude ────────────────────────
    if content_type == "application/pdf":
        imagen_b64, media_type = _pdf_a_imagen_base64(contenido)
    elif content_type in TIPOS_IMAGEN:
        imagen_b64 = base64.standard_b64encode(contenido).decode("utf-8")
        media_type = MEDIA_TYPE_MAP.get(content_type, "image/jpeg")
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Tipo de archivo no soportado: '{content_type or 'desconocido'}'. "
                "Formatos aceptados: JPEG, PNG, WebP, GIF o PDF."
            ),
        )

    # ── Llamar a Claude con visión ─────────────────────────────────────────
    mensaje = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type":       "base64",
                            "media_type": media_type,
                            "data":       imagen_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Analiza esta factura de proveedor y extrae todos los productos.\n"
                            "Devuelve SOLO un JSON con este formato exacto, sin texto adicional:\n"
                            "{\n"
                            '  "proveedor": "nombre del proveedor o vacío si no se ve",\n'
                            '  "fecha": "fecha de la factura o vacío",\n'
                            '  "productos": [\n'
                            "    {\n"
                            '      "nombre": "nombre del producto",\n'
                            '      "cantidad": numero,\n'
                            '      "precio_unitario": numero,\n'
                            '      "precio_venta_sugerido": numero o null,\n'
                            '      "descripcion": "descripcion adicional o vacío"\n'
                            "    }\n"
                            "  ]\n"
                            "}\n"
                            "precio_venta_sugerido solo si aparece explícitamente en la factura, de lo contrario null."
                        ),
                    },
                ],
            }
        ],
    )

    texto = mensaje.content[0].text.strip()
    # Limpiar posibles bloques de código markdown
    if texto.startswith("```"):
        lineas = texto.splitlines()
        texto  = "\n".join(lineas[1:-1] if lineas[-1].strip() == "```" else lineas[1:])

    try:
        return json.loads(texto)
    except Exception as e:
        return {"error": str(e), "respuesta": texto}
