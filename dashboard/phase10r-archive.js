(() => {
  const FRONTIER_URL = "/phases/phase10r/";
  const REPO_URL = "https://github.com/suhaslord/uav-safety-research";
  const PHASE11_URL = "https://github.com/suhaslord/uav-safety-research/blob/main/docs/phase11_domain_shift_reliability_preregistration.md";

  const phase10r = {
    label: "Phase 10R · Frozen holdout",
    era: "Current frontier",
    title: "Mean error fell. Trust still broke under distribution shift.",
    lede: "A frozen partial-view recovery candidate was exposed exactly once to 12 new geometry trajectories across three appearance conditions. Typical ambiguous-view error improved sharply, but tail risk, target availability, and uncertainty coverage failed the preregistered all-gates rule.",
    status: "Latest published frontier · frozen",
    role: "simulation-only · phase10r_frozen_holdout",
    change: [
      "Causal partial-view recovery frozen before the protected holdout",
      "New geometry trajectories crossed with nominal, dim/contrast, and blur/noise appearance shifts",
      "Frozen development uncertainty calibration tested without post-holdout retuning"
    ],
    before: "Phase 10 left five truth-visible misses and Phase 10R validation suggested partial-view recovery could improve availability while preserving average geometry.",
    after: "The protected holdout showed that average geometry can improve strongly while difficult-tail error, availability, and calibration still fail under combined distribution shift.",
    metrics: [
      ["Ambiguous lateral MAE", "79.2% better"],
      ["Truth-visible miss rate", "20.0%"],
      ["95% coverage", "84.3% / 79.7%"]
    ],
    finding: "Phase 10R improved typical ambiguous-view estimates without earning a reliability claim: p95 tail error barely improved, one in five truth-visible frames was still missed, and development-frozen uncertainty became under-covering after appearance + geometry shift.",
    source: "Phase 10R frozen holdout result",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/main/docs/phase10r_frozen_holdout_result.md"
  };

  const phase10rDetails = {
    problem: "Phase 10's unchanged camera front end still missed truth-visible targets near difficult viewing geometry. Phase 10R asked whether causal partial-view recovery could regain those observations without degrading clean geometry or making uncertainty dishonest.",
    goal: "Freeze one recovery candidate and one uncertainty calibration before a genuinely new protected holdout, then test clean-case regression, ambiguous-view accuracy, tail error, availability, false positives, and coverage under combined geometry + appearance shift.",
    systemIntro: "Phase 10R keeps the earlier metric-perception stack frozen around one preregistered recovery rule. The final holdout introduces new trajectory geometry and appearance shifts, then evaluates the candidate once under an all-gates rule.",
    architecture: [
      "Frozen Phase 10 / Phase 9 camera geometry reference",
      "Partial-view visibility state",
      "Frozen MIN_VISIBLE = 0.66 recovery candidate",
      "Causal accepted / abstained observations",
      "Development-frozen uncertainty calibration",
      "One-time protected holdout evaluation"
    ],
    architectureNote: "The protected holdout was not used for model selection. The candidate SHA, visibility threshold, and calibration digest were fixed before seed 1618033 was exposed.",
    evidenceStory: "Across 1,440 truth-visible frames, ambiguous lateral MAE improved 79.2% and altitude MAE improved 73.7%, with zero false positives and no clean-case regression. But lateral p95 slightly regressed, altitude p95 improved only 7.3%, miss rate remained 20.0%, and nominal 95% intervals covered only 84.3% lateral / 79.7% altitude.",
    evidenceFacts: [
      "12 new geometry trajectories × 3 appearance conditions = 36 sequences",
      "1,440 truth-visible frames · 0.0% false positives",
      "Final verdict: mixed / failed overall under the preregistered all-gates rule"
    ],
    limitations: [
      "Truth-visible miss rate was 20.0%, above the preregistered ≤10% requirement.",
      "Ambiguous lateral p95 changed by −1.1%; the difficult tail remained unresolved.",
      "Ambiguous altitude p95 improved only 7.3%, below the required 25%.",
      "Development-frozen 95% uncertainty under-covered at 84.3% lateral and 79.7% altitude under the harder shift.",
      "All evidence remains simulation-only and does not establish physical-flight safety."
    ],
    nextReason: "Phase 11 should treat the Phase 10R holdout as permanently seen motivation and test domain-shift-aware reliability: conditional/conformal coverage, explicit shift detection, selective abstention, and tail-risk control on new development evidence.",
    visual: {
      kind: "bars",
      title: "Frozen Phase 10R holdout · reliability split",
      note: "Strong mean gains did not transfer to tail/coverage gates",
      items: [
        {label: "Lateral MAE gain", value: 79.2, text: "79.2%"},
        {label: "Altitude MAE gain", value: 73.7, text: "73.7%"},
        {label: "Lateral 95% coverage", value: 84.3, text: "84.3%"},
        {label: "Altitude 95% coverage", value: 79.7, text: "79.7%"}
      ]
    }
  };

  // Register Phase 10R into the exact same data structures the shared phase renderer uses.
  // This executes before DOMContentLoaded, so phase-runtime.js sees 10R as a native phase.
  try {
    if (typeof PHASES !== "undefined") PHASES.phase10r = phase10r;
    if (typeof ORDER !== "undefined" && !ORDER.includes("phase10r")) ORDER.push("phase10r");
    if (typeof DETAILS !== "undefined") DETAILS.phase10r = phase10rDetails;
  } catch (error) {
    console.warn("Phase 10R shared registration skipped", error);
  }

  function decorateLogo() {
    const words = document.querySelectorAll(".top .word");
    words.forEach(word => {
      if (word.querySelector(".aegis-mini-mark")) return;
      word.innerHTML = '<span class="aegis-mini-mark" aria-hidden="true"><i></i><b></b></span><span>AEGISLAND</span>';
    });
    if (document.getElementById("aegisArchiveLogoStyle")) return;
    const style = document.createElement("style");
    style.id = "aegisArchiveLogoStyle";
    style.textContent = `
      .top .word{display:inline-flex;align-items:center;gap:9px;letter-spacing:.18em}
      .aegis-mini-mark{width:26px;height:26px;border-radius:8px;background:#171a20;display:inline-grid;place-items:center;position:relative;box-shadow:0 6px 18px rgba(23,26,32,.16);flex:0 0 auto}
      .aegis-mini-mark:before,.aegis-mini-mark:after{content:"";position:absolute;width:2px;height:14px;top:6px;background:#fff;border-radius:2px}
      .aegis-mini-mark:before{transform:rotate(25deg);left:9px}.aegis-mini-mark:after{transform:rotate(-25deg);right:9px}
      .aegis-mini-mark i{width:9px;height:2px;background:#fff;border-radius:2px;position:absolute;top:15px}
      .aegis-mini-mark b{position:absolute;width:5px;height:5px;border-radius:50%;background:#2f6fed;right:3px;top:3px;box-shadow:0 0 0 2px rgba(47,111,237,.2)}
    `;
    document.head.appendChild(style);
  }

  function patchHeader() {
    const buttons = document.querySelectorAll(".top .top-end .top-btn");
    if (buttons[0]) {
      buttons[0].href = REPO_URL;
      buttons[0].textContent = "GitHub ↗";
    }
    if (document.getElementById("archiveMap") && buttons[1]) {
      buttons[1].href = FRONTIER_URL;
      buttons[1].textContent = "Phase 10R";
    }
  }

  function patchIndex() {
    const map = document.getElementById("archiveMap");
    if (!map) return;

    const big = document.querySelector(".index-hero .big");
    if (big) big.textContent = "From early supervisory safety experiments through PX4/Gazebo camera evidence, temporal metric perception, and the final Phase 10R frozen holdout. Positive results, mismatches, failed gates, and the naming gap all stay visible.";

    const phase10Link = Array.from(map.querySelectorAll(".phase-link")).find(link => /\/phases\/phase10\/?$/.test(new URL(link.href, location.href).pathname));
    if (phase10Link) {
      phase10Link.classList.remove("frontier-link");
      const phase10Era = phase10Link.closest(".era");
      const heading = phase10Era?.querySelector("h2");
      if (heading && !phase10Era.querySelector('[href*="phase10r"]')) heading.textContent = "Temporal metric perception";
    }

    // If shared ORDER rendered Phase 10R already, just make its era unmistakably current.
    const phase10rLink = Array.from(map.querySelectorAll(".phase-link")).find(link => /\/phases\/phase10r\/?$/.test(new URL(link.href, location.href).pathname));
    if (phase10rLink) {
      phase10rLink.classList.add("frontier-link");
      const era = phase10rLink.closest(".era");
      const heading = era?.querySelector("h2");
      if (heading) heading.textContent = "Current frontier";
      return;
    }

    const era = document.createElement("section");
    era.className = "era";
    era.id = "phase10rArchiveEra";
    era.innerHTML = `
      <header><span>05</span><h2>Current frontier</h2></header>
      <div class="track">
        <a class="phase-link frontier-link" href="${FRONTIER_URL}">
          <span>Phase 10R · Frozen holdout</span>
          <strong>Mean error fell. Trust still broke under distribution shift.</strong>
          <small>Latest published frontier · mixed / failed overall · frozen without retuning</small>
          <i>→</i>
        </a>
      </div>`;
    map.appendChild(era);
  }

  function patchRail() {
    const rail = document.getElementById("phaseRail");
    if (!rail) return;
    let step = Array.from(rail.querySelectorAll(".rail-step")).find(link => /\/phases\/phase10r\/?$/.test(new URL(link.href, location.href).pathname));
    if (!step) {
      step = document.createElement("a");
      step.className = "rail-step frontier";
      step.href = FRONTIER_URL;
      step.setAttribute("aria-current", "false");
      step.innerHTML = "<span>12</span><i></i><strong>Phase 10R\nFrozen holdout</strong>";
      rail.appendChild(step);
    }
    step.classList.add("frontier");
  }

  function patchPhase10() {
    const phase = document.body.dataset.signaturePhase || location.pathname.match(/phase\d+[a-z]?/i)?.[0]?.toLowerCase();
    if (phase !== "phase10") return;

    const badgeLabel = document.querySelector("#phaseHero .frontier-badge span");
    if (badgeLabel) badgeLabel.textContent = "Frozen predecessor";
    const heroKicker = document.querySelector("#phaseHero .hero-copy > .kicker");
    if (heroKicker) heroKicker.textContent = "Previous frontier · AegisLand research archive";
    const overviewLabel = document.querySelector("#phaseOverviewVisual figcaption strong");
    if (overviewLabel) overviewLabel.textContent = "Previous frontier";

    const next = document.getElementById("nextPhase");
    if (next) {
      next.href = FRONTIER_URL;
      next.innerHTML = "<span>Latest published frontier</span><strong>Phase 10R · Frozen holdout</strong><i>→</i>";
    }
  }

  function insertGoalAfterHero() {
    const hero = document.getElementById("phaseHero");
    if (!hero || document.querySelector(".program-goal")) return;
    const section = document.createElement("section");
    section.className = "program-goal is-visible";
    section.setAttribute("aria-labelledby", "programGoalTitle");
    section.innerHTML = `
      <div class="program-goal-copy">
        <p class="kicker">Our goal</p>
        <h2 id="programGoalTitle">Make autonomous perception worthy of trust.</h2>
        <p>AegisLand studies how autonomous aerial systems can make safer decisions under uncertainty. Rather than chasing success alone, the research focuses on trustworthy perception, calibrated confidence, controlled abstention, and evidence you can inspect phase by phase.</p>
      </div>
      <div class="program-pillars" aria-label="AegisLand research priorities">
        <div><span>01</span><strong>Trust only when justified</strong></div>
        <div><span>02</span><strong>Detect uncertainty before unsafe action</strong></div>
        <div><span>03</span><strong>Preserve safety without hiding failures</strong></div>
        <div><span>04</span><strong>Show evidence phase by phase</strong></div>
      </div>`;
    hero.insertAdjacentElement("afterend", section);
  }

  function patchPhase10R() {
    const phase = location.pathname.match(/phase10r/i)?.[0]?.toLowerCase();
    if (phase !== "phase10r") return;
    document.body.dataset.signaturePhase = "phase10r";
    document.title = "Phase 10R · Frozen holdout — AegisLand";

    const hero = document.getElementById("phaseHero");
    if (!hero) return;
    hero.classList.add("frontier-hero");

    const copy = hero.querySelector(".hero-copy");
    if (copy && !copy.querySelector(".frontier-badge")) {
      const badge = document.createElement("div");
      badge.className = "frontier-badge";
      badge.innerHTML = "<span>Latest published frontier</span><strong>Phase 10R · Frozen holdout</strong>";
      copy.prepend(badge);
    }
    const kicker = copy?.querySelector(":scope > .kicker");
    if (kicker) kicker.textContent = "Latest published frontier · AegisLand research archive";

    const object = hero.querySelector(".object");
    if (object) {
      object.className = "object signature-visual signature-phase10 signature-phase10r";
      object.removeAttribute("aria-hidden");
      object.setAttribute("role", "img");
      object.setAttribute("aria-label", "Phase 10R frozen holdout reliability result");
      object.innerHTML = `
        <div class="frontier-topline"><span>LATEST FRONTIER</span><strong>FROZEN HOLDOUT</strong></div>
        <div class="frontier-core" aria-hidden="true">
          <span class="frontier-ring r1"></span><span class="frontier-ring r2"></span><span class="frontier-ring r3"></span>
          <svg class="frontier-trace" viewBox="0 0 260 260"><path pathLength="1" d="M24 166 C62 82 96 205 132 119 S198 65 236 126"/></svg>
          <span class="frontier-center"><small>AEGIS</small><strong>10R</strong></span>
        </div>
        <div class="frontier-metrics">
          <div><span>ambiguous lateral MAE gain</span><strong>79.2%</strong></div>
          <div><span>truth-visible miss rate</span><strong>20.0%</strong></div>
          <div><span>lateral 95% coverage</span><strong>84.3%</strong></div>
          <div><span>altitude 95% coverage</span><strong>79.7%</strong></div>
        </div>
        <div class="frontier-foot"><span>Mean error improved strongly</span><strong>Tail risk + calibration gates still failed.</strong></div>`;
    }

    const overview = document.querySelector("#phaseOverviewVisual figcaption strong");
    if (overview) overview.textContent = "Frozen shift verdict";

    const source = document.getElementById("phaseSource");
    if (source) source.href = phase10r.sourceUrl;

    const next = document.getElementById("nextPhase");
    if (next) {
      next.href = PHASE11_URL;
      next.target = "_blank";
      next.rel = "noreferrer";
      next.innerHTML = "<span>Next research design</span><strong>Phase 11 · Domain-shift-aware reliability</strong><i>↗</i>";
    }

    insertGoalAfterHero();
  }

  function install() {
    decorateLogo();
    patchHeader();
    patchIndex();
    patchRail();
    patchPhase10();
    patchPhase10R();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => requestAnimationFrame(install), {once:true});
  else requestAnimationFrame(install);
})();
