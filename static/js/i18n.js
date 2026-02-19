/**
 * Internationalization (i18n) helper for JavaScript.
 * Loads translations from /static/locale/{locale}.json.
 * Usage: i18n.t('key') or i18n.t('key', {param: value})
 */
const i18n = {
    _locale: 'ja',
    _messages: {},
    _loaded: false,

    /**
     * Initialize i18n by detecting locale and loading translations.
     * Called automatically; can also be awaited for guaranteed load.
     */
    async init() {
        // Try to get locale from html lang attribute (set by server)
        const htmlLang = document.documentElement.lang;
        if (htmlLang && (htmlLang === 'ja' || htmlLang === 'en')) {
            this._locale = htmlLang;
        }

        // Load JSON translation file
        try {
            const resp = await fetch(`/static/locale/${this._locale}.json`);
            if (resp.ok) {
                this._messages = await resp.json();
            }
        } catch(e) {
            // Fallback: use keys as-is
            this._messages = {};
        }
        this._loaded = true;
    },

    /**
     * Translate a message key, with optional parameter substitution.
     * @param {string} key - The translation key (English text)
     * @param {Object} [params] - Parameters for substitution: {name} in msg replaced by params.name
     * @returns {string} Translated string, or key if not found
     */
    t(key, params) {
        let msg = this._messages[key] || key;
        if (params) {
            Object.entries(params).forEach(([k, v]) => {
                msg = msg.replace(new RegExp(`\\{${k}\\}`, 'g'), v);
            });
        }
        return msg;
    }
};

// Auto-initialize on load
i18n.init();
