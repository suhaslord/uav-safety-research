(() => {
  const RESULT_URL = "/phases/phase10r/";
  const RECORD_URL = "https://github.com/suhaslord/uav-safety-research/blob/main/docs/phase10r_frozen_holdout_result.md";
  const MODELS = [
    ["01","Phase 1","/phases/phase1/"],
    ["02","Phase 2","/phases/phase2/"],
    ["03","Phase 3","/phases/phase3/"],
    ["04","Phase 4","/phases/phase4/","gap"],
    ["05","Phase 5","/phases/phase5/"],
    ["06","Phase 6","/phases/phase6/"],
    ["07","Phase 6B","/phases/phase6b/"],
    ["08","Phase 7","/phases/phase7/"],
    ["09","Phase 8","/phases/phase8/"],
    ["10","Phase 9","/phases/phase9/"],
    ["11","Phase 10","/phases/phase10/"],
    ["12","Phase 10R","/phases/phase10r/","current"]
  ];

  function setText(selector, text) {
    const node = document.querySelector(selector);
    if (node) node.textContent = text;
  }

  function installBrandStyle() {
    if (document.getElementById("aegisBrandStyle")) return;
    const style = document.createElement("style");
    style.id = "aegisBrandStyle";
    style.textContent = `
      .wordmark{display:inline-flex!important;align-items:center;gap:9px;letter-spacing:.18em!important}
      .aegis-mini-mark{width:28px;height:28px;border-radius:9px;background:#171a20;display:inline-grid;place-items:center;position:relative;box-shadow:0 7px 20px rgba(23,26,32,.17);flex:0 0 auto}
      .aegis-mini-mark:before,.aegis-mini-mark:after{content:"";position:absolute;width:2px;height:15px;top:6px;background:#fff;border-radius:2px}.aegis-mini-mark:before{transform:rotate(25deg);left:9px}.aegis-mini-mark:after{transform:rotate(-25deg);right:9px}.aegis-mini-mark i{width:10px;height:2px;background:#fff;border-radius:2px;position:absolute;top:16px}.aegis-mini-mark b{position:absolute;width:5px;height:5px;border-radius:50%;background:#2f6fed;right:3px;top:3px;box-shadow:0 0 0 2px rgba(47,111,237,.22)}
    `;
    document.head.appendChild(style);
  }

  function decorateLogo() {
    installBrandStyle();
    const wordmark = document.querySelector(".site-header .wordmark");
    if (wordmark && !wordmark.querySelector(".aegis-mini-mark")) {
      wordmark.innerHTML = '<span class="aegis-mini-mark" aria-hidden="true"><i></i><b></b></span><span>AEGISLAND</span>';
    }
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

  function installModelRail() {
    if (document.getElementById("homeModelRail")) return;
    const hero = document.querySelector("main .hero");
    if (!hero) return;

    const style = document.createElement("style");
    style.id = "homeModelRailStyle";
    style.textContent = `
      .home-model-rail{background:#fff;border-top:1px solid #e5e5e7;border-bottom:1px solid #e5e5e7;padding:22px clamp(20px,5vw,72px) 18px;overflow:hidden}
      .home-model-rail-head{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:15px}.home-model-rail-head p{margin:0;color:#6b6d70;font-size:10px;font-weight:700;letter-spacing:.13em;text-transform:uppercase}.home-model-rail-head strong{font-size:13px;font-weight:600}.home-model-rail-head a{font-size:11px;color:#5c5e62;border-bottom:1px solid #bbb;padding-bottom:2px}
      .home-model-track{display:grid;grid-template-columns:repeat(12,minmax(76px,1fr));position:relative;min-width:980px}.home-model-track:before{content:"";position:absolute;left:3%;right:3%;top:14px;height:1px;background:#c9cacc}.home-model-step{position:relative;display:grid;justify-items:center;gap:6px;padding:0 4px;text-align:center;color:#6b6d70;transition:transform .2s ease,color .2s ease}.home-model-step:hover{transform:translateY(-2px);color:#171a20}.home-model-step i{width:9px;height:9px;border:2px solid #9fa0a3;background:#fff;border-radius:50%;z-index:1;margin-top:10px}.home-model-step span{font-size:9px;letter-spacing:.08em}.home-model-step strong{font-size:10px;font-weight:600;line-height:1.15}.home-model-step.current{color:#171a20}.home-model-step.current i{width:13px;height:13px;margin-top:8px;background:#2f6fed;border-color:#2f6fed;box-shadow:0 0 0 5px rgba(47,111,237,.13)}.home-model-step.current strong{font-weight:750}.home-model-step.gap{opacity:.6}
      .home-model-scroll{overflow-x:auto;scrollbar-width:thin;padding-bottom:5px}
      @media(max-width:767px){.home-model-rail{padding-left:20px;padding-right:20px}.home-model-rail-head{align-items:flex-start}.home-model-track{min-width:900px}.home-model-step strong{font-size:9px}}
    `;
    document.head.appendChild(style);

    const section = document.createElement("section");
    section.id = "homeModelRail";
    section.className = "home-model-rail";
    section.setAttribute("aria-label", "AegisLand model and research phase timeline");
    section.innerHTML = `
      <div class="home-model-rail-head">
        <div><p>Research progression</p><strong>Every model stays reachable.</strong></div>
        <a href="/phases/">Open full archive ↗</a>
      </div>
      <div class="home-model-scroll"><div class="home-model-track">
        ${MODELS.map(([number,label,url,state]) => `<a class="home-model-step ${state || ""}" href="${url}" ${state === "current" ? 'aria-current="page"' : ""}><i></i><span>${number}</span><strong>${label}</strong></a>`).join("")}
      </div></div>`;
    hero.insertAdjacentElement("afterend", section);
  }

  function installFrontier() {
    if (document.getElementById("phase10rFrontier")) return;
    const anchor = document.getElementById("homeModelRail") || document.querySelector("main .hero");
    if (!anchor) return;

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
    anchor.insertAdjacentElement("afterend", section);
  }

  function install() {
    decorateLogo();
    promoteHero();
    installModelRail();
    installFrontier();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install, {once:true});
  else install();
})();
