import { initCalculator } from "./calculator.js";
import {
    applyTranslations,
    bindLanguageEvents,
    setCurrentDate,
    t,
    updateLanguageButtons
} from "./languageswitching.js";
import {
    applyTheme,
    bindThemeEvents,
    updateThemeButtons
} from "./theme.js";

document.addEventListener("DOMContentLoaded", function () {
    const calculator = initCalculator({
        calcInput: document.getElementById("calc_input"),
        addButton: document.getElementById("add_button"),
        subtractButton: document.getElementById("subtract_button"),
        clearButton: document.getElementById("clear_button"),
        currentTotalElement: document.getElementById("current_total"),
        historyList: document.getElementById("history_list"),
        emptyHistory: document.getElementById("empty_history"),
        applyToFormButton: document.getElementById("apply_to_form_button"),
        leftNumberInput: document.getElementById("number_input"),
        t
    });

    function initSaveErrorState() {
        const saveErrorBox = document.getElementById("save_error_box");
        const saveErrorMessage = document.getElementById("save_error_message");

        if (saveErrorBox && saveErrorMessage && !saveErrorMessage.textContent.trim()) {
            saveErrorBox.style.display = "none";
        }
    }

    applyTheme();
    applyTranslations();
    updateLanguageButtons();
    updateThemeButtons();
    setCurrentDate();

    bindLanguageEvents(function () {
        calculator.render();
    });

    bindThemeEvents();
    initSaveErrorState();
});