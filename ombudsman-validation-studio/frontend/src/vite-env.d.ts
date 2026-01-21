/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SNOWFLAKE_ACCOUNT?: string
  readonly VITE_SNOWFLAKE_USER?: string
  readonly VITE_SNOWFLAKE_PASSWORD?: string
  readonly VITE_SNOWFLAKE_WAREHOUSE?: string
  readonly VITE_SNOWFLAKE_ROLE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
