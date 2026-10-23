import {defineConfig} from 'vite';
import {execFileSync} from 'node:child_process';
import react from '@vitejs/plugin-react';
export default defineConfig({define:{__PIVA_REVISION__:JSON.stringify(execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim())},plugins:[react()],build:{target:'es2022'}});
