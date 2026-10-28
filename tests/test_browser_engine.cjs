// Browser-independent tests of the exact search engine shipped to Figma.
const assert = require("node:assert/strict"),
  fs = require("node:fs"),
  vm = require("node:vm"),
  path = require("node:path");
const root = path.resolve(__dirname, ".."),
  context = { window: {} };
vm.runInNewContext(
  fs.readFileSync(path.join(root, "app/data.js"), "utf8"),
  context,
);
const { Engine, expand } = require("../app/search.js"),
  data = context.window.RH_DATA,
  e = new Engine(data);
let count = 0;
function test(name, f) {
  f();
  count++;
  console.log("PASS " + name);
}
test("unknown queries return no matches", () =>
  assert.equal(e.search("zzzzzzquuxzz").length, 0));
test("earworm questions expand transparently", () =>
  assert.match(
    expand("Why do songs get stuck in my head?"),
    /involuntary musical imagery/,
  ));
test("retracted papers never enter discovery", () =>
  assert.ok(
    e
      .search("retracted music emotion", { limit: 2000 })
      .every((r) => !r.p.retracted),
  ));
test("open access filter is strict", () =>
  assert.ok(e.search("music memory", { oa: true }).every((r) => r.p.oa)));
test("year filter is strict", () =>
  assert.ok(e.search("music", { year: 2020 }).every((r) => r.p.year >= 2020)));
test("theme filter is strict", () =>
  assert.ok(
    e
      .search("memory", { theme: "dreams" })
      .every((r) => r.p.themes.includes("dreams")),
  ));
test("trails contain unique non-retracted papers", () => {
  const trail = e.trail("music memory");
  assert.equal(trail.length, 5);
  assert.equal(new Set(trail.map((r) => r.p.id)).size, 5);
  assert.ok(trail.every((r) => !r.p.retracted));
});
test("citation explanations preserve direction", () => {
  for (const r of e.related(data.papers[0].id, 50)) {
    if (r.kind === "cites")
      assert.ok(data.papers[0].references.includes(r.p.id));
    if (r.kind === "cited by")
      assert.ok(r.p.references.includes(data.papers[0].id));
  }
});
const parityPath = path.join(root, "outputs/search_parity.json");
if (fs.existsSync(parityPath)) {
  const cases = JSON.parse(fs.readFileSync(parityPath));
  for (const c of cases)
    if (c.ml_ids)
      test("Python/browser ML parity: " + c.query, () => {
        const results = e.search(c.query, {
          mode: "learned",
          expand: false,
          limit: 10,
        });
        assert.deepEqual(
          results.map((r) => r.p.id),
          c.ml_ids,
        );
        for (let i = 0; i < 10; i++)
          assert.ok(Math.abs(results[i].score - c.ml_scores[i]) < 0.001);
      });
  for (const c of cases)
    test("Python/browser parity: " + c.query, () => {
      const results = e.search(c.query, { expand: false, limit: 10 });
      assert.deepEqual(
        results.map((r) => r.p.id),
        c.ids,
      );
      for (let i = 0; i < 10; i++)
        assert.ok(Math.abs(results[i].score - c.scores[i]) < 0.0003);
    });
}
fs.writeFileSync(
  path.join(root, "outputs/js_test_report.json"),
  JSON.stringify(
    {
      tests: count,
      passed: count,
      failed: 0,
      scope:
        "Exact shipped browser search engine; interaction checks are recorded separately.",
    },
    null,
    2,
  ),
);
console.log(`${count} tests passed`);
