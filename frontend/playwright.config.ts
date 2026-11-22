import { defineConfig } from '@playwright/test'
import { mkdtempSync, existsSync } from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import { fileURLToPath } from 'node:url'

const frontend=path.dirname(fileURLToPath(import.meta.url))
const root=path.dirname(frontend)
const db=path.join(mkdtempSync(path.join(os.tmpdir(),'relay-e2e-')),'relay.sqlite')
const chrome='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
export default defineConfig({
  testDir:'./tests',workers:1,timeout:30000,
  use:{baseURL:'http://127.0.0.1:5183',viewport:{width:1440,height:1000},
    launchOptions:{executablePath:existsSync(chrome)?chrome:undefined},acceptDownloads:true},
  webServer:[
    {command:'.venv/bin/python -m uvicorn backend.main:create_app --factory --host 127.0.0.1 --port 8010',
      cwd:root,env:{RELAY_DB:db,RELAY_EXPORT_ROOT:path.join(path.dirname(db),'exports'),APP_MODE:'offline_demo',RELAY_FRONTEND_ORIGIN:'http://127.0.0.1:5183'},url:'http://127.0.0.1:8010/api/workflows',timeout:25000},
    {command:'npm run dev -- --port 5183',cwd:frontend,env:{RELAY_API_PORT:'8010'},
      url:'http://127.0.0.1:5183/api/workflows',timeout:25000},
  ],
})
