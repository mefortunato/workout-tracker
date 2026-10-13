import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		sveltekit({
			alias: {
				'$lib': './src/lib',
				'$lib/*': './src/lib/*'
			},
			adapter: adapter({
				pages: '../backend/app/static',
				assets: '../backend/app/static',
				fallback: 'index.html',
				precompress: false,
				strict: false
			})
		})
	],
	server: {
		proxy: {
			'/api': {
				target: 'http://127.0.0.1:8000',
				changeOrigin: true
			}
		}
	}
});
