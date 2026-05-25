# Pablito POS — Sistema de Punto de Venta

Sistema de ventas (POS) web con facturación electrónica SUNAT para negocios peruanos.

## Stack

| Componente | Tecnología |
|---|---|
| **Frontend** | React 19 + Vite 8 + TailwindCSS + DaisyUI |
| **Backend** | Supabase (PostgreSQL + Auth) |
| **Facturación** | PHP API (Greenter) en Docker/Render |
| **Deploy** | GitHub Pages + CI/CD |

## Módulos

- 🛒 **POS** — Punto de venta con carrito, búsqueda de productos y selección de clientes
- 📊 **Dashboard** — KPIs en tiempo real, top productos, control de régimen tributario
- 📋 **Historial** — Historial de ventas con detalle expandible y reimpresión
- 👥 **Clientes** — CRUD de clientes con DNI/RUC
- 📦 **Productos** — Gestión de catálogo con stock y estados
- 💰 **Fiados** — Control de créditos con abonos parciales
- ⚙️ **Configuración** — Perfil de empresa, régimen tributario, credenciales SUNAT
- ✅ **Verificación** — Página pública para validar comprobantes vía QR

## Regímenes Tributarios

Soporta los 4 regímenes peruanos: NRUS, RER, Mype Tributario y Régimen General.

## Setup

```bash
cd pablito-pos-web
cp .env.example .env       # Configura tus credenciales
npm install
npm run dev
```

## Variables de Entorno

```
VITE_SUPABASE_URL=https://tu-proyecto.supabase.co
VITE_SUPABASE_ANON_KEY=tu-anon-key
VITE_SUNAT_API_URL=https://tu-api.onrender.com
```

## Base de Datos

Ejecuta `supabase_schema_mejorado.sql` en tu proyecto Supabase, luego `disable_rls.sql` para las políticas de seguridad.

## API de Facturación (Docker)

```bash
docker build -t pablito-pos-api .
docker run -p 8080:80 pablito-pos-api
```

---

© 2026 Pablito POS · Facturación Electrónica SUNAT