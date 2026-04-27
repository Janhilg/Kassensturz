const STORAGE_THEME_KEY = "kassensturz_theme";

export function getCurrentTheme() {
    return localStorage.getItem(STORAGE_THEME_KEY) || "dark";
}

export function applyTheme() {
    document.body.setAttribute("data-theme", getCurrentTheme());
}

export function updateThemeButtons() {
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

export function bindThemeEvents() {
    document.querySelectorAll(".theme-button").forEach((button) => {
        button.addEventListener("click", function () {
            localStorage.setItem(STORAGE_THEME_KEY, button.dataset.theme);
            applyTheme();
            updateThemeButtons();
        });
    });
}