# Editor de criterios — frontend

Interfaz con la que el docente lee sus documentos normativos y propone
cambios de valor sobre los criterios que derivan de ellos. React + Vite +
TypeScript + Tailwind.

## Desarrollo

El backend (FastAPI) tiene que estar corriendo en `127.0.0.1:8000`: el
servidor de desarrollo de Vite reenvía todas las peticiones a `/api` hacia
ahí (ver `vite.config.ts`).

```bash
npm install
npm run dev
```

Se sirve en `http://localhost:5173`.

## Compilación

```bash
npm run build
```

Comprueba los tipos (`tsc -b`) y genera el sitio estático en `dist/`.
