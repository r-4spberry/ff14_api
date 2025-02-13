document.addEventListener('DOMContentLoaded', () => {
    const itemInput = document.getElementById('item_name');
    const suggestionsDiv = document.getElementById('item_names');
    let timeoutId;

    const debounce = (func, delay) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(func, delay);
    };

    const updateSuggestions = async (query) => {
        try {
            const response = await fetch(`/api/items?query=${encodeURIComponent(query)}`);
            const items = await response.json();
            suggestionsDiv.innerHTML = '';
            if (items.length < 3) {
                suggestionsDiv.style.display = 'none';
                return;
            }
            suggestionsDiv.style.display = 'block';
            console.log(items);
            Object.entries(items).forEach(([id, name]) => {
                const suggestion = document.createElement('div');

                suggestion.innerHTML = `
                    <div class="suggestion-item">
                        <img src="https://universalis-ffxiv.github.io/universalis-assets/icon2x/${id}.png" alt="*" class="item-icon">
                        <span class="item-name">${name}</span>
                    </div>
                `;

                console.log(suggestion.innerHTML)
                suggestion.addEventListener('click', () => {
                    itemInput.value = name;
                    suggestionsDiv.style.display = 'none';
                });
                suggestionsDiv.appendChild(suggestion)
            });

        } catch (error) {
            console.error('Error fetching suggestions:', error);
        }
    };
    itemInput.addEventListener('focus', () => {
        const query = e.target.value.trim();

        if (query.length >= 3) {
            debounce(() => updateSuggestions(query), 300);
        } else {
            datalist.innerHTML = '';
        }
    });
    itemInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();

        if (query.length >= 3) {
            debounce(() => updateSuggestions(query), 300);
        } else {
            datalist.innerHTML = '';
        }
    });
    document.addEventListener('click', (e) => {
        if (!suggestionsDiv.contains(e.target) && e.target !== itemInput) {
            suggestionsDiv.style.display = 'none';
        }
    });
});