const tg = window.Telegram.WebApp;
const API_BASE = "/api";
const CURRENCY = "TMT";
const screens = ["language", "master", "service", "datetime", "contact", "confirm", "success"];

const I18N = {
    ru: {
        master_title: "Выберите мастера",
        master_subtitle: "Кто будет вас стричь?",
        service_title: "Выберите услугу",
        service_subtitle: "Что будем делать?",
        datetime_title: "Дата и время",
        datetime_subtitle: "Когда вам удобно?",
        time_label: "Время",
        contact_title: "Ваши данные",
        contact_subtitle: "Как с вами связаться?",
        name_label: "Имя",
        name_placeholder: "Иван Иванов",
        phone_label: "Телефон",
        confirm_title: "Всё верно?",
        confirm_subtitle: "Проверьте детали записи",
        summary_master: "Мастер",
        summary_service: "Услуга",
        summary_date: "Дата",
        summary_time: "Время",
        summary_name: "Имя",
        summary_phone: "Телефон",
        summary_price: "Стоимость",
        success_title: "Заявка отправлена!",
        success_text: "Мастер подтвердит запись в течение часа. Ответ придёт сюда, в этот чат.",
        btn_next: "Далее",
        btn_confirm: "Подтвердить запись",
        btn_close: "Закрыть",
        error_contact: "Введите корректные имя и телефон",
        no_slots: "Нет свободных слотов на эту дату",
        booking_conflict: "Не удалось создать запись: слот мог быть уже занят. Попробуйте выбрать другое время.",
        min_duration: "мин",
        weekdays: ["вс", "пн", "вт", "ср", "чт", "пт", "сб"],
    },
    tk: {
        master_title: "Ussany saýlaň",
        master_subtitle: "Sizi kim saç kesip berer?",
        service_title: "Hyzmaty saýlaň",
        service_subtitle: "Näme ederis?",
        datetime_title: "Sene we wagt",
        datetime_subtitle: "Haçan amatly?",
        time_label: "Wagt",
        contact_title: "Maglumatlaryňyz",
        contact_subtitle: "Siz bilen nähili habarlaşmaly?",
        name_label: "Ady",
        name_placeholder: "Aman Amanow",
        phone_label: "Telefon",
        confirm_title: "Hemmesi dogrymy?",
        confirm_subtitle: "Ýazgynyň jikme-jikliklerini barlaň",
        summary_master: "Ussa",
        summary_service: "Hyzmat",
        summary_date: "Sene",
        summary_time: "Wagt",
        summary_name: "Ady",
        summary_phone: "Telefon",
        summary_price: "Bahasy",
        success_title: "Ýüztutma iberildi!",
        success_text: "Ussa bir sagadyň dowamynda ýazgyny tassyklar. Jogap şu çata geler.",
        btn_next: "Indiki",
        btn_confirm: "Ýazgyny tassykla",
        btn_close: "Ýap",
        error_contact: "Dogry ady we telefon belgisini giriziň",
        no_slots: "Bu sene üçin boş wagt ýok",
        booking_conflict: "Ýazgy döredip bolmady: wagt eýýäm alnan bolup biler. Başga wagt saýlaň.",
        min_duration: "min",
        weekdays: ["Ýb", "Du", "Si", "Ça", "Pe", "An", "Şe"],
    },
};

let currentLang = localStorage.getItem("lang");

function t(key) {
    const lang = I18N[currentLang] ? currentLang : "ru";
    return I18N[lang][key] || key;
}

function applyTranslations() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
        el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
        el.placeholder = t(el.dataset.i18nPlaceholder);
    });
    document.getElementById("lang-toggle").textContent = currentLang === "tk" ? "TM" : "RU";
}

function localizedName(obj) {
    return currentLang === "tk" ? obj.name_tk : obj.name_ru;
}

function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem("lang", lang);
    applyTranslations();
    renderDates();
    loadMasters();
    loadServices();
}

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

    if (screen === "language") {
        tg.BackButton.hide();
        tg.MainButton.hide();
        return;
    }

    if (screen === "success") {
        tg.BackButton.hide();
        tg.MainButton.setParams({ text: t("btn_close"), is_active: true, is_visible: true });
        return;
    }

    if (currentScreenIndex === 0) {
        tg.BackButton.hide();
    } else {
        tg.BackButton.show();
    }

    tg.MainButton.setParams({
        text: screen === "confirm" ? t("btn_confirm") : t("btn_next"),
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
            "X-Telegram-Init-Data": tg.initData,
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

function initLanguageScreen() {
    document.querySelectorAll(".lang-item").forEach((item) => {
        item.addEventListener("click", () => {
            setLanguage(item.dataset.lang);
            showScreen("master");
        });
    });
    document.getElementById("lang-toggle").addEventListener("click", () => {
        showScreen("language");
    });
}

async function loadMasters() {
    const masters = await apiFetch("/masters");
    const list = document.getElementById("master-list");
    list.innerHTML = "";
    masters.forEach((m) => {
        const item = document.createElement("div");
        item.className = "list-item";
        item.innerHTML = `
            <div class="item-avatar">${escapeHtml(localizedName(m).charAt(0).toUpperCase())}</div>
            <div class="item-body"><span class="name">${escapeHtml(localizedName(m))}</span></div>
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
                <span class="name">${escapeHtml(localizedName(s))}</span>
                <span class="meta">${s.duration_minutes} ${t("min_duration")} · ${s.price} ${CURRENCY}</span>
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
        chip.textContent = `${t("weekdays")[d.getDay()]} ${d.getDate()}.${String(d.getMonth() + 1).padStart(2, "0")}`;
        chip.dataset.dayIndex = d.getDay();
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
        slotList.innerHTML = `<p class="error-text">${t("no_slots")}</p>`;
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
    const phoneDigits = phoneInput.value.trim();

    if (name.length < 2 || !/^\d{8}$/.test(phoneDigits)) {
        if (showErrors) {
            errorEl.textContent = t("error_contact");
        }
        return false;
    }
    errorEl.textContent = "";
    state.name = name;
    state.phone = "+993" + phoneDigits;
    return true;
}

document.getElementById("client-name").addEventListener("input", updateNavButtons);
document.getElementById("client-phone").addEventListener("input", (e) => {
    e.target.value = e.target.value.replace(/\D/g, "").slice(0, 8);
    updateNavButtons();
});

function renderSummary() {
    const summary = document.getElementById("summary");
    summary.innerHTML = `
        <div class="row"><span class="label">${t("summary_master")}</span><span>${escapeHtml(localizedName(state.master))}</span></div>
        <div class="row"><span class="label">${t("summary_service")}</span><span>${escapeHtml(localizedName(state.service))}</span></div>
        <div class="row"><span class="label">${t("summary_date")}</span><span>${state.date}</span></div>
        <div class="row"><span class="label">${t("summary_time")}</span><span>${state.slot.slot_time.slice(0, 5)}</span></div>
        <div class="row"><span class="label">${t("summary_name")}</span><span>${escapeHtml(state.name)}</span></div>
        <div class="row"><span class="label">${t("summary_phone")}</span><span>${escapeHtml(state.phone)}</span></div>
        <div class="row total"><span class="label">${t("summary_price")}</span><span>${state.service.price} ${CURRENCY}</span></div>
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
                language: I18N[currentLang] ? currentLang : "ru",
            }),
        });
        tg.MainButton.hideProgress();
        showScreen("success");
    } catch (e) {
        tg.MainButton.hideProgress();
        tg.showAlert(t("booking_conflict"));
        showScreen("datetime");
        loadSlots();
    }
}

async function init() {
    tg.ready();
    tg.expand();
    initLanguageScreen();
    renderDates();
    applyTranslations();
    await Promise.all([loadMasters(), loadServices()]);
    showScreen(I18N[currentLang] ? "master" : "language");
}

init();
