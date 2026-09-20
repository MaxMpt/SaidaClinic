const ADMIN_ID = "6935237776";
function adminIds() {
  const extra = Array.isArray(window.ADMIN_IDS) ? window.ADMIN_IDS : [];
  const fromData = state.data?.settings?.adminIds || [];
  return [...new Set([ADMIN_ID, ...extra, ...fromData].map(String).filter(Boolean))];
}
function isAdminUser(id) {
  return adminIds().includes(String(id || ""));
}
const INTAKE = [
  ["pregnancy", "Беременность или грудное вскармливание"],
  ["herpes", "Герпес или воспаление на лице"],
  ["blood", "Препараты, разжижающие кровь"],
  ["lidocaine", "Аллергия на лидокаин или анестетики"],
  ["autoimmune", "Аутоиммунное заболевание"],
  ["keloid", "Склонность к келоидным рубцам"],
  ["retinoids", "Сейчас ретиноиды или сильные кислоты"],
  ["diabetes", "Сахарный диабет"],
  ["sun", "Свежий загар или сильная фоточувствительность"],
];
const STATUS = {
  hold: "Ждёт оплату",
  confirmed: "Подтверждена",
  arrived: "В кабинете",
  completed: "Проведена",
  cancelled: "Отменена",
  noshow: "Не пришла",
  expired: "Слот снят",
};
const MONTHS = ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"];
const MONTHS_NOM = ["Январь","Февраль","Март","Апрель","Май","Июнь","Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"];
const WD = ["пн","вт","ср","чт","пт","сб","вс"];
const WD_LONG = ["понедельник","вторник","среда","четверг","пятница","суббота","воскресенье"];

const state = {
  tab: "home",
  data: null,
  profile: { key: "anna", name: "Анна", role: "client" },
  tg: null,
  picked: null,
  reschedule: null,
  overlay: null,
  toast: "",
  careActive: 0,
  chipsOpen: true,
  intakeOpen: false,
  historyOpen: false,
  day: null,
  month: null,
  slots: [],
  grid: [],
  startMin: null,
  adminDay: null,
  prepayDraft: 30,
};

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "\u0026amp;")
    .replaceAll("<", "\u0026lt;")
    .replaceAll(">", "\u0026gt;")
    .replaceAll('"', "\u0026quot;")
    .replaceAll("'", "\u0026#39;");
}
function money(n) { return `${Number(n || 0).toLocaleString("ru-RU")} ₽`; }
function pad(n) { return String(n).padStart(2, "0"); }
function minToTime(m) { return `${pad(Math.floor(m / 60))}:${pad(m % 60)}`; }
function ymd(d) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }
function parseDay(s) { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); }
function isoWd(s) { const d = parseDay(s).getDay(); return d === 0 ? 7 : d; }
function dayLong(s) { const d = parseDay(s); return `${WD_LONG[isoWd(s) - 1]}, ${d.getDate()} ${MONTHS[d.getMonth()]}`; }
function dayShort(s) { const d = parseDay(s); return `${d.getDate()} ${MONTHS[d.getMonth()]}`; }
function csrf() {
  return window.CSRF || (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";
}
function tg() { return window.Telegram?.WebApp; }
function initData() { return tg()?.initData || ""; }
function readUser() { return tg()?.initDataUnsafe?.user || null; }
function haptic(kind) {
  const h = tg()?.HapticFeedback;
  try {
    if (h) {
      if (kind === "success" || kind === "error" || kind === "warning") h.notificationOccurred(kind);
      else if (kind === "select") h.selectionChanged();
      else h.impactOccurred(kind === "heavy" ? "medium" : "light");
    } else if (navigator.vibrate) {
      navigator.vibrate(kind === "error" ? [12, 30, 12] : kind === "heavy" ? 24 : 10);
    }
  } catch (_) {}
}

async function api(path, body) {
  const user = readUser();
  const payload = {
    ...body,
    initData: initData() || undefined,
    clientKey: state.profile.key,
    isAdmin: state.profile.role === "admin",
    telegram: user
      ? { telegramId: String(user.id), firstName: user.first_name, lastName: user.last_name, username: user.username }
      : undefined,
  };
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
    body: JSON.stringify(payload),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.error || "Ошибка");
  return json;
}
function toast(msg) {
  state.toast = msg;
  render();
  setTimeout(() => { if (state.toast === msg) { state.toast = ""; render(); } }, 2200);
}
function bootTg() {
  const w = tg();
  if (!w) return;
  const syncH = () => {
    const h = w.viewportStableHeight || w.viewportHeight || window.innerHeight;
    document.documentElement.style.setProperty("--tg-viewport-stable-height", `${Math.round(h)}px`);
  };
  try {
    w.ready();
    w.expand();
    w.disableVerticalSwipes?.();
    w.setHeaderColor?.("#F6F0ED");
    w.setBackgroundColor?.("#F6F0ED");
    syncH();
    w.onEvent?.("viewportChanged", syncH);
  } catch (_) {}
  const u = readUser();
  if (u?.id) {
    state.tg = u;
    const admin = isAdminUser(u.id);
    state.profile = { key: `tg-${u.id}`, name: u.first_name, role: admin ? "admin" : "client" };
    if (admin) state.tab = "admin";
  }
}
async function load() {
  state.data = await api("/api/bootstrap", {});
  const me = state.data.me || {};
  const admin = !!(me.isAdmin || isAdminUser(me.telegramId) || isAdminUser(state.tg?.id));
  if (admin) {
    state.profile.role = "admin";
    if (state.tab === "home") state.tab = "admin";
  }
  if (me.name) state.profile.name = me.name;
  const c = state.data.client;
  if (c?.telegramId && !c.intakeDone && state.profile.role !== "admin") state.overlay = "intake";
  render();
}

function icon(name) {
  const p = {
    home: "M4 10 12 3l8 7v10H4z",
    cal: "M7 3v3M17 3v3M4 8h16v13H4z",
    drop: "M12 3s7 8 7 12a7 7 0 1 1-14 0c0-4 7-12 7-12z",
    user: "M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-4 0-8 2-8 6h16c0-4-4-6-8-6z",
    left: "M15 5 8 12l7 7",
    right: "M9 5l7 7-7 7",
    down: "M6 9l6 6 6-6",
    card: "M3 7h18v12H3zM3 11h18",
  };
  return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">${name === "home" || name === "drop" || name === "user" || name === "card" ? `<path d="${p[name]}"/>` : `<path d="${p[name]}"/>`}</svg>`;
}

function tabs() {
  const items = [
    ["home", "Главная", "home"],
    ["book", "Запись", "cal"],
    ["care", "Уход", "drop"],
    ["profile", "Профиль", "user"],
  ];
  if (state.profile.role === "admin") items.push(["admin", "Кабинет", "user"]);
  return `<nav class="tabs">${items.map(([id, label, ic]) => `<button class="${state.tab === id ? "on" : ""}" data-tab="${id}">${icon(ic)}<span>${label}</span></button>`).join("")}</nav>`;
}

function home() {
  const d = state.data;
  const next = d.nextSlots?.[0];
  return `<div class="space">
    <div>
      <p class="kicker">Здравствуйте, ${esc(state.profile.name)}</p>
      <h2 class="h2">${esc(d.affirmation || "Я доверяю своему ритму.")}</h2>
    </div>
    <img class="hero" src="/static/clinic-room.jpg" alt="">
    <button class="btn wide" data-go="book">Записаться</button>
    ${next ? `<button class="card" style="width:100%;text-align:left" data-go="book">
      <div class="kicker">Ближайшее окно</div>
      <b>${esc(next.serviceTitle)}</b>
      <div class="sm muted mt">${dayShort(next.day)} в ${minToTime(next.startMin)}</div>
    </button>` : ""}
    ${d.services.map((s) => `<button class="card" style="width:100%;text-align:left" data-pick="${s.id}"><b>${esc(s.title)}</b><div class="sm muted mt">${s.durationMin} мин · ${money(s.price)}</div></button>`).join("")}
    <button class="card" style="width:100%;text-align:left" data-overlay="about"><div class="kicker">О нас</div><div class="sm">Кабинет и подход</div></button>
  </div>`;
}

function book() {
  const d = state.data;
  const sid = state.picked || d.services[0]?.id;
  const s = d.services.find((x) => x.id === sid) || d.services[0];
  const now = new Date();
  const cur = state.month || { y: now.getFullYear(), m: now.getMonth() + 1 };
  const daysIn = new Date(cur.y, cur.m, 0).getDate();
  const startWd = (new Date(cur.y, cur.m - 1, 1).getDay() + 6) % 7;
  const cells = Array(startWd).fill("") + "";
  let grid = WD.map((w) => `<div class="tiny muted" style="text-align:center">${w}</div>`).join("");
  for (let i = 0; i < startWd; i++) grid += `<div></div>`;
  for (let day = 1; day <= daysIn; day++) {
    const ds = `${cur.y}-${pad(cur.m)}-${pad(day)}`;
    const info = (state.grid || []).find((x) => x.date === ds);
    const sel = state.day === ds;
    const cls = ["day", sel ? "sel" : "", info?.available ? "lit" : "mute", info?.closed ? "strike" : ""].join(" ");
    grid += `<button class="${cls}" data-day="${ds}">${day}</button>`;
  }
  return `<div class="space">
    <div>
      <p class="kicker">${state.reschedule ? "Перенос" : "Новая запись"}</p>
      <h2 class="h2">${esc(s?.title || "Процедура")}</h2>
      <p class="sm muted mt">${s ? `${s.durationMin} мин · ${money(s.price)}` : ""}</p>
      ${s ? `<button class="sm" style="color:var(--accent);margin-top:4px" data-svc="${s.id}">Подробнее о процедуре</button>` : ""}
    </div>
    ${state.reschedule ? "" : `<div class="chips">${d.services.map((x) => `<button class="chip ${x.id === s?.id ? "on" : ""}" data-pick="${x.id}">${esc(x.title)}</button>`).join("")}</div>`}
    <div class="row">
      <button data-m="-1">${icon("left")}</button>
      <b>${MONTHS_NOM[cur.m - 1]} ${cur.y}</b>
      <button data-m="1">${icon("right")}</button>
    </div>
    <div class="month">${grid}</div>
    ${state.day ? `<div>
      <p class="sm muted">${dayLong(state.day)}</p>
      <div class="chips">${(state.slots || []).map((t) => `<button class="chip ${state.startMin === t ? "on" : ""}" data-slot="${t}">${minToTime(t)}</button>`).join("") || '<span class="sm muted">Нет окон</span>'}</div>
      ${state.startMin != null ? `<button class="btn wide" data-confirm="1">Записать</button>` : (state.slots?.length === 0 ? `<button class="btn outline wide" data-wait="1">В лист ожидания</button>` : "")}
    </div>` : ""}
  </div>`;
}

function care() {
  const d = state.data;
  const cats = d.careCategories || [];
  const products = d.careProducts || [];
  if (!state.careActive && cats[0]) state.careActive = cats[0].id;
  return `<div>
    <div class="chips" style="margin:0 -4px 8px">
      ${cats.map((c) => `<button class="chip ${state.careActive === c.id ? "on" : ""}" data-jump="${c.id}">${esc(c.title)}</button>`).join("")}
    </div>
    <p class="kicker">Витрина</p>
    <h2 class="h2">Уход домой</h2>
    <p class="sm muted mt">То, что стоит на полке кабинета может стоять у вас дома</p>
    <div style="height:12px"></div>
    ${cats.map((c) => {
      const list = products.filter((p) => p.categoryId === c.id);
      return `<section id="care-cat-${c.id}" style="margin-bottom:28px">
        <h3 class="h3" style="margin-bottom:12px">${esc(c.title)}</h3>
        <div class="grid2">${list.map((p) => `<button class="card" style="padding:0;overflow:hidden;text-align:left" data-prod="${p.id}">
          <div class="sq">${p.photo ? `<img src="${esc(p.photo)}" alt="">` : ""}</div>
          <div style="padding:12px"><div class="sm">${esc(p.title)}</div><div class="tiny muted mt">${esc(p.description)}</div><div class="sm mt">${p.price ? money(p.price) : "по запросу"}</div></div>
        </button>`).join("")}</div>
      </section>`;
    }).join("")}
  </div>`;
}

function visits() {
  const d = state.data;
  const now = new Date();
  const today = ymd(now);
  const mins = now.getHours() * 60 + now.getMinutes();
  const key = state.profile.key;
  const mine = (d.appointments || []).filter((a) => a.clientKey === key);
  const upcoming = mine.filter((a) => ["hold", "confirmed", "arrived"].includes(a.status) && (a.day > today || (a.day === today && a.startMin >= mins)));
  const past = mine.filter((a) => !upcoming.some((u) => u.id === a.id));
  const shown = state.historyOpen || past.length <= 3 ? past : past.slice(0, 3);
  return `<div class="space">
    <h2 class="h3">Визиты</h2>
    ${upcoming.length ? upcoming.map((a) => `<article class="card">
      <div class="row"><div><b>${esc(a.serviceTitle)}</b><div class="sm muted">${dayLong(a.day)} · ${minToTime(a.startMin)}</div></div><span class="badge">${STATUS[a.status] || a.status}</span></div>
      <p class="sm mt">${money(a.price)}</p>
      <div class="chips">
        <button class="btn sm outline" data-reschedule="${a.id}" data-sid="${a.serviceId}">Перенести</button>
        <button class="btn sm ghost" data-cancel="${a.id}">Отменить</button>
        ${a.prepayRequired > a.prepayPaid ? `<button class="btn sm" data-pay="${a.id}">Оплатить</button>` : ""}
      </div>
    </article>`).join("") : `<p class="sm muted">Пока пусто — откройте запись.</p>`}
    ${past.length ? `<section>
      <p class="kicker">История</p>
      ${shown.map((a) => `<div class="card" style="margin-top:8px"><b>${esc(a.serviceTitle)}</b><div class="sm muted">${dayShort(a.day)} · ${minToTime(a.startMin)}</div></div>`).join("")}
      ${past.length > 3 ? `<button class="sm" style="margin-top:8px;color:var(--accent)" data-hist="1">${state.historyOpen ? "Свернуть" : "Показать все"}</button>` : ""}
    </section>` : ""}
  </div>`;
}

function intakeFields(answers) {
  const a = answers || {};
  return INTAKE.map(([k, label]) => `<button class="row" data-int="${k}" style="width:100%;text-align:left">
    <span class="sm">${esc(label)}</span>
    <span class="switch ${a[k] ? "on" : ""}"><i></i></span>
  </button>`).join("") + `<textarea class="field mt" data-note="1" placeholder="Ещё важно сказать" rows="3">${esc(a.note || "")}</textarea>`;
}

function profile() {
  const c = state.data.client || {};
  const answers = c.intake || {};
  const risks = INTAKE.filter(([k]) => answers[k]).length;
  return `${visits()}
    <section class="card" style="padding:0;margin-top:24px" id="intake-card">
      <button class="row" style="width:100%;padding:12px 16px;text-align:left" data-intake="1">
        <div><div class="sm">Анкета рисков</div><div class="tiny muted">${c.intakeDone ? (risks ? `${risks} отмечено` : "Противопоказаний нет") : "Нажмите, чтобы заполнить"}</div></div>
        ${icon("down")}
      </button>
      ${state.intakeOpen ? `<div style="padding:8px 16px 16px;border-top:1px solid var(--line)">${intakeFields(answers)}</div>` : ""}
    </section>`;
}

function admin() {
  const d = state.data;
  const day = state.adminDay || ymd(new Date());
  const list = (d.appointments || []).filter((a) => a.day === day);
  const closed = (d.closedDays || []).includes(day);
  return `<div class="space">
    <div class="row">
      <button data-ad="-1">${icon("left")}</button>
      <div style="text-align:center"><p class="kicker">День</p><h2 class="h3">${dayLong(day)}</h2></div>
      <button data-ad="1">${icon("right")}</button>
    </div>
    <button class="admin-link" data-overlay="prepay">${icon("card")}<span style="flex:1"><b class="sm">Предоплата ${d.settings.prepayEnabled ? d.settings.prepayDefaultPercent + "%" : "выключена"}</b><div class="tiny muted">${d.settings.prepayEnabled ? "Холд от цены процедуры" : "Включить и задать процент"}</div></span></button>
    <button class="admin-link" data-overlay="schedule">${icon("cal")}<span style="flex:1"><b class="sm">Рабочие дни</b><div class="tiny muted">Календарь приёма</div></span></button>
    <button class="admin-link" data-overlay="services">${icon("user")}<span style="flex:1"><b class="sm">Процедуры</b><div class="tiny muted">Прайс и описания</div></span></button>
    <button class="admin-link" data-overlay="careadmin">${icon("drop")}<span style="flex:1"><b class="sm">Уход</b><div class="tiny muted">Витрина косметики</div></span></button>
    <button class="admin-link" data-overlay="aboutadmin">${icon("user")}<span style="flex:1"><b class="sm">О нас</b><div class="tiny muted">Текст и фото</div></span></button>
    ${closed ? `<p class="cream" style="padding:12px 16px" class="sm muted">День закрыт как выходной.</p>` : ""}
    ${list.length ? list.map((a) => `<div class="card"><b>${esc(a.clientName)}</b><div class="sm muted">${minToTime(a.startMin)} · ${esc(a.serviceTitle)}</div>
      <div class="chips mt">
        <button class="btn sm outline" data-st="${a.id}" data-to="arrived">В кабинете</button>
        <button class="btn sm" data-st="${a.id}" data-to="completed">Проведена</button>
      </div></div>`).join("") : `<p class="sm muted">В этот день записей нет.</p>`}
    ${closed ? `<button class="btn outline wide" data-openday="1">Открыть день</button>` : `<button class="btn outline wide" data-closeday="1">Закрыть день как выходной</button>`}
    ${(d.notifications || []).slice(0, 8).map((n) => `<article class="card">
      <div class="sm"><b>${esc(n.title)}</b></div>
      <div class="tiny muted mt">${esc(n.body)}</div>
    </article>`).join("")}
  </div>`;
}

function overlayHtml() {
  const o = state.overlay;
  if (!o) return "";
  const d = state.data;
  if (o === "intake") {
    const a = d.client?.intake || {};
    return `<div class="overlay"><div class="header"><p class="kicker">Анкета</p><h2 class="h3">Перед записью</h2></div><div class="body">${intakeFields(a)}<button class="btn wide mt" data-intake-done="1">Дальше</button></div></div>`;
  }
  if (o === "about") {
    const blocks = d.settings.aboutBlocks || [];
    return `<div class="overlay"><div class="header"><button data-close="1">${icon("left")}</button></div><div class="body"><p class="kicker">О нас</p><h2 class="h2">${esc(d.settings.clinicName)}</h2>${blocks.map((b) => b.type === "image" ? `<img class="photo mt" src="${esc(b.src)}" alt="">` : `<p class="sm mt">${esc(b.text)}</p>`).join("")}</div></div>`;
  }
  if (typeof o === "object" && o.kind === "product") {
    const p = o.p;
    return `<div class="overlay"><div class="header"><button data-close="1">${icon("left")}</button></div><div class="body">
      ${p.photo ? `<img class="hero" src="${esc(p.photo)}" alt="">` : ""}
      <p class="kicker mt">${esc(o.cat)}</p>
      <h2 class="h2">${esc(p.title)}</h2>
      <p class="sm mt">${esc(p.description)}</p>
      ${p.indications ? `<p class="sm mt"><b>Показания.</b> ${esc(p.indications)}</p>` : ""}
      ${p.contraindications ? `<p class="sm mt"><b>Нельзя.</b> ${esc(p.contraindications)}</p>` : ""}
      ${p.composition ? `<p class="sm mt"><b>Состав.</b> ${esc(p.composition)}</p>` : ""}
      <p class="mt"><b>${p.price ? money(p.price) : "по запросу"}</b></p>
      <button class="btn wide mt" data-buy="${p.id}">Купить</button>
    </div></div>`;
  }
  if (typeof o === "object" && o.kind === "service") {
    const s = o.s;
    return `<div class="overlay"><div class="header"><button data-close="1">${icon("left")}</button></div><div class="body">
      <p class="kicker">Процедура</p><h2 class="h2">${esc(s.title)}</h2>
      <p class="sm muted mt">${s.durationMin} мин · ${money(s.price)}</p>
      <p class="sm mt">${esc(s.description)}</p>
      ${s.indications ? `<p class="sm mt"><b>Показания.</b> ${esc(s.indications)}</p>` : ""}
      ${s.contraindications ? `<p class="sm mt"><b>Нельзя.</b> ${esc(s.contraindications)}</p>` : ""}
      ${s.resultText ? `<p class="sm mt"><b>Результат.</b> ${esc(s.resultText)}</p>` : ""}
      ${s.prepText ? `<p class="sm mt"><b>Подготовка.</b> ${esc(s.prepText)}</p>` : ""}
    </div></div>`;
  }
  if (o === "prepay") {
    const on = d.settings.prepayEnabled;
    const pct = state.prepayDraft || d.settings.prepayDefaultPercent || 30;
    return `<div class="overlay"><div class="header"><button data-close="1">${icon("left")}</button><h2 class="h3">Предоплата</h2></div><div class="body">
      <button class="row" style="width:100%" data-prepay-toggle="1"><span>Включена</span><span class="switch ${on ? "on" : ""}"><i></i></span></button>
      <label class="sm muted mt">Процент<input class="field mt" type="number" min="1" max="100" value="${pct}" data-prepay-pct="1"></label>
      <button class="btn wide mt" data-prepay-save="1">Сохранить</button>
    </div></div>`;
  }
  if (o === "services") {
    return `<div class="overlay"><div class="header"><button data-close="1">${icon("left")}</button><h2 class="h3">Процедуры</h2></div><div class="body">
      ${d.services.map((s) => `<div class="card" style="margin-bottom:10px"><b>${esc(s.title)}</b>
        <div class="sm muted">${s.durationMin} мин</div>
        <input class="field mt" type="number" value="${s.price}" data-price="${s.id}">
      </div>`).join("")}
      <button class="btn wide" data-save-prices="1">Сохранить цены</button>
    </div></div>`;
  }
  if (o === "careadmin") {
    return `<div class="overlay"><div class="header"><button data-close="1">${icon("left")}</button><h2 class="h3">Витрина</h2></div><div class="body">
      ${(d.careProducts || []).map((p) => `<div class="card" style="margin-bottom:10px"><b>${esc(p.title)}</b><input class="field mt" type="number" value="${p.price}" data-pprice="${p.id}"></div>`).join("")}
      <button class="btn wide" data-save-pprices="1">Сохранить</button>
    </div></div>`;
  }
  if (o === "aboutadmin") {
    return `<div class="overlay"><div class="header"><button data-close="1">${icon("left")}</button><h2 class="h3">О нас</h2></div><div class="body">
      <textarea class="field" rows="8" data-about="1">${esc(d.settings.about || "")}</textarea>
      <button class="btn wide mt" data-save-about="1">Сохранить</button>
    </div></div>`;
  }
  if (o === "schedule") {
    return `<div class="overlay"><div class="header"><button data-close="1">${icon("left")}</button><h2 class="h3">Рабочие дни</h2></div><div class="body">
      <p class="sm muted">По умолчанию открыты суббота и воскресенье. Часы одни на все рабочие дни.</p>
      <div class="grid2 mt"><label class="sm muted">С<input class="field mt" type="time" value="${d.settings.workStart}" data-ws="1"></label>
      <label class="sm muted">По<input class="field mt" type="time" value="${d.settings.workEnd}" data-we="1"></label></div>
      <p class="sm muted mt">Полный календарь рабочих дней можно править после выгрузки; здесь часы приёма.</p>
      <button class="btn wide mt" data-save-hours="1">Сохранить часы</button>
    </div></div>`;
  }
  return "";
}

function view() {
  if (!state.data) return `<div class="header"><p class="brand">Doc Saya</p></div><div class="scroll"><p class="muted">Открываю кабинет…</p></div>`;
  const page = { home: home, book: book, care: care, profile: profile, admin: admin }[state.tab] || home;
  return `<section class="shell" id="clinic-shell">
    <header class="header"><p class="brand">Doc Saya</p></header>
    <div class="scroll" id="clinic-scroll">${page()}</div>
    ${tabs()}
    ${overlayHtml()}
    ${state.toast ? `<div class="toast">${esc(state.toast)}</div>` : ""}
  </section>`;
}

function render() {
  document.getElementById("app").innerHTML = view();
  bind();
}

async function loadGrid() {
  const s = state.picked || state.data.services[0]?.id;
  const now = new Date();
  const cur = state.month || { y: now.getFullYear(), m: now.getMonth() + 1 };
  if (!s) return;
  const g = await api("/api/month", { serviceId: s, year: cur.y, month: cur.m });
  state.grid = g.days || [];
  render();
}
async function loadSlots() {
  if (!state.day) return;
  const s = state.picked || state.data.services[0]?.id;
  const r = await api("/api/slots", { serviceId: s, date: state.day });
  state.slots = r.slots || [];
  render();
}

function openBuy(p) {
  const text = `Здравствуйте! Хочу купить «${p.title}»${p.price ? `, ${p.price.toLocaleString("ru-RU")} ₽` : ""}.`;
  const handle = (state.data.settings.adminUsername || "").replace(/^@/, "");
  const url = handle ? `https://t.me/${handle}?text=${encodeURIComponent(text)}` : `https://t.me/user?id=${ADMIN_ID}`;
  try { navigator.clipboard?.writeText(text); } catch (_) {}
  const w = tg();
  if (w?.openTelegramLink) { w.openTelegramLink(url); return; }
  window.open(url, "_blank");
}

function bind() {
  const root = document.getElementById("app");
  root.onclick = async (e) => {
    const btn = e.target.closest("button");
    const t = e.target.closest("[data-tab],[data-go],[data-pick],[data-day],[data-slot],[data-confirm],[data-wait],[data-prod],[data-buy],[data-close],[data-overlay],[data-svc],[data-jump],[data-int],[data-intake],[data-intake-done],[data-reschedule],[data-cancel],[data-pay],[data-hist],[data-ad],[data-closeday],[data-openday],[data-st],[data-prepay-toggle],[data-prepay-save],[data-save-prices],[data-save-pprices],[data-save-about],[data-save-hours],[data-m]");
    if (btn || t) {
      const heavy = t && (t.dataset.confirm || t.dataset.buy || t.dataset.savePrices || t.dataset.savePprices || t.dataset.saveAbout || t.dataset.saveHours || t.dataset.prepaySave || t.dataset.closeday);
      haptic(t?.dataset.tab || t?.dataset.jump || t?.dataset.slot || t?.dataset.int ? "select" : heavy ? "heavy" : "light");
    }
    if (!t) return;
    try {
      if (t.dataset.tab) { state.tab = t.dataset.tab; state.overlay = null; document.getElementById("clinic-scroll") && (document.getElementById("clinic-scroll").scrollTop = 0); render(); if (state.tab === "book") loadGrid(); return; }
      if (t.dataset.go) { state.tab = t.dataset.go; render(); if (state.tab === "book") loadGrid(); return; }
      if (t.dataset.pick) { state.picked = Number(t.dataset.pick); state.day = null; state.startMin = null; state.tab = "book"; render(); loadGrid(); return; }
      if (t.dataset.m) {
        const now = new Date();
        const cur = state.month || { y: now.getFullYear(), m: now.getMonth() + 1 };
        let m = cur.m + Number(t.dataset.m), y = cur.y;
        if (m < 1) { m = 12; y -= 1; }
        if (m > 12) { m = 1; y += 1; }
        state.month = { y, m }; loadGrid(); return;
      }
      if (t.dataset.day) { state.day = t.dataset.day; state.startMin = null; loadSlots(); return; }
      if (t.dataset.slot) { state.startMin = Number(t.dataset.slot); render(); return; }
      if (t.dataset.confirm) {
        await api("/api/book", { serviceId: state.picked || state.data.services[0].id, day: state.day, startMin: state.startMin, clientName: state.profile.name, source: state.profile.role === "admin" ? "admin" : "app" });
        toast("Записала"); state.reschedule = null; state.tab = "profile"; await load(); return;
      }
      if (t.dataset.wait) { await api("/api/waitlist", { serviceId: state.picked || state.data.services[0].id, day: state.day, clientName: state.profile.name }); toast("Добавила в лист ожидания"); return; }
      if (t.dataset.prod) {
        const p = state.data.careProducts.find((x) => x.id === Number(t.dataset.prod));
        const cat = state.data.careCategories.find((c) => c.id === p.categoryId)?.title || "";
        state.overlay = { kind: "product", p, cat }; render(); return;
      }
      if (t.dataset.buy) {
        const p = state.data.careProducts.find((x) => x.id === Number(t.dataset.buy));
        const r = await api("/api/product", { productId: p.id });
        openBuy({ ...p, ...r.product });
        if (r.adminUsername) state.data.settings.adminUsername = r.adminUsername;
        return;
      }
      if (t.dataset.close) { state.overlay = null; render(); return; }
      if (t.dataset.overlay) { state.overlay = t.dataset.overlay; state.prepayDraft = state.data.settings.prepayDefaultPercent; render(); return; }
      if (t.dataset.svc) { state.overlay = { kind: "service", s: state.data.services.find((x) => x.id === Number(t.dataset.svc)) }; render(); return; }
      if (t.dataset.jump) {
        state.careActive = Number(t.dataset.jump);
        root.querySelectorAll("[data-jump]").forEach((el) => el.classList.toggle("on", Number(el.dataset.jump) === state.careActive));
        document.getElementById(`care-cat-${t.dataset.jump}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      if (t.dataset.int) {
        const c = state.data.client.intake || {};
        c[t.dataset.int] = !c[t.dataset.int];
        state.data.client.intake = c;
        render();
        api("/api/intake", { answers: c }).catch(() => {});
        return;
      }
      if (t.dataset.intake) { state.intakeOpen = !state.intakeOpen; render(); return; }
      if (t.dataset.intakeDone) { await api("/api/intake", { answers: state.data.client.intake || {} }); state.data.client.intakeDone = true; state.overlay = null; render(); return; }
      if (t.dataset.reschedule) { state.reschedule = Number(t.dataset.reschedule); state.picked = Number(t.dataset.sid); state.tab = "book"; render(); loadGrid(); return; }
      if (t.dataset.cancel) { await api("/api/cancel", { appointmentId: Number(t.dataset.cancel) }); toast("Отменила"); await load(); return; }
      if (t.dataset.pay) { await api("/api/prepay", { appointmentId: Number(t.dataset.pay) }); toast("Оплата прошла"); await load(); return; }
      if (t.dataset.hist) { state.historyOpen = !state.historyOpen; render(); return; }
      if (t.dataset.ad) {
        const d = parseDay(state.adminDay || ymd(new Date()));
        d.setDate(d.getDate() + Number(t.dataset.ad));
        state.adminDay = ymd(d); render(); return;
      }
      if (t.dataset.closeday) { await api("/api/block-day", { day: state.adminDay || ymd(new Date()) }); toast("День закрыт как выходной"); await load(); return; }
      if (t.dataset.openday) { await api("/api/block-day", { day: state.adminDay || ymd(new Date()), clear: true }); toast("День открыт"); await load(); return; }
      if (t.dataset.st) { await api("/api/status", { appointmentId: Number(t.dataset.st), status: t.dataset.to }); await load(); return; }
      if (t.dataset.prepayToggle) { state.data.settings.prepayEnabled = !state.data.settings.prepayEnabled; render(); return; }
      if (t.dataset.prepaySave) {
        const pct = Number(document.querySelector("[data-prepay-pct]")?.value || 30);
        await api("/api/settings", { patch: { prepayEnabled: state.data.settings.prepayEnabled, prepayDefaultPercent: pct } });
        toast("Сохранила"); await load(); state.overlay = null; render(); return;
      }
      if (t.dataset.savePrices) {
        const inputs = [...document.querySelectorAll("[data-price]")];
        for (const inp of inputs) {
          await api("/api/service", { id: Number(inp.dataset.price), title: state.data.services.find((s) => s.id === Number(inp.dataset.price)).title, price: Number(inp.value), durationMin: state.data.services.find((s) => s.id === Number(inp.dataset.price)).durationMin });
        }
        toast("Цены обновлены"); await load(); return;
      }
      if (t.dataset.savePprices) {
        for (const inp of document.querySelectorAll("[data-pprice]")) {
          const p = state.data.careProducts.find((x) => x.id === Number(inp.dataset.pprice));
          await api("/api/care/product", { ...p, price: Number(inp.value) });
        }
        toast("Сохранила"); await load(); return;
      }
      if (t.dataset.saveAbout) {
        const text = document.querySelector("[data-about]")?.value || "";
        await api("/api/settings", { patch: { about: text } });
        toast("Сохранила"); await load(); state.overlay = null; render(); return;
      }
      if (t.dataset.saveHours) {
        await api("/api/settings", { patch: { workStart: document.querySelector("[data-ws]")?.value, workEnd: document.querySelector("[data-we]")?.value } });
        toast("Часы сохранены"); await load(); return;
      }
    } catch (err) {
      haptic("error");
      toast(err.message || "Не получилось");
    }
  };
  root.oninput = (e) => {
    if (e.target.dataset.note) {
      state.data.client.intake = state.data.client.intake || {};
      state.data.client.intake.note = e.target.value;
      clearTimeout(window.__intakeT);
      window.__intakeT = setTimeout(() => api("/api/intake", { answers: state.data.client.intake }).catch(() => {}), 400);
    }
  };
}

bootTg();
render();
(async () => {
  const t0 = Date.now();
  while (!readUser() && Date.now() - t0 < 1200) {
    await new Promise((r) => setTimeout(r, 50));
  }
  bootTg();
  try { await load(); } catch (e) { state.toast = e.message; render(); }
})();