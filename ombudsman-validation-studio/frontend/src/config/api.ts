/**
 * API Configuration
 *
 * The API base URL can be configured via environment variable VITE_API_URL
 * Default: http://localhost:8000 (for local development)
 *
 * For production, set VITE_API_URL in .env file before building:
 *   VITE_API_URL=http://your-server:8000
 *
 * Or use empty string for same-origin requests with a reverse proxy:
 *   VITE_API_URL=
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

/**
 * Build full API URL
 */
export function apiUrl(path: string): string {
    // Remove leading slash if present to avoid double slashes
    const cleanPath = path.startsWith('/') ? path.slice(1) : path;

    // If API_BASE_URL is empty, use relative URL (for reverse proxy setup)
    if (!API_BASE_URL) {
        return `/${cleanPath}`;
    }

    return `${API_BASE_URL}/${cleanPath}`;
}

export default API_BASE_URL;
