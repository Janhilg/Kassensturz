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

        apply_cash_counter_to_form: "Apply result to form",
        apply_cash_counter_to_calculator: "Send total to calculator",

        bills: "Bills",
        coins: "Coins",
        admin_title: "Admin",

        admin_back_to_app: "Back to app",
        admin_access_active: "Admin access active",
        admin_logout_button: "Logout",
        admin_error_title: "Error",
        admin_system_status_title: "System Status",
        admin_database_label: "Database",
        admin_rows_label: "Rows",
        admin_rows_meta: "Entries in DB",
        admin_excel_export_label: "Excel Export",
        admin_text_export_label: "Text Export",
        admin_backups_label: "Backups",
        admin_nextcloud_label: "Nextcloud",
        admin_actions_title: "Actions",
        admin_password_label: "Admin password",
        admin_rebuild_exports_button: "Rebuild exports now",
        admin_sync_now_button: "Sync now",
        admin_restore_backup_title: "Restore Backup",
        admin_restore_button: "Restore",
        admin_no_backups_text: "No backups available.",
        admin_login_title: "Admin Login",
        admin_login_button: "Login",
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

        apply_cash_counter_to_form: "Ergebnis übernehmen",
        apply_cash_counter_to_calculator: "Summe an Rechner senden",

        bills: "Scheine",
        coins: "Münzen",

        admin_title: "Admin",
        admin_back_to_app: "Zur App",
        admin_access_active: "Admin-Zugriff aktiv",
        admin_logout_button: "Abmelden",
        admin_error_title: "Fehler",
        admin_system_status_title: "Systemstatus",
        admin_database_label: "Datenbank",
        admin_rows_label: "Zeilen",
        admin_rows_meta: "Einträge in der DB",
        admin_excel_export_label: "Excel-Export",
        admin_text_export_label: "Text-Export",
        admin_backups_label: "Backups",
        admin_nextcloud_label: "Nextcloud",
        admin_actions_title: "Aktionen",
        admin_password_label: "Admin-Passwort",
        admin_rebuild_exports_button: "Exporte neu erstellen",
        admin_sync_now_button: "Jetzt synchronisieren",
        admin_restore_backup_title: "Backup wiederherstellen",
        admin_restore_button: "Wiederherstellen",
        admin_no_backups_text: "Keine Backups verfügbar.",
        admin_login_title: "Admin-Anmeldung",
        admin_login_button: "Anmelden",
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

    setText("apply_cash_counter_to_form_button", t("apply_cash_counter_to_form"));
    setText("apply_cash_counter_to_calculator_button", t("apply_cash_counter_to_calculator"));

    setText("bills_label", t("bills"));
    setText("coins_label", t("coins"));

    setText("admin_title", t("admin_title"));
    setText("admin_back_to_app", t("admin_back_to_app"));
    setText("admin_access_active", t("admin_access_active"));
    setText("admin_logout_button", t("admin_logout_button"));
    setText("admin_error_title", t("admin_error_title"));
    setText("admin_system_status_title", t("admin_system_status_title"));
    setText("admin_database_label", t("admin_database_label"));
    setText("admin_rows_label", t("admin_rows_label"));
    setText("admin_rows_meta", t("admin_rows_meta"));
    setText("admin_excel_export_label", t("admin_excel_export_label"));
    setText("admin_text_export_label", t("admin_text_export_label"));
    setText("admin_backups_label", t("admin_backups_label"));
    setText("admin_nextcloud_label", t("admin_nextcloud_label"));
    setText("admin_actions_title", t("admin_actions_title"));
    setText("admin_password_label", t("admin_password_label"));
    setText("admin_rebuild_exports_button", t("admin_rebuild_exports_button"));
    setText("admin_sync_now_button", t("admin_sync_now_button"));
    setText("admin_restore_backup_title", t("admin_restore_backup_title"));
    setText("admin_restore_button", t("admin_restore_button"));
    setText("admin_no_backups_text", t("admin_no_backups_text"));
    setText("admin_login_title", t("admin_login_title"));
    setText("admin_login_button", t("admin_login_button"));

    const adminPasswordInput = document.getElementById("admin_password_shared");
    const loginPasswordInput = document.getElementById("password");

    if (adminPasswordInput) adminPasswordInput.placeholder = t("admin_password_label");
    if (loginPasswordInput) loginPasswordInput.placeholder = t("admin_password_label");



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