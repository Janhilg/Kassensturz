export function initCalculator(options) {
    const {
        calcInput,
        addButton,
        subtractButton,
        clearButton,
        currentTotalElement,
        historyList,
        emptyHistory,
        applyToFormButton,
        leftNumberInput,
        amountInput,
        t
    } = options;

    const STORAGE_TOTAL_KEY = "kassensturz_current_total";
    const STORAGE_HISTORY_KEY = "kassensturz_history";

    const modeCalculatorButton = document.getElementById("mode_calculator_button");
    const modeCashCounterButton = document.getElementById("mode_cash_counter_button");
    const calculatorMode = document.getElementById("calculator_mode");
    const cashCounterMode = document.getElementById("cash_counter_mode");

    const denominationInputs = document.querySelectorAll(".denomination-input");
    const cashCounterTotalElement = document.getElementById("cash_counter_total");
    const applyCashCounterToFormButton = document.getElementById("apply_cash_counter_to_form_button");
    const applyCashCounterToCalculatorButton = document.getElementById("apply_cash_counter_to_calculator_button");
    const clearCashCounterButton = document.getElementById("clear_cash_counter_button");

    function getFormAmountTarget() {
        return leftNumberInput || amountInput || null;
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
        return Number(value).toFixed(2).replace(/\.00$/, "");
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

    function applyResultToForm(value) {
        const targetInput = getFormAmountTarget();
        if (!targetInput) {
            return;
        }

        targetInput.value = formatNumber(value);
        targetInput.dispatchEvent(new Event("input", { bubbles: true }));
        targetInput.dispatchEvent(new Event("change", { bubbles: true }));

        targetInput.style.border = "2px solid #28a745";
        setTimeout(() => {
            targetInput.style.border = "";
        }, 600);
    }

    function applyResultToCalculator(value) {
        if (!calcInput) return;

        switchMode("calculator");

        calcInput.value = formatNumber(value);
        applyOperation("+");

        calcInput.style.border = "2px solid #28a745";
        calcInput.focus();

        setTimeout(() => {
            calcInput.style.border = "";
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

    function switchMode(mode) {
        if (mode === "calculator") {
            if (calculatorMode) calculatorMode.style.display = "block";
            if (cashCounterMode) cashCounterMode.style.display = "none";
            if (modeCalculatorButton) modeCalculatorButton.classList.add("active");
            if (modeCashCounterButton) modeCashCounterButton.classList.remove("active");
        } else {
            if (calculatorMode) calculatorMode.style.display = "none";
            if (cashCounterMode) cashCounterMode.style.display = "block";
            if (modeCalculatorButton) modeCalculatorButton.classList.remove("active");
            if (modeCashCounterButton) modeCashCounterButton.classList.add("active");
        }
    }

    function calculateCashCounterTotal() {
        let total = 0;

        denominationInputs.forEach((input) => {
            const quantity = parseInt(input.value || "0", 10);
            const denominationValue = parseFloat(input.dataset.value || "0");

            if (!isNaN(quantity) && !isNaN(denominationValue)) {
                total += quantity * denominationValue;
            }
        });

        if (cashCounterTotalElement) {
            cashCounterTotalElement.textContent = formatNumber(total);
        }

        return total;
    }

    function changeDenominationValue(inputId, delta) {
        const input = document.getElementById(inputId);
        if (!input) return;

        let value = parseInt(input.value || "0", 10);
        if (isNaN(value)) value = 0;

        value += delta;
        if (value < 0) value = 0;

        input.value = value;
        calculateCashCounterTotal();
    }

    function clearCashCounter() {
        denominationInputs.forEach((input) => {
            input.value = "";
        });
        syncHiddenDenominationFields();
        calculateCashCounterTotal();
    }

    function syncHiddenDenominationFields() {
        denominationInputs.forEach((input) => {
            const hiddenField = document.getElementById(`hidden_${input.id}`);
            if (!hiddenField) return;
            hiddenField.value = input.value || "";
        });
    }

    function bindEvents() {
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
                applyResultToForm(loadTotal());
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

        if (modeCalculatorButton) {
            modeCalculatorButton.addEventListener("click", function () {
                switchMode("calculator");
            });
        }

        if (modeCashCounterButton) {
            modeCashCounterButton.addEventListener("click", function () {
                switchMode("cash_counter");
            });
        }

        denominationInputs.forEach((input) => {
            input.addEventListener("input", function () {
                syncHiddenDenominationFields();
                calculateCashCounterTotal();
            });
        });

        if (applyCashCounterToFormButton) {
            applyCashCounterToFormButton.addEventListener("click", function () {
                syncHiddenDenominationFields();
                applyResultToForm(calculateCashCounterTotal());
            });
        }

        if (applyCashCounterToCalculatorButton) {
            applyCashCounterToCalculatorButton.addEventListener("click", function () {
                applyResultToCalculator(calculateCashCounterTotal());
            });
        }

        if (clearCashCounterButton) {
            clearCashCounterButton.addEventListener("click", function () {
                clearCashCounter();
            });
        }
    }

    document.querySelectorAll(".plus-btn").forEach((btn) => {
        btn.addEventListener("click", function () {
            changeDenominationValue(btn.dataset.target, 1);
        });
    });

    document.querySelectorAll(".minus-btn").forEach((btn) => {
        btn.addEventListener("click", function () {
            changeDenominationValue(btn.dataset.target, -1);
        });
    });

    clearOnReloadIfNeeded();
    bindEvents();
    render();
    syncHiddenDenominationFields();
    calculateCashCounterTotal();
    switchMode("cash_counter");

    return {
        render
    };
}