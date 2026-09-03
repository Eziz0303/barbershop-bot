const tg = window.Telegram.WebApp;
const initData = tg.initData;
const API_BASE = "/api";
const PHONE_REGEX = /^\+?\d{10,15}$/;
const WEEKDAYS = ["вс", "пн", "вт", "ср", "чт", "пт", "сб"];
const screens = ["master", "service", "datetime", "contact", "confirm", "success"];

const state = {
    master: null,
    service: null,
    date: null,
    slot: null,
    name: "",
    phone: "",
};

let currentScreenIndex = 0;

function showScreen(name) {
    document.querySelectorAll(".screen").forEach((el) => el.classList.remove("active"));
    document.getElementById(`screen-${name}`).classList.add("active");
    currentScreenIndex = screens.indexOf(name);
    updateProgress();
    updateNavButtons();
}

function updateProgress() {
    const screen = screens[currentScreenIndex];
    const stepIndex = screens.indexOf(screen);
    document.querySelectorAll(".progress .dot").forEach((dot) => {
        const dotIndex = screens.indexOf(dot.dataset.step);
        dot.classList.remove("done", "current");
        if (screen === "success" || dotIndex < stepIndex) {
            dot.classList.add("done");
        } else if (dotIndex === stepIndex) {
            dot.classList.add("current");
        }
    });
}

function checkCanProceed() {
    switch (screens[currentScreenIndex]) {
        case "master":
            return !!state.master;
        case "service":
            return !!state.service;
        case "datetime":
            return !!state.slot;
        case "contact":
            return validateContact(false);
        case "confirm":
            return true;
        default:
            return false;
    }
}

function updateNavButtons() {
    const screen = screens[currentScreenIndex];

    if (screen === "success") {
        tg.BackButton.hide();
        tg.MainButton.setParams({ text: "Закрыть", is_active: true, is_visible: true });
        return;
    }

    if (currentScreenIndex === 0) {
        tg.BackButton.hide();
    } else {
        tg.BackButton.show();
    }

    tg.MainButton.setParams({
        text: screen === "confirm" ? "Подтвердить запись" : "Далее",
        is_active: checkCanProceed(),
        is_visible: true,
    });
}

tg.BackButton.onClick(() => {
    if (currentScreenIndex > 0) {
        showScreen(screens[currentScreenIndex - 1]);
    }
});

tg.MainButton.onClick(() => {
    const screen = screens[currentScreenIndex];

    if (screen === "success") {
        tg.close();
        return;
    }
    if (screen === "contact" && !validateContact(true)) {
        return;
    }
    if (!checkCanProceed()) {
        return;
    }
    if (screen === "confirm") {
        submitBooking();
        return;
    }

    const next = screens[currentScreenIndex + 1];
    if (next === "confirm") renderSummary();
    showScreen(next);
});

async function apiFetch(path, options = {}) {
    const res = await fetch(API_BASE + path, {
        ...options,
        headers: {
            "X-Telegram-Init-Data": initData,
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ? JSON.stringify(err.detail) : `HTTP ${res.status}`);
    }
    return res.json();
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

async function loadMasters() {
    const masters = await apiFetch("/masters");
    const list = document.getElementById("master-list");
    list.innerHTML = "";
    masters.forEach((m) => {
        const item = document.createElement("div");
        item.className = "list-item";
        item.innerHTML = `
            <div class="item-avatar">${escapeHtml(m.name.charAt(0).toUpperCase())}</div>
            <div class="item-body"><span class="name">${escapeHtml(m.name)}</span></div>
            <div class="item-check"></div>
        `;
        item.addEventListener("click", () => {
            state.master = m;
            [...list.children].forEach((c) => c.classList.remove("selected"));
            item.classList.add("selected");
            updateNavButtons();
        });
        list.appendChild(item);
    });
}

async function loadServices() {
    const services = await apiFetch("/services");
    const list = document.getElementById("service-list");
    list.innerHTML = "";
    services.forEach((s) => {
        const item = document.createElement("div");
        item.className = "list-item";
        item.innerHTML = `
            <div class="item-icon">✂️</div>
            <div class="item-body">
                <span class="name">${escapeHtml(s.name)}</span>
                <span class="meta">${s.duration_minutes} мин · ${s.price} ₽</span>
            </div>
            <div class="item-check"></div>
        `;
        item.addEventListener("click", () => {
            state.service = s;
            [...list.children].forEach((c) => c.classList.remove("selected"));
            item.classList.add("selected");
            updateNavButtons();
        });
        list.appendChild(item);
    });
}

function renderDates() {
    const dateList = document.getElementById("date-list");
    dateList.innerHTML = "";
    const today = new Date();
    for (let i = 1; i <= 7; i++) {
        const d = new Date(today);
        d.setDate(d.getDate() + i);
        const iso = d.toISOString().slice(0, 10);
        const chip = document.createElement("div");
        chip.className = "chip";
        chip.textContent = `${WEEKDAYS[d.getDay()]} ${d.getDate()}.${String(d.getMonth() + 1).padStart(2, "0")}`;
        chip.addEventListener("click", () => {
            state.date = iso;
            state.slot = null;
            [...dateList.children].forEach((c) => c.classList.remove("selected"));
            chip.classList.add("selected");
            loadSlots();
            updateNavButtons();
        });
        dateList.appendChild(chip);
    }
}

async function loadSlots() {
    const slotList = document.getElementById("slot-list");
    slotList.innerHTML = "";
    if (!state.date || !state.master) return;
    const slots = await apiFetch(`/slots?master_id=${state.master.id}&slot_date=${state.date}`);
    if (slots.length === 0) {
        slotList.innerHTML = `<p class="error-text">Нет свободных слотов на эту дату</p>`;
        return;
    }
    slots.forEach((s) => {
        const chip = document.createElement("div");
        chip.className = "chip";
        chip.textContent = s.slot_time.slice(0, 5);
        chip.addEventListener("click", () => {
            state.slot = s;
            [...slotList.children].forEach((c) => c.classList.remove("selected"));
            chip.classList.add("selected");
            updateNavButtons();
        });
        slotList.appendChild(chip);
    });
}

function validateContact(showErrors) {
    const nameInput = document.getElementById("client-name");
    const phoneInput = document.getElementById("client-phone");
    const errorEl = document.getElementById("contact-error");
    const name = nameInput.value.trim();
    const phone = phoneInput.value.trim();

    if (name.length < 2 || !PHONE_REGEX.test(phone)) {
        if (showErrors) {
            errorEl.textContent = "Введите корректные имя и телефон (например +79991234567)";
        }
        return false;
    }
    errorEl.textContent = "";
    state.name = name;
    state.phone = phone;
    return true;
}

document.getElementById("client-name").addEventListener("input", updateNavButtons);
document.getElementById("client-phone").addEventListener("input", updateNavButtons);

function renderSummary() {
    const summary = document.getElementById("summary");
    summary.innerHTML = `
        <div class="row"><span class="label">Мастер</span><span>${escapeHtml(state.master.name)}</span></div>
        <div class="row"><span class="label">Услуга</span><span>${escapeHtml(state.service.name)}</span></div>
        <div class="row"><span class="label">Дата</span><span>${state.date}</span></div>
        <div class="row"><span class="label">Время</span><span>${state.slot.slot_time.slice(0, 5)}</span></div>
        <div class="row"><span class="label">Имя</span><span>${escapeHtml(state.name)}</span></div>
        <div class="row"><span class="label">Телефон</span><span>${escapeHtml(state.phone)}</span></div>
        <div class="row total"><span class="label">Стоимость</span><span>${state.service.price} ₽</span></div>
    `;
}

async function submitBooking() {
    tg.MainButton.showProgress(false);
    try {
        await apiFetch("/booking", {
            method: "POST",
            body: JSON.stringify({
                master_id: state.master.id,
                service_id: state.service.id,
                slot_id: state.slot.id,
                client_name: state.name,
                client_phone: state.phone,
            }),
        });
        tg.MainButton.hideProgress();
        showScreen("success");
    } catch (e) {
        tg.MainButton.hideProgress();
        tg.showAlert("Не удалось создать запись: слот мог быть уже занят. Попробуйте выбрать другое время.");
        showScreen("datetime");
        loadSlots();
    }
}

async function init() {
    tg.ready();
    tg.expand();
    renderDates();
    await Promise.all([loadMasters(), loadServices()]);
    showScreen("master");
}

init();
