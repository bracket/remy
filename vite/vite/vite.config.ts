import * as vite from 'vite';
import vue from '@vitejs/plugin-vue'

export default vite.defineConfig(
    ({ command, mode }) => {
        let config = vite.defineConfig({ plugins: [vue()] });

        if (command === 'serve') {
            let cross = {
                server: {
                    proxy: {
                        '/api': {
                            target: 'http://host.docker.internal:5000/api',
                            rewrite: (path) => path.replace(/^\/api/, ''),
                        },
                    },
                }
            }

            config = { ...config, ...cross };
        }

        return config;
    }
);
