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
                            target: 'http://remy-api:42625',
                        },
                    },
                }
            }

            config = { ...config, ...cross };
        }

        return config;
    }
);
