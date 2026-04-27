const STORAGE_LANGUAGE_KEY = "kassensturz_language";

const translations = {
    en: {
        html_lang: "en",
        form_title: "Input Form",
        date_prefix: "Date: ",
        event_name: "Event",
        event_name_placeholder: "Enter event name",

        counted_by: "Counted by",
        counted_by_placeholder: "Enter name of person counting",

        cash_sum: "Cash sum",
        cash_sum_placeholder: "Enter cash amount",

        event_state: "Event status",
        event_state_opening: "Opening",
        event_state_closing: "Closing",

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
        clear_calculator: "Clear calculator",
        session_history: "Session History",
        no_history: "No calculations yet.",

        language: "Language:",
        theme: "Theme:",
        theme_dark: "Dark",
        theme_light: "Light",

        debug_mode: "DEBUG MODE",

        success: "Success",
        upload_success: "Upload to Nextcloud successful",

        calculator_mode: "Calculator",
        cash_counter_mode: "Cash counter",
        cash_counter_title: "Euro cash counter",
        cash_counter_total: "Cash counter total",
        clear_cash_counter: "Clear cash counter",

        bills: "Bills",
        coins: "Coins"
    },

    de: {
        html_lang: "de",
        form_title: "Eingabeformular",
        date_prefix: "Datum: ",

        event_name: "Veranstaltung",
        event_name_placeholder: "Veranstaltung eingeben",

        counted_by: "Gezählt von",
        counted_by_placeholder: "Name der zählenden Person eingeben",

        cash_sum: "Bargeldsumme",
        cash_sum_placeholder: "Bargeldbetrag eingeben",

        event_state: "Status",
        event_state_opening: "Öffnung",
        event_state_closing: "Schließung",

        comment: "Kommentar (optional)",
        comment_placeholder: "Kommentar eingeben (optional)",

        confirm: "Bestätigen",

        submitted_values: "Übermittelte Werte",
        submitted_date: "Datum",
        timestamp: "Zeitstempel",

        live_calculation: "Berechnung",
        calc_input: "Zahl",
        calc_input_placeholder: "Zahl eingeben",
        current_total: "Gesamtsumme",

        apply_result: "Ergebnis übernehmen",
        clear_calculator: "Rechner zurücksetzen",
        session_history: "Verlauf",
        no_history: "Noch keine Berechnungen.",

        language: "Sprache:",
        theme: "Design:",
        theme_dark: "Dunkel",
        theme_light: "Hell",

        debug_mode: "DEBUG-MODUS",

        success: "Erfolg",
        upload_success: "Upload zu Nextcloud erfolgreich",

        calculator_mode: "Rechner",
        cash_counter_mode: "Geldzähler",
        cash_counter_title: "Bargeldzähler",
        cash_counter_total: "Gesamtsumme",
        clear_cash_counter: "Zähler leeren",

        bills: "Scheine",
        coins: "Münzen"
    }
};

export function getCurrentLanguage() {
    return localStorage.getItem(STORAGE_LANGUAGE_KEY) || "en";
}

export function t(key) {
    const lang = getCurrentLanguage();
    return translations[lang][key] || key;
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = value;
    }
}

export function formatDate(date) {
    const lang = getCurrentLanguage();
    return date.toLocaleDateString(lang === "de" ? "de-DE" : "en-US", {
        year: "numeric",
        month: "long",
        day: "numeric"
    });
}

export function setCurrentDate() {
    const el = document.getElementById("current_date");
    if (!el) return;

    el.textContent = t("date_prefix") + formatDate(new Date());
}

export function updateLanguageButtons() {
    const buttons = document.querySelectorAll(".lang-button");
    const currentLang = getCurrentLanguage();

    buttons.forEach((button) => {
        button.classList.toggle("active", button.dataset.lang === currentLang);
    });
}

export function applyTranslations() {
    const lang = getCurrentLanguage();
    document.documentElement.lang = translations[lang].html_lang;

    setText("form_title", t("form_title"));
    setText("label_event_name", t("event_name"));
    setText("label_counted_by", t("counted_by"));
    setText("label_cash_sum", t("cash_sum"));
    setText("label_event_state", t("event_state"));
    setText("event_state_opening_label", t("event_state_opening"));
    setText("event_state_closing_label", t("event_state_closing"));
    setText("label_comment", t("comment"));
    setText("confirm_button", t("confirm"));

    setText("submitted_values_title", t("submitted_values"));
    setText("submitted_date_label", t("submitted_date") + ":");
    setText("submitted_timestamp_label", t("timestamp") + ":");
    setText("submitted_event_name_label", t("event_name") + ":");
    setText("submitted_counted_by_label", t("counted_by") + ":");
    setText("submitted_cash_sum_label", t("cash_sum") + ":");
    setText("submitted_event_state_label", t("event_state") + ":");
    setText("submitted_comment_label", t("comment").replace(" (optional)", "") + ":");

    setText("calc_title", t("live_calculation"));
    setText("label_calc_input", t("calc_input"));
    setText("current_total_label", t("current_total"));
    setText("apply_to_form_button", t("apply_result"));
    setText("clear_button", t("clear_calculator"));
    setText("history_title", t("session_history"));
    setText("language_label", t("language"));
    setText("theme_label", t("theme"));
    setText("theme_dark_button", t("theme_dark"));
    setText("theme_light_button", t("theme_light"));
    setText("debug_banner", t("debug_mode"));

    setText("mode_calculator_button", t("calculator_mode"));
    setText("mode_cash_counter_button", t("cash_counter_mode"));
    setText("cash_counter_title", t("cash_counter_title"));
    setText("cash_counter_total_label", t("cash_counter_total"));
    setText("clear_cash_counter_button", t("clear_cash_counter"));

    setText("bills_label", t("bills"));
    setText("coins_label", t("coins"));

    const textInput = document.getElementById("text_input");
    const countedByInput = document.getElementById("counted_by_input");
    const numberInput = document.getElementById("number_input");
    const commentInput = document.getElementById("comment_input");

    if (textInput) textInput.placeholder = t("event_name_placeholder");
    if (countedByInput) countedByInput.placeholder = t("counted_by_placeholder");
    if (numberInput) numberInput.placeholder = t("cash_sum_placeholder");
    if (commentInput) commentInput.placeholder = t("comment_placeholder");
}

export function setCurrentLanguage(lang, callback) {
    localStorage.setItem(STORAGE_LANGUAGE_KEY, lang);
    applyTranslations();
    setCurrentDate();
    updateLanguageButtons();
    if (callback) callback();
}

export function bindLanguageEvents(callback) {
    document.querySelectorAll(".lang-button").forEach((button) => {
        button.addEventListener("click", function () {
            setCurrentLanguage(button.dataset.lang, callback);
        });
    });
}