import os
from sqlalchemy import create_engine, text
url = os.environ['DATABASE_URL']
if url.startswith('postgres://'):
    url = url.replace('postgres://', 'postgresql://', 1)
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text('ALTER TABLE apartados ADD COLUMN IF NOT EXISTS convertido_a_venta BOOLEAN NOT NULL DEFAULT FALSE'))
    conn.execute(text('ALTER TABLE ventas ADD COLUMN IF NOT EXISTS apartado_id INTEGER REFERENCES apartados(id)'))
    conn.commit()
print('columnas agregadas')