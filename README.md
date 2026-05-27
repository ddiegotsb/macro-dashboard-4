# 📊 Monitor Macroeconómico Chile

Dashboard automático con datos del Banco Central de Chile.
Se actualiza solo cada día hábil a las 11:00 AM hora Chile.

## Setup (5 minutos)

### 1. Crear el repositorio en GitHub
- Ve a [github.com/new](https://github.com/new)
- Nombre: `macro-dashboard` (o el que quieras)
- Visibilidad: **Public** (necesario para GitHub Pages gratis)
- Crea el repositorio

### 2. Subir estos archivos
Arrastra todos los archivos de esta carpeta al repositorio, o usa Git:
```bash
git init
git add .
git commit -m "primer commit"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/macro-dashboard.git
git push -u origin main
```

### 3. Agregar las credenciales del Banco Central
- En tu repositorio ve a **Settings → Secrets and variables → Actions**
- Clic en **New repository secret**
- Agrega estos dos secretos:
  - Nombre: `BCENTRAL_USER` → Valor: tu email de si.bcentral.cl
  - Nombre: `BCENTRAL_PASS` → Valor: tu contraseña

### 4. Activar GitHub Pages
- Ve a **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: `gh-pages` / `/ (root)`
- Guardar

### 5. Correr por primera vez
- Ve a **Actions → Actualizar Dashboard Macro**
- Clic en **Run workflow**
- Espera ~1 minuto

### 6. ¡Listo!
Tu dashboard estará en:
```
https://TU_USUARIO.github.io/macro-dashboard/
```

## Funcionamiento
- Corre automáticamente **lunes a viernes a las 11 AM** (hora Chile)
- Puedes correrlo manualmente cuando quieras desde Actions → Run workflow
- Los datos vienen directo del Banco Central, siempre frescos
