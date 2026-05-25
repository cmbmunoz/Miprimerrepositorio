# Configuración — Pre-Facturación Automática

## Requisitos

- Python 3.11+
- Cuenta Microsoft 365 (Outlook Web)
- Clave de Anthropic API

---

## 1. Registrar la app en Azure

1. Andá a **https://portal.azure.com**
2. Buscá **"App registrations"** → **New registration**
   - Name: `Facturacion-Automatica`
   - Supported account types: *Accounts in this organizational directory only*
   - Redirect URI: dejar vacío
3. Anotá:
   - **Application (client) ID** → `AZURE_CLIENT_ID`
   - **Directory (tenant) ID** → `AZURE_TENANT_ID`

### 1a. Crear un Client Secret

4. En la app: **Certificates & secrets** → **New client secret**
   - Description: `facturacion`
   - Expires: 24 months
5. Anotá el **Value** (no el Secret ID) → `AZURE_CLIENT_SECRET`

### 1b. Asignar permisos

6. **API permissions** → **Add a permission** → **Microsoft Graph** → **Application permissions**
7. Agregá estos permisos:
   - `Mail.Read`
   - `Mail.ReadWrite`  ← para marcar emails como leídos
8. Hacé clic en **Grant admin consent for [tu org]** (requiere ser admin del tenant)

> Si no sos admin, pedile al administrador de M365 que apruebe los permisos.

---

## 2. Obtener la Anthropic API Key

1. Andá a **https://console.anthropic.com/**
2. **API Keys** → **Create Key**
3. Anotá la clave → `ANTHROPIC_API_KEY`

---

## 3. Configurar el .env

```bash
# En la carpeta facturacion-automatica/
cp .env.example .env
# Editá .env con los valores obtenidos en los pasos anteriores
```

---

## 4. Instalar dependencias

```bash
cd facturacion-automatica
pip install -r requirements.txt
```

---

## 5. Verificar configuración

```bash
python test_config.py
```

Salida esperada:
```
  ✔  Variables de entorno (.env)
  ✔  Autenticación Microsoft 365  →  token OK (1234 chars)
  ✔  Acceso a buzón de correo     →  0 OC(s) sin leer en bandeja
  ✔  Conexión con Anthropic API   →  OK

Todo OK. Ejecutá:  python run.py
```

---

## 6. Ejecutar

```bash
# Modo continuo (recomendado)
python run.py

# Una sola pasada y sale (útil para tests)
python run.py --once

# En Windows podés hacer doble clic en:
start.bat
```

---

## ¿Cómo funciona?

```
Bandeja M365 (Graph API)
     │
     │  email con PDF adjunto + asunto que contiene "OC" / "orden de compra"
     ▼
email_watcher.py  ──→  descarga el PDF
     │
     ▼
pdf_extractor.py  ──→  pdfplumber extrae texto → Claude lo estructura como JSON
     │
     ▼
prefactura.py     ──→  genera prefactura_{N}_{fecha}.xlsx en output/prefacturas/
     │
     ▼
email marcado como leído
```

### Salida

```
output/
├── facturacion.log          ← log completo
├── pdfs/                    ← PDFs originales
│   └── OC-12345.pdf
└── prefacturas/             ← prefacturas generadas
    └── prefactura_PF-20240315-143022_20240315.xlsx
```

---

## Configurar como tarea programada en Windows (opcional)

Para que corra al inicio sin abrir ventana:

1. **Buscá** "Programador de tareas" en el menú Inicio
2. **Crear tarea básica**
   - Desencadenador: Al iniciar sesión
   - Acción: Iniciar programa → `python.exe`
   - Argumentos: `C:\ruta\facturacion-automatica\run.py`
   - Directorio: `C:\ruta\facturacion-automatica\`
3. En "Condiciones" → desmarcá "Iniciar solo si hay conexión a la red de CA"

---

## Palabras clave para detectar OCs

Editá `OC_SUBJECT_KEYWORDS` en el `.env` para ajustar qué emails se procesan:

```
OC_SUBJECT_KEYWORDS=orden de compra,purchase order,OC ,PO-,P.O.,solicitud de compra
```
