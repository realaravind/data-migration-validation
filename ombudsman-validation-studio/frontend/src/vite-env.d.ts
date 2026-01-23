/// <reference types="vite/client" />

// Global constant injected by Vite at build time
declare const __API_URL__: string;

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  readonly VITE_SNOWFLAKE_ACCOUNT?: string
  readonly VITE_SNOWFLAKE_USER?: string
  readonly VITE_SNOWFLAKE_PASSWORD?: string
  readonly VITE_SNOWFLAKE_WAREHOUSE?: string
  readonly VITE_SNOWFLAKE_ROLE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
