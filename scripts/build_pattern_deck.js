/* Four slides in the house format of decks/Sample_Arch.pptx:

     1. the user flow - the integrated asset used as a standard pattern
     2. the console wireframe, with all four pillars in one frame
     3. the AML data schema and its mapping to the source extract
     4. the spec the AML build was run from

   Slides 1 and 2 are generic: they describe the pattern, not this use case.
   Slides 3 and 4 are the AML instance of it. Every field name on slide 3 is
   read from aml/corpus/model.py and aml/corpus/loader.py; every figure on
   slide 4 is from PRD.md.

   Rebuild with:
     NODE_PATH="$PWD/node_modules" node scripts/build_pattern_deck.js out.pptx
*/
const pptxgen = require("pptxgenjs");

const PURPLE = "A100FF", DEEP = "460073", PALE = "F3EAFE";
const INK = "1A1A1A", GREY = "555A5F", LINE = "C9CFD6", MUTE = "A8ADB2",
      SILVER = "BDC1C6", AMBER = "FF9900", WHITE = "FFFFFF", MIST = "EDEFF2";
const F = "Graphik";

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";  // 13.333 x 7.5in, as decks/Sample_Arch.pptx

const L = 0.5, W = 12.35;

function frame(s, title, sub, band) {
  s.background = { color: WHITE };
  s.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.22, h: 7.5, fill: { color: PURPLE } });
  s.addText(title, { x: L, y: 0.32, w: 11.9, h: 0.46,
    fontFace: F, fontSize: 24, bold: true, color: INK });
  s.addText(sub, { x: 0.52, y: 0.98, w: 12.3, h: 0.3,
    fontFace: F, fontSize: 11.5, color: DEEP });
  s.addShape(pptx.ShapeType.rect, { x: L, y: 1.42, w: 2.2, h: 0.04, fill: { color: PURPLE } });
  s.addShape(pptx.ShapeType.rect, { x: L, y: 1.66, w: W, h: 0.5, fill: { color: PALE } });
  s.addText(band, { x: 0.72, y: 1.66, w: 11.9, h: 0.5,
    fontFace: F, fontSize: 10.5, color: DEEP, valign: "middle" });
}

function note(s, text, y) {
  s.addText(text, { x: L, y: y || 6.95, w: W, h: 0.34,
    fontFace: F, fontSize: 9, color: GREY });
}

/* A labelled chip. Used for pillars, phases and schema keys. */
function chip(s, text, x, y, w, h, fill, ink, size) {
  s.addText(text, {
    shape: pptx.ShapeType.roundRect, rectRadius: 0.08,
    x, y, w, h, fill: { color: fill }, line: { color: fill, width: 1 },
    fontFace: F, fontSize: size || 8.5, bold: true, color: ink,
    align: "center", valign: "middle", margin: 0,
  });
}

/* A card with a heading and a body, in the house rounded-rect style. */
function card(s, x, y, w, h, heading, body, opts) {
  const o = opts || {};
  const runs = [{ text: heading, options: {
    fontSize: o.headSize || 11, bold: true,
    color: o.headInk || DEEP, breakLine: true } }];
  if (body) {
    runs.push({ text: body, options: { fontSize: o.bodySize || 8.5, color: o.bodyInk || GREY } });
  }
  s.addText(runs, {
    x, y, w, h, shape: pptx.ShapeType.roundRect, rectRadius: 0.06,
    fill: { color: o.fill || PALE }, line: { color: o.line || LINE, width: 1 },
    fontFace: F, align: "left", valign: "top", margin: o.margin || 9,
    lineSpacingMultiple: 1.05,
  });
}

/* ================================================ 1. the standard pattern */

const s1 = pptx.addSlide();
frame(s1,
  "One pattern for any product: the integrated asset in use",
  "Twelve stages, five phases, four pillars. What changes between products is the use case - not the flow.",
  "ONE LOOP, NOT FOUR PROGRAMMES - EVERY PASS INHERITS TESTED CAPABILITY INSTEAD OF RESTARTING");

const PHASES = [
  ["PLAN", [["01", "Use-case triage"], ["02", "Requirements & spec"]]],
  ["DESIGN", [["03", "Architecture"], ["04", "Agent graph design"], ["05", "Context & skills"]]],
  ["BUILD", [["06", "Development"], ["07", "Code review"], ["08", "Remediation"]]],
  ["TEST", [["09", "Unit & component"], ["10", "Functional test"]]],
  ["DEPLOY", [["11", "Release & promotion"], ["12", "Observability & eval"]]],
];
const PW = (W - 4 * 0.13) / 5, PY = 2.46, PH = 1.84;

s1.addText("PLANNER + ORCHESTRATOR   ·   turns the spec into a plan, dispatches specialist loops, joins shared state and re-plans",
  { x: L, y: 2.26, w: W, h: 0.2, fontFace: F, fontSize: 8.5, bold: true, color: MUTE });

PHASES.forEach(([name, stages], i) => {
  const x = L + i * (PW + 0.13);
  if (i > 0) {
    s1.addShape(pptx.ShapeType.line, { x: x - 0.13, y: PY + PH / 2, w: 0.13, h: 0,
      line: { color: AMBER, width: 2 } });
  }
  s1.addShape(pptx.ShapeType.roundRect, { x, y: PY, w: PW, h: PH, rectRadius: 0.06,
    fill: { color: WHITE }, line: { color: LINE, width: 1 } });
  chip(s1, name, x, PY, PW, 0.34, DEEP, WHITE, 10);
  // Phases carry two or three stages; centre the shorter lists in the card.
  const top = PY + 0.44 + (PH - 0.46 - stages.length * 0.44) / 2;
  stages.forEach(([n, label], j) => {
    s1.addText(
      [{ text: n + "  ", options: { fontSize: 9, bold: true, color: PURPLE } },
       { text: label, options: { fontSize: 9, color: INK } }],
      { x: x + 0.12, y: top + j * 0.44, w: PW - 0.24, h: 0.4,
        fontFace: F, align: "left", valign: "middle", margin: 0 });
  });
});

s1.addText("↑  Human in the lead after every phase - the gate is a person, not a confidence score",
  { x: L, y: PY + PH + 0.08, w: W, h: 0.24, fontFace: F, fontSize: 9,
    bold: true, color: DEEP });

const PILLARS = [
  ["AI builds AI", PURPLE, "Specs · Context · Skills · Loops · Graphs · Evaluation",
   "Turns the spec into working, tested agents. Every failure becomes a new test or a sharper spec."],
  ["AI runs AI", DEEP, "Routing · Reliability · Observability · FinOps",
   "Cheapest model above the quality floor, fallback on failure, and every call on one ledger."],
  ["AI secures AI", AMBER, "Threat modelling · Runtime defense · Pen-test swarm",
   "Threat model written in the spec, defended live, and probed again on every change."],
  ["AI improves AI", SILVER, "Harness · Tokenomics · Failure mining · Value engineering",
   "Clusters the failures, proposes with evidence, and puts every change to a gate that can refuse."],
];
const LW = (W - 3 * 0.14) / 4, LY = 4.76;
PILLARS.forEach(([name, accent, disciplines, body], i) => {
  const x = L + i * (LW + 0.14);
  s1.addShape(pptx.ShapeType.roundRect, { x, y: LY, w: LW, h: 1.08, rectRadius: 0.06,
    fill: { color: WHITE }, line: { color: LINE, width: 1 } });
  // Amber and silver are light: they take ink, not white.
  chip(s1, name, x, LY, LW, 0.28, accent,
       accent === SILVER || accent === AMBER ? INK : WHITE, 9.5);
  s1.addText(
    [{ text: disciplines, options: { fontSize: 7.5, bold: true, color: DEEP, breakLine: true } },
     { text: body, options: { fontSize: 8, color: GREY } }],
    { x: x + 0.1, y: LY + 0.32, w: LW - 0.2, h: 0.72, fontFace: F,
      align: "left", valign: "top", margin: 0, lineSpacingMultiple: 1.0 });
});

s1.addShape(pptx.ShapeType.roundRect, { x: L, y: 6.04, w: W, h: 0.74, rectRadius: 0.06,
  fill: { color: PALE }, line: { color: PALE, width: 1 } });
s1.addText(
  [{ text: "WHAT THE NEXT PRODUCT INHERITS   ", options: { fontSize: 9, bold: true, color: DEEP } },
   { text: "acceptance-criteria patterns  ·  reusable skills  ·  agent-graph and gate patterns  "
         + "·  the guardrail and probe catalogue  ·  eval families  ·  the value-contract template  "
         + "·  the SR 11-7 model-risk template", options: { fontSize: 9, color: INK } }],
  { x: 0.72, y: 6.04, w: W - 0.44, h: 0.74, fontFace: F, align: "left",
    valign: "middle", margin: 0, lineSpacingMultiple: 1.05 });

note(s1, "The asset is the library, not the product. The AML investigator is the first thing built on it; the thirteen reusable skills and eighteen pattern assets it left behind are what the next build starts from.");

/* ===================================================== 2. the wireframe */

const s2 = pptx.addSlide();
frame(s2,
  "One console, four pillars: how it works together",
  "A generic wireframe. Each pillar is a page, each discipline a panel, and each panel does the real thing rather than describing it.",
  "THE SHELL DOES NOT CHANGE BETWEEN PRODUCTS - SWAP THE USE CASE AND THE NAVIGATION, PANELS AND EVIDENCE STRIP STAY AS THEY ARE");

const BX = L, BY = 2.46, BW = 8.5, BH = 4.3;

/* browser chrome */
s2.addShape(pptx.ShapeType.roundRect, { x: BX, y: BY, w: BW, h: BH, rectRadius: 0.03,
  fill: { color: WHITE }, line: { color: MUTE, width: 1 } });
s2.addShape(pptx.ShapeType.rect, { x: BX, y: BY, w: BW, h: 0.34, fill: { color: MIST } });
[0.18, 0.34, 0.50].forEach((dx) => {
  s2.addShape(pptx.ShapeType.ellipse, { x: BX + dx - 0.045, y: BY + 0.125, w: 0.09, h: 0.09,
    fill: { color: SILVER } });
});
s2.addText("ai-engineering-factory.ai / builds", {
  shape: pptx.ShapeType.roundRect, rectRadius: 0.08,
  x: BX + 0.68, y: BY + 0.06, w: 3.3, h: 0.22, fill: { color: WHITE },
  line: { color: LINE, width: 1 }, fontFace: F, fontSize: 7.5, color: GREY,
  align: "left", valign: "middle", margin: 6 });

/* left rail */
const RW = 2.05, RY = BY + 0.34, RH = BH - 0.34;
s2.addShape(pptx.ShapeType.rect, { x: BX, y: RY, w: RW, h: RH, fill: { color: DEEP } });
s2.addText("AI ENGINEERING\nFACTORY", { x: BX + 0.16, y: RY + 0.16, w: RW - 0.3, h: 0.44,
  fontFace: F, fontSize: 8.5, bold: true, color: WHITE, charSpacing: 1,
  align: "left", valign: "top", margin: 0, lineSpacingMultiple: 1.05 });
[["AI builds AI", true], ["AI runs AI", false], ["AI secures AI", false],
 ["AI improves AI", false]].forEach(([label, active], i) => {
  const y = RY + 0.78 + i * 0.42;
  if (active) {
    s2.addShape(pptx.ShapeType.roundRect, { x: BX + 0.1, y, w: RW - 0.2, h: 0.34,
      rectRadius: 0.06, fill: { color: PURPLE }, line: { color: PURPLE, width: 1 } });
  }
  s2.addText(label, { x: BX + 0.24, y, w: RW - 0.34, h: 0.34, fontFace: F,
    fontSize: 9, bold: active, color: active ? WHITE : "C9B4E8",
    align: "left", valign: "middle", margin: 0 });
});
s2.addText("every panel is backed by\nsomething real in the repo", {
  x: BX + 0.16, y: RY + RH - 0.62, w: RW - 0.3, h: 0.46, fontFace: F,
  fontSize: 7, italic: true, color: "C9B4E8", align: "left", valign: "bottom",
  margin: 0, lineSpacingMultiple: 1.05 });

/* main area */
const MX = BX + RW + 0.2, MW = BW - RW - 0.4;
s2.addText("AI builds AI  ›  disciplines", { x: MX, y: RY + 0.16, w: MW, h: 0.2,
  fontFace: F, fontSize: 8, color: MUTE, margin: 0 });
s2.addText("Turning AI development into a repeatable factory", {
  x: MX, y: RY + 0.38, w: MW, h: 0.26, fontFace: F, fontSize: 12.5, bold: true,
  color: INK, margin: 0 });

const DISCIPLINES = ["Specs", "Context", "Skills", "Loops", "Graphs", "Evaluation"];
const DW = (MW - 2 * 0.12) / 3;
DISCIPLINES.forEach((d, i) => {
  const x = MX + (i % 3) * (DW + 0.12);
  const y = RY + 0.74 + Math.floor(i / 3) * 0.56;
  s2.addShape(pptx.ShapeType.roundRect, { x, y, w: DW, h: 0.48, rectRadius: 0.06,
    fill: { color: i === 3 ? PALE : WHITE }, line: { color: i === 3 ? PURPLE : LINE, width: 1 } });
  s2.addText(
    [{ text: String(i + 1).padStart(2, "0") + "  ", options: { fontSize: 7.5, bold: true, color: PURPLE } },
     { text: d, options: { fontSize: 9, bold: true, color: INK } }],
    { x: x + 0.1, y, w: DW - 0.2, h: 0.48, fontFace: F, align: "left",
      valign: "middle", margin: 0 });
});

const PNY = RY + 1.94;
s2.addShape(pptx.ShapeType.roundRect, { x: MX, y: PNY, w: MW, h: 1.08, rectRadius: 0.06,
  fill: { color: WHITE }, line: { color: PURPLE, width: 1 } });
s2.addText("PANEL  ·  04 Loops", { x: MX + 0.12, y: PNY + 0.08, w: MW - 0.24, h: 0.2,
  fontFace: F, fontSize: 7.5, bold: true, color: PURPLE, margin: 0 });
s2.addText("Goal  →  Act  →  Verify  →  Iterate", { x: MX + 0.12, y: PNY + 0.3, w: 2.8, h: 0.24,
  fontFace: F, fontSize: 9.5, bold: true, color: INK, margin: 0 });
chip(s2, "run it for real", MX + MW - 1.5, PNY + 0.28, 1.38, 0.28, PURPLE, WHITE, 8);
s2.addText("attempt 1  ·  19 passed, 1 failed        attempt 2  ·  20 passed, 0 failed", {
  x: MX + 0.12, y: PNY + 0.64, w: MW - 0.24, h: 0.22, fontFace: F, fontSize: 8,
  color: GREY, margin: 0 });

const EVY = PNY + 1.2;
s2.addShape(pptx.ShapeType.rect, { x: MX, y: EVY, w: MW, h: 0.4, fill: { color: MIST } });
s2.addText("EVIDENCE   model · tokens · cost · latency · citations checked · pass or fail", {
  x: MX + 0.12, y: EVY, w: MW - 0.24, h: 0.4, fontFace: F, fontSize: 7.5,
  bold: true, color: GREY, valign: "middle", margin: 0 });

/* annotations */
const AX = BX + BW + 0.35, AW = W - BW - 0.35;
[
  ["01", "Pillar rail", "Four pillars, always on screen. The product never leaves the frame, so nobody loses the thread."],
  ["02", "Discipline grid", "Each pillar carries its own disciplines. One panel per discipline, numbered in the order you would present them."],
  ["03", "Live panel", "A button that makes a real call against the real system. Not a screenshot, not a recording."],
  ["04", "Evidence strip", "Every panel ends the same way: what it cost, what it cited, and whether it was right."],
  ["05", "One shell, four pillars", "Builds, Runs, Secures and Improves render through the same shell, so the audience learns the layout once."],
].forEach(([n, head, body], i) => {
  const y = BY + i * 0.86;
  s2.addText(n, { x: AX, y, w: 0.34, h: 0.24, fontFace: F, fontSize: 10,
    bold: true, color: PURPLE, margin: 0 });
  s2.addText(
    [{ text: head, options: { fontSize: 10, bold: true, color: INK, breakLine: true } },
     { text: body, options: { fontSize: 8.5, color: GREY } }],
    { x: AX + 0.38, y, w: AW - 0.38, h: 0.8, fontFace: F, align: "left",
      valign: "top", margin: 0, lineSpacingMultiple: 1.05 });
});

note(s2, "The wireframe is the delivery pattern as much as the demonstration: a pillar page, a discipline panel, a live call and the evidence it returns - for any product built on the asset.");

/* ================================================ 3. the AML data schema */

const s3 = pptx.addSlide();
frame(s3,
  "AML alert investigator: data schema and source mapping",
  "Four entities, loaded once from the supplied extract, joined to the Actimize rule catalogue at run time.",
  "70 ALERTS - 35 FROM THE PRODUCTION EXTRACT AND 35 SYNTHETIC CLOSES  |  1,073 TRANSACTIONS  |  60 PARTIES  |  6 SCENARIOS");

const EW = (W - 3 * 0.14) / 4, EY = 2.42, EH = 1.98;
const ENTITIES = [
  ["Alert", "1", [
    "alert_id, scenario", "description, triggered", "run_date", "label, provenance",
    "hero, rationale", "case_id, form_type"]],
  ["Party", "1", [
    "number, name, type", "dob, occupation", "annual_income", "city, state", "country"]],
  ["Account", "1", [
    "number, product", "opened, status", "currency", "registration"]],
  ["Transaction", "n", [
    "date, ref", "amount, direction", "medium, country", "reference_text"]],
];
ENTITIES.forEach(([name, card_, fields], i) => {
  const x = L + i * (EW + 0.14);
  if (i > 0) {
    s3.addShape(pptx.ShapeType.line, { x: x - 0.14, y: EY + 0.45, w: 0.14, h: 0,
      line: { color: AMBER, width: 2 } });
    s3.addText(card_, { x: x - 0.18, y: EY + 0.14, w: 0.22, h: 0.2, fontFace: F,
      fontSize: 7.5, bold: true, color: AMBER, align: "center", margin: 0 });
  }
  s3.addShape(pptx.ShapeType.roundRect, { x, y: EY, w: EW, h: EH, rectRadius: 0.06,
    fill: { color: WHITE }, line: { color: LINE, width: 1 } });
  chip(s3, name.toUpperCase(), x, EY, EW, 0.32, i === 3 ? PURPLE : DEEP, WHITE, 10);
  fields.forEach((f, j) => {
    s3.addText(f, { x: x + 0.14, y: EY + 0.44 + j * 0.25, w: EW - 0.28, h: 0.24,
      fontFace: "Consolas", fontSize: 8.5, color: INK, align: "left",
      valign: "middle", margin: 0 });
  });
});
s3.addText("reference_text is the only attacker-controlled field in the record: it is written by whoever sent the payment",
  { x: L, y: EY + EH + 0.04, w: W, h: 0.22, fontFace: F, fontSize: 8.5,
    bold: true, color: AMBER, margin: 0 });

/* The mapping is drawn as fixed-height rows rather than a pptxgenjs table:
   an auto-sized table grew past the foot of the slide. */
const COLS = [3.05, 2.25, 2.25], TW = 7.55, MAPY = 5.0, ROW_H = 0.3;
const MAP = [
  ["ALERT_ID", "alert.alert_id", "one alert per group of rows"],
  ["SCENARIO_NAME", "alert.scenario", "the join key into the rule catalogue"],
  ["PARTY_NAME, OCCUPATION_DESC,  ANNUAL_INCOME_AMOUNT",
   "party.name / .occupation / .annual_income", "the context it is judged on using"],
  ["DATE_KEY, TRANSACTION_REFERENCE_NUMBER,  CURRENCY_AMOUNT",
   "transaction.date / .ref / .amount", "refs a grounded answer may cite"],
  ["CASE_ID, FORM_TYPE_CODE", "alert.case_id / .form_type",
   "every extract row filed, so label = escalate"],
];
s3.addText("MAPPED FROM Alert_Final_table.xlsx", { x: L, y: 4.74, w: TW, h: 0.22,
  fontFace: F, fontSize: 9, bold: true, color: DEEP, margin: 0 });

function cells(y, values, size, bold, ink, fill) {
  if (fill) {
    s3.addShape(pptx.ShapeType.rect, { x: L, y, w: TW, h: ROW_H, fill: { color: fill } });
  }
  let x = L;
  values.forEach((text, i) => {
    s3.addText(text, { x: x + 0.08, y, w: COLS[i] - 0.16, h: ROW_H, fontFace: F,
      fontSize: size, bold, color: ink, align: "left", valign: "middle",
      margin: 0, lineSpacingMultiple: 0.9 });
    x += COLS[i];
  });
}

cells(MAPY, ["Extract column", "Model field", "Note"], 7.5, true, DEEP, MIST);
MAP.forEach((row, i) => {
  const y = MAPY + ROW_H + i * ROW_H;
  cells(y, row, 7, false, INK, i % 2 ? "FAFAFB" : WHITE);
  s3.addShape(pptx.ShapeType.line, { x: L, y: y + ROW_H, w: TW, h: 0,
    line: { color: LINE, width: 0.5 } });
});

const JX = L + TW + 0.25, JW = W - TW - 0.25;
card(s3, JX, 4.74, JW, 1.04,
  "Joined at run time, not written into the prompt",
  "library/aml/rules.json - 28 rule specifications lifted from the 677-page Actimize AML SAM 8.5.0 "
  + "Solution Guide. scenario → detection model → rule_id → page.",
  { headSize: 10 });
card(s3, JX, 5.9, JW, 0.9,
  "Labels the harness scores against",
  "escalate_to_case / close_no_further_action, and provenance real / synthetic. "
  + "Neither reaches the model: the rendered alert carries no label and no rationale.",
  { headSize: 10, fill: WHITE, line: PURPLE });

note(s3, "Six scenarios map onto four Actimize detection models: AML-STR structuring, AML-ECT excessive cash equivalents, AML-EBB burst in beneficiary activity, AML-MLT customer identity discovery.");

/* ========================================================= 4. the spec */

const s4 = pptx.addSlide();
frame(s4,
  "Specs: what the AML alert investigator must do",
  "The spec is the source of truth. The threat model, the code and the acceptance suite are generated from it and trace back to it.",
  "PRD.md, 6,248 CHARACTERS, WRITTEN BY HAND - THE ONLY HUMAN-AUTHORED INPUT IN THE ENTIRE BUILD");

const CW = 6.05;
s4.addShape(pptx.ShapeType.rect, { x: L, y: 2.42, w: 1.6, h: 0.04, fill: { color: PURPLE } });
s4.addText("What we want built", { x: L, y: 2.54, w: CW, h: 0.3,
  fontFace: F, fontSize: 14, bold: true, color: PURPLE });
s4.addText("An agent that takes one alert and produces a disposition with evidence, so an analyst "
  + "reviews a recommendation instead of starting from nothing.",
  { x: L, y: 2.94, w: CW, h: 0.46, fontFace: F, fontSize: 10, color: INK,
    align: "left", valign: "top", margin: 0, lineSpacingMultiple: 1.05 });

s4.addText("SIX SCENARIOS IN SCOPE", { x: L, y: 3.5, w: CW, h: 0.2,
  fontFace: F, fontSize: 8.5, bold: true, color: DEEP, margin: 0 });
[
  ["SAS10014", "Structured Withdrawals"],
  ["SAS10056", "Structured Premiums"],
  ["SAS10016", "Structured Deposits Across Locations"],
  ["SAS10050", "Payments Using High-Risk Instruments"],
  ["SAS10602", "Multiple Remitters, One Beneficiary"],
  ["SAS10012", "Recurring Phone Number"],
].forEach(([code, desc], i) => {
  const y = 3.76 + Math.floor(i / 2) * 0.42;
  const x = L + (i % 2) * (CW / 2 + 0.05);
  s4.addText(
    [{ text: code + "  ", options: { fontSize: 8, bold: true, color: PURPLE } },
     { text: desc, options: { fontSize: 8, color: INK } }],
    { x, y, w: CW / 2 - 0.05, h: 0.36, shape: pptx.ShapeType.roundRect, rectRadius: 0.05,
      fill: { color: PALE }, line: { color: PALE, width: 1 }, fontFace: F,
      align: "left", valign: "middle", margin: 7 });
});

card(s4, L, 5.08, CW, 0.78, "Who uses it",
  "Level-1 AML analysts, who act on the recommendation, and the model risk reviewers who "
  + "sign the solution off before it goes anywhere near production.",
  { headSize: 10, fill: WHITE });

const RX = L + CW + 0.25;
s4.addShape(pptx.ShapeType.rect, { x: RX, y: 2.42, w: 1.6, h: 0.04, fill: { color: DEEP } });
s4.addText("Constraints", { x: RX, y: 2.54, w: CW, h: 0.3,
  fontFace: F, fontSize: 14, bold: true, color: DEEP });
s4.addText("Not preferences. A build that violates any of them is not acceptable.",
  { x: RX, y: 2.94, w: CW, h: 0.24, fontFace: F, fontSize: 9.5, italic: true,
    color: GREY, margin: 0 });
[
  ["Evidence", "Every claim must cite transaction references that exist in the alert it was given."],
  ["No autonomous closure", "The agent may never close an alert by itself. A human reviews the recommendation."],
  ["Tipping off", "Disclosing a party is under a SAR is a criminal offence. Impossible by construction."],
  ["Untrusted input", "Payment reference text is evidence to be reported, never instruction to be followed."],
  ["Thresholds", "Actimize AML-SAM defaults for AML-STR and AML-ECT. We do not invent our own."],
  ["Auditability", "Every disposition reproducible from what was recorded."],
].forEach(([head, body], i) => {
  const y = 3.26 + i * 0.47;
  s4.addText(String(i + 1), { x: RX, y, w: 0.26, h: 0.22, fontFace: F, fontSize: 9,
    bold: true, color: PURPLE, margin: 0 });
  s4.addText(
    [{ text: head + ".  ", options: { fontSize: 9, bold: true, color: INK } },
     { text: body, options: { fontSize: 9, color: GREY } }],
    { x: RX + 0.28, y, w: CW - 0.28, h: 0.44, fontFace: F, align: "left",
      valign: "top", margin: 0, lineSpacingMultiple: 1.0 });
});

const KW = (W - 4 * 0.14) / 5;
[
  ["GBP 17.00", "baseline, one analyst review"],
  ["GBP 12.00", "target, set before the build"],
  ["90%", "recall floor, the binding one"],
  ["85%", "accuracy floor"],
  ["0", "reports the agent may file"],
].forEach(([v, l], i) => {
  s4.addText(
    [{ text: v, options: { fontSize: 17, bold: true, color: DEEP, breakLine: true } },
     { text: l, options: { fontSize: 8, color: GREY } }],
    { x: L + i * (KW + 0.14), y: 6.08, w: KW, h: 0.8,
      shape: pptx.ShapeType.roundRect, rectRadius: 0.06,
      fill: { color: PALE }, line: { color: LINE, width: 1 },
      fontFace: F, align: "left", valign: "top", margin: 8, lineSpacingMultiple: 0.95 });
});

note(s4, "Recall is the binding constraint. The regulator's question is never how much you saved, it is what you missed. Signed off by the Head of Financial Crime Technology before a line was written.");

const out = process.argv[2] || "decks/AI_for_AI_Pattern_And_Specs.pptx";
pptx.writeFile({ fileName: out }).then(() => console.log("wrote " + out));
