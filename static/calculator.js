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
        t
    } = options;

    const STORAGE_TOTAL_KEY = "kassensturz_current_total";
    const STORAGE_HISTORY_KEY = "kassensturz_history";

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

    clearOnReloadIfNeeded();
    bindEvents();
    render();

    return {
        render
    };
}