"use strict";

/* ---------- helpers ---------- */
const $ = (id) => document.getElementById(id);

// Builds elements with textContent only, so nothing from a resume, job post or AI reply is ever parsed as HTML.
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat(Infinity)) if (kid != null && kid !== false && kid !== "") el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  return el;
}
const nodes = (...a) => a.flat(Infinity).filter((x) => x != null && x !== false && x !== "");
const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "");
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); return true; } catch { return false; } },
  del(k) { try { localStorage.removeItem(k); } catch { /* ignore */ } },
};

function toast(msg, kind) {
  const t = h("div", { class: "toast" + (kind === "err" ? " err" : ""), role: kind === "err" ? "alert" : "status" }, msg);
  $("toasts").append(t);
  setTimeout(() => t.remove(), kind === "err" ? 6000 : 3200);
}

async function api(path, { json, form } = {}) {
  let res;
  try {
    res = await fetch(path, json ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(json) }
                                  : { method: "POST", body: form });
  } catch { throw new Error("Couldn't reach the server. Is it still running?"); }
  if (res.ok && (res.headers.get("content-type") || "").includes("application/pdf")) return res.blob();
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Something went wrong. Please try again.");
  return data;
}

// Disables a button and swaps its label while an async action runs.
function busy(btn, text, fn) {
  return async (...a) => {
    if (btn.disabled) return;
    const old = btn.textContent;
    btn.disabled = true; btn.textContent = text;
    try { return await fn(...a); } finally { btn.disabled = false; btn.textContent = old; }
  };
}
// A loading line that admits it when the AI is slow, instead of looking frozen.
function loading(text, slow) {
  const el = h("div", { class: "loading", role: "status" }, text);
  if (slow) {
    setTimeout(() => el.isConnected && (el.textContent = "Still working — the AI can take up to a minute…"), 12000);
    setTimeout(() => el.isConnected && (el.textContent = "Nearly there — Gemini is slow when it's busy…"), 45000);
  }
  return el;
}
const failure = (text) => h("p", { class: "callout err", role: "alert" }, text);

function ago(sec) {
  if (!sec) return "";
  const d = Math.floor((Date.now() / 1000 - sec) / 86400);
  return d <= 0 ? "Today" : d === 1 ? "Yesterday" : d < 30 ? `${d}d ago` : d < 365 ? `${Math.floor(d / 30)}mo ago` : "1y+ ago";
}
// Multi-line text becomes bullet points; a single line stays a paragraph.
function prose(text) {
  const lines = String(text || "").split("\n").map((l) => l.replace(/^\s*[-•*]\s*/, "").trim()).filter(Boolean);
  if (!lines.length) return null;
  return lines.length === 1 ? h("p", {}, lines[0]) : h("ul", {}, lines.map((l) => h("li", {}, l)));
}

/* ---------- state ---------- */
const BLANK = () => ({ name: "", email: "", phone: "", location: "", linkedin: "", github: "", summary: "", skills: [],
  education: [], projects: [], experience: [], certifications: [] });
const LISTS = {
  education: { title: "Education", one: "Education", fields: [["college", "College / university", "full"], ["degree", "Degree"], ["branch", "Branch / major"], ["grad_year", "Graduation year"], ["cgpa", "CGPA / %"]] },
  experience: { title: "Experience", one: "Role", fields: [["role", "Role"], ["company", "Company"], ["duration", "Dates", "full"], ["details", "What you did — one point per line", "area"]] },
  projects: { title: "Projects", one: "Project", fields: [["title", "Title"], ["tech", "Built with"], ["link", "Link", "full"], ["description", "What it does and what changed because of it — one point per line", "area"]] },
  certifications: { title: "Certifications", one: "Certification", fields: [["name", "Name", "full"], ["organisation", "Issued by"], ["completed", "Completed"]] },
};
const TOP = [["name", "Full name"], ["email", "Email"], ["phone", "Phone"], ["location", "City"], ["linkedin", "LinkedIn"], ["github", "GitHub / portfolio"]];
const SAMPLE = {
  name: "Priya Sharma", email: "priya.sharma@example.com", phone: "+91 98765 43210", location: "Pune, Maharashtra",
  linkedin: "linkedin.com/in/priya-sharma", github: "github.com/priyasharma",
  summary: "Final-year Computer Engineering student who builds full-stack web apps. Comfortable across Python, React and SQL, with a summer internship shipping features used by 2,000+ people.",
  skills: ["Python", "JavaScript", "React", "Flask", "SQL", "MySQL", "Git", "HTML", "CSS", "REST APIs", "Data Structures"],
  education: [{ college: "Savitribai Phule Pune University", degree: "B.E.", branch: "Computer Engineering", grad_year: "2026", cgpa: "8.6" }],
  experience: [{ company: "Finlytics Pvt Ltd", role: "Software Engineering Intern", duration: "May 2025 – Jul 2025",
    details: "Built 6 REST API endpoints in Flask for the expense dashboard\nCut report load time from 4s to 1.2s with SQL indexes and caching\nWrote unit tests that raised coverage from 48% to 75%" }],
  projects: [
    { title: "CampusCart — student marketplace", tech: "React, Flask, MySQL", link: "github.com/priyasharma/campuscart",
      description: "Marketplace where students buy and sell used books\nLogin, search, chat and image upload\n300+ listings in the first month" },
    { title: "Placement Prep Tracker", tech: "Python, Pandas, Chart.js", link: "",
      description: "Tracks coding practice across platforms and charts weekly progress for 40 classmates." }],
  certifications: [{ name: "Python for Data Science", organisation: "NPTEL", completed: "2024" }],
};

let resume = BLANK();
let template = "modern";
let status = { ai: false, database: false, jobs: {} };
let careersStale = true;

try {
  const saved = JSON.parse(store.get("careerforge.resume") || "null");
  if (saved && typeof saved === "object") for (const k of Object.keys(resume)) if (Array.isArray(resume[k]) === Array.isArray(saved[k])) resume[k] = saved[k] ?? resume[k];
  if (["modern", "classic", "minimal"].includes(store.get("careerforge.template"))) template = store.get("careerforge.template");
} catch { /* start blank */ }

const hasContent = () => JSON.stringify(resume) !== JSON.stringify(BLANK());

/* ---------- tabs ---------- */
function showTab(name) {
  if (!document.getElementById(name)?.classList.contains("panel")) name = "builder";
  document.querySelectorAll("#tabs button").forEach((b) => {
    b.classList.toggle("on", b.dataset.tab === name);
    if (b.dataset.tab === name) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
  });
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("on", p.id === name));
  if (name === "careers") loadCareers();
  history.replaceState(null, "", "#/" + name);
  window.scrollTo({ top: 0 });
}
$("tabs").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) showTab(b.dataset.tab); });
document.querySelector(".wordmark").addEventListener("click", (e) => { e.preventDefault(); showTab("builder"); });

/* ---------- builder form ---------- */
function field(label, value, onInput, kind) {
  const input = kind === "area" ? h("textarea", { rows: 4 }) : h("input", { type: kind === "email" ? "email" : "text" });
  input.value = value || "";
  input.addEventListener("input", () => onInput(input.value));
  return h("label", { class: "field" + (kind === "full" || kind === "area" ? " full" : "") }, h("span", { class: "label" }, label), input);
}

let blockNo = 0;
function block(title, open, ...body) {
  const count = h("span", { class: "count" });
  const d = h("details", { class: "block", open },
    h("summary", {}, h("span", { class: "n" }, String(++blockNo).padStart(2, "0")), h("span", { class: "t" }, title), count),
    h("div", { class: "block-body" }, body));
  d.setCount = (n) => { count.textContent = n ? `${n} added` : ""; };
  return d;
}

function skillsInput() {
  const box = h("div", { class: "tokens" });
  const input = h("input", { type: "text", placeholder: "Type a skill, press Enter", "aria-label": "Add a skill" });
  const add = (text) => {
    let added = false;
    for (const s of text.split(",").map((x) => x.trim()).filter(Boolean)) {
      if (!resume.skills.some((x) => x.toLowerCase() === s.toLowerCase())) { resume.skills.push(s.slice(0, 80)); added = true; }
    }
    input.value = "";
    if (added) { render(); changed(); }
  };
  const render = () => {
    box.replaceChildren(...resume.skills.map((s, i) => h("span", { class: "token" }, s,
      h("button", { type: "button", "aria-label": "Remove " + s, onclick: () => { resume.skills.splice(i, 1); render(); changed(); input.focus(); } }, "×"))), input);
    sec.setCount(resume.skills.length);
  };
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(input.value); }
    else if (e.key === "Backspace" && !input.value && resume.skills.length) { resume.skills.pop(); render(); changed(); }
  });
  input.addEventListener("blur", () => input.value.trim() && add(input.value));
  input.addEventListener("paste", (e) => { const t = e.clipboardData.getData("text"); if (t.includes(",")) { e.preventDefault(); add(t); } });
  box.addEventListener("click", (e) => { if (e.target === box) input.focus(); });
  const sec = block("Skills", true, h("div", { class: "field" }, h("span", { class: "label" }, "One at a time, or paste a comma-separated list"), box));
  render();
  return sec;
}

function listBlock(key, spec) {
  const body = h("div");
  const sec = block(spec.title, resume[key].length > 0, body);
  const render = () => {
    const n = resume[key].length;
    body.replaceChildren(...resume[key].map((item, i) => {
      const move = (d) => { const a = resume[key]; [a[i], a[i + d]] = [a[i + d], a[i]]; render(); changed(); };
      return h("div", { class: "entry" },
        h("div", { class: "entry-head" }, h("span", { class: "label" }, `${spec.one} ${String(i + 1).padStart(2, "0")}`), h("div", { class: "acts" },
          i > 0 && h("button", { type: "button", "aria-label": `Move ${spec.one} ${i + 1} up`, onclick: () => move(-1) }, "↑ up"),
          i < n - 1 && h("button", { type: "button", "aria-label": `Move ${spec.one} ${i + 1} down`, onclick: () => move(1) }, "↓ down"),
          h("button", { class: "rm", type: "button", "aria-label": `Remove ${spec.one} ${i + 1}`, onclick: () => { resume[key].splice(i, 1); render(); changed(); } }, "remove"))),
        h("div", { class: "grid2" }, spec.fields.map(([f, l, kind]) => field(l, item[f], (v) => { item[f] = v; changed(); }, kind))));
    }), h("button", { class: "add", type: "button", onclick: () => {
      resume[key].push(Object.fromEntries(spec.fields.map(([f]) => [f, ""]))); render(); changed();
      body.querySelectorAll(".entry")[resume[key].length - 1]?.querySelector("input,textarea")?.focus();
    } }, `+ Add ${spec.one.toLowerCase()}`));
    sec.setCount(n);
  };
  render();
  return sec;
}

function buildForm() {
  blockNo = 0;
  const personal = block("About you", true,
    h("div", { class: "grid2" }, TOP.map(([k, l]) => field(l, resume[k], (v) => { resume[k] = v; changed(); }, k === "email" ? "email" : null))),
    field("Summary — two or three lines on who you are and what you're after", resume.summary, (v) => { resume.summary = v; changed(); }, "area"));
  $("form").replaceChildren(personal, skillsInput(), ...Object.entries(LISTS).map(([k, spec]) => listBlock(k, spec)));
}

/* ---------- completeness ---------- */
function strength() {
  const r = resume, checks = [
    [10, r.name && r.email, "add your name and email."],
    [5, r.phone, "add a phone number recruiters can call."],
    [15, r.summary.length >= 60, "write a two or three line summary."],
    [15, r.education.some((e) => e.college || e.degree), "add your education."],
    [15, r.skills.length >= 5, `list at least five skills — you have ${r.skills.length}.`],
    [15, r.projects.some((p) => p.title && p.description.length >= 40), "describe at least one project you built."],
    [10, r.experience.some((e) => e.role || e.company), "add an internship or job, if you've had one."],
    [5, /\d/.test([...r.projects.map((p) => p.description), ...r.experience.map((e) => e.details)].join(" ")), "put a number on your impact — “cut load time by 40%”."],
    [5, r.linkedin || r.github, "link your LinkedIn or GitHub."],
    [5, r.certifications.some((c) => c.name), "add a certification or course, if you have one."],
  ];
  const score = checks.reduce((s, [w, ok]) => s + (ok ? w : 0), 0);
  const tip = checks.find(([, ok]) => !ok);
  $("strengthPct").textContent = score;
  $("strengthBar").style.width = score + "%";
  $("strengthBar").classList.toggle("done", score === 100);
  $("strengthTip").replaceChildren(...(tip ? [h("b", {}, "Next: "), tip[2]] : ["Every section is filled in. Run it through the Analyzer next."]));
}

/* ---------- live preview ---------- */
function renderPreview() {
  const r = resume, p = $("preview");
  p.className = "sheet tpl-" + template;
  document.querySelectorAll("#templates button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.tpl === template)));
  if (!hasContent()) { p.replaceChildren(h("div", { class: "empty" }, "Your resume takes shape here as you type.")); return; }
  const sec = (title, kids) => [h("h4", {}, title), kids];
  const ent = (title, sub, body) => h("div", { class: "ent" }, title && h("b", {}, title), sub && h("div", { class: "sub" }, sub), prose(body));
  const join = (...a) => a.filter(Boolean).join("  |  ");
  p.replaceChildren(...nodes(h("h2", {}, r.name || "Your Name"), h("div", { class: "contact" }, join(r.email, r.phone, r.location, r.linkedin, r.github)),
    r.summary && sec("Summary", h("p", {}, r.summary)),
    r.education.length > 0 && sec("Education", r.education.map((e) => {
      const degree = [e.degree, e.branch].filter(Boolean).join(", ");
      return ent(degree || e.college, join(degree && e.college, e.grad_year, e.cgpa && "CGPA " + e.cgpa), "");
    })),
    r.experience.length > 0 && sec("Experience", r.experience.map((e) => ent(e.role || e.company, join(e.role && e.company, e.duration), e.details))),
    r.projects.length > 0 && sec("Projects", r.projects.map((x) => ent(x.title, join(x.tech, x.link), x.description))),
    r.skills.length > 0 && sec("Skills", h("p", {}, r.skills.join(", "))),
    r.certifications.length > 0 && sec("Certifications", r.certifications.map((c) => ent(c.name, join(c.organisation, c.completed), "")))));
}

/* ---------- saving ---------- */
let saveTimer, syncTimer;
function changed() {
  careersStale = true;
  renderPreview(); strength();
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    const ok = store.set("careerforge.resume", JSON.stringify(resume));
    $("saveNote").textContent = ok ? "Saved in this browser." : "This browser is blocking storage, so nothing is saved. Download the PDF to keep your work.";
  }, 300);
  if (status.database) { clearTimeout(syncTimer); syncTimer = setTimeout(syncServer, 2000); }
}

async function syncServer(retry = true) {
  if (!hasContent()) return;
  const token = store.get("careerforge.token");
  try {
    const res = await fetch(token ? "/api/resume/" + encodeURIComponent(token) : "/api/resume", {
      method: token ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ resume, template }) });
    if (res.status === 404 && token && retry) { store.del("careerforge.token"); return syncServer(false); }
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.token) store.set("careerforge.token", data.token);
  } catch { /* the browser copy is the main store */ }
}

function replaceResume(next, message) {
  resume = { ...BLANK(), ...structuredClone(next) };
  buildForm(); changed();
  if (message) toast(message);
}

$("templates").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-tpl]");
  if (!b) return;
  template = b.dataset.tpl; store.set("careerforge.template", template); renderPreview();
  if (status.database) { clearTimeout(syncTimer); syncTimer = setTimeout(syncServer, 1000); }
});
$("sampleBtn").addEventListener("click", () => {
  if (hasContent() && !confirm("Replace what you've entered with the sample resume?")) return;
  replaceResume(SAMPLE, "Sample loaded — edit anything, or Clear to start fresh.");
});
$("clearBtn").addEventListener("click", () => {
  if (!hasContent() || !confirm("Clear everything you've entered? This can't be undone.")) return;
  replaceResume(BLANK(), "Cleared.");
});
$("pdfBtn").addEventListener("click", busy($("pdfBtn"), "Typesetting…", async () => {
  try {
    const blob = await api("/api/resume/pdf", { json: { resume, template } });
    const a = h("a", { href: URL.createObjectURL(blob), download: (resume.name.trim() || "resume").replace(/[^\w.-]+/g, "_") + "_Resume.pdf" });
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    toast("PDF downloaded.");
  } catch (e) { toast(e.message, "err"); }
}));
$("importFile").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  if (!status.ai) { toast("Import reads your PDF with AI, so it needs GEMINI_API_KEY on the server.", "err"); return; }
  if (hasContent() && !confirm("Replace what you've entered with the imported resume?")) return;
  const lbl = $("importLbl"), old = lbl.firstChild.textContent;
  lbl.firstChild.textContent = "Reading PDF…";
  try {
    const form = new FormData(); form.append("file", file);
    const { resume: r } = await api("/api/resume/import", { form });
    replaceResume(r, "Imported. Check each section — layouts can be misread.");
  } catch (err) { toast(err.message, "err"); }
  finally { lbl.firstChild.textContent = old; }
});

/* ---------- analyzer ---------- */
const strs = (a) => (Array.isArray(a) ? a.map((x) => (typeof x === "string" ? x.trim() : "")).filter(Boolean) : []);

function renderAnalysis(d, source) {
  const score = Math.max(0, Math.min(100, Math.round(Number(d.ats_score) || 0)));
  const tone = score >= 75 ? "good" : score >= 50 ? "warn" : "bad";
  const verdict = { good: "Ready to send.", warn: "Close — a few fixes away.", bad: "Needs another pass." }[tone];
  const strengths = strs(d.strengths), missing = strs(d.missing_sections), kw = strs(d.keywords_to_add);
  const imps = (Array.isArray(d.improvements) ? d.improvements : []).filter((i) => i && (typeof i === "string" || i.suggestion || i.issue));
  $("analyzeOut").replaceChildren(h("article", { class: "report" },
    h("div", { class: "verdict" },
      h("div", { class: "big tone-" + tone, "aria-label": `Estimated ATS score ${score} out of 100` }, score, h("small", {}, "/100")),
      h("div", {}, h("span", { class: "label" }, "Estimated ATS score — " + source), h("h2", {}, verdict), d.summary && h("p", {}, d.summary))),
    (strengths.length > 0 || missing.length > 0) && h("div", { class: "columns" },
      h("div", {}, h("h3", { class: "label" }, "Working for you"), strengths.length ? h("ul", { class: "marks yes" }, strengths.map((s) => h("li", {}, s))) : h("p", { class: "fine" }, "Nothing stood out yet.")),
      h("div", {}, h("h3", { class: "label" }, "Missing sections"), missing.length ? h("ul", { class: "marks no" }, missing.map((s) => h("li", {}, s))) : h("p", { class: "fine" }, "None — every expected section is there."))),
    imps.length > 0 && h("section", {}, h("h3", { class: "label" }, "What to fix, in order"),
      h("ol", { class: "fixes" }, imps.map((i) => h("li", {}, h("div", {},
        typeof i === "string" ? h("p", { class: "fix" }, i)
          : [h("span", { class: "label where" }, i.section || "General"), i.issue && h("p", { class: "issue" }, i.issue), i.suggestion && h("p", { class: "fix" }, i.suggestion)]))))),
    kw.length > 0 && h("section", {}, h("h3", { class: "label" }, "Keywords to add — only the ones that are true"),
      h("p", { class: "words" }, kw.map((k) => h("span", {}, k))))));
  $("analyzeOut").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function runAnalysis(call, source) {
  $("analyzeOut").replaceChildren(loading("Reading your resume…", true));
  try { renderAnalysis(await call(), source); } catch (e) { $("analyzeOut").replaceChildren(failure(e.message)); }
}
$("analyzeBtn").addEventListener("click", busy($("analyzeBtn"), "Analyzing…", () => runAnalysis(() => {
  if (!hasContent()) throw new Error("Your resume is empty. Fill it in on the Build tab, or upload a PDF instead.");
  return api("/api/analyze", { json: { resume } });
}, "your builder resume")));

function analyzePdf(file) {
  if (!file) return;
  runAnalysis(() => {
    if (!/\.pdf$/i.test(file.name)) throw new Error("That isn't a PDF. Choose a .pdf file.");
    if (file.size > 5 * 1024 * 1024) throw new Error("The PDF must be under 5 MB.");
    const form = new FormData(); form.append("file", file);
    return api("/api/analyze/pdf", { form });
  }, file.name);
}
$("analyzeFile").addEventListener("change", (e) => { analyzePdf(e.target.files[0]); e.target.value = ""; });
const drop = $("drop");
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove("over")));
drop.addEventListener("drop", (e) => { e.preventDefault(); analyzePdf(e.dataTransfer.files[0]); });

/* ---------- assistant ---------- */
let chatHistory = [];
const STARTERS = ["Tighten my summary", "Which skills should a backend developer add?", "Rewrite my projects with numbers"];
function say(who, content) {
  const said = h("p", { class: "said" }, content);
  const turn = h("div", { class: "turn " + who }, h("span", { class: "label who" }, who === "you" ? "You" : "CareerForge"), said);
  $("chatLog").append(turn);
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
  return { turn, said };
}
function prompts(items) {
  $("chatChips").replaceChildren(...items.slice(0, 3).map((t) => h("button", { type: "button", onclick: () => send(t) }, t)));
}
function resetChat() {
  chatHistory = [];
  $("chatLog").replaceChildren();
  say("ai", "I've read the resume on your Build tab. Tell me the role you're aiming for, or pick a starting point below.");
  prompts(STARTERS);
}
async function send(message) {
  message = message.trim();
  const btn = $("chatForm").querySelector("button");
  if (!message || btn.disabled) return;
  $("chatInput").value = ""; prompts([]); btn.disabled = true;
  say("you", message);
  const { turn, said } = say("ai", h("span", { class: "typing", "aria-label": "Writing" }));
  const slow = setTimeout(() => said.querySelector(".typing") && said.replaceChildren("Still thinking — this can take up to a minute ", h("span", { class: "typing" })), 12000);
  try {
    const d = await api("/api/chat", { json: { message, resume, history: chatHistory.slice(-8) } });
    said.textContent = String(d.reply || "I couldn't come up with an answer. Try asking another way.");
    chatHistory.push({ role: "user", text: message }, { role: "assistant", text: said.textContent });
    prompts(strs(d.suggestions));
  } catch (e) { said.textContent = e.message; turn.classList.add("err"); prompts(STARTERS); }
  finally { clearTimeout(slow); btn.disabled = false; $("chatInput").focus(); }
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
}
$("chatForm").addEventListener("submit", (e) => { e.preventDefault(); send($("chatInput").value); });
$("chatClear").addEventListener("click", resetChat);

/* ---------- careers ---------- */
async function loadCareers() {
  if (!careersStale) return;
  const out = $("careersOut");
  if (!(resume.skills.length || resume.projects.length || resume.experience.length)) {
    out.replaceChildren(h("li", {}, h("p", { class: "callout" }, "Add skills, projects or experience on the Build tab and your best-fit roles show up here. ",
      h("a", { href: "#/builder", onclick: (e) => { e.preventDefault(); showTab("builder"); } }, "Go to Build →"))));
    return;
  }
  out.replaceChildren(h("li", {}, loading("Matching roles…")));
  try {
    const { roles } = await api("/api/recommendations", { json: { resume } });
    if (!roles.length) { out.replaceChildren(h("li", {}, h("p", { class: "callout" }, "No clear match yet. Add specific skills — Python, SQL, React — and try again."))); return; }
    out.replaceChildren(...roles.map((r, i) => h("li", { class: "role" },
      h("span", { class: "rank" }, String(i + 1).padStart(2, "0")),
      h("div", {},
        h("h3", {}, r.role),
        h("p", { class: "about" }, r.summary),
        r.matched.length > 0 && h("p", { class: "line" }, h("span", { class: "label" }, "You have"), h("span", {}, r.matched.join(", "))),
        r.missing.length > 0 && h("p", { class: "line lack" }, h("span", { class: "label" }, "To learn"), h("span", {}, r.missing.join(", "))),
        r.to_learn.length > 0 && h("p", { class: "line" }, h("span", { class: "label" }, "Bonus"), h("span", {}, r.to_learn.join(", ")))),
      h("div", { class: "side" },
        h("div", { class: "pct" }, r.score, h("small", {}, "% fit")),
        h("div", { class: "track" }, h("i", { style: `width:${r.score}%` })),
        h("button", { class: "link", type: "button", onclick: () => findJobs(r.role.replace(/\s*\/.*$/, "")) }, "See open jobs →")))));
    careersStale = false;
  } catch (e) { out.replaceChildren(h("li", {}, failure(e.message))); }
}
$("careersBtn").addEventListener("click", () => { careersStale = true; loadCareers(); });

function findJobs(q) {
  $("jq").value = q;
  showTab("jobs");
  $("jobForm").requestSubmit();
}

/* ---------- jobs ---------- */
let lastJobs = [];
$("jobForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.target.querySelector("button[type=submit]");
  if (btn.disabled) return;
  let q = $("jq").value.trim();
  if (!q && resume.skills.length) q = resume.skills.slice(0, 2).join(" ");
  $("resultsBar").hidden = true; $("credit").hidden = true;
  $("jobsOut").replaceChildren(loading("Searching live listings…"));
  btn.disabled = true;
  try {
    const d = await api("/api/jobs/search", { json: { resume, q, location: $("jloc").value, type: $("jtype").value,
      experience: $("jexp").value, source: $("jsrc").value, days: Number($("jdays").value) } });
    if (!d.configured) { $("jobsOut").replaceChildren(h("p", { class: "callout" }, "Live job search is currently unavailable.")); return; }
    lastJobs = d.jobs; lastSources = d.sources;
    const sources = Object.entries(d.sources).map(([k, v]) => `${k[0].toUpperCase() + k.slice(1)} ${v}`).join("  ·  ");
    $("jobStatus").replaceChildren(h("b", {}, `${d.jobs.length} listing${d.jobs.length === 1 ? "" : "s"}`), q ? ` for “${q}”` : "", "  —  ", sources);
    $("resultsBar").hidden = false;
    $("credit").hidden = !d.jobs.some((j) => j.provider === "Himalayas");
    renderJobs();
  } catch (err) { $("jobsOut").replaceChildren(failure(err.message)); }
  finally { btn.disabled = false; }
});
$("jsort").addEventListener("change", renderJobs);

let lastSources = {};
function renderJobs() {
  if (!lastJobs.length) {
    const tried = Object.values(lastSources).filter((v) => v !== "not configured");
    const allDown = tried.length > 0 && tried.every((v) => !/jobs$/.test(v));
    $("jobsOut").replaceChildren(h("p", { class: "callout" }, allDown
      ? "The job sites didn't respond this time. Wait a moment and search again."
      : "Nothing matched. Try a broader role, another source, or drop the location."));
    return;
  }
  const by = $("jsort").value;
  const sorted = [...lastJobs].sort((a, b) => by === "new" ? b.posted - a.posted : by === "pay" ? b.salary_value - a.salary_value || b.score - a.score : b.score - a.score);
  $("jobsOut").replaceChildren(...sorted.map(listing));
}

function listing(j) {
  const facts = [j.type, j.remote && "Remote", j.experience, j.provider, j.posted && ago(j.posted)].filter(Boolean);
  const tone = j.basis === "none" ? "lo" : j.score >= 60 ? "hi" : j.score >= 35 ? "mid" : "lo";
  const approx = j.salary_note.startsWith("Converted");
  return h("article", { class: "listing" },
    h("div", {},
      h("h3", {}, j.title),
      h("p", { class: "org" }, j.company && h("b", {}, j.company), j.company && j.location && " — ", j.location),
      h("div", { class: "facts" }, facts.map((f) => h("span", {}, f))),
      j.matched.length > 0 && h("p", { class: "skills-line" }, h("span", { class: "label" }, "Match"), h("span", { class: "have" }, j.matched.join(", "))),
      j.missing.length > 0 && h("p", { class: "skills-line" }, h("span", { class: "label" }, "Gap"), h("span", { class: "lack", title: "In the listing, not in your resume" }, j.missing.join(", ")))),
    h("div", { class: "side" },
      j.salary ? h("div", { class: "pay", title: j.salary_note || "Salary from the listing" }, j.salary, (approx || j.salary_note) && h("small", {}, approx ? "approx., converted" : "estimated"))
               : h("div", { class: "nopay" }, "Salary not listed"),
      h("div", { class: "fit " + tone, title: "Estimated fit with your resume" }, h("b", {}, j.basis === "none" ? "—" : j.score), j.basis === "none" ? "no skills to compare" : j.basis === "title" ? "% fit (title only)" : "% fit"),
      safeUrl(j.url) && h("a", { class: "btn ink", href: j.url, target: "_blank", rel: "noopener noreferrer" }, "Apply ↗")),
    j.description && h("details", {}, h("summary", {}, "Read the listing"), h("p", {}, j.description)));
}

/* ---------- start ---------- */
function renderServices() {
  const jobsOn = Object.values(status.jobs || {}).some(Boolean);
  $("services").replaceChildren(
    h("span", { class: status.ai ? "on" : "", title: status.ai ? "Gemini is configured" : "Add GEMINI_API_KEY to enable" }, h("i"), "AI"),
    h("span", { class: jobsOn ? "on" : "", title: Object.entries(status.jobs || {}).map(([k, v]) => `${k}: ${v ? "on" : "off"}`).join(", ") }, h("i"), "Jobs"),
    h("span", { class: status.database ? "on" : "", title: status.database ? "Saving a copy to MySQL" : "Saved in this browser only" }, h("i"), "Sync"));
}
buildForm(); renderPreview(); strength(); resetChat(); renderServices();
fetch("/api/status").then((r) => r.json()).then((s) => {
  status = s;
  $("aiOff").hidden = !!s.ai;
  renderServices();
  if (s.database && hasContent()) syncServer();
}).catch(() => {});
// "#/jobs" rather than "#jobs", so the browser doesn't also jump to the panel with that id.
showTab(location.hash.replace(/^#\/?/, "") || "builder");
