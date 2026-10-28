(function (root) {
  "use strict";
  const STOP = new Set(
    "a an and are as at be been but by can could did do does for from had has have how i if in into is it its may more most not of on or our should so some than that the their there these they this those to was we were what when where which who why will with would you your".split(
      " ",
    ),
  );
  const tokenize = (text) =>
    (
      String(text)
        .toLowerCase()
        .match(/[a-z0-9]+/g) || []
    ).filter((t) => t.length > 1 && !STOP.has(t));
  const dot = (a, b) => a.reduce((s, v, i) => s + v * (b[i] || 0), 0);
  const norm = (a) => {
    const n = Math.sqrt(dot(a, a)) || 1;
    return a.map((x) => x / n);
  };
  const expand = (q) => {
    let x = q;
    const pairs = [
      [
        /songs? (get )?stuck|stuck in my head|earworms?/i,
        "involuntary musical imagery music",
      ],
      [/why.*dream|what.*dream/i, "dreaming sleep memory"],
      [/put.*off|procrastinat/i, "procrastination self regulation"],
      [/lose track of time|time.*fly/i, "time perception subjective"],
      [/make.*friends|feel.*lonely/i, "loneliness social connection"],
      [/phone.*focus|focus.*phone/i, "attention distraction social media"],
    ];
    for (const [r, s] of pairs) if (r.test(q)) x += " " + s;
    return x;
  };
  class Engine {
    constructor(data) {
      this.data = data;
      this.papers = data.papers;
      this.n = this.papers.length;
      this.terms = new Map(data.search.vocab.map((t, i) => [t, i]));
      this.counts = [];
      this.df = new Map();
      this.lengths = [];
      this.vectors = data.papers.map((p) => p.vector);
      this.ids = new Map(this.papers.map((p, i) => [p.id, i]));
      for (const p of this.papers) {
        const text =
          p.title +
          " " +
          p.title +
          " " +
          p.abstract +
          " " +
          p.topics.map((t) => t.name).join(" ");
        const c = new Map();
        for (const t of tokenize(text)) c.set(t, (c.get(t) || 0) + 1);
        this.counts.push(c);
        this.lengths.push([...c.values()].reduce((a, b) => a + b, 0));
        for (const t of c.keys()) this.df.set(t, (this.df.get(t) || 0) + 1);
      }
      this.avg = this.lengths.reduce((a, b) => a + b, 0) / this.n || 1;
    }
    score(query, weight = 0.15, doExpand = true) {
      const queryTerms = tokenize(doExpand ? expand(query) : query),
        unique = [...new Set(queryTerms)],
        lex = Array(this.n).fill(0);
      for (const t of unique) {
        const df = this.df.get(t);
        if (!df) continue;
        const idf = Math.log(1 + (this.n - df + 0.5) / (df + 0.5));
        for (let i = 0; i < this.n; i++) {
          const tf = this.counts[i].get(t) || 0;
          lex[i] +=
            (idf * tf * 2.2) /
            (tf + 1.2 * (0.25 + (0.75 * this.lengths[i]) / this.avg));
        }
      }
      const max = Math.max(...lex);
      if (max <= 0) return lex;
      const qc = new Map();
      for (const t of queryTerms) qc.set(t, (qc.get(t) || 0) + 1);
      const qv = Array(this.data.search.dimensions).fill(0);
      const weights = [];
      for (const [t, c] of qc) {
        const id = this.terms.get(t);
        if (id !== undefined)
          weights.push([id, (1 + Math.log(c)) * this.data.search.idf[id]]);
      }
      const denominator =
        Math.sqrt(weights.reduce((s, [, v]) => s + v * v, 0)) || 1;
      for (const [id, v] of weights)
        for (let k = 0; k < qv.length; k++)
          qv[k] += (v / denominator) * this.data.search.basis[id][k];
      const q = norm(qv);
      this.signals = {
        lexical: lex.map((v) => v / max),
        latent: this.vectors.map((v) => Math.max(0, dot(v, q))),
        terms: unique,
      };
      return lex.map(
        (v, i) =>
          ((1 - weight) * v) / max +
          weight * Math.max(0, dot(this.vectors[i], q)),
      );
    }
    search(query, options = {}) {
      const scores = this.score(
        query,
        options.weight ?? 0.15,
        options.expand !== false,
      );
      const rows = scores
        .map((score, i) => ({ i, score, p: this.papers[i] }))
        .filter(
          (r) =>
            r.score > 0 &&
            !r.p.retracted &&
            (!options.theme || r.p.themes.includes(options.theme)) &&
            (!options.oa || r.p.oa) &&
            (!options.year || r.p.year >= options.year),
        )
        .sort((a, b) => b.score - a.score || a.i - b.i)
        .slice(0, options.mode === "learned" ? 50 : (options.limit ?? 60));
      if (options.mode === "learned" && this.data.ml_model && rows.length) {
        const model = this.data.ml_model,
          terms = this.signals.terms,
          den = Math.max(terms.length, 1);
        for (const row of rows) {
          const i = row.i,
            title = new Set(tokenize(row.p.title));
          const x = [
            this.signals.lexical[i],
            this.signals.latent[i],
            terms.filter((t) => this.counts[i].has(t)).length / den,
            terms.filter((t) => title.has(t)).length / den,
            Math.log1p(this.lengths[i]) / 10,
          ];
          row.score = x.reduce(
            (sum, v, k) => sum + (v / model.scale[k]) * model.weights[k],
            0,
          );
        }
        rows.sort((a, b) => b.score - a.score || a.i - b.i);
      }
      return rows.slice(0, options.limit ?? 60);
    }
    related(id, limit = 6) {
      const i = this.ids.get(id);
      if (i === undefined) return [];
      const p = this.papers[i],
        refs = new Set(p.references),
        out = [];
      for (let j = 0; j < this.n; j++) {
        const q = this.papers[j];
        if (i === j || q.retracted) continue;
        let kind = "similarity",
          score = Math.max(0, dot(p.vector, q.vector));
        if (refs.has(q.id)) {
          kind = "cites";
          score += 2;
        } else if (q.references.includes(p.id)) {
          kind = "cited by";
          score += 2;
        } else if (p.topics.some((t) => q.topics.some((u) => u.id === t.id))) {
          kind = "shared topic";
          score += 0.3;
        }
        if (score > 0.1) out.push({ p: q, i: j, kind, score });
      }
      return out.sort((a, b) => b.score - a.score || a.i - b.i).slice(0, limit);
    }
    trail(query, options = {}) {
      const candidates = this.search(query, { ...options, limit: 60 }),
        scores = this.score(query),
        selected = [];
      while (candidates.length && selected.length < 5) {
        let best = 0,
          value = -Infinity;
        for (let k = 0; k < candidates.length; k++) {
          const r = candidates[k];
          const redundancy = Math.max(
            0,
            ...selected.map((s) => dot(s.p.vector, r.p.vector)),
          );
          const intro =
            selected.length === 0 && r.p.type === "review" ? 0.12 : 0;
          const utility = 0.75 * scores[r.i] - 0.25 * redundancy + intro;
          if (utility > value) {
            best = k;
            value = utility;
          }
        }
        selected.push(candidates.splice(best, 1)[0]);
      }
      return selected;
    }
  }
  const api = { Engine, tokenize, expand, dot, norm };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.RH = api;
})(typeof window !== "undefined" ? window : globalThis);
