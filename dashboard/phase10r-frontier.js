(() => {
  const RESULT_URL = "/phases/phase10r/";
  const RECORD_URL = "https://github.com/suhaslord/uav-safety-research/blob/main/docs/phase10r_frozen_holdout_result.md";

  function setText(selector, text) {
    const node = document.querySelector(selector);
    if (node) node.textContent = text;
  }

  function promoteHero() {
    document.title = "AegisLand — Phase 10R Frozen Frontier";
    const description = document.querySelector('meta[name="description"]');
    if (description) description.content = "AegisLand Phase 10R frozen holdout — simulation-only evidence on perception reliability under appearance and geometry shift.";

    const headerPhase = document.querySelector(".site-header .phase-link");
    if (headerPhase) {
      headerPhase.textContent = "Phase 10R";
      headerPhase.href = RESULT_URL;
    }

    setText("main .hero .kicker", "simulation-only research · latest published frontier");
    setText("main .hero .hero-subtitle", "Phase 10R frozen holdout: mean error fell, but tail risk and calibration still broke under shift.");

    const actions = document.querySelectorAll("main .hero .hero-actions a");
    if (actions[0]) {
      actions[0].textContent = "Open Phase 10R";
      actions[0].href = RESULT_URL;
    }
    if (actions[1]) {
      actions[1].textContent = "Read frozen record";
      actions[1].href = RECORD_URL;
    }

    const meta = document.querySelector("main .hero .hero-meta");
    if (meta) {
      meta.setAttribute("aria-label", "Current published evidence role");
      meta.innerHTML = "<span>Phase 10R</span><span>phase10r_frozen_holdout</span><span>mixed / failed overall</span><span>safety acceptance: false</span>";
    }

    const image = document.querySelector("main .hero .hero-image");
    if (image) image.alt = "Stylized landing target representing the frozen Phase 10R perception-reliability holdout.";

    const telemetry = document.querySelector("main .hero .hero-telemetry");
    if (telemetry) {
      telemetry.setAttribute("aria-label", "Phase 10R frozen holdout summary");
      telemetry.innerHTML = "<span><strong>1,440</strong><small>truth-visible frames</small></span><span><strong>36</strong><small>holdout sequences</small></span><span><strong>0.0%</strong><small>false positives</small></span>";
    }

    const captions = document.querySelectorAll("main .hero figcaption span");
    if (captions[0]) captions[0].textContent = "Phase 10R frozen holdout";
    if (captions[1]) captions[1].textContent = "latest published frontier · evidence frozen without retuning";

    const foot = document.querySelectorAll("main .hero .hero-foot span");
    if (foot[0]) foot[0].textContent = "frozen holdout · no post-holdout retuning";
    if (foot[1]) foot[1].textContent = "Phase 10R is the current published frontier · checking current CI…";

    setText("#timeline .lineage-intro .lead", "The complete project history stays inspectable through the current Phase 10R frozen holdout. Protocols, failures, mixed results, external-simulator evidence, and the final shift result remain linked instead of being rewritten after the fact.");
  }

  function installFrontier() {
    if (document.getElementById("phase10rFrontier")) return;
    const hero = document.querySelector("main .hero");
    if (!hero) return;

    const style = document.createElement("style");
    style.id = "phase10rFrontierStyle";
    style.textContent = `
      .phase10r-frontier{background:#171a20;color:#fff;padding:24px clamp(24px,7vw,120px);display:grid;grid-template-columns:minmax(0,1fr) auto;gap:28px;align-items:center;border-top:1px solid rgba(255,255,255,.12)}
      .phase10r-frontier-copy{display:grid;gap:6px}.phase10r-frontier-kicker{margin:0;color:#9fa0a3;font-size:10px;font-weight:600;letter-spacing:.14em;text-transform:uppercase}.phase10r-frontier strong{font-size:clamp(17px,2vw,24px);font-weight:500;letter-spacing:-.02em}.phase10r-frontier p{margin:0;color:#c7c7c7;font-size:13px;line-height:1.55}.phase10r-frontier-metrics{display:flex;gap:22px;align-items:center}.phase10r-frontier-metrics span{display:grid;gap:2px;min-width:86px}.phase10r-frontier-metrics b{font-size:18px;font-weight:500}.phase10r-frontier-metrics small{color:#9fa0a3;font-size:9px;text-transform:uppercase;letter-spacing:.08em}.phase10r-frontier a{color:#fff;border-bottom:1px solid rgba(255,255,255,.45);padding-bottom:2px}
      @media(max-width:767px){.phase10r-frontier{grid-template-columns:1fr;padding:22px 20px}.phase10r-frontier-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.phase10r-frontier-metrics span{min-width:0}.phase10r-frontier-metrics b{font-size:16px}}
    `;
    document.head.appendChild(style);

    const section = document.createElement("section");
    section.id = "phase10rFrontier";
    section.className = "phase10r-frontier";
    section.setAttribute("aria-label", "Latest published Phase 10R frozen holdout frontier");
    section.innerHTML = `
      <div class="phase10r-frontier-copy">
        <p class="phase10r-frontier-kicker">Latest published frontier · Phase 10R frozen holdout</p>
        <strong>Average ambiguous-view error fell sharply. Tail risk, availability, and calibration under shift did not.</strong>
        <p>Final all-gates verdict: mixed / failed overall · frozen without retuning · <a href="${RESULT_URL}">open Phase 10R ↗</a></p>
      </div>
      <div class="phase10r-frontier-metrics" aria-label="Phase 10R frozen holdout metrics">
        <span><b>79.2%</b><small>lateral MAE gain</small></span>
        <span><b>20.0%</b><small>miss rate</small></span>
        <span><b>84.3%</b><small>95% lat coverage</small></span>
      </div>`;
    hero.insertAdjacentElement("afterend", section);
  }

  function install() {
    promoteHero();
    installFrontier();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install, {once:true});
  else install();
})();
