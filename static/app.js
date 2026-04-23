document.addEventListener("DOMContentLoaded", function () {
    const calcInput = document.getElementById("calc_input");
    const addButton = document.getElementById("add_button");
    const subtractButton = document.getElementById("subtract_button");
    const clearButton = document.getElementById("clear_button");
    const currentTotalElement = document.getElementById("current_total");
    const historyList = document.getElementById("history_list");
    const emptyHistory = document.getElementById("empty_history");
    const applyToFormButton = document.getElementById("apply_to_form_button");
    const leftNumberInput = document.getElementById("number_input");
    const currentDateElement = document.getElementById("current_date");

    const textInput = document.getElementById("text_input");
    const numberInput = document.getElementById("number_input");
    const commentInput = document.getElementById("comment_input");

    const STORAGE_TOTAL_KEY = "kassensturz_current_total";
    const STORAGE_HISTORY_KEY = "kassensturz_history";
    const STORAGE_LANGUAGE_KEY = "kassensturz_language";
    const STORAGE_THEME_KEY = "kassensturz_theme";

    const translations = {
        en: {
            html_lang: "en",
            form_title: "Input Form",
            date_prefix: "Date: ",
            event_name: "Event name",
            event_name_placeholder: "Enter event name",
            cash_sum: "Cash sum",
            cash_sum_placeholder: "Enter cash amount",
            comment: "Comment (optional)",
            comment_placeholder: "Enter comment (optional)",
            confirm: "Confirm",
            submitted_values: "Submitted values",
            submitted_date: "Date",
            timestamp: "Timestamp",
            live_calculation: "Live Calculation",
            calc_input: "Number for calculation",
            calc_input_placeholder: "Enter number to add or subtract",
            current_total: "Current total",
            apply_result: "Apply result to form",
            clear_history: "Clear Session History",
            session_history: "Session History",
            no_history: "No calculations yet.",
            language: "Language:",
            theme: "Theme:",
            theme_dark: "Dark",
            theme_light: "Light"
        },
        de: {
            html_lang: "de",
            form_title: "Eingabeformular",
            date_prefix: "Datum: ",
            event_name: "Ereignisname",
            event_name_placeholder: "Ereignisname eingeben",
            cash_sum: "Bargeldsumme",
            cash_sum_placeholder: "Bargeldbetrag eingeben",
            comment: "Kommentar (optional)",
            comment_placeholder: "Kommentar eingeben (optional)",
            confirm: "Bestätigen",
            submitted_values: "Übermittelte Werte",
            submitted_date: "Datum",
            timestamp: "Zeitstempel",
            live_calculation: "Live-Berechnung",
            calc_input: "Zahl für die Berechnung",
            calc_input_placeholder: "Zahl zum Addieren oder Subtrahieren eingeben",
            current_total: "Aktueller Gesamtbetrag",
            apply_result: "Ergebnis ins Formular übernehmen",
            clear_history: "Sitzungsverlauf löschen",
            session_history: "Sitzungsverlauf",
            no_history: "Noch keine Berechnungen.",
            language: "Sprache:",
            theme: "Design:",
            theme_dark: "Dunkel",
            theme_light: "Hell"
        }
    };

    function getCurrentLanguage() {
        return localStorage.getItem(STORAGE_LANGUAGE_KEY) || "en";
    }

    function getCurrentTheme() {
        return localStorage.getItem(STORAGE_THEME_KEY) || "dark";
    }

    function t(key) {
        const lang = getCurrentLanguage();
        return translations[lang][key];
    }

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = value;
        }
    }

    function applyTheme() {
        const theme = getCurrentTheme();
        document.body.setAttribute("data-theme", theme);
    }

    function updateLanguageButtons() {
        const langButtons = document.querySelectorAll(".lang-button");
        const currentLang = getCurrentLanguage();

        langButtons.forEach((button) => {
            if (button.dataset.lang === currentLang) {
                button.classList.add("active");
            } else {
                button.classList.remove("active");
            }
        });
    }

    function updateThemeButtons() {
        const themeButtons = document.querySelectorAll(".theme-button");
        const currentTheme = getCurrentTheme();

        themeButtons.forEach((button) => {
            if (button.dataset.theme === currentTheme) {
                button.classList.add("active");
            } else {
                button.classList.remove("active");
            }
        });
    }

    function applyTranslations() {
        const lang = getCurrentLanguage();
        document.documentElement.lang = translations[lang].html_lang;

        setText("form_title", t("form_title"));
        setText("label_event_name", t("event_name"));
        setText("label_cash_sum", t("cash_sum"));
        setText("label_comment", t("comment"));
        setText("confirm_button", t("confirm"));

        setText("submitted_values_title", t("submitted_values"));
        setText("submitted_date_label", t("submitted_date") + ":");
        setText("submitted_timestamp_label", t("timestamp") + ":");
        setText("submitted_event_name_label", t("event_name") + ":");
        setText("submitted_cash_sum_label", t("cash_sum") + ":");
        setText("submitted_comment_label", t("comment").replace(" (optional)", "") + ":");

        setText("calc_title", t("live_calculation"));
        setText("label_calc_input", t("calc_input"));
        setText("current_total_label", t("current_total"));
        setText("apply_to_form_button", t("apply_result"));
        setText("clear_button", t("clear_history"));
        setText("history_title", t("session_history"));
        setText("language_label", t("language"));
        setText("theme_label", t("theme"));
        setText("theme_dark_button", t("theme_dark"));
        setText("theme_light_button", t("theme_light"));

        if (textInput) {
            textInput.placeholder = t("event_name_placeholder");
        }

        if (numberInput) {
            numberInput.placeholder = t("cash_sum_placeholder");
        }

        if (commentInput) {
            commentInput.placeholder = t("comment_placeholder");
        }

        if (calcInput) {
            calcInput.placeholder = t("calc_input_placeholder");
        }
    }

    function formatDate(date) {
        const lang = getCurrentLanguage();
        return date.toLocaleDateString(lang === "de" ? "de-DE" : "en-US", {
            year: "numeric",
            month: "long",
            day: "numeric"
        });
    }

    function setCurrentDate() {
        if (!currentDateElement) {
            return;
        }

        const now = new Date();
        currentDateElement.textContent = t("date_prefix") + formatDate(now);
    }

    function setCurrentLanguage(lang) {
        localStorage.setItem(STORAGE_LANGUAGE_KEY, lang);
        applyTranslations();
        setCurrentDate();
        updateLanguageButtons();
        render();
    }

    function bindLanguageEvents() {
        document.querySelectorAll(".lang-button").forEach((button) => {
            button.addEventListener("click", function () {
                setCurrentLanguage(button.dataset.lang);
            });
        });
    }

    function bindThemeEvents() {
        document.querySelectorAll(".theme-button").forEach((button) => {
            button.addEventListener("click", function () {
                localStorage.setItem(STORAGE_THEME_KEY, button.dataset.theme);
                applyTheme();
                updateThemeButtons();
            });
        });
    }

    function loadTotal() {
        const stored = sessionStorage.getItem(STORAGE_TOTAL_KEY);
        return stored ? parseFloat(stored) : 0;
    }

    function loadHistory() {
        const stored = sessionStorage.getItem(STORAGE_HISTORY_KEY);
        return stored ? JSON.parse(stored) : [];
    }

    function saveTotal(total) {
        sessionStorage.setItem(STORAGE_TOTAL_KEY, total);
    }

    function saveHistory(history) {
        sessionStorage.setItem(STORAGE_HISTORY_KEY, JSON.stringify(history));
    }

    function formatNumber(value) {
        if (Number.isInteger(value)) {
            return value.toString();
        }
        return value.toFixed(2).replace(/\.00$/, "");
    }

    function render() {
        const total = loadTotal();
        const history = loadHistory();

        if (currentTotalElement) {
            currentTotalElement.textContent = formatNumber(total);
        }

        if (!historyList || !emptyHistory) {
            return;
        }

        historyList.innerHTML = "";

        if (history.length === 0) {
            emptyHistory.style.display = "block";
            emptyHistory.textContent = t("no_history");
        } else {
            emptyHistory.style.display = "none";

            history.forEach((entry) => {
                const li = document.createElement("li");
                li.textContent = entry;
                historyList.appendChild(li);
            });
        }
    }

    function applyOperation(operator) {
        if (!calcInput) {
            return;
        }

        const rawValue = calcInput.value.trim();

        if (rawValue === "") {
            return;
        }

        const inputValue = parseFloat(rawValue);

        if (isNaN(inputValue)) {
            return;
        }

        let total = loadTotal();
        const history = loadHistory();
        const previousTotal = total;

        if (operator === "+") {
            total += inputValue;
        } else if (operator === "-") {
            total -= inputValue;
        }

        const historyEntry =
            `${formatNumber(previousTotal)} ${operator} ${formatNumber(inputValue)} = ${formatNumber(total)}`;

        history.unshift(historyEntry);

        saveTotal(total);
        saveHistory(history);

        calcInput.value = "";
        render();
    }

    function clearSession() {
        sessionStorage.removeItem(STORAGE_TOTAL_KEY);
        sessionStorage.removeItem(STORAGE_HISTORY_KEY);
        render();
    }

    function applyResultToForm() {
        if (!leftNumberInput) {
            return;
        }

        const total = loadTotal();
        leftNumberInput.value = total;

        leftNumberInput.style.border = "2px solid #28a745";
        setTimeout(() => {
            leftNumberInput.style.border = "";
        }, 600);
    }

    function clearOnReloadIfNeeded() {
        const navigationEntries = performance.getEntriesByType("navigation");
        const isReload = navigationEntries.length > 0 && navigationEntries[0].type === "reload";

        if (isReload) {
            sessionStorage.removeItem(STORAGE_TOTAL_KEY);
            sessionStorage.removeItem(STORAGE_HISTORY_KEY);
        }
    }

    function bindCalculatorEvents() {
        if (addButton) {
            addButton.addEventListener("click", function () {
                applyOperation("+");
            });
        }

        if (subtractButton) {
            subtractButton.addEventListener("click", function () {
                applyOperation("-");
            });
        }

        if (clearButton) {
            clearButton.addEventListener("click", function () {
                clearSession();
            });
        }

        if (applyToFormButton) {
            applyToFormButton.addEventListener("click", function () {
                applyResultToForm();
            });
        }

        if (calcInput) {
            calcInput.addEventListener("keydown", function (event) {
                if (event.key === "Enter") {
                    event.preventDefault();
                    applyOperation("+");
                }
            });
        }
    }

    function initSaveErrorState() {
        const saveErrorBox = document.getElementById("save_error_box");
        const saveErrorMessage = document.getElementById("save_error_message");

        if (saveErrorBox && saveErrorMessage && !saveErrorMessage.textContent.trim()) {
            saveErrorBox.style.display = "none";
        }
    }

    clearOnReloadIfNeeded();
    applyTheme();
    applyTranslations();
    updateLanguageButtons();
    updateThemeButtons();
    setCurrentDate();
    bindLanguageEvents();
    bindThemeEvents();
    bindCalculatorEvents();
    initSaveErrorState();
    render();
});