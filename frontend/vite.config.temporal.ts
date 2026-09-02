// Temporal: el puerto 8000 lo ocupa otro proyecto, así que el backend corre
// en el 8010. Este fichero NO forma parte del proyecto y se borra al terminar.
import base from "./vite.config"
import { defineConfig } from "vitest/config"

export default defineConfig({
  ...base,
  server: { port: 5174, proxy: { "/api": "http://127.0.0.1:8020" } },
})
