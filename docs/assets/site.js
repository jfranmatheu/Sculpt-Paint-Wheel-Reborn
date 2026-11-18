/* Sculpt-Paint Wheel docs: interactions. Vanilla JS, no dependencies. */
(() => {
  "use strict";

  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } },
  };

  /* ------------------------------------------------------------------ Data */
  const B = (lib, names) => names.map((n) => ({ name: n, img: `assets/brushes/${lib}/${n.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}.webp` }));
  const btn = (name, icon, kind = "panel") => ({ name, icon: `assets/icons/${icon}.png`, kind });
  const STROKE = btn("Stroke", "stroke"), FALLOFF = btn("Falloff", "falloff"), TEXTURE = btn("Texture", "texture");

  const MODES = [
    { id: "sculpt", name: "Sculpt", tint: "", sub: "Mesh sculpting",
      brushes: B("mesh_sculpt", ["Draw", "Draw Sharp", "Clay Strips", "Inflate/Deflate", "Crease Polish", "Crease Sharp", "Blob", "Layer", "Fill/Deepen", "Flatten/Contrast", "Plateau", "Scrape Multiplane", "Scrape/Fill", "Pinch/Magnify", "Grab", "Grab 2D", "Elastic Grab", "Pose"]),
      buttons: [STROKE, FALLOFF, TEXTURE, btn("Remesh", "grid"), btn("Mask Clear", "mask_clear", "operator"), btn("Mask Invert", "mask_invert", "operator"), btn("Mask Sharpen", "mask_sharp", "operator"), btn("Mask Smooth", "mask_smooth", "operator")] },
    { id: "texture", name: "Texture Paint", tint: "texture", sub: "Paint image textures",
      brushes: B("mesh_texture", ["Paint Pixel Art", "Erase Pixel Art", "Airbrush", "Paint Hard", "Paint Hard Pressure", "Paint Soft", "Paint Soft Pressure", "Erase Hard", "Erase Hard Pressure", "Erase Soft", "Blur", "Smear", "Clone", "Fill", "Mask"]),
      buttons: [btn("Advanced Settings", "brush"), STROKE, FALLOFF, TEXTURE] },
    { id: "vertex", name: "Vertex Paint", tint: "vertex", sub: "Paint vertex colors",
      brushes: B("mesh_vertex", ["Paint Soft", "Paint Soft Pressure", "Paint Hard", "Paint Hard Pressure", "Airbrush", "Blur", "Average", "Smear"]),
      buttons: [STROKE, FALLOFF, TEXTURE, btn("Symmetry", "mirror"), btn("Paint", "brush", "menu"), btn("Smooth Colors", "mask_smooth", "operator")] },
    { id: "weight", name: "Weight Paint", tint: "weight", sub: "Weight dial instead of brushes", weight: true,
      buttons: [btn("Brush Settings", "brush"), STROKE, FALLOFF, btn("Mirror", "mirror"), btn("Weight Options", "options"), btn("Weights", "weights", "menu")] },
    { id: "curves", name: "Sculpt Curves", tint: "curves", sub: "Hair and curves",
      brushes: B("curve_sculpt", ["Add", "Delete", "Density", "Comb", "Slide", "Pinch", "Puff", "Smooth", "Grow Shrink", "Pull Tips", "Select"]).map((b) => (b.name === "Grow Shrink" ? { ...b, name: "Grow/Shrink" } : b)),
      extra: "+ Cut (Blender 5.3)",
      buttons: [btn("Brush Settings", "brush"), STROKE, FALLOFF, btn("Symmetry", "mirror"), btn("Curves", "grid", "menu")] },
    { id: "gp-draw", name: "GP Draw", tint: "gp", sub: "Grease Pencil draw mode",
      brushes: B("gp_draw", ["Pencil", "Pencil Soft", "Pen", "Ink Pen", "Ink Pen Rough", "Marker Bold", "Marker Chisel", "Airbrush", "Tint", "Fill", "Eraser Soft", "Eraser Hard", "Eraser Stroke"]),
      buttons: [btn("Layers", "grid"), btn("Materials", "texture"), STROKE, btn("Stabilize Stroke", "falloff_2"), btn("Advanced", "brush"), btn("Insert Blank Keyframe", "options", "operator")] },
    { id: "gp-sculpt", name: "GP Sculpt", tint: "gp", sub: "Grease Pencil sculpt mode",
      brushes: B("gp_sculpt", ["Smooth", "Thickness", "Strength", "Randomize", "Grab", "Pull", "Twist", "Pinch", "Clone"]),
      buttons: [FALLOFF, btn("Auto-Masking", "mask"), btn("Multi Frame", "options"), btn("Layers", "grid")] },
    { id: "gp-weight", name: "GP Weight", tint: "weight", sub: "Grease Pencil weight paint", weight: true,
      buttons: [btn("Options", "options"), FALLOFF, btn("Weights", "weights", "menu"), btn("Normalize All", "weights", "operator"), btn("Invert Weight", "mask_invert", "operator"), btn("Smooth Weight", "mask_smooth", "operator")] },
    { id: "gp-vertex", name: "GP Vertex", tint: "gp", sub: "Grease Pencil vertex paint",
      brushes: B("gp_vertex", ["Paint", "Blur", "Average", "Smear", "Replace"]),
      buttons: [btn("Color", "texture"), FALLOFF, btn("Multi Frame", "options"), btn("Paint", "brush", "menu"), btn("Reset Vertex Color", "mask_clear", "operator"), btn("Invert Colors", "mask_invert", "operator")] },
  ];
  const modeIcon = (m) => (m.weight ? "assets/icons/weights.png" : m.brushes[0].img);

  /* ------------------------------------------------------------------ Theme */
  $("#theme-toggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    store.set("spw-theme", next);
  });

  /* ------------------------------------------------------------------ Scroll: progress, reveal, scrollspy */
  const progress = $(".progress");
  const onScroll = () => {
    const h = document.documentElement;
    progress.style.transform = `scaleX(${h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight)})`;
  };
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  const revealObs = new IntersectionObserver((entries) => {
    entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); revealObs.unobserve(e.target); } });
  }, { rootMargin: "0px 0px -8% 0px" });
  $$(".reveal").forEach((el) => revealObs.observe(el));

  const spy = (links, attr) => {
    const map = new Map(links.map((a) => [a.getAttribute("href").slice(1), a]));
    const targets = [...map.keys()].map((id) => document.getElementById(id)).filter(Boolean);
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        links.forEach((a) => a.classList.remove(attr));
        map.get(e.target.id)?.classList.add(attr);
      });
    }, { rootMargin: "-40% 0px -55% 0px" });
    targets.forEach((t) => obs.observe(t));
  };
  spy($$(".nav-links a"), "active");
  spy($$("#toc a"), "active");

  /* ------------------------------------------------------------------ Feature cards: glow + tilt */
  $$("[data-tilt]").forEach((card) => {
    card.addEventListener("pointermove", (e) => {
      const r = card.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      card.style.setProperty("--mx", `${x * 100}%`);
      card.style.setProperty("--my", `${y * 100}%`);
      if (!reduceMotion) card.style.transform = `perspective(700px) rotateX(${(0.5 - y) * 6}deg) rotateY(${(x - 0.5) * 8}deg) translateY(-3px)`;
    });
    card.addEventListener("pointerleave", () => { card.style.transform = ""; });
  });

  /* ------------------------------------------------------------------ Lightbox */
  const lb = $("#lightbox"), lbImg = $("#lightbox-img"), lbCap = $("#lightbox-cap");
  let lbReturn = null;
  document.addEventListener("click", (e) => {
    const shot = e.target.closest("[data-lightbox]");
    if (!shot) return;
    lbReturn = shot;
    lbImg.src = shot.dataset.lightbox;
    lbImg.alt = shot.dataset.caption || "";
    lbCap.textContent = shot.dataset.caption || "";
    lb.hidden = false;
    $(".lightbox-close", lb).focus();
  });
  const closeLightbox = () => { lb.hidden = true; lbReturn?.focus(); };
  lb.addEventListener("click", closeLightbox);

  /* ------------------------------------------------------------------ Copy buttons */
  $$("[data-copy]").forEach((b) => b.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(b.dataset.copy); b.textContent = "Copied"; b.classList.add("done"); }
    catch (e) { b.textContent = "Select & copy"; }
    setTimeout(() => { b.textContent = "Copy"; b.classList.remove("done"); }, 1600);
  }));

  /* ------------------------------------------------------------------ Modes explorer */
  const tabs = $("#mode-tabs"), panel = $("#mode-panel");
  const renderModePanel = (m) => {
    const kind = { panel: "Opens a panel", menu: "Opens a menu", operator: "Runs an operator" };
    const brushes = m.weight
      ? `<div class="dial-preview"><div class="mini-dial"></div><p>A color-coded <b>weight dial</b> replaces the brush ring: pick any weight from <b>0.0</b> to <b>1.0</b> in one gesture.</p></div>`
      : `<div class="brush-grid">${m.brushes.map((b, i) => `<div class="brush" style="animation-delay:${i * 18}ms"><img src="${b.img}" alt="" loading="lazy"><span>${b.name}</span></div>`).join("")}</div>${m.extra ? `<p class="sub" style="margin-top:12px">${m.extra}</p>` : ""}`;
    panel.innerHTML = `
      <h3>${m.name}</h3><p class="sub">${m.sub}${m.weight ? "" : ` · ${m.brushes.length} brushes`}</p>
      <h4>${m.weight ? "Outer ring" : "Brush ring"}</h4>${brushes}
      <h4>Center buttons</h4>
      <div class="chips">${m.buttons.map((b, i) => `<span class="chip" style="animation-delay:${i * 30}ms" title="${kind[b.kind]}"><img src="${b.icon}" alt="">${b.name}</span>`).join("")}</div>
      <p style="margin-top:22px"><button class="btn btn-ghost btn-sm" type="button" data-try="${m.id}">See it in Blender ↑</button></p>`;
  };
  const selectMode = (id, focus = false) => {
    const m = MODES.find((x) => x.id === id) || MODES[0];
    $$(".mode-tab", tabs).forEach((t) => { const on = t.dataset.id === m.id; t.setAttribute("aria-selected", on); t.tabIndex = on ? 0 : -1; if (on && focus) t.focus(); });
    renderModePanel(m);
  };
  tabs.innerHTML = MODES.map((m) => `<button class="mode-tab" role="tab" type="button" data-id="${m.id}" aria-controls="mode-panel"><img src="${modeIcon(m)}" alt=""><span>${m.name}<small>${m.weight ? "Weight dial" : `${m.brushes.length} brushes`}</small></span></button>`).join("");
  tabs.addEventListener("click", (e) => { const t = e.target.closest(".mode-tab"); if (t) selectMode(t.dataset.id); });
  tabs.addEventListener("keydown", (e) => {
    const list = $$(".mode-tab", tabs), i = list.indexOf(document.activeElement);
    if (i < 0) return;
    const d = ["ArrowDown", "ArrowRight"].includes(e.key) ? 1 : ["ArrowUp", "ArrowLeft"].includes(e.key) ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    selectMode(list[(i + d + list.length) % list.length].dataset.id, true);
  });
  panel.addEventListener("click", (e) => {
    const t = e.target.closest("[data-try]");
    if (!t) return;
    demo.setMode(t.dataset.try);
    $("#demo").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
  });
  selectMode("sculpt");

  /* ------------------------------------------------------------------ Wheel viewer (real add-on captures) */
  const demo = (() => {
    const tabsEl = $("#viewer-tabs"), viewer = $("#viewer");
    const imgs = [$("#viewer-a"), $("#viewer-b")];
    const title = $("#viewer-title"), sub = $("#viewer-sub");
    let front = 0, current = null, token = 0;

    const describe = (m) => (m.weight ? `Weight dial · ${m.buttons.length} buttons` : `${m.brushes.length} brushes · ${m.buttons.length} buttons`);
    tabsEl.innerHTML = MODES.map((m) => `<button class="viewer-tab" role="tab" type="button" data-id="${m.id}" aria-selected="false" tabindex="-1"><img src="${modeIcon(m)}" alt="">${m.name}</button>`).join("");

    // Preload every capture so switching is instant.
    MODES.forEach((m) => { const i = new Image(); i.src = `images/wheels/${m.id}.webp`; });

    const setMode = (id, focusTab = false) => {
      const m = MODES.find((x) => x.id === id) || MODES[0];
      $$(".viewer-tab", tabsEl).forEach((t) => {
        const on = t.dataset.id === m.id;
        t.setAttribute("aria-selected", on);
        t.tabIndex = on ? 0 : -1;
        if (on && focusTab) t.focus();
        if (on && current !== null) t.scrollIntoView({ block: "nearest", inline: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
      });
      title.textContent = m.name;
      sub.textContent = describe(m);
      if (current === null) { current = m.id; return; } // first paint: the <img> already shows Sculpt
      if (m.id === current) return;
      current = m.id;
      const my = ++token;
      const back = imgs[1 - front];
      back.onload = () => {
        if (my !== token) return; // a newer switch won
        back.classList.add("show");
        imgs[front].classList.toggle("show", false);
        front = 1 - front;
      };
      back.alt = `The wheel in ${m.name} mode`;
      back.src = `images/wheels/${m.id}.webp`;
    };

    const step = (d) => {
      const i = MODES.findIndex((m) => m.id === current);
      setMode(MODES[(i + d + MODES.length) % MODES.length].id, tabsEl.contains(document.activeElement));
    };

    tabsEl.addEventListener("click", (e) => { const t = e.target.closest(".viewer-tab"); if (t) setMode(t.dataset.id); });
    tabsEl.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); step(e.key === "ArrowRight" ? 1 : -1); }
    });

    // Arrow keys also work while the viewer is on screen and nothing else is focused.
    let visible = false;
    new IntersectionObserver(([en]) => { visible = en.isIntersecting; }, { threshold: 0.4 }).observe(viewer);
    document.addEventListener("keydown", (e) => {
      if (!visible || (e.key !== "ArrowRight" && e.key !== "ArrowLeft")) return;
      const a = document.activeElement;
      if (a && a !== document.body) return; // focused controls (incl. the tabs) handle their own keys
      if (!$("#palette").hidden || !$("#lightbox").hidden) return;
      e.preventDefault();
      step(e.key === "ArrowRight" ? 1 : -1);
    });

    // Swipe on touch screens; a plain click opens the capture full size.
    let sx = null, swiped = false;
    viewer.addEventListener("pointerdown", (e) => { sx = e.clientX; swiped = false; });
    viewer.addEventListener("pointerup", (e) => {
      if (sx === null) return;
      const dx = e.clientX - sx; sx = null;
      if (Math.abs(dx) > 40) { swiped = true; step(dx < 0 ? 1 : -1); }
    });
    viewer.addEventListener("click", () => {
      if (swiped) return;
      const img = imgs[front];
      lbImg.src = img.src; lbImg.alt = img.alt; lbCap.textContent = img.alt;
      lbReturn = viewer; lb.hidden = false; $(".lightbox-close", lb).focus();
    });

    setMode(MODES[0].id);
    return { setMode };
  })();

  /* ------------------------------------------------------------------ FAQ filter */
  const faqInput = $("#faq-filter"), faqItems = $$("#faq-list details"), faqEmpty = $("#faq-empty");
  faqItems.forEach((d) => { d._sum = $("summary", d).innerHTML; d._p = $("p", d).innerHTML; });
  const mark = (html, q) => (q ? html.replace(new RegExp(`(?![^<]*>)(${q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"), "<mark>$1</mark>") : html);
  faqInput.addEventListener("input", () => {
    const q = faqInput.value.trim().toLowerCase();
    let shown = 0;
    faqItems.forEach((d) => {
      const text = `${d.textContent} ${d.dataset.search}`.toLowerCase();
      const ok = !q || q.split(/\s+/).every((w) => text.includes(w));
      d.hidden = !ok;
      if (ok) shown++;
      $("summary", d).innerHTML = mark(d._sum, q);
      $("p", d).innerHTML = mark(d._p, q);
      d.open = !!q && ok && shown <= 2;
    });
    faqEmpty.hidden = shown > 0;
  });

  /* ------------------------------------------------------------------ Search palette */
  const palette = $("#palette"), pInput = $("#palette-input"), pList = $("#palette-results");
  const index = [
    ...$$("[data-search]").filter((el) => el.tagName === "ARTICLE").map((a) => ({
      title: $("h3", a).textContent.replace(/^\d+/, "").trim(), sub: "User guide", href: `#${a.id}`,
      text: `${a.dataset.search} ${a.textContent}`.toLowerCase(),
    })),
    ...faqItems.map((d, i) => ({
      title: $("summary", d).textContent, sub: "FAQ", href: "#faq", faq: i, text: `${d.dataset.search} ${d.textContent}`.toLowerCase(),
    })),
    ...MODES.map((m) => ({
      title: `${m.name} wheel`, sub: "Modes", href: "#modes", mode: m.id,
      text: `${m.name} ${m.sub} ${(m.brushes || []).map((b) => b.name).join(" ")} ${m.buttons.map((b) => b.name).join(" ")}`.toLowerCase(),
    })),
    ...$$(".feature").map((f) => ({ title: $("h3", f).textContent, sub: "Features", href: "#features", text: f.textContent.toLowerCase() })),
    { title: "See the wheel in every mode", sub: "Wheel", href: "#demo", text: "demo wheel screenshot capture mode see" },
    { title: "Get it on Superhive", sub: "Buy", href: "https://superhivemarket.com/products/sculpt-paint-wheel", text: "buy superhive purchase support store get" },
    { title: "Free download (GitHub)", sub: "Try it first", href: "https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/releases/latest", text: "download free try install zip release latest github" },
    { title: "Support the developer", sub: "Support", href: "#support", text: "support independent developer years fund" },
  ];
  let results = [], sel = 0, lastFocus = null;
  const searchFor = (q) => {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!words.length) return index.filter((r) => r.sub === "User guide");
    return index
      .map((r) => ({ r, score: words.every((w) => r.text.includes(w)) ? words.reduce((s, w) => s + (r.title.toLowerCase().includes(w) ? 3 : 1), 0) : 0 }))
      .filter((x) => x.score).sort((a, b) => b.score - a.score).slice(0, 10).map((x) => x.r);
  };
  const drawResults = () => {
    pList.innerHTML = results.length
      ? results.map((r, i) => `<li role="option" aria-selected="${i === sel}" id="pr-${i}"><a href="${r.href}" data-i="${i}">${r.title}<small>${r.sub}</small></a></li>`).join("")
      : `<li class="none">No results for “${pInput.value.replace(/</g, "&lt;")}”</li>`;
    pInput.setAttribute("aria-activedescendant", results.length ? `pr-${sel}` : "");
  };
  const openSearch = () => {
    lastFocus = document.activeElement;
    palette.hidden = false;
    pInput.value = "";
    results = searchFor(""); sel = 0; drawResults();
    pInput.focus();
  };
  const closeSearch = () => { palette.hidden = true; lastFocus?.focus?.(); };
  const go = (r) => {
    closeSearch();
    if (!r) return;
    if (r.href.startsWith("http")) { location.href = r.href; return; }
    if (r.mode) selectMode(r.mode);
    if (r.faq !== undefined) { faqInput.value = ""; faqInput.dispatchEvent(new Event("input")); faqItems[r.faq].open = true; }
    const target = r.faq !== undefined ? faqItems[r.faq] : $(r.href);
    target?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
    history.replaceState(null, "", r.href);
  };
  pInput.addEventListener("input", () => { results = searchFor(pInput.value); sel = 0; drawResults(); });
  pInput.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!results.length) return;
      sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + results.length) % results.length;
      drawResults();
      $(`#pr-${sel}`)?.scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") { e.preventDefault(); go(results[sel]); }
  });
  pList.addEventListener("click", (e) => { const a = e.target.closest("a[data-i]"); if (a) { e.preventDefault(); go(results[+a.dataset.i]); } });
  palette.addEventListener("click", (e) => { if (e.target.matches("[data-close-search]")) closeSearch(); });
  document.addEventListener("click", (e) => { if (e.target.closest("[data-open-search]")) { e.preventDefault(); openSearch(); } });

  document.addEventListener("keydown", (e) => {
    const typing = document.activeElement?.matches("input, textarea, select, [contenteditable]");
    if ((e.key === "k" || e.key === "K") && (e.ctrlKey || e.metaKey)) { e.preventDefault(); palette.hidden ? openSearch() : closeSearch(); }
    else if (e.key === "/" && !typing && palette.hidden) { e.preventDefault(); openSearch(); }
    else if (e.key === "Escape") {
      if (!palette.hidden) closeSearch();
      else if (!lb.hidden) closeLightbox();
    }
  });
  if (/Mac|iPhone|iPad/.test(navigator.platform)) $$(".search-trigger kbd").forEach((k) => { k.textContent = "⌘ K"; });
})();
