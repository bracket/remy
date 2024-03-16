const REMY_API_ENDPOINT = "http://localhost:3000/api";

export async function get_card(label:string) {
    const endpoint = `${REMY_API_ENDPOINT}/notecard/${label}`;

    const out = await fetch(endpoint)
        .then(response => response.json());

    return out;
}

