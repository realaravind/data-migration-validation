import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
    // Load env file based on `mode` in the current working directory.
    const env = loadEnv(mode, process.cwd(), '')

    // API URL: use VITE_API_URL from env, or default to localhost for dev
    const apiUrl = env.VITE_API_URL || 'http://localhost:8000'

    return {
        plugins: [react()],
        define: {
            // Replace all instances of the hardcoded URL with the env variable
            '__API_URL__': JSON.stringify(apiUrl),
        },
        server: {
            port: 3000,
            proxy: {
                '/api': {
                    target: apiUrl,
                    changeOrigin: true,
                    rewrite: (path) => path.replace(/^\/api/, '')
                }
            }
        },
        build: {
            // Generate unique filenames with timestamps for cache busting
            rollupOptions: {
                output: {
                    entryFileNames: `assets/[name]-[hash]-${Date.now()}.js`,
                    chunkFileNames: `assets/[name]-[hash]-${Date.now()}.js`,
                    assetFileNames: `assets/[name]-[hash]-${Date.now()}.[ext]`
                }
            }
        }
    }
})
