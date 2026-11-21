(() => {
  "use strict";

  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* ignore */ } },
  };

  // Standard-Zusatzstoffe (Zahlen-Codes), falls die Quelle sie nicht selbst erklärt
  const ADDITIVES = {
    1: "mit Farbstoff", 2: "mit Konservierungsstoff", 3: "mit Antioxidationsmittel",
    4: "mit Geschmacksverstärker", 5: "geschwefelt", 6: "geschwärzt", 7: "mit Phosphat",
    8: "mit Milcheiweiß", 9: "koffeinhaltig", 10: "chininhaltig", 11: "mit Süßungsmittel", 12: "gewachst",
  };
  const TAG_LABEL = { vegan: "🌱 vegan", vegetarisch: "🥕 vegetarisch", "geflügel": "🐔 Geflügel", schwein: "🐷 Schwein", rind: "🐮 Rind", fisch: "🐟 Fisch" };
  const MEAT = ["geflügel", "schwein", "rind"];
  const FILTERS = [
    { id: "all", label: "Alle", test: () => true },
    { id: "vegan", label: "🌱 Vegan", test: (d) => d.tags.includes("vegan") },
    { id: "nomeat", label: "🥕 Ohne Fleisch", test: (d) => !d.tags.some((t) => MEAT.includes(t)) },
    { id: "nopork", label: "🚫🐷 Ohne Schwein", test: (d) => !d.tags.includes("schwein") },
  ];
  const fmtDate = (iso, opts) => new Date(iso + "T12:00:00").toLocaleDateString("de-DE", opts);
  const todayISO = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 10); };

  const state = { index: null, restaurant: null, week: null, menu: null, day: null, filter: store.get("filter") || "all", picked: null };

  // ---------- Theme ----------
  const applyTheme = (t) => { if (t) document.documentElement.dataset.theme = t; };
  applyTheme(store.get("theme"));
  $("#themeToggle").addEventListener("click", () => {
    const cur = document.documentElement.dataset.theme
      || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    applyTheme(next); store.set("theme", next);
  });

  // ---------- Routing (#restaurant/week) ----------
  const readHash = () => { const [r, w] = location.hash.replace(/^#\/?/, "").split("/"); return { r, w }; };
  const writeHash = () => {
    const h = `#${state.restaurant.id}${state.week && state.week !== state.restaurant.weeks[0] ? "/" + state.week : ""}`;
    if (location.hash !== h) history.replaceState(null, "", h);
  };

  async function getJSON(url) {
    const res = await fetch(url, { cache: "no-cache" });
    if (!res.ok) throw new Error(`${res.status} ${url}`);
    return res.json();
  }

  // ---------- Picker ----------
  function renderPicker() {
    $("#picker").innerHTML = state.index.restaurants.map((r) => `
      <button class="r-card" type="button" data-id="${esc(r.id)}" style="--rc:${esc(r.color || "")}"
        aria-pressed="${state.restaurant && r.id === state.restaurant.id}">
        <span class="r-emoji">${esc(r.emoji || "🍽️")}</span>
        <span><strong>${esc(r.name)}</strong><small>${esc(r.hours || r.address || "")}</small></span>
        ${r.status && r.status !== "ok" ? '<span class="dot" title="Letzte Aktualisierung fehlgeschlagen"></span>' : ""}
      </button>`).join("");
    $("#picker").querySelectorAll(".r-card").forEach((b) =>
      b.addEventListener("click", () => selectRestaurant(b.dataset.id)));
  }

  async function selectRestaurant(id, week) {
    const r = state.index.restaurants.find((x) => x.id === id) || state.index.restaurants[0];
    state.restaurant = r;
    state.picked = null;
    store.set("restaurant", r.id);
    document.documentElement.style.setProperty("--accent", r.color || "#2f9e9a");
    renderPicker();

    $("#hero").hidden = false;
    $("#rName").textContent = r.name;
    $("#rSub").textContent = r.subtitle || "";
    $("#rMeta").innerHTML = [
      r.address && `<li>📍 ${esc(r.address)}</li>`,
      r.hours && `<li>🕚 ${esc(r.hours)}</li>`,
      r.url && `<li>🔗 <a href="${esc(r.url)}" target="_blank" rel="noopener">Original-Speiseplan</a></li>`,
    ].filter(Boolean).join("");
    $("#sourceLink").href = r.url || "#";

    const weeks = r.weeks || [];
    $("#weekSelect").innerHTML = weeks.map((w, i) => {
      const end = new Date(w + "T12:00:00"); end.setDate(end.getDate() + 4);
      const label = `${fmtDate(w, { day: "2-digit", month: "2-digit" })} – ${end.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" })}`;
      return `<option value="${w}">${i === 0 ? "Aktuell · " : ""}${label}</option>`;
    }).join("");
    await selectWeek(weeks.includes(week) ? week : weeks[0]);
  }

  async function selectWeek(week) {
    state.week = week || null;
    $("#weekSelect").value = week || "";
    writeHash();
    $("#menu").innerHTML = `<div class="grid">${'<div class="skeleton"></div>'.repeat(4)}</div>`;
    try {
      const file = week ? `${week}.json` : "latest.json";
      state.menu = await getJSON(`data/${state.restaurant.id}/${file}`);
    } catch (e) {
      state.menu = null;
      $("#toolbar").hidden = true;
      ["#weekly", "#notes", "#legend"].forEach((s) => ($(s).hidden = true));
      $("#menu").innerHTML = `<div class="empty"><div class="big">🥲</div><p>Für dieses Restaurant liegt noch kein Speiseplan vor.</p></div>`;
      return;
    }
    const t = todayISO();
    state.day = state.menu.days.some((d) => d.date === t) ? t : "week";
    renderAll();
  }

  // ---------- Rendering ----------
  function renderAll() { renderToolbar(); renderMenu(); renderExtras(); }

  function renderToolbar() {
    $("#toolbar").hidden = false;
    const t = todayISO();
    const tabs = [{ key: "week", wd: "Woche", dt: "alle Tage" }].concat(
      state.menu.days.map((d) => ({ key: d.date, wd: d.weekday.slice(0, 2), dt: fmtDate(d.date, { day: "2-digit", month: "2-digit" }), today: d.date === t })));
    $("#days").style.gridTemplateColumns = `repeat(${tabs.length}, minmax(64px, 1fr))`;
    $("#days").innerHTML = tabs.map((x) => `
      <button class="day${x.today ? " today" : ""}" role="tab" type="button" data-key="${x.key}" aria-selected="${state.day === x.key}">
        <span class="wd">${esc(x.wd)}</span><span class="dt">${esc(x.dt)}</span>
      </button>`).join("");
    $("#days").querySelectorAll(".day").forEach((b) => b.addEventListener("click", () => {
      state.day = b.dataset.key; state.picked = null; renderToolbar(); renderMenu();
    }));

    $("#filters").innerHTML = FILTERS.map((f) =>
      `<button class="chip" type="button" data-f="${f.id}" aria-pressed="${state.filter === f.id}">${esc(f.label)}</button>`).join("");
    $("#filters").querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => {
      state.filter = b.dataset.f; store.set("filter", state.filter); state.picked = null; renderToolbar(); renderMenu();
    }));
  }

  const allergenTitle = (code) => {
    const legend = state.menu?.legend?.allergens || {};
    return legend[code] || ADDITIVES[code] || code;
  };

  function dishCard(d, key) {
    const parts = d.name.split(/\s*\/\s*/);
    const title = parts.shift();
    const sides = parts.join(" · ");
    return `
      <article class="dish${state.picked === key ? " picked" : ""}" data-key="${esc(key)}">
        <div class="top"><span class="cat">${esc(d.category)}</span>${d.price ? `<span class="price">${esc(d.price)}</span>` : ""}</div>
        <h3>${esc(title)}</h3>
        ${sides ? `<p class="sides">${esc(sides)}</p>` : ""}
        <div class="bottom">
          <div class="tags">${d.tags.map((t) => `<span class="tag ${esc(t)}">${esc(TAG_LABEL[t] || t)}</span>`).join("")}</div>
          <div class="allergens">${d.allergens.map((a) => `<abbr title="${esc(allergenTitle(a))}">${esc(a)}</abbr>`).join("")}</div>
        </div>
      </article>`;
  }

  const filterFn = () => (FILTERS.find((f) => f.id === state.filter) || FILTERS[0]).test;

  function renderMenu() {
    const days = state.day === "week" ? state.menu.days : state.menu.days.filter((d) => d.date === state.day);
    const test = filterFn();
    const html = days.map((day) => {
      const dishes = day.dishes.map((d, i) => [d, `${day.date}#${i}`]).filter(([d]) => test(d));
      const body = dishes.length
        ? `<div class="grid">${dishes.map(([d, k]) => dishCard(d, k)).join("")}</div>`
        : `<div class="empty"><div class="big">🍃</div><p>Keine passenden Gerichte an diesem Tag.</p></div>`;
      return `<section class="day-block">
        <div class="day-head"><h2>${esc(day.weekday)}</h2><span>${fmtDate(day.date, { day: "numeric", month: "long" })}</span></div>
        ${body}</section>`;
    }).join("");
    $("#menu").innerHTML = html || `<div class="empty"><div class="big">📭</div><p>Für diese Woche gibt es keine Einträge.</p></div>`;
  }

  function renderExtras() {
    const m = state.menu;
    $("#weekly").hidden = !m.weekly?.length;
    $("#weeklyGrid").innerHTML = (m.weekly || []).map((d, i) => dishCard(d, `w${i}`)).join("");
    $("#notes").hidden = !m.notes?.length;
    $("#notesList").innerHTML = (m.notes || []).map((n) => `<li>${esc(n)}</li>`).join("");

    const used = new Set(m.days.flatMap((d) => d.dishes.flatMap((x) => x.allergens)).concat((m.weekly || []).flatMap((x) => x.allergens)));
    const legend = { ...(m.legend?.allergens || {}) };
    used.forEach((c) => { if (!legend[c] && ADDITIVES[c]) legend[c] = ADDITIVES[c]; });
    const entries = Object.entries(legend);
    $("#legend").hidden = !entries.length;
    $("#legendList").innerHTML = entries.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("");

    const ts = m.fetchedAt ? new Date(m.fetchedAt).toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" }) : "–";
    $("#updated").textContent = `Zuletzt aktualisiert: ${ts}`;
  }

  // ---------- "Was ess ich heute?" ----------
  $("#surprise").addEventListener("click", () => {
    if (!state.menu) return;
    const t = todayISO();
    if (state.day === "week") state.day = state.menu.days.some((d) => d.date === t) ? t : state.menu.days[0]?.date;
    const day = state.menu.days.find((d) => d.date === state.day);
    if (!day) return;
    const test = filterFn();
    const pool = day.dishes.map((d, i) => [d, `${day.date}#${i}`]).filter(([d]) => test(d) && !/suppe/i.test(d.category));
    if (!pool.length) return;
    state.picked = null; renderToolbar(); renderMenu();

    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    let n = 0; const steps = reduce ? 1 : 10;
    const tick = () => {
      document.querySelectorAll("#menu .dish").forEach((el) => el.classList.remove("picked", "shuffling"));
      const [, key] = pool[Math.floor(Math.random() * pool.length)];
      const el = document.querySelector(`#menu .dish[data-key="${key}"]`);
      if (++n < steps) { el?.classList.add("shuffling"); setTimeout(tick, 60 + n * 18); return; }
      state.picked = key; el?.classList.add("picked");
      el?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
    };
    tick();
  });

  $("#weekSelect").addEventListener("change", (e) => selectWeek(e.target.value));
  window.addEventListener("hashchange", () => {
    const { r, w } = readHash();
    if (r && (r !== state.restaurant?.id || (w || state.restaurant.weeks[0]) !== state.week)) selectRestaurant(r, w);
  });

  // ---------- Boot ----------
  (async () => {
    try {
      state.index = await getJSON("data/index.json");
    } catch {
      $("#menu").innerHTML = `<div class="empty"><div class="big">⚠️</div><p>Daten konnten nicht geladen werden.</p></div>`;
      return;
    }
    const { r, w } = readHash();
    selectRestaurant(r || store.get("restaurant") || state.index.restaurants[0]?.id, w);
  })();
})();
