/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_API_TIMEOUT: string
  readonly VITE_ENABLE_MOCK_DATA: string
  readonly VITE_ENABLE_DEBUG_MODE: string
  readonly VITE_ANALYTICS_ID?: string
  readonly VITE_APP_VERSION: string
  readonly VITE_APP_NAME: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
