# Despliegue en Azure

## Arquitectura recomendada

Para este proyecto, la opcion mas simple es:

- `Azure App Service` para ejecutar la app Reflex en un contenedor.
- `Azure Container Registry (ACR)` para almacenar la imagen Docker.
- `Supabase` se mantiene como base de datos y auth.
- `Anthropic` se mantiene como proveedor IA principal.

La app queda accesible con una URL publica de Azure y no hace falta separar frontend/backend porque la version instalada de Reflex soporta `--single-port` en produccion.

## Variables necesarias en Azure

Configura estas variables en `App Service > Environment variables`:

```env
API_URL=https://TU-APP.azurewebsites.net
ANTHROPIC_API_KEY=...
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
OLLAMA_BASE_URL=...
```

Notas:

- `API_URL` debe ser la URL publica final de la app.
- Si no vais a usar Ollama en Azure, podeis omitir `OLLAMA_BASE_URL`.
- `SUPABASE_SERVICE_KEY` debe quedar solo como secreto de servidor.

## Flujo de despliegue

### 1. Crear recursos

```powershell
az group create --name rg-constellation --location westeurope
az acr create --resource-group rg-constellation --name acrconstellation --sku Basic
az appservice plan create --name plan-constellation --resource-group rg-constellation --is-linux --sku B1
az webapp create --resource-group rg-constellation --plan plan-constellation --name TU-APP --deployment-container-image-name acrconstellation.azurecr.io/constellation:latest
```

### 2. Construir y subir imagen a ACR

```powershell
az acr build --registry acrconstellation --image constellation:latest .
```

### 3. Dar permiso a App Service para leer ACR

```powershell
$appId = az webapp identity assign --resource-group rg-constellation --name TU-APP --query principalId -o tsv
$acrId = az acr show --name acrconstellation --resource-group rg-constellation --query id -o tsv
az role assignment create --assignee $appId --scope $acrId --role AcrPull
```

### 4. Configurar el contenedor y secretos

```powershell
az webapp config appsettings set --resource-group rg-constellation --name TU-APP --settings `
  WEBSITES_PORT=8000 `
  API_URL=https://TU-APP.azurewebsites.net `
  ANTHROPIC_API_KEY=... `
  SUPABASE_URL=... `
  SUPABASE_ANON_KEY=... `
  SUPABASE_SERVICE_KEY=...
```

### 5. Activar WebSockets

```powershell
az webapp config set --resource-group rg-constellation --name TU-APP --web-sockets-enabled true
```

## Recomendaciones operativas

- Usa dominio propio y SSL desde App Service en cuanto salga de demo.
- Mueve secretos a `Azure Key Vault` si esto va a tener usuarios reales.
- Activa `Application Insights` para logs y errores.
- Si quereis modelos locales con Ollama, no lo monteis en el mismo App Service; mejor una VM o contenedor separado y privado.

## Cuello de botella actual

La app genera nodos y metadatos dentro del proceso web. Para una demo sirve. Si va a crecer en uso, el siguiente paso es sacar esas tareas a un worker separado.
