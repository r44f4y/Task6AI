import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
export default defineConfig({
  plugins: [tailwindcss()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true,
    proxy: { '/api': {target:'http://127.0.0.1:'+(process.env.RELAY_API_PORT||'8000'),changeOrigin:false} } },
})
