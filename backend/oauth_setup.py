"""
Autorizacion unica para el backup a Google Drive.

Lee el client_id/client_secret desde oauth_client.json (descargado de Google Cloud
Console) en la misma carpeta que este script. Abre el navegador para que el dueno
del Drive (Luis) inicie sesion y acepte el acceso. Al terminar, guarda el refresh
token en oauth_token.json, en la misma carpeta. Ningun valor sensible se imprime
por pantalla.

Se corre UNA SOLA VEZ. No hace falta volver a correrlo salvo que se revoque el acceso.

Uso:
    python oauth_setup.py

Requiere (solo para este script, no en produccion):
    pip install google-auth-oauthlib
"""
import json
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, "oauth_client.json")
TOKEN_FILE = os.path.join(BASE_DIR, "oauth_token.json")


def main():
    if not os.path.exists(CLIENT_SECRETS_FILE):
        raise SystemExit(
            f"No se encontro {CLIENT_SECRETS_FILE}.\n"
            "Descarga el JSON del cliente OAuth desde Google Cloud Console y "
            "guardalo con ese nombre exacto en esa carpeta."
        )

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    creds = flow.run_local_server(host="127.0.0.1", port=8080, prompt="consent")

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump({"refresh_token": creds.refresh_token}, f)

    print("\n=== Autorizacion completa ===")
    print(f"Refresh token guardado en: {TOKEN_FILE}")
    print("(el valor no se muestra por pantalla)")


if __name__ == "__main__":
    main()
