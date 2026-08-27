export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        papel: "#FAFAF8",
        tinta: "#111111",
        grisclaro: "#E5E4E0",
        gris: "#6B6B66",
        // Una sola tinta de color, reservada a señalar la relación entre
        // una seccion y lo que deriva de ella. No decora nada mas.
        senal: "#C1301B",
      },
      fontFamily: {
        base: ["Inter", "Helvetica Neue", "Arial", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
      maxWidth: {
        lectura: "66ch",
      },
    },
  },
  plugins: [],
}
