export function notecard_grammar(compile = true) {
    let g = { }
    let r = String.raw;

    g['prefix']          = r`NOTECARD`;
    g['label_character'] = r`[-_0-9a-zA-Z]`;
    g['label']           = r`{label_character}+`;
    g['labels_tail']     = r`(?:\s+{label})`;
    g['labels']          = r`{label}{labels_tail}?`;
    g['endline']         = r`\r\n|\n`;
    g['endblock']        = r`(?:\r\n|\n)(?:\r\n|\n)`;
;
    g['field_content'] = r`.*?`;
    g['field']         = r`:{label}:\s*{field_content}{endline}`;
;
    g['notecard_start_line']      = r`{prefix}\s+{labels}\s*{endline}`;
;
    g['lbracket']  = r`\[`;
    g['rbracket']  = r`\]`;
    g['url']       = r`[^\]]+`;
    g['reference'] = r`{lbracket}\s*{url}\s*{rbracket}`;
;
    g['element'] = r`{field}|{reference}`;

    if (!compile) { return g; }

    let expanded = expand_grammar(g);

    let named = Object.fromEntries(
        Object.keys(expanded).map(k => [k, '(?<'+k+'>'+expanded[k]+')'])
    );

    g = Object.fromEntries(
        Object.keys(g).map(k => [k, format(g[k], named)])
    );

    return Object.fromEntries(
        Object.keys(g).map(k => [k, new RegExp(g[k], 'ug')])
    );
}

function format(str, replacements) {
    return str.replace(/{([^}]+)}/g, (_, key) => {
        return replacements[key];
    });
}

function expand_grammar(g)  {
    let grouped = Object.fromEntries(
        Object.keys(g).map(k => [k, '(?:' + g[k] + ')'])
    );

    function expand(r) {
        let x = null;

        while (x != r) {
            let t = format(r, grouped);
            x = r;
            r = t;
        }

        return x
    }

    return Object.fromEntries(
        Object.keys(grouped).map(k => [k, expand(grouped[k])])
    );
}

const grammar = notecard_grammar();

export function parse_card(raw: string) {
    let element_re   = grammar['element'];
    let field_re     = grammar['field'];
    let reference_re = grammar['reference'];

    let offset = 0;
    let out = [ ];

    for (const m of raw.matchAll(element_re)) {
        if (offset < m.index) {
            out.push({ 'type' : 'text', 'content' : raw.slice(offset, m.index) });
        }

        offset = m.index + m[0].length;

        if (m.groups['field']) {
            // Convoluted way to get a match object without modifying the
            // RegExp's internal state.
            let field = m.groups['field'].matchAll(field_re).next().value;

            let label = field.groups['label'];
            let field_content = field.groups['field_content'];


            out.push({ 'type' : 'field', 'label' : label, 'content' : field_content });
        }
        else if (m.groups['reference']) {
            let reference = m.groups['reference'].matchAll(reference_re).next().value;
            out.push({ 'type' : 'reference', 'url' : reference.groups['url'] });
        }
    }

    if (offset < raw.length) {
        out.push({ 'type' : 'text', 'content' : raw.slice(offset) });
    }

    return out;
}
