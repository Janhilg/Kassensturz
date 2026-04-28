import {
    applyTranslations,
    bindLanguageEvents,
    setCurrentDate,
    updateLanguageButtons
} from "./languageswitching.js";

const STORAGE_THEME_KEY = "kassensturz_theme";

function getCurrentTheme() {
    return localStorage.getItem(STORAGE_THEME_KEY) || "dark";
}

function applyTheme(theme) {
    document.body.setAttribute("data-theme", theme);
}

function updateThemeButtons() {
    const currentTheme = getCurrentTheme();

    document.querySelectorAll(".theme-button").forEach((button) => {
        button.classList.toggle("active", button.dataset.theme === currentTheme);
    });
}

function setTheme(theme) {
    localStorage.setItem(STORAGE_THEME_KEY, theme);
    applyTheme(theme);
    updateThemeButtons();
}

function bindThemeEvents() {
    document.querySelectorAll(".theme-button").forEach((button) => {
        button.addEventListener("click", function () {
            setTheme(button.dataset.theme);
        });
    });
}

document.addEventListener("DOMContentLoaded", function () {
    applyTheme(getCurrentTheme());
    updateThemeButtons();

    applyTranslations();
    setCurrentDate();
    updateLanguageButtons();

    bindLanguageEvents(function () {
        applyTranslations();
        setCurrentDate();
    });

    bindThemeEvents();
});