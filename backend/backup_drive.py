"""
Backup de la base de datos a Google Drive con rotacion automatica.

Uso:
    python backup_drive.py

Credenciales OAuth (en este orden de prioridad):
    1. Local: oauth_client.json + oauth_token.json en esta misma carpeta
       (generados con oauth_setup.py). Para pruebas locales.
    2. Variables de entorno, para produccion en Railway:
       GOOGLE_OAUTH_CLIENT_ID
       GOOGLE_OAUTH_CLIENT_SECRET
       GOOGLE_OAUTH_REFRESH_TOKEN

Variables de entorno requeridas:
    DATABASE_URL              - cadena de conexion (Postgres en produccion, SQLite en local)
    GOOGLE_DRIVE_FOLDER_ID     - ID de la carpeta "Ferreutil Backups" en Drive

Variable de entorno opcional:
    BACKUP_RETENTION - cuantos backups conservar (default: 30)

Autentica como el usuario dueno del Drive (no una cuenta de servicio), porque las
cuentas de servicio no tienen cuota de almacenamiento en un Drive personal (Gmail).

Sale con codigo 1 si algo falla, para que Railway marque el cron job como fallido.
"""
import io
import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime, date
from decimal import Decimal

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from sqlalchemy import create_engine, MetaData

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
DEFAULT_RETENTION = 30
TOKEN_URI = "https://oauth2.googleapis.com/token"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, "oauth_client.json")
TOKEN_FILE = os.path.join(BASE_DIR, "oauth_token.json")


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _cargar_desde_archivos_locales():
    if not (os.path.exists(CLIENT_SECRETS_FILE) and os.path.exists(TOKEN_FILE)):
        return None

    with open(CLIENT_SECRETS_FILE, "r", encoding="utf-8") as f:
        client_config = json.load(f)
    datos_cliente = client_config.get("web") or client_config.get("installed")
    if not datos_cliente:
        raise RuntimeError(f"{CLIENT_SECRETS_FILE} no tiene el formato esperado (clave 'web' o 'installed')")

    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        token_data = json.load(f)

    return {
        "client_id": datos_cliente["client_id"],
        "client_secret": datos_cliente["client_secret"],
        "refresh_token": token_data["refresh_token"],
    }


def _cargar_desde_env():
    try:
        return {
            "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
            "refresh_token": os.environ["GOOGLE_OAUTH_REFRESH_TOKEN"],
        }
    except KeyError as e:
        raise RuntimeError(f"Falta la variable de entorno {e}")


def cargar_credenciales():
    datos = _cargar_desde_archivos_locales()
    if datos is None:
        datos = _cargar_desde_env()

    return Credentials(
        token=None,
        refresh_token=datos["refresh_token"],
        token_uri=TOKEN_URI,
        client_id=datos["client_id"],
        client_secret=datos["client_secret"],
        scopes=DRIVE_SCOPES,
    )


def obtener_database_url():
    url = os.environ.get("DATABASE_URL", "sqlite:///./ferreteria.db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, (bytes, bytearray)):
        return o.hex()
    return str(o)


def volcar_base_datos(carpeta_destino):
    """Vuelca cada tabla de la base de datos a un archivo JSON dentro de carpeta_destino."""
    engine = create_engine(obtener_database_url())
    metadata = MetaData()
    metadata.reflect(bind=engine)

    tablas = sorted(metadata.tables.keys())
    if not tablas:
        raise RuntimeError("No se encontraron tablas en la base de datos, algo esta mal")

    with engine.connect() as conn:
        for nombre_tabla in tablas:
            tabla = metadata.tables[nombre_tabla]
            filas = conn.execute(tabla.select()).mappings().all()
            registros = [dict(fila) for fila in filas]
            ruta_json = os.path.join(carpeta_destino, f"{nombre_tabla}.json")
            with open(ruta_json, "w", encoding="utf-8") as f:
                json.dump(registros, f, ensure_ascii=False, default=json_default)
            log(f"  {nombre_tabla}: {len(registros)} filas")

    return tablas


def crear_zip_backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_zip = f"ferreutil_backup_{timestamp}.zip"

    with tempfile.TemporaryDirectory() as tmp_dir:
        log("Volcando tablas de la base de datos...")
        volcar_base_datos(tmp_dir)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for archivo in os.listdir(tmp_dir):
                zf.write(os.path.join(tmp_dir, archivo), arcname=archivo)

    buffer.seek(0)
    log(f"Backup comprimido: {nombre_zip} ({buffer.getbuffer().nbytes} bytes)")
    return buffer, nombre_zip


def subir_a_drive(service, folder_id, buffer, nombre_zip):
    metadata = {"name": nombre_zip, "parents": [folder_id]}
    media = MediaIoBaseUpload(buffer, mimetype="application/zip", resumable=True)
    archivo = service.files().create(body=metadata, media_body=media, fields="id,name,createdTime").execute()
    log(f"Subido a Drive: {archivo['name']} (id={archivo['id']})")
    return archivo


def rotar_backups(service, folder_id, retencion):
    query = f"'{folder_id}' in parents and trashed = false and name contains 'ferreutil_backup_'"
    resultado = service.files().list(
        q=query,
        orderBy="createdTime",
        fields="files(id,name,createdTime)",
        pageSize=1000,
    ).execute()
    archivos = resultado.get("files", [])
    log(f"Backups actuales en Drive: {len(archivos)} (retencion: {retencion})")

    de_mas = len(archivos) - retencion
    if de_mas <= 0:
        return

    for archivo in archivos[:de_mas]:
        service.files().delete(fileId=archivo["id"]).execute()
        log(f"  Eliminado por rotacion: {archivo['name']} ({archivo['createdTime']})")


def main():
    try:
        folder_id = os.environ["GOOGLE_DRIVE_FOLDER_ID"]
    except KeyError:
        log("ERROR: falta la variable de entorno GOOGLE_DRIVE_FOLDER_ID")
        sys.exit(1)

    retencion = int(os.environ.get("BACKUP_RETENTION", DEFAULT_RETENTION))

    try:
        creds = cargar_credenciales()
        service = build("drive", "v3", credentials=creds)

        buffer, nombre_zip = crear_zip_backup()
        subir_a_drive(service, folder_id, buffer, nombre_zip)

        rotar_backups(service, folder_id, retencion)
        log("Backup completado con exito.")
    except Exception as e:
        log(f"ERROR: backup fallido: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
