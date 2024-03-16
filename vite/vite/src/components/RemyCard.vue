<script setup lang="ts">
    import { ref, onMounted } from "vue";
    import { get_card } from "../api";
    import { parse_card } from "../parser";
    import MarkdownIt from "markdown-it";

    const props = defineProps<{
        label: string
    }>()

    const data = ref({});

    function to_markdown(parsed) {
        let out = [ ];

        for (const node of parsed) {
            if (node.type === 'field') { continue; }
            else if (node.type === 'text') { out.push(node.content); }
            else if (node.type === 'reference') {
                out.push('[' + node.url + ']');
                out.push('(' + node.url + ')');
            }
        }

        return out.join('');
    }

    onMounted(() => {
        setTimeout(async () => {
            let json = await get_card(props.label);

            let parsed = parse_card(json['raw']);
            let markdown = to_markdown(parsed);

            let md = MarkdownIt({ breaks: true });

            data.value = md.render(markdown);

            // data.value = await get_card(props.label);
        });
    });
</script>

<template>
    <div class="card" v-html="data"></div>
</template>

<style>
    @import '../assets/styles/base.css';
</style>
