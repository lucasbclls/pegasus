/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'claro-red': '#e50019', // Vermelho principal da Claro (exemplo)
        'claro-red-light': '#ff334d', // Um tom mais claro (opcional)
        'claro-red-dark': '#b20014', // Um tom mais escuro (opcional)
        'white': '#ffffff', // Branco (já existe, mas podemos explicitar)
        'gray-claro': '#f2f2f2', // Um tom de cinza claro para fundos (opcional)
        'text-gray': '#333333', // Cor de texto principal (opcional)
      },
    },
  },
  plugins: [],
}