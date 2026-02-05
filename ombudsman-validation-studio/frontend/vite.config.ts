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
            // Mermaid's flowchart-elk uses the large ELK layout engine (~1.4MB)
            // It's already lazy-loaded by mermaid, only when elk layout is needed
            chunkSizeWarningLimit: 1500,
            // Generate unique filenames with timestamps for cache busting
            rollupOptions: {
                output: {
                    entryFileNames: `assets/[name]-[hash]-${Date.now()}.js`,
                    chunkFileNames: `assets/[name]-[hash]-${Date.now()}.js`,
                    assetFileNames: `assets/[name]-[hash]-${Date.now()}.[ext]`,
                    manualChunks: {
                        // Core React vendor chunk
                        'vendor-react': ['react', 'react-dom', 'react-router-dom'],
                        // MUI components (large library)
                        'vendor-mui': ['@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled'],
                        // Data grid (separate from core MUI)
                        'vendor-datagrid': ['@mui/x-data-grid'],
                        // Charting library
                        'vendor-recharts': ['recharts'],
                        // Mermaid diagrams (only loaded on diagram pages)
                        'vendor-mermaid': ['mermaid'],
                    }
                }
            }
        }
    }
})
