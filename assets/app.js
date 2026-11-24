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
  const TAG_LABEL = { vegan: "🌱 vegan", vegetarisch: "🥕 vegetarisch", "geflügel": "🐔 Geflügel", schwein: "🐷 Schwein", rind: "🐮 Rind", fisch: "🐟 Fisch", fleisch: "🍖 Fleisch" };
  const MEAT = ["geflügel", "schwein", "rind", "fleisch"];
  const FILTERS = [
    { id: "all", label: "Alle", test: () => true },
    { id: "vegan", label: "🌱 Vegan", test: (d) => d.tags.includes("vegan") },
    // d.unknown: Zutaten unbekannt -> nicht als fleischlos/schweinefrei anzeigen
    { id: "nomeat", label: "🥕 Ohne Fleisch", test: (d) => !d.unknown && !d.tags.some((t) => MEAT.includes(t)) },
    { id: "nopork", label: "🚫🐷 Ohne Schwein", test: (d) => !d.unknown && !d.tags.includes("schwein") },
  ];
  const fmtDate = (iso, opts) => new Date(iso + "T12:00:00").toLocaleDateString("de-DE", opts);
  const todayISO = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 10); };

  // heute (falls Werktag) + die nächsten Werktage, insgesamt 3
  const isoOf = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const WD_NAMES = ["Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"];
  function targetDays(n = 3) {
    const out = []; const d = new Date(); d.setHours(12, 0, 0, 0);
    while (out.length < n) {
      if (d.getDay() >= 1 && d.getDay() <= 5) out.push({ date: isoOf(d), weekday: WD_NAMES[d.getDay()] });
      d.setDate(d.getDate() + 1);
    }
    return out;
  }

  const state = { index: null, restaurant: null, menu: null, day: null, filter: store.get("filter") || "all", picked: null };

  // ---------- Theme ----------
  const applyTheme = (t) => { if (t) document.documentElement.dataset.theme = t; };
  applyTheme(store.get("theme"));
  $("#themeToggle").addEventListener("click", () => {
    const cur = document.documentElement.dataset.theme
      || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    applyTheme(next); store.set("theme", next);
  });

  // ---------- Routing (#restaurant) ----------
  const readHash = () => location.hash.replace(/^#\/?/, "").split("/")[0];
  const writeHash = () => {
    const h = `#${state.restaurant.id}`;
    if (location.hash !== h) history.replaceState(null, "", h);
  };

  async function getJSON(url) {
    const res = await fetch(url, { cache: "no-cache" });
    if (!res.ok) throw new Error(`${res.status} ${url}`);
    return res.json();
  }

  // ---------- Picker ----------
  const cardBadge = (r) => r.kind === "static" ? "Feste Karte" : !r.weeks?.length ? "Infos & Links" : r.kind === "images" ? "Fotokarte" : "Speiseplan";
  // saisonale Einträge (z. B. Weihnachtsmarkt) nach ihrem Enddatum ausblenden
  const visibleRestaurants = () => state.index.restaurants.filter((r) => !r.until || r.until >= todayISO());

  function renderPicker() {
    $("#picker").innerHTML = visibleRestaurants().map((r) => `
      <button class="r-card" type="button" data-id="${esc(r.id)}" style="--rc:${esc(r.color || "")}"
        aria-pressed="${state.restaurant && r.id === state.restaurant.id}">
        <span class="r-emoji">${esc(r.emoji || "🍽️")}</span>
        <span><strong>${esc(r.name)}</strong><small>${esc(r.cuisine || "")}${r.cuisine ? " · " : ""}${esc(cardBadge(r))}</small></span>
        ${String(r.status || "").startsWith("error") ? '<span class="dot" title="Letzte Aktualisierung fehlgeschlagen"></span>' : ""}
      </button>`).join("");
    $("#picker").querySelectorAll(".r-card").forEach((b) =>
      b.addEventListener("click", () => selectRestaurant(b.dataset.id)));
  }

  async function selectRestaurant(id) {
    const r = visibleRestaurants().find((x) => x.id === id) || visibleRestaurants()[0];
    state.restaurant = r;
    state.picked = null;
    store.set("restaurant", r.id);
    document.documentElement.style.setProperty("--accent", r.color || "#2f9e9a");
    renderPicker();

    $("#hero").hidden = false;
    $("#rName").textContent = r.name;
    $("#rSub").textContent = r.subtitle || "";
    $("#rMeta").innerHTML = [
      r.address && `<li>📍 <a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(r.name + ", " + r.address)}" target="_blank" rel="noopener">${esc(r.address)}</a></li>`,
      r.hours && `<li>🕚 ${esc(r.hours)}</li>`,
      r.phone && `<li>📞 <a href="tel:${esc(r.phone.replace(/\s/g, ""))}">${esc(r.phone)}</a></li>`,
      r.url && `<li>🔗 <a href="${esc(r.url)}" target="_blank" rel="noopener">Website</a></li>`,
    ].filter(Boolean).join("");
    $("#sourceLink").href = r.url || "#";

    writeHash();
    if (r.kind === "static") { await loadStatic(r); return; }
    const weeks = r.weeks || [];
    if (!weeks.length) { renderProfile(r); return; }
    await loadUpcoming(r);
  }

  // Lädt die Wochendateien, die heute + die nächsten 2 Werktage abdecken,
  // und baut daraus genau diese drei Tage zusammen.
  async function loadUpcoming(r) {
    $("#menu").innerHTML = `<div class="grid">${'<div class="skeleton"></div>'.repeat(3)}</div>`;
    const targets = targetDays(3);
    try {
      const latest = await getJSON(`data/${r.id}/latest.json`);
      if (state.restaurant !== r) return;
      if (latest.kind === "images") { state.menu = latest; renderGallery(); return; }

      const first = new Date(targets[0].date + "T12:00:00"); first.setDate(first.getDate() - 6);
      const lo = isoOf(first), hi = targets[targets.length - 1].date;
      const files = (r.weeks || []).filter((w) => w >= lo && w <= hi);
      const menus = (await Promise.all(files.map((w) => getJSON(`data/${r.id}/${w}.json`).catch(() => null)))).filter(Boolean);
      if (state.restaurant !== r) return;

      const byDate = {};
      menus.concat([latest]).forEach((m) => m.days.forEach((d) => { byDate[d.date] = byDate[d.date] || d; }));
      const newest = menus.concat([latest]).sort((a, b) => b.week.from.localeCompare(a.week.from))[0];
      state.menu = {
        ...newest,
        legend: { allergens: Object.assign({}, ...menus.concat([latest]).map((m) => m.legend?.allergens || {})) },
        fetchedAt: latest.fetchedAt,
        days: targets.map((t) => byDate[t.date] || { ...t, dishes: [], missing: true }),
      };
    } catch (e) {
      state.menu = null;
      $("#toolbar").hidden = true;
      ["#weekly", "#notes", "#legend"].forEach((s) => ($(s).hidden = true));
      $("#menu").innerHTML = `<div class="empty"><div class="big">🥲</div><p>Für dieses Restaurant liegt noch kein Speiseplan vor.</p></div>`;
      return;
    }
    state.day = "all";
    $("#surprise").hidden = false;
    renderAll();
  }

  async function loadStatic(r) {
    try {
      const m = await getJSON(`data/${r.id}/latest.json`);
      if (state.restaurant !== r) return;
      state.menu = m;
      renderStatic();
    } catch { renderProfile(r); }
  }

  function renderStatic() {
    const m = state.menu;
    hideMenuChrome();
    $("#toolbar").hidden = false;
    $("#days").hidden = true;
    $("#filters").innerHTML = FILTERS.map((f) =>
      `<button class="chip" type="button" data-f="${f.id}" aria-pressed="${state.filter === f.id}">${esc(f.label)}</button>`).join("");
    $("#filters").querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => {
      state.filter = b.dataset.f; store.set("filter", state.filter); renderStatic();
    }));
    const test = filterFn();
    const asOf = m.asOf ? fmtDate(m.asOf, { day: "numeric", month: "long", year: "numeric" }) : "";
    const sections = m.sections.map((sec, si) => {
      const dishes = sec.dishes.map((d, i) => [d, `s${si}#${i}`]).filter(([d]) => test(d));
      if (!dishes.length) return "";
      return `<section class="day-block">
        <div class="day-head"><h2>${esc(sec.title)}</h2></div>
        <div class="grid">${dishes.map(([d, k]) => dishCard(d, k)).join("")}</div></section>`;
    }).join("");
    $("#menu").innerHTML = `
      <div class="static-info">
        <span>📋 Feste Karte${asOf ? ` · Stand ${esc(asOf)}` : ""}${m.source ? ` · ${esc(m.source)}` : ""}</span>
        ${m.photo ? `<button type="button" class="btn" id="showPhoto">📷 Originalfoto ansehen</button>` : ""}
      </div>
      ${sections || `<div class="empty"><div class="big">🍃</div><p>Keine passenden Gerichte.</p></div>`}`;
    $("#showPhoto")?.addEventListener("click", () => {
      $("#lightboxImg").src = m.photo; $("#lightboxImg").alt = "Originalfoto der Karte"; $("#lightboxCap").textContent = `Originalfoto · ${asOf}`;
      $("#lightbox").showModal();
    });
    $("#notes").hidden = !m.notes?.length;
    $("#notesList").innerHTML = (m.notes || []).map((n) => `<li>${esc(n)}</li>`).join("");
    $("#updated").textContent = asOf ? `Karte Stand: ${asOf}` : "";
  }

  function hideMenuChrome() {
    $("#toolbar").hidden = true;
    $("#surprise").hidden = true;
    ["#weekly", "#notes", "#legend"].forEach((s) => ($(s).hidden = true));
  }

  function renderProfile(r) {
    state.menu = null;
    hideMenuChrome();
    $("#updated").textContent = "";
    $("#menu").innerHTML = `
      <div class="profile">
        <div class="profile-emoji" style="--rc:${esc(r.color || "")}">${esc(r.emoji || "🍽️")}</div>
        <div>
          <h2>Kein Online-Speiseplan</h2>
          <p>${esc(r.info || "Für dieses Restaurant gibt es keinen automatisch abrufbaren Speiseplan.")}</p>
          <div class="profile-actions">
            ${r.url ? `<a class="btn primary" href="${esc(r.url)}" target="_blank" rel="noopener">Zur Website ↗</a>` : ""}
            ${r.phone ? `<a class="btn" href="tel:${esc(r.phone.replace(/\s/g, ""))}">📞 Anrufen</a>` : ""}
            ${r.photo ? `<button type="button" class="btn" id="showProfilePhoto">📷 Foto ansehen</button>` : ""}
          </div>
        </div>
      </div>`;
    $("#showProfilePhoto")?.addEventListener("click", () => {
      $("#lightboxImg").src = r.photo; $("#lightboxImg").alt = `Foto ${r.name}`; $("#lightboxCap").textContent = r.name;
      $("#lightbox").showModal();
    });
  }

  function renderGallery() {
    hideMenuChrome();
    const imgs = state.menu.images || [];
    const ts = state.menu.fetchedAt ? new Date(state.menu.fetchedAt).toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" }) : "–";
    $("#updated").textContent = `Zuletzt aktualisiert: ${ts}`;
    const daily = state.menu.daily && state.menu.daily.date === todayISO() ? state.menu.daily : null;
    $("#menu").innerHTML = `${daily ? `
      <section class="day-block daily">
        <div class="day-head"><h2>${esc(daily.title || "Mittagsmenü heute")}</h2><span>${fmtDate(daily.date, { weekday: "long", day: "numeric", month: "long" })}</span></div>
        <div class="static-info"><span>📋 ${esc(daily.source || "Aushang vor Ort")}</span>
          ${daily.photo ? `<button type="button" class="btn" id="showDaily">📷 Aushang ansehen</button>` : ""}</div>
        <div class="grid">${daily.dishes.map((d, i) => dishCard(d, `d#${i}`)).join("")}</div>
      </section>
      <h2 class="section-title">Karte von der Website</h2>` : ""}
      <p class="gallery-hint">Dieses Restaurant veröffentlicht seine Karte als Fotos – automatisch von der Website übernommen. Zum Vergrößern antippen.</p>
      <div class="gallery">${imgs.map((im, i) => `
        <figure>
          <button type="button" class="shot" data-i="${i}" aria-label="${esc(im.section)} vergrößern">
            <img src="${esc(im.thumb || im.src)}" alt="${esc(im.alt)}" loading="lazy" referrerpolicy="no-referrer">
          </button>
          <figcaption>${esc(im.section)}</figcaption>
        </figure>`).join("")}</div>`;
    $("#showDaily")?.addEventListener("click", () => {
      $("#lightboxImg").src = daily.photo; $("#lightboxImg").alt = "Foto des Tagesaushangs"; $("#lightboxCap").textContent = `Aushang · ${fmtDate(daily.date, { day: "numeric", month: "long" })}`;
      $("#lightbox").showModal();
    });
    $("#menu").querySelectorAll(".shot").forEach((b) => b.addEventListener("click", () => {
      const im = imgs[+b.dataset.i];
      $("#lightboxImg").src = im.src; $("#lightboxImg").alt = im.alt; $("#lightboxCap").textContent = im.section;
      $("#lightbox").showModal();
    }));
  }

  // ---------- Rendering ----------
  function renderAll() { renderToolbar(); renderMenu(); renderExtras(); }

  function renderToolbar() {
    $("#toolbar").hidden = false;
    $("#days").hidden = false;
    const t = todayISO();
    const tabs = [{ key: "all", wd: "Übersicht", dt: "3 Werktage" }].concat(
      state.menu.days.map((d) => ({ key: d.date, wd: d.date === t ? "Heute" : d.weekday.slice(0, 2), dt: fmtDate(d.date, { day: "2-digit", month: "2-digit" }), today: d.date === t })));
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
    const sides = d.description || parts.join(" · ");
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
    const days = state.day === "all" ? state.menu.days : state.menu.days.filter((d) => d.date === state.day);
    const test = filterFn();
    const html = days.map((day) => {
      const dishes = day.dishes.map((d, i) => [d, `${day.date}#${i}`]).filter(([d]) => test(d));
      const body = day.missing
        ? `<div class="empty"><div class="big">🕐</div><p>Für diesen Tag ist noch kein Speiseplan veröffentlicht.</p></div>`
        : dishes.length
        ? `<div class="grid">${dishes.map(([d, k]) => dishCard(d, k)).join("")}</div>`
        : `<div class="empty"><div class="big">🍃</div><p>Keine passenden Gerichte an diesem Tag.</p></div>`;
      return `<section class="day-block">
        <div class="day-head"><h2>${day.date === todayISO() ? "Heute · " : ""}${esc(day.weekday)}</h2><span>${fmtDate(day.date, { day: "numeric", month: "long" })}</span></div>
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
    if (state.day === "all") state.day = (state.menu.days.find((d) => d.date >= t && !d.missing) || state.menu.days[0])?.date;
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

  $("#lightbox").addEventListener("click", () => $("#lightbox").close());
  window.addEventListener("hashchange", () => {
    const r = readHash();
    if (r && r !== state.restaurant?.id) selectRestaurant(r);
  });

  // ---------- Boot ----------
  (async () => {
    try {
      state.index = await getJSON("data/index.json");
    } catch {
      $("#menu").innerHTML = `<div class="empty"><div class="big">⚠️</div><p>Daten konnten nicht geladen werden.</p></div>`;
      return;
    }
    selectRestaurant(readHash() || store.get("restaurant") || state.index.restaurants[0]?.id);
  })();
})();
