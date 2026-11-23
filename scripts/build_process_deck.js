/* Three slides in the house format of decks/Sample_Arch.pptx:
   why we are doing this, the AML investigation as it runs today, and the same
   process with the agent.

   Every number here is one the repo can produce: the corpus counts come from
   the loaded extract, the money comes from the contract recorded in
   artifacts/improve.json. Nothing about accuracy appears on these slides.

   Rebuild with:
     NODE_PATH="$PWD/node_modules" node scripts/build_process_deck.js out.pptx
*/
const pptxgen = require("pptxgenjs");

const PURPLE = "A100FF", DEEP = "460073", PALE = "F3EAFE";
const INK = "1A1A1A", GREY = "555A5F", LINE = "C9CFD6", MUTE = "A8ADB2",
      SILVER = "BDC1C6", AMBER = "FF9900", WHITE = "FFFFFF";
const F = "Graphik";

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";  // 13.333 x 7.5in, as decks/Sample_Arch.pptx

const BOX_W = 2.32, GAP = 0.13, LEFT = 0.6, ROW_Y = 2.95, BOX_H = 1.62;
const UNDER_Y = 5.2, UW = (12.35 - 3 * 0.14) / 4;

function frame(s, title, sub, band) {
  s.background = { color: WHITE };
  s.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.22, h: 7.5, fill: { color: PURPLE } });
  s.addText(title, {
    x: 0.5, y: 0.32, w: 11.9, h: 0.46,
    fontFace: F, fontSize: 24, bold: true, color: INK,
  });
  s.addText(sub, {
    x: 0.52, y: 0.98, w: 12.3, h: 0.3, fontFace: F, fontSize: 11.5, color: DEEP,
  });
  s.addShape(pptx.ShapeType.rect, {
    x: 0.5, y: 1.42, w: 2.2, h: 0.04, fill: { color: PURPLE } });
  s.addShape(pptx.ShapeType.rect, {
    x: 0.5, y: 1.66, w: 12.35, h: 0.5, fill: { color: PALE } });
  s.addText(band, {
    x: 0.72, y: 1.66, w: 11.9, h: 0.5, fontFace: F, fontSize: 10.5,
    color: DEEP, valign: "middle",
  });
}

/* A small pill: the actor under a step, or a status on top of one. */
function pill(s, text, x, y, w, fill, ink) {
  s.addText(text, {
    shape: pptx.ShapeType.roundRect, rectRadius: 0.1,
    x, y, w, h: 0.24, fill: { color: fill }, line: { color: fill, width: 1 },
    fontFace: F, fontSize: 8, bold: true, color: ink, align: "center",
    valign: "middle", margin: 0,
  });
}

/* The five steps, left to right, each labelled with who does it. */
function chain(s, steps) {
  steps.forEach((st, i) => {
    const x = LEFT + i * (BOX_W + GAP);
    if (i > 0) {
      s.addShape(pptx.ShapeType.line, {
        x: x - GAP, y: ROW_Y + BOX_H / 2, w: GAP, h: 0,
        line: { color: AMBER, width: 2 },
      });
    }
    s.addText(
      [
        { text: String(i + 1).padStart(2, "0") + "   ",
          options: { fontSize: 11.5, bold: true, color: st.ink === INK ? DEEP : "D8B4FF" } },
        { text: st.title, options: { fontSize: 11.5, bold: true, breakLine: true } },
        { text: st.body, options: { fontSize: 9, breakLine: true } },
      ],
      {
        shape: pptx.ShapeType.roundRect, rectRadius: 0.06,
        x, y: ROW_Y, w: BOX_W, h: BOX_H,
        fill: { color: st.fill }, line: { color: st.fill, width: 1 },
        color: st.ink || WHITE, fontFace: F, align: "left", valign: "top",
        margin: 10, lineSpacingMultiple: 1.05,
      });
    if (st.tag) {
      pill(s, st.tag, x + BOX_W - 1.0, ROW_Y - 0.3, 1.0,
           st.tag === "NEW" ? PURPLE : PALE, st.tag === "NEW" ? WHITE : DEEP);
    }
    pill(s, st.who, x + (BOX_W - 1.5) / 2, ROW_Y + BOX_H + 0.1, 1.5,
         st.whoFill, st.whoInk);
  });
}

/* The four small boxes under the chain. */
function supports(s, items) {
  items.forEach(([h, b], i) => {
    s.addText(
      [{ text: h, options: { fontSize: 9.5, bold: true, color: DEEP, breakLine: true } },
       { text: b, options: { fontSize: 8.5, color: GREY } }],
      { x: 0.5 + i * (UW + 0.14), y: UNDER_Y, w: UW, h: 0.86,
        shape: pptx.ShapeType.roundRect, rectRadius: 0.06,
        fill: { color: PALE }, line: { color: LINE, width: 1 },
        fontFace: F, align: "left", valign: "top", margin: 8, lineSpacingMultiple: 1.05 });
  });
}

function note(s, text) {
  s.addText(text, {
    x: 0.5, y: 6.52, w: 12.35, h: 0.5, fontFace: F, fontSize: 9.5, color: GREY,
  });
}

const SYSTEM = { whoFill: "EDEFF2", whoInk: GREY };
const PERSON = { whoFill: DEEP, whoInk: WHITE };
const AGENT = { whoFill: PURPLE, whoInk: WHITE };

/* ------------------------------------------- slide 1: what and why */
const s0 = pptx.addSlide();
frame(s0,
  "Anti-money laundering alert triage",
  "What we set out to do, what stood in the way, and what we built.",
  "Built on a real transaction-monitoring extract: 35 production alerts, 35 more written to cover what the extract has none of, 60 parties, 6 Actimize scenarios");

const COL_W = 6.05;
[
  ["The problem", DEEP, [
    ["Detection is automated. Nothing after it is.",
     "Actimize raises the alert. A person then reads the party, the KYC file, the transactions and any earlier alerts - one system at a time."],
    ["The work is the reading, not the deciding.",
     "By the time an analyst has gathered the evidence, the call itself is usually obvious. Most alerts end in a close."],
    ["It does not scale with the queue.",
     "GBP 17.00 of analyst time per alert, and the queue only moves as fast as the people on it."],
  ]],
  ["What we built", PURPLE, [
    ["An agent does the reading.",
     "It is handed the alert and the detection rule that fired - retrieved from the Actimize Solution Guide, cited to its page - and it recommends."],
    ["It has to show its working.",
     "An answer that cannot point at the transactions behind it is not trusted, and the same alert goes to a stronger model."],
    ["A person still decides.",
     "Every escalation is reviewed. The agent cannot close an alert, write to a party record, or file a report."],
  ]],
].forEach(([heading, accent, points], col) => {
  const x = 0.5 + col * (COL_W + 0.25);
  s0.addShape(pptx.ShapeType.rect, { x, y: 2.5, w: 1.6, h: 0.04, fill: { color: accent } });
  s0.addText(heading, { x, y: 2.62, w: COL_W, h: 0.3,
    fontFace: F, fontSize: 14, bold: true, color: accent });
  points.forEach(([h, b], i) => {
    s0.addText(
      [{ text: h, options: { fontSize: 11, bold: true, color: INK, breakLine: true } },
       { text: b, options: { fontSize: 9, color: GREY } }],
      { x, y: 3.06 + i * 0.94, w: COL_W, h: 0.86, fontFace: F,
        align: "left", valign: "top", margin: 0, lineSpacingMultiple: 1.05 });
  });
});

const KPI = [
  ["GBP 17.00", "what one alert costs today"],
  ["GBP 12.00", "the target, set before the build"],
  ["90%", "recall floor, the binding constraint"],
  ["0", "reports the agent may file"],
];
KPI.forEach(([v, l], i) => {
  s0.addText(
    [{ text: v, options: { fontSize: 18, bold: true, color: DEEP, breakLine: true } },
     { text: l, options: { fontSize: 8.5, color: GREY } }],
    { x: 0.5 + i * (UW + 0.14), y: 5.88, w: UW, h: 0.98,
      shape: pptx.ShapeType.roundRect, rectRadius: 0.06,
      fill: { color: PALE }, line: { color: LINE, width: 1 },
      fontFace: F, align: "left", valign: "top", margin: 9, lineSpacingMultiple: 0.95 });
});
s0.addText("Signed off by the Head of Financial Crime Technology before a line was written.",
  { x: 0.5, y: 6.98, w: 12.35, h: 0.3, fontFace: F, fontSize: 9, color: GREY });

/* ------------------------------------------------ slide 2: as it runs today */
const s1 = pptx.addSlide();
frame(s1,
  "How an AML alert is investigated today",
  "One alert, one analyst, five steps - and only the first of them is automated.",
  "Actimize SAM raises the alert   |   an analyst gathers the evidence, decides and writes the narrative   |   the MLRO files");

chain(s1, [
  { title: "Detection", body: "Actimize SAM runs the scenario over the night's transactions and raises an alert.",
    fill: DEEP, who: "system", ...SYSTEM },
  { title: "Alert queue", body: "Alerts are assigned to an L1 analyst, oldest first.",
    fill: SILVER, ink: INK, who: "system", ...SYSTEM },
  { title: "Triage", body: "The analyst opens the alert and reads the party, the KYC file, the transactions and any prior alerts.",
    fill: PURPLE, who: "analyst", ...PERSON },
  { title: "Disposition", body: "Close it with a written narrative, or escalate it to a case.",
    fill: PURPLE, who: "analyst", ...PERSON },
  { title: "Case and filing", body: "L2 investigates the case; the MLRO decides whether a SAR is filed.",
    fill: AMBER, who: "L2 and MLRO", ...PERSON },
]);

s1.addShape(pptx.ShapeType.rect, {
  x: LEFT + 2 * (BOX_W + GAP) - 0.14, y: ROW_Y - 0.56,
  w: 3 * BOX_W + 2 * GAP + 0.28, h: BOX_H + 1.0,
  fill: { type: "none" }, line: { color: MUTE, width: 1, dashType: "dash" } });
s1.addText("Manual, one alert at a time", {
  x: LEFT + 2 * (BOX_W + GAP), y: ROW_Y - 0.52, w: 3.2, h: 0.3,
  fontFace: F, fontSize: 9.5, color: GREY, bold: true });

supports(s1, [
  ["Evidence gathering", "The alert, the party, the KYC file and any prior alerts, read one system at a time."],
  ["Written by hand", "Every disposition carries a narrative the analyst types out."],
  ["Varies by reader", "Two analysts can read the same alert and write it up differently."],
  ["Throughput", "The queue moves at the speed of the people on it."],
]);

note(s1,
  "Most alerts close with no further action, and each one still costs the analyst time: "
  + "GBP 17.00 per alert on the manual baseline this demo is measured against. "
  + "The slow part is not the decision - it is reading the evidence.");

/* --------------------------------------------- slide 3: the same with an agent */
const s2 = pptx.addSlide();
frame(s2,
  "The same process with the agent",
  "Three steps change. The detection engine and the filing decision do not move at all.",
  "The agent reads and recommends   |   a person reviews every escalation   |   nothing is filed by the agent");

chain(s2, [
  { title: "Detection", body: "Actimize SAM raises the alert exactly as it does today.",
    fill: DEEP, who: "system", tag: "UNCHANGED", ...SYSTEM },
  { title: "Assemble", body: "The alert, its transactions, and the detection rule itself - retrieved from the Solution Guide by scenario code.",
    fill: SILVER, ink: INK, who: "system", tag: "NEW", ...SYSTEM },
  { title: "AML Alert Investigator", body: "Reads the alert against the rule it fired. The cheap model answers first; one that cannot cite its evidence goes to the stronger model.",
    fill: PURPLE, who: "agent", tag: "NEW", ...AGENT },
  { title: "Recommendation", body: "Escalate, close, or insufficient information - with the transactions it relied on and a written narrative.",
    fill: PURPLE, who: "agent", tag: "NEW", ...AGENT },
  { title: "Case and filing", body: "The analyst confirms every escalation; the MLRO decides whether a SAR is filed.",
    fill: AMBER, who: "analyst and MLRO", tag: "UNCHANGED", ...PERSON },
]);

supports(s2, [
  ["Rule catalogue", "28 detection rules read out of the Actimize Solution Guide, each cited to its page."],
  ["Untrusted-data envelope", "Text written by an outsider is labelled as evidence, never as an instruction."],
  ["Evidence check", "An answer that cites no transaction, or one that is not in the alert, is not trusted."],
  ["Cost ledger", "Every call priced, per alert, as it happens."],
]);

note(s2,
  "The agent recommends; it has no authority to close an alert, write to a party record or file a report. "
  + "Nobody has to read a close, so the measure that matters is recall on the alerts that should escalate.");

pptx.writeFile({ fileName: process.argv[2] }).then((f) => console.log("wrote", f));
