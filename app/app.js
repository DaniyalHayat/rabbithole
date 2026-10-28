/* RabbitHole UI: every displayed paper and citation comes from the locked snapshot. */
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s),
    $$ = (s) => [...document.querySelectorAll(s)],
    D = window.RH_DATA,
    engine = new RH.Engine(D);
  const esc = (s) =>
    String(s ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const themes = {
    music: {
      name: "Music & memory",
      query: "music memory emotion",
      color: "#c4a4ec",
    },
    dreams: {
      name: "Dreams & consciousness",
      query: "dreaming sleep memory",
      color: "#92b9d2",
    },
    attention: {
      name: "Attention & distraction",
      query: "attention distraction",
      color: "#d0b485",
    },
    connection: {
      name: "Human connection",
      query: "loneliness social connection friendship",
      color: "#d9a1b7",
    },
    creativity: {
      name: "Creativity & curiosity",
      query: "creativity curiosity learning",
      color: "#c7b4e5",
    },
    habits: {
      name: "Habits & motivation",
      query: "habit formation procrastination",
      color: "#b6cda0",
    },
    awe: {
      name: "Nature & wonder",
      query: "awe nature wellbeing",
      color: "#9ac9bc",
    },
    perception: {
      name: "Time & perception",
      query: "time perception illusions",
      color: "#e2b092",
    },
  };
  const questions = [
    "Why do songs get stuck in my head?",
    "Why do we dream?",
    "How does curiosity help learning?",
    "Why do we procrastinate?",
    "How does nature affect wellbeing?",
    "Why do we lose track of time?",
    "What helps people feel less lonely?",
    "How does distraction affect attention?",
  ];
  let saved = [];
  try {
    const raw = JSON.parse(localStorage.getItem("rabbithole.saved.v1") || "[]");
    if (Array.isArray(raw))
      saved = [
        ...new Set(
          raw.filter(
            (x) =>
              typeof x === "string" &&
              engine.ids.has(x) &&
              !D.papers[engine.ids.get(x)].retracted,
          ),
        ),
      ].slice(0, 300);
  } catch {}
  let state = {
    view: "explore",
    query: $("#query").value,
    theme: "",
    oa: false,
    year: 0,
    edges: "all",
    mode: "hybrid",
    presentation: "map",
    results: [],
    selected: null,
    compare: [],
    zoom: 1,
    pan: [0, 0],
    origin: "",
    path: [],
    following: false,
  };
  let toastTimer;
  function toast(message) {
    $("#toast").textContent = message;
    $("#toast").classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $("#toast").classList.remove("show"), 3500);
  }
  function persist() {
    try {
      localStorage.setItem("rabbithole.saved.v1", JSON.stringify(saved));
    } catch {
      toast("Browser storage is unavailable. Export your list to keep it.");
    }
    $("#saved-count").textContent = saved.length;
  }
  function safeURL(url, fallback) {
    try {
      const x = new URL(url);
      return x.protocol === "https:" ? x.href : fallback;
    } catch {
      return fallback;
    }
  }
  function source(p) {
    return safeURL(p.doi || p.oa_url, "https://openalex.org/" + p.id);
  }
  function options() {
    return {
      theme: state.theme,
      oa: state.oa,
      year: state.year,
      mode: state.mode,
      limit: 60,
    };
  }
  function view(name) {
    state.view = name;
    for (const v of ["explore", "trails", "method", "atlas"])
      $("#" + v + "-view").classList.toggle("hidden", v !== name);
    $$("[data-view]").forEach((b) =>
      b.classList.toggle("active", b.dataset.view === name),
    );
    $("#view-label").textContent = {
      explore: "Explore",
      trails: "My trails",
      method: "Behind the map",
      atlas: "Research atlas",
    }[name];
    if (name === "trails") renderTrails();
    if (name === "method") {
      renderMethod();
      renderMLDetails();
    }
    if (name === "atlas") renderAtlas();
  }
  function search() {
    state.query = $("#query").value.trim();
    if (state.query !== state.origin) state.following = false;
    state.origin = state.query;
    state.results = engine.search(state.query, options());
    state.selected = state.results[0]?.p.id || null;
    state.path = state.selected ? [state.selected] : [];
    state.zoom = 1;
    state.pan = [0, 0];
    $("#result-summary").textContent = state.results.length
      ? `${state.results.length === 60 ? "Top 60" : state.results.length} matching papers · ${state.theme ? themes[state.theme].name : "all threads"} · ${D.stats.papers.toLocaleString()} papers in this snapshot`
      : "No matching papers in this snapshot";
    $("#map-empty").classList.toggle("hidden", state.results.length > 0);
    $("#create-trail").disabled = !state.results.length;
    renderGraph();
    renderList();
    renderPaper();
    renderThread();
  }
  function choose(id, record = true) {
    if (!engine.ids.has(id)) return;
    state.selected = id;
    if (record && state.path.at(-1) !== id) {
      state.path.push(id);
      state.following = true;
    }
    const p = D.papers[engine.ids.get(id)];
    if (!state.results.some((r) => r.p.id === id))
      state.results.unshift({ i: engine.ids.get(id), p, score: 0 });
    renderPaper();
    renderGraph();
    renderList();
    renderThread();
  }
  function connectedPapers(p, limit = 3) {
    if (!p) return [];
    // A branch must also match the original question, so a citation hop cannot
    // silently turn an earworm question into an unrelated research theme.
    const matches = new Map(state.results.map((r, i) => [r.p.id, i]));
    const visited = new Set(state.path);
    return engine.related(p.id, D.papers.length)
      .filter((r) => matches.has(r.p.id) && !visited.has(r.p.id))
      .sort((a, b) => {
        const directA = a.kind === "similarity" ? 0 : 1;
        const directB = b.kind === "similarity" ? 0 : 1;
        return directB - directA || Number(!!b.p.abstract) - Number(!!a.p.abstract) || matches.get(a.p.id) - matches.get(b.p.id);
      }).slice(0, limit);
  }
  function connectionLabel(kind) {
    return { cites: "A source cited by this paper", "cited by": "Research that cites this paper", "shared topic": "Another angle on a shared research topic", similarity: "A related idea in the text" }[kind];
  }
  function renderThread() {
    const p = D.papers[engine.ids.get(state.selected)];
    const related = connectedPapers(p);
    const context = $("#thread-context");
    context.classList.toggle("hidden", !p || !state.following);
    if (p && state.following) {
      const previous = state.path.length > 1 ? state.path[state.path.length - 2] : null;
      const relation = previous ? engine.related(previous, D.papers.length).find((r) => r.p.id === p.id) : null;
      const terms = RH.tokenize(RH.expand(state.origin));
      const sentences = (p.abstract || "").match(/[^.!?]+[.!?]+(?:\s|$)|[^.!?]+$/g) || [];
      const scored = sentences.map((text, index) => ({ text: text.trim(), index, score: terms.filter((t) => text.toLowerCase().includes(t)).length }));
      scored.sort((a, b) => b.score - a.score || a.index - b.index);
      const excerpt = scored.slice(0, 2).sort((a, b) => a.index - b.index).map((x) => x.text).join(" ");
      context.innerHTML = `<div class="thread-top"><p class="eyebrow">YOUR ORIGINAL QUESTION</p><span>Step ${state.path.length}</span></div><h2>${esc(state.origin || "Explore connected research")}</h2><nav class="thread-history" aria-label="Reading path">${state.path.map((id, index) => `<button data-step="${index}" ${index === state.path.length - 1 ? 'aria-current="step"' : ""}>${index + 1}. ${esc(D.papers[engine.ids.get(id)].title.slice(0, 54))}${D.papers[engine.ids.get(id)].title.length > 54 ? "…" : ""}</button>`).join('<span aria-hidden="true">→</span>')}</nav><p class="thread-connection">${esc(relation ? connectionLabel(relation.kind) + ". Still connected to your original question." : "Start with the research behind your question.")}</p><h3>${esc(p.title)}</h3><p class="eyebrow thread-source-label">IN THE RESEARCHER’S WORDS · SOURCE ABSTRACT EXCERPT</p><blockquote>${esc(excerpt || "This record has no source abstract. Open the original paper to explore this angle.")}</blockquote><a class="paper-link" target="_blank" rel="noopener" href="${esc(source(p))}">Read the full source ↗</a><div class="thread-actions"><button id="thread-back" ${state.path.length < 2 ? "disabled" : ""}>← Previous step</button><button id="thread-root" ${state.path.length < 2 ? "disabled" : ""}>Back to the original</button><button id="thread-deeper" ${!related.length ? "disabled" : ""}>${related.length ? "Go one step deeper ↗" : "You’ve explored these connections"}</button></div>`;
      $("#thread-back").onclick = () => revisitStep(state.path.length - 2);
      $("#thread-root").onclick = () => revisitStep(0);
      $("#thread-deeper").onclick = () => related[0] && choose(related[0].p.id);
      $$("[data-step]").forEach((b) => b.onclick = () => revisitStep(Number(b.dataset.step)));
    }
    $("#thread-cards").innerHTML = related.length
      ? related.map((r) => `<button class="thread-card" data-branch="${esc(r.p.id)}" style="--color:#c4a4ec"><small>${esc(connectionLabel(r.kind).toUpperCase())}</small><span>${esc(r.p.title)}</span><b>↗</b></button>`).join("")
      : '<p class="thread-end">No further connected papers match this question and your filters. Go back a step to take another branch.</p>';
    $$("[data-branch]").forEach((b) => b.onclick = () => { choose(b.dataset.branch); $("#thread-context").scrollIntoView({ behavior: "smooth", block: "start" }); });
  }
  function revisitStep(index) {
    if (index < 0 || index >= state.path.length) return;
    state.path = state.path.slice(0, index + 1);
    choose(state.path[index], false);
  }
  function toggleSave(id) {
    if (saved.includes(id)) {
      saved = saved.filter((x) => x !== id);
      toast("Removed from your collection.");
    } else {
      saved.push(id);
      toast("Saved to My trails.");
    }
    persist();
    renderPaper();
    if (state.view === "trails") renderTrails();
  }
  function renderPaper() {
    const panel = $("#paper-panel"),
      p = D.papers[engine.ids.get(state.selected)];
    if (!p) {
      panel.innerHTML =
        '<p class="eyebrow">ROOM FOR YOUR NEXT QUESTION</p><h2 style="margin-top:20px">Good discoveries start with a little wondering.</h2><p class="paper-abstract" style="margin-top:20px">Search a topic or try a question above. This app searches a fixed research snapshot; it does not search the whole internet.</p>';
      return;
    }
    const expanded = RH.expand(state.query),
      terms = [...new Set(RH.tokenize(expanded))]
        .filter((t) => (p.title + " " + p.abstract).toLowerCase().includes(t))
        .slice(0, 5);
    const selectedSaved = saved.includes(p.id);
    const related = connectedPapers(p);
    const text =
      p.abstract ||
      "No abstract is supplied for this paper in the source metadata. Open the original record to investigate it.";
    panel.innerHTML = `<p class="eyebrow">A PAPER WORTH FOLLOWING <span style="float:right">↗</span></p><div class="paper-meta"><span class="paper-tag">${esc(p.type)}</span><span>${p.year || "Year unknown"}</span></div><h2>${esc(p.title)}</h2><p class="authors">${esc(p.authors.filter(Boolean).join(", "))}${p.authors.length === 3 ? " et al." : ""}</p><div class="paper-stats"><span>${p.cited.toLocaleString()} citations in OpenAlex</span>${p.oa ? '<span class="oa-badge">◉ Open access</span>' : ""}</div><p class="abstract-label">FROM THE SOURCE ABSTRACT</p><div class="paper-abstract" id="abstract-text">${esc(text)}</div><button class="abstract-more" id="abstract-expand">Expand abstract ↓</button><a class="paper-link" target="_blank" rel="noopener" href="${esc(source(p))}">Open original source ↗</a><div class="paper-actions"><button id="save-paper" class="${selectedSaved ? "saved" : ""}" aria-pressed="${selectedSaved}">${selectedSaved ? "✓ Saved to trails" : "+ Save paper"}</button><button id="compare-paper">${state.compare.includes(p.id) ? "✓ Selected" : "+ Compare"}</button></div><div class="why-card"><strong>✧ Why this paper?</strong>${terms.length ? "Your search connects with: " + esc(terms.join(" · ")) + "." : "Connected through the research map."}${p.topics[0] ? " Tagged by OpenAlex: " + esc(p.topics[0].name) + "." : ""}<small>Search similarity is a discovery signal. Citation counts don’t establish quality or agreement.</small></div><div class="related-section"><h3>Keep following the thread</h3>${related.map((r) => `<button class="related-item" data-related="${r.p.id}">${esc(r.p.title.slice(0, 96))}<span>${r.kind === "cites" ? "THIS PAPER CITES" : r.kind === "cited by" ? "CITES THE SELECTED PAPER" : r.kind === "shared topic" ? "SHARED OPENALEX TOPIC" : "LATENT TEXT SIMILARITY"} · ${r.p.year || "n.d."} ↗</span></button>`).join("")}</div>`;
    $("#save-paper").onclick = () => toggleSave(p.id);
    $("#compare-paper").onclick = () => compare(p.id);
    $("#abstract-expand").onclick = (e) => {
      const expanded = e.currentTarget.getAttribute("aria-expanded") === "true";
      e.currentTarget.setAttribute("aria-expanded", String(!expanded));
      $("#abstract-text").style.maxHeight = expanded ? "174px" : "none";
      e.currentTarget.textContent = expanded
        ? "Expand abstract ↓"
        : "Collapse abstract ↑";
    };
    $$("[data-related]").forEach(
      (b) => (b.onclick = () => choose(b.dataset.related)),
    );
  }
  function compare(id) {
    if (state.compare.includes(id)) {
      state.compare = state.compare.filter((x) => x !== id);
      renderPaper();
      return;
    }
    state.compare.push(id);
    if (state.compare.length < 2) {
      toast("First paper selected. Choose another paper and press Compare.");
      renderPaper();
      return;
    }
    const [a, b] = state.compare
      .slice(-2)
      .map((id) => D.papers[engine.ids.get(id)]);
    const shared = a.topics.filter((t) => b.topics.some((u) => u.id === t.id));
    const cited = a.references.includes(b.id)
      ? "The left paper cites the right paper."
      : b.references.includes(a.id)
        ? "The right paper cites the left paper."
        : "No direct citation between these papers appears in this snapshot.";
    $("#compare-content").innerHTML =
      `<p class="compare-note">${esc(cited)} ${shared.length ? "Shared topics: " + esc(shared.map((t) => t.name).join(", ")) + "." : ""} This comparison shows metadata and abstracts; it does not determine whether findings agree.</p><div class="compare-grid">${[a, b].map((p) => `<div><p>${p.year || "n.d."} · ${esc(p.type)} · ${p.oa ? "Open access" : "Access varies"}</p><h3>${esc(p.title)}</h3><p>${esc(p.abstract || "No abstract available in the source metadata.")}</p><a href="${esc(source(p))}" target="_blank" rel="noopener">Read original source ↗</a></div>`).join("")}</div>`;
    $("#compare-dialog").showModal();
    state.compare = [];
    renderPaper();
  }
  function renderList() {
    $("#results-list").innerHTML = state.results
      .map(
        (r) =>
          `<button class="result-row ${r.p.id === state.selected ? "selected" : ""}" data-paper="${r.p.id}"><strong>${esc(r.p.title)}</strong><small>${r.p.year || "n.d."} · ${esc(r.p.type)} · ${esc(r.p.topics[0]?.name || "Unclassified")} ${r.p.oa ? "· Open access" : ""}</small></button>`,
      )
      .join("");
    $$("[data-paper]").forEach(
      (b) => (b.onclick = () => choose(b.dataset.paper)),
    );
  }
  function renderGraph() {
    const world = $("#graph-world");
    let rows = state.results.slice(0, 24);
    if (!rows.some((r) => r.p.id === state.selected) && state.selected) {
      const p = D.papers[engine.ids.get(state.selected)];
      rows = [{ p, i: engine.ids.get(p.id) }, ...rows.slice(0, 23)];
    }
    if (!rows.length) {
      world.innerHTML = "";
      return;
    }
    const positions = new Map(),
      selectedIndex = rows.findIndex((r) => r.p.id === state.selected);
    const n = rows.length;
    rows.forEach((r, i) => {
      const angle = i * 2.399963,
        ring = i === selectedIndex ? 0 : 85 + Math.sqrt(i + 1) * 27;
      positions.set(r.p.id, {
        x: i === selectedIndex ? 440 : 440 + Math.cos(angle) * ring * 1.23,
        y: i === selectedIndex ? 255 : 255 + Math.sin(angle) * ring * 0.82,
      });
    });
    // Separate nearby labels with a deterministic repulsion pass.
    for (let iter = 0; iter < 90; iter++) {
      for (let i = 0; i < n; i++)
        for (let j = i + 1; j < n; j++) {
          const a = positions.get(rows[i].p.id),
            b = positions.get(rows[j].p.id);
          let dx = a.x - b.x,
            dy = a.y - b.y,
            dist = Math.hypot(dx, dy) || 1;
          if (dist < 87) {
            const f = (87 - dist) * 0.035,
              fx = (dx / dist) * f,
              fy = (dy / dist) * f;
            if (i !== selectedIndex) {
              a.x += fx;
              a.y += fy;
            }
            if (j !== selectedIndex) {
              b.x -= fx;
              b.y -= fy;
            }
          }
        }
      for (const pos of positions.values()) {
        pos.x = Math.min(790, Math.max(85, pos.x));
        pos.y = Math.min(462, Math.max(64, pos.y));
      }
    }
    const links = [],
      seen = new Set();
    function link(a, b, kind) {
      const key = [a, b].sort().join(":");
      if (a !== b && !seen.has(key)) {
        seen.add(key);
        links.push({ a, b, kind });
      }
    }
    for (const r of rows)
      for (const ref of r.p.references)
        if (positions.has(ref)) link(r.p.id, ref, "citation");
    for (let i = 1; i < n; i++) {
      const p = rows[i].p;
      let best = null;
      for (let j = 0; j < i; j++) {
        const q = rows[j].p,
          shared = p.topics.some((t) => q.topics.some((u) => u.id === t.id));
        const score = RH.dot(p.vector, q.vector);
        if (!best || score > best.score)
          best = { id: q.id, score, kind: shared ? "topic" : "similarity" };
      }
      if (best && (best.kind === "topic" || best.score > 0.25))
        link(p.id, best.id, best.kind);
    }
    const visible = links.filter(
      (l) => state.edges === "all" || l.kind === state.edges,
    );
    $("#graph").setAttribute(
      "aria-label",
      `Research map with ${rows.length} papers and ${visible.length} displayed connections. Switch to List for keyboard-friendly results.`,
    );
    world.innerHTML = `<defs><marker id="arrow" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#ad91bf"/></marker></defs>${visible
      .map((l) => {
        const a = positions.get(l.a),
          b = positions.get(l.b);
        return `<path class="graph-link ${l.kind}" d="M${a.x},${a.y} Q${(a.x + b.x) / 2 + 12},${(a.y + b.y) / 2 - 8} ${b.x},${b.y}" ${l.kind === "citation" ? 'marker-end="url(#arrow)"' : ""}><title>${l.kind === "citation" ? esc(D.papers[engine.ids.get(l.a)].title) + " cites " + esc(D.papers[engine.ids.get(l.b)].title) : l.kind === "topic" ? "Shared OpenAlex topic" : "Latent text similarity"}</title></path>`;
      })
      .join("")}${rows
      .map((r, i) => {
        const p = r.p,
          pos = positions.get(p.id),
          selected = p.id === state.selected,
          color = themes[p.themes[0]]?.color || "#c7a4ed",
          label = p.title.length > 44 ? p.title.slice(0, 42) + "…" : p.title;
        const words = label.split(" "),
          half = Math.ceil(words.length / 2);
        return `<g class="graph-node ${selected ? "selected" : ""}" transform="translate(${pos.x},${pos.y})" data-node="${p.id}" tabindex="0" role="button" aria-label="Explore ${esc(p.title)}"><title>${esc(p.title)} (${p.year || "n.d."})</title>${selected ? `<circle r="31" fill="${color}" opacity=".07"/><circle r="23" fill="none" stroke="${color}" opacity=".24"/>` : ""}<circle r="${selected ? 15 : 5 + Math.min(5, Math.log10(p.cited + 1))}" fill="${color}" opacity="${selected ? 1 : 0.74}"/>${selected ? '<text text-anchor="middle" y="4" style="font-size:11px;fill:#37233f">✦</text>' : ""}<text text-anchor="middle" y="${selected ? 45 : 25}"><tspan x="0">${esc(words.slice(0, half).join(" "))}</tspan><tspan x="0" dy="13">${esc(words.slice(half).join(" "))}</tspan></text></g>`;
      })
      .join("")}`;
    $$("[data-node]").forEach((node) => {
      node.onclick = () => {
        if (!dragMoved) choose(node.dataset.node);
      };
      node.onkeydown = (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          choose(node.dataset.node);
        }
      };
    });
    transformGraph();
  }
  function transformGraph() {
    $("#graph-world").setAttribute(
      "transform",
      `translate(${state.pan[0]},${state.pan[1]}) translate(440,265) scale(${state.zoom}) translate(-440,-265)`,
    );
  }
  let dragging = false,
    dragMoved = false,
    start = [0, 0],
    original = [0, 0];
  const svg = $("#graph");
  svg.addEventListener("pointerdown", (e) => {
    if (e.target.closest("[data-node]")) return;
    dragging = true;
    dragMoved = false;
    start = [e.clientX, e.clientY];
    original = [...state.pan];
    svg.setPointerCapture(e.pointerId);
  });
  svg.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const factor =
      svg.viewBox.baseVal.width / svg.getBoundingClientRect().width;
    const dx = (e.clientX - start[0]) * factor,
      dy = (e.clientY - start[1]) * factor;
    dragMoved = Math.abs(dx) + Math.abs(dy) > 3;
    state.pan = [original[0] + dx, original[1] + dy];
    transformGraph();
  });
  svg.addEventListener("pointerup", () => {
    dragging = false;
    setTimeout(() => (dragMoved = false), 0);
  });
  svg.addEventListener("pointercancel", () => (dragging = false));
  function renderTrails() {
    const target = $("#trail-list");
    $("#export-trail").disabled = !saved.length;
    $("#clear-trail").disabled = !saved.length;
    if (!saved.length) {
      target.innerHTML =
        '<div class="empty"><span>↝</span><h3>Your next discovery belongs here.</h3><p>Save a paper from the map or build a suggested reading trail.</p><button id="back-explore">Back to exploring ↗</button></div>';
      $("#back-explore").onclick = () => view("explore");
      return;
    }
    target.innerHTML = saved
      .map((id, i) => {
        const p = D.papers[engine.ids.get(id)];
        return `<article class="trail-card"><span class="number">${String(i + 1).padStart(2, "0")}</span><div><h3>${esc(p.title)}</h3><p>${p.year || "n.d."} · ${esc(p.authors.slice(0, 2).join(", "))} · ${esc(p.type)}</p><a href="${esc(source(p))}" target="_blank" rel="noopener">Original source ↗</a> <button class="quiet" data-revisit="${id}">Explore connections</button></div><button class="remove" data-remove="${id}" aria-label="Remove ${esc(p.title)}">Remove ×</button></article>`;
      })
      .join("");
    $$("[data-remove]").forEach(
      (b) => (b.onclick = () => toggleSave(b.dataset.remove)),
    );
    $$("[data-revisit]").forEach(
      (b) =>
        (b.onclick = () => {
          view("explore");
          choose(b.dataset.revisit);
        }),
    );
  }
  function renderMethod() {
    const b = D.benchmark;
    $("#method-content").innerHTML = `<div class="method-grid">${[
      [D.stats.papers.toLocaleString(), "real research papers"],
      [
        D.stats.citation_edges.toLocaleString(),
        "verified in-snapshot citation edges",
      ],
      [D.stats.topics, "OpenAlex topics"],
      [D.stats.abstracts.toLocaleString(), "papers with source abstracts"],
      [D.stats.open_access.toLocaleString(), "open-access records"],
      [D.stats.retracted, "retracted records excluded from discovery"],
    ]
      .map(
        ([n, s]) => `<div class="method-card"><h2>${n}</h2><p>${s}</p></div>`,
      )
      .join(
        "",
      )}</div><article class="method-explanation"><h2>How a question becomes a map</h2><ol><li>Search combines BM25 keyword matching with 48-dimensional latent semantic analysis. LSA is a compact statistical text model, not a large language model.</li><li>Searchable text includes titles, source abstracts where available, and OpenAlex topic labels. A few visible question patterns receive documented synonym expansions.</li><li>Solid arrows follow actual reference metadata. Dashed connections show a shared topic; dotted connections show text similarity. A citation does not mean agreement.</li><li>Reading trails use relevance and diversity, with a small first-position preference for reviews. Their order is a suggestion, not an established learning prerequisite.</li></ol></article><article class="method-explanation"><h2>What the snapshot can and cannot tell you</h2><p>This is a fixed, English-language sample from 16 curiosity searches, retrieved ${esc(D.stats.snapshot.slice(0, 10))}. It is not a complete or representative literature review. Metadata, abstracts, open-access links, and retraction flags may be incomplete or change.</p><p>All scientific text in the paper panel comes from the supplied abstract. The app does not generate answers, determine scientific consensus, or establish whether two papers contradict each other. Your collection stays in your browser.</p><p><a href="https://openalex.org" target="_blank" rel="noopener">OpenAlex source</a> · <a href="https://github.com/DaniyalHayat/rabbithole/blob/main/docs/METHODOLOGY.md" target="_blank" rel="noopener">Read the method and limitations ↗</a></p></article>${b ? `<article class="method-explanation"><h2>Measured search performance</h2><p>External BEIR SciFact benchmark: ${b.documents.toLocaleString()} documents and ${b.test_queries} held-out test queries. Fusion weight was selected on ${b.train_queries} training queries. This biomedical retrieval test does not validate curiosity-topic relevance or learning outcomes.</p><table><thead><tr><th>Method</th><th>nDCG@10</th><th>Recall@10</th><th>MRR@10</th></tr></thead><tbody><tr><td>BM25 baseline</td><td>${b.baseline.ndcg10.toFixed(3)}</td><td>${b.baseline.recall10.toFixed(3)}</td><td>${b.baseline.mrr10.toFixed(3)}</td></tr><tr><td>Train-selected fusion (${b.selected_weight})</td><td>${b.selected.ndcg10.toFixed(3)}</td><td>${b.selected.recall10.toFixed(3)}</td><td>${b.selected.mrr10.toFixed(3)}</td></tr></tbody></table><p>Paired difference in nDCG@10: ${b.ndcg10_difference.toFixed(4)}; 95% bootstrap interval [${b.paired_bootstrap_95_ci.map((x) => x.toFixed(4)).join(", ")}], based on 5,000 resamples. The app uses a fixed exploration weight of 0.15; the benchmark reports its separately selected setting.</p></article>` : ""}`;
  }
  function renderMLDetails() {
    const m = D.ml_benchmark;
    if (!m) return;
    const element = document.createElement("article");
    element.className = "method-explanation";
    element.innerHTML = `<h2>A trained ML model, with a deployment decision</h2><p>I trained a pairwise logistic learning-to-rank model on ${m.training_queries} SciFact training queries and ${m.training_pairs.toLocaleString()} positive/negative pairs. It learns weights for BM25, latent similarity, query coverage, title coverage, and document length. Regularization was selected within the training split.</p><table><tr><th>Held-out method</th><th>nDCG@10</th><th>Recall@10</th></tr><tr><td>Hybrid baseline</td><td>${m.hybrid_baseline.ndcg10.toFixed(3)}</td><td>${m.hybrid_baseline.recall10.toFixed(3)}</td></tr><tr><td>Learned reranker</td><td>${m.metrics.ndcg10.toFixed(3)}</td><td>${m.metrics.recall10.toFixed(3)}</td></tr></table><p>The ML model underperformed the simpler baseline on the held-out test. Hybrid remains the default. The ML option is available as an explicitly experimental comparison; its utilities are not relevance probabilities. Transfer from biomedical queries to curiosity topics has not been validated.</p>`;
    $("#method-content").append(element);
  }
  let atlasCountry = "";
  function renderAtlas() {
    const theme = $("#atlas-theme").value,
      counts = new Map(),
      papers = D.papers.filter(
        (p) => !p.retracted && (!theme || p.themes.includes(theme)),
      );
    for (const p of papers)
      for (const code of new Set(p.countries || []))
        counts.set(code, (counts.get(code) || 0) + 1);
    const names = new Map(
      D.geography.features.map((f) => [
        f.properties.country_code,
        f.properties.country_name,
      ]),
    );
    const entries = [...counts].sort(
      (a, b) => b[1] - a[1] || a[0].localeCompare(b[0]),
    );
    if (!counts.has(atlasCountry)) atlasCountry = entries[0]?.[0] || "";
    const max = Math.max(1, ...counts.values());
    function ringPath(ring) {
      return (
        ring
          .map(
            ([lon, lat], i) =>
              (i ? "L" : "M") +
              ((lon + 180) * 2.5).toFixed(2) +
              "," +
              ((90 - lat) * 2.5).toFixed(2),
          )
          .join(" ") + " Z"
      );
    }
    $("#atlas-svg").innerHTML = D.geography.features
      .map((f) => {
        const props = f.properties,
          code = props.country_code,
          n = counts.get(code) || 0,
          polygons =
            f.geometry.type === "Polygon"
              ? [f.geometry.coordinates]
              : f.geometry.coordinates;
        const path = polygons.flatMap((p) => p.map(ringPath)).join(" "),
          light = 13 + (Math.log1p(n) / Math.log1p(max)) * 48;
        return `<path d="${path}" fill="${n ? `hsl(269 35% ${light}%)` : "#211d2a"}" fill-rule="evenodd" stroke="${code === atlasCountry ? "#f1d7ff" : "#51415d"}" stroke-width="${code === atlasCountry ? 1.5 : 0.45}" data-country="${esc(code)}"><title>${esc(props.country_name)}: ${n} snapshot papers</title></path>`;
      })
      .join("");
    $("#atlas-countries").innerHTML = entries
      .map(
        ([code, n]) =>
          `<button data-country="${esc(code)}" class="${code === atlasCountry ? "active" : ""}">${esc(names.get(code) || code)} <span>${n}</span></button>`,
      )
      .join("");
    const selected = papers.filter((p) =>
      (p.countries || []).includes(atlasCountry),
    );
    $("#atlas-detail").innerHTML =
      `<p class="eyebrow">INSTITUTION AFFILIATION</p><h2>${esc(names.get(atlasCountry) || atlasCountry || "No data")}</h2><p>${selected.length} distinct snapshot papers</p><p style="margin-top:12px">A paper with institutions in multiple countries counts once in each. These counts do not identify author nationality or measure national research output.</p><h3 style="font-size:12px;margin:20px 0 8px">Follow a paper from here</h3>${selected
        .slice()
        .sort((a, b) => (b.year || 0) - (a.year || 0))
        .slice(0, 5)
        .map(
          (p) =>
            `<button class="atlas-paper" data-atlas-paper="${p.id}">${esc(p.title)}<small>${p.year || "n.d."} ↗</small></button>`,
        )
        .join("")}`;
    $$("[data-country]").forEach(
      (e) =>
        (e.onclick = () => {
          atlasCountry = e.dataset.country;
          renderAtlas();
        }),
    );
    $$("[data-atlas-paper]").forEach(
      (e) =>
        (e.onclick = () => {
          const p = D.papers[engine.ids.get(e.dataset.atlasPaper)];
          state.theme = "";
          $("#query").value = p.title;
          view("explore");
          search();
          choose(p.id);
        }),
    );
  }
  $("#atlas-theme").innerHTML += Object.entries(themes)
    .map(([k, t]) => `<option value="${k}">${esc(t.name)}</option>`)
    .join("");
  $("#atlas-theme").onchange = () => {
    atlasCountry = "";
    renderAtlas();
  };
  $("#atlas-export").onclick = () => {
    const theme = $("#atlas-theme").value,
      counts = new Map();
    for (const p of D.papers)
      if (!p.retracted && (!theme || p.themes.includes(theme)))
        for (const c of new Set(p.countries || []))
          counts.set(c, (counts.get(c) || 0) + 1);
    const geo = {
      type: "FeatureCollection",
      features: D.geography.features.map((f) => ({
        ...f,
        properties: {
          ...f.properties,
          papers: counts.get(f.properties.country_code) || 0,
          theme: theme || "all",
        },
      })),
    };
    const a = document.createElement("a");
    a.href = URL.createObjectURL(
      new Blob([JSON.stringify(geo)], { type: "application/geo+json" }),
    );
    a.download = "rabbithole-research-atlas.geojson";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    toast(
      "ArcGIS-compatible GeoJSON exported. Counts represent this selected snapshot.",
    );
  };
  $("#theme-nav").innerHTML = Object.entries(themes)
    .map(
      ([key, t]) =>
        `<button data-theme="${key}" style="--color:${t.color}"><span class="theme-dot"></span>${t.name}</button>`,
    )
    .join("");
  $$("[data-theme]").forEach(
    (b) =>
      (b.onclick = () => {
        state.theme = state.theme === b.dataset.theme ? "" : b.dataset.theme;
        $$("[data-theme]").forEach((x) =>
          x.classList.toggle("active", x.dataset.theme === state.theme),
        );
        $("#query").value = state.theme
          ? themes[state.theme].query
          : questions[0];
        view("explore");
        search();
      }),
  );
  $$("[data-view]").forEach((b) => (b.onclick = () => view(b.dataset.view)));
  $(".brand").onclick = (e) => {
    e.preventDefault();
    view("explore");
  };
  $("#search-form").onsubmit = (e) => {
    e.preventDefault();
    state.theme = "";
    $$("[data-theme]").forEach((x) => x.classList.remove("active"));
    if ($("#query").value.trim() === state.origin && state.following) {
      const next = connectedPapers(D.papers[engine.ids.get(state.selected)], 1)[0];
      if (next) choose(next.p.id);
      else toast("You’ve reached the end of this branch. Go back to explore another connection.");
    } else {
      search();
      state.following = true;
      renderThread();
    }
    $("#thread-context").scrollIntoView({ behavior: "smooth", block: "start" });
  };
  $$("[data-question]").forEach(
    (b) =>
      (b.onclick = () => {
        state.theme = "";
        $("#query").value = b.dataset.question;
        $$("[data-theme]").forEach((x) => x.classList.remove("active"));
        search();
      }),
  );
  $("#surprise").onclick = () => {
    view("explore");
    state.theme = "";
    $("#query").value = questions[Math.floor(Math.random() * questions.length)];
    search();
  };
  $("#oa-filter").onchange = (e) => {
    state.oa = e.target.checked;
    search();
  };
  $("#year-filter").onchange = (e) => {
    state.year = Number(e.target.value);
    search();
  };
  $("#edge-filter").onchange = (e) => {
    state.edges = e.target.value;
    renderGraph();
  };
  $("#ranking-mode").onchange = (e) => {
    state.mode = e.target.value;
    search();
    if (state.mode === "learned")
      toast(
        "Experimental ML reranking. Trained on SciFact; curiosity-topic transfer is not validated.",
      );
  };
  function presentation(mode) {
    state.presentation = mode;
    $("#map-stage").classList.toggle("hidden", mode !== "map");
    $("#results-list").classList.toggle("hidden", mode !== "list");
    $("#map-tab").setAttribute("aria-pressed", String(mode === "map"));
    $("#list-tab").setAttribute("aria-pressed", String(mode === "list"));
  }
  $("#map-tab").onclick = () => presentation("map");
  $("#list-tab").onclick = () => presentation("list");
  $("#zoom-in").onclick = () => {
    state.zoom = Math.min(2.2, state.zoom + 0.2);
    transformGraph();
  };
  $("#zoom-out").onclick = () => {
    state.zoom = Math.max(0.5, state.zoom - 0.2);
    transformGraph();
  };
  $("#zoom-reset").onclick = () => {
    state.zoom = 1;
    state.pan = [0, 0];
    transformGraph();
  };
  $("#reset-search").onclick = () => {
    state.theme = "";
    state.oa = false;
    state.year = 0;
    $("#oa-filter").checked = false;
    $("#year-filter").value = "0";
    $("#query").value = questions[0];
    search();
  };
  $("#create-trail").onclick = () => {
    const path = engine.trail(state.query, options());
    for (const r of path) if (!saved.includes(r.p.id)) saved.push(r.p.id);
    persist();
    view("trails");
    toast(
      "Suggested trail saved. Relevance and variety guide this reading order.",
    );
  };
  $("#export-trail").onclick = () => {
    const text =
      "# My RabbitHole reading trail\n\n" +
      saved
        .map((id, i) => {
          const p = D.papers[engine.ids.get(id)];
          return `${i + 1}. **${p.title}** (${p.year || "n.d."})\n   ${p.authors.join(", ")}\n   ${source(p)}\n   OpenAlex: https://openalex.org/${id}`;
        })
        .join("\n\n") +
      "\n\nResearch discovery snapshot. Reading order is a suggestion, not a scientific conclusion.\n";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(
      new Blob([text], { type: "text/markdown;charset=utf-8" }),
    );
    a.download = "rabbithole-reading-trail.md";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    toast("Reading list exported.");
  };
  $("#clear-trail").onclick = () => {
    saved = [];
    persist();
    renderTrails();
    toast("Collection cleared from this browser.");
  };
  $("#close-compare").onclick = () => $("#compare-dialog").close();
  $("#snapshot-label").textContent =
    `OpenAlex · snapshot ${D.stats.snapshot.slice(0, 10)}`;
  persist();
  search();
  function responsiveMap() {
    const small = window.matchMedia("(max-width:700px)").matches;
    svg.setAttribute("viewBox", small ? "240 65 400 400" : "0 0 880 530");
  }
  responsiveMap();
  window.addEventListener("resize", responsiveMap);
  if (window.matchMedia("(max-width:700px)").matches) presentation("list");
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") $("#compare-dialog").close();
    if (
      e.key === "/" &&
      !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)
    ) {
      e.preventDefault();
      view("explore");
      $("#query").focus();
    }
  });
})();
