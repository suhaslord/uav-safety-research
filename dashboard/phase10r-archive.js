(() => {
  const FRONTIER_URL = "/phases/phase10r/";
  const REPO_URL = "https://github.com/suhaslord/uav-safety-research";
  const PHASE11_URL = "https://github.com/suhaslord/uav-safety-research/blob/main/docs/phase11_domain_shift_reliability_preregistration.md";

  const phase10r = {
    label: "Phase 10R · Frozen holdout",
    era: "Current frontier",
    title: "Mean error improved, but the hard cases still failed the locked checks.",
    lede: "The frozen rule faced new geometry and appearance. Typical error improved; the locked tail and coverage checks failed.",
    status: "Latest published frontier · frozen",
    role: "simulation-only · phase10r_frozen_holdout",
    change: [
      "Causal partial-view recovery frozen before the protected holdout",
      "New geometry trajectories crossed with nominal, dim/contrast, and blur/noise appearance shifts",
      "Frozen development uncertainty calibration tested without post-holdout retuning"
    ],
    before: "Phase 10 still missed five truth-visible targets. Development work for Phase 10R suggested that partial-view recovery might regain some of those observations without hurting the average clean geometry.",
    after: "On the protected holdout, the average geometry improved strongly, but the difficult tail, availability, and calibration still missed their locked requirements under the combined shift.",
    metrics: [
      ["Ambiguous lateral MAE", "79.2% better"],
      ["Truth-visible miss rate", "20.0%"],
      ["95% coverage", "84.3% / 79.7%"]
    ],
    finding: "Typical ambiguous-view error fell. Tail error, missed frames, and under-coverage kept the verdict failed.",
    source: "Phase 10R frozen holdout result",
    sourceUrl: "https://github.com/suhaslord/uav-safety-research/blob/main/docs/phase10r_frozen_holdout_result.md"
  };

  const phase10rDetails = {
    problem: "Phase 10 still missed targets that were actually visible near difficult viewing geometry. Phase 10R tested whether a causal partial-view recovery rule could get some of those observations back without hurting clean geometry or making the uncertainty less honest.",
    goal: "Freeze one recovery rule and one uncertainty calibration before opening a genuinely new holdout, then check clean-case regression, ambiguous-view accuracy, tail error, availability, false positives, and coverage under a combined geometry and appearance shift.",
    systemIntro: "Phase 10R keeps the earlier metric-perception stack fixed and adds one preregistered recovery rule. New trajectory geometry and appearance changes are introduced only in the final holdout, where the frozen candidate is evaluated once against the full gate set.",
    architecture: [
      "Frozen Phase 10 / Phase 9 camera geometry reference",
      "Partial-view visibility state",
      "Frozen MIN_VISIBLE = 0.66 recovery candidate",
      "Causal accepted / abstained observations",
      "Development-frozen uncertainty calibration",
      "One-time protected holdout evaluation"
    ],
    architectureNote: "The protected holdout was not used for model selection. The candidate SHA, visibility threshold, and calibration digest were fixed before seed 1618033 was exposed.",
    evidenceStory: "Across 1,440 truth-visible frames, ambiguous lateral MAE improved 79.2% and altitude MAE improved 73.7%, with zero false positives and no clean-case regression. The harder part of the result went the other way: lateral p95 slightly regressed, altitude p95 improved only 7.3%, miss rate stayed at 20.0%, and nominal 95% intervals covered only 84.3% lateral / 79.7% altitude.",
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
    nextReason: "Phase 11 should treat the Phase 10R holdout as permanently seen evidence and move to a narrower question: can new development data support better coverage under shift, explicit shift detection, selective abstention, and better tail control?",
    visual: {
      kind: "bars",
      title: "Frozen Phase 10R holdout · reliability split",
      note: "Mean error improved; the tail and coverage gates did not",
      items: [
        {label: "Lateral MAE gain", value: 79.2, text: "79.2%"},
        {label: "Altitude MAE gain", value: 73.7, text: "73.7%"},
        {label: "Lateral 95% coverage", value: 84.3, text: "84.3%"},
        {label: "Altitude 95% coverage", value: 79.7, text: "79.7%"}
      ]
    }
  };

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
    if (big) big.textContent = "The early work starts with a separate landing supervisor, moves through PX4/Gazebo and camera-based perception, and eventually reaches the frozen Phase 10R holdout. The archive keeps the mismatches and failed gates in the same record as the successful results.";

    const phase10Link = Array.from(map.querySelectorAll(".phase-link")).find(link => /\/phases\/phase10\/?$/.test(new URL(link.href, location.href).pathname));
    if (phase10Link) {
      phase10Link.classList.remove("frontier-link");
      const phase10Era = phase10Link.closest(".era");
      const heading = phase10Era?.querySelector("h2");
      if (heading && !phase10Era.querySelector('[href*="phase10r"]')) heading.textContent = "Temporal metric perception";
    }

    const phase10rLink = Array.from(map.querySelectorAll(".phase-link")).find(link => /\/phases\/phase10r\/?$/.test(new URL(link.href, location.href).pathname));
    if (phase10rLink) {
      phase10rLink.classList.add("frontier-link");
      const era = phase10rLink.closest(".era");
      const heading = era?.querySelector("h2");
      if (heading) heading.textContent = "Phase 10R holdout";
      return;
    }

    const era = document.createElement("section");
    era.className = "era";
    era.id = "phase10rArchiveEra";
    era.innerHTML = `
      <header><span>05</span><h2>Phase 10R holdout</h2></header>
      <div class="track">
        <a class="phase-link frontier-link" href="${FRONTIER_URL}">
          <span>Phase 10R · Frozen holdout</span>
          <strong>Mean error improved, but the hard cases still failed the locked checks.</strong>
          <small>Mixed / failed overall · frozen without retuning</small>
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
    if (heroKicker) heroKicker.textContent = "Phase 10 · frozen earlier result";
    const overviewLabel = document.querySelector("#phaseOverviewVisual figcaption strong");
    if (overviewLabel) overviewLabel.textContent = "Earlier frozen result";

    const next = document.getElementById("nextPhase");
    if (next) {
      next.href = FRONTIER_URL;
      next.innerHTML = "<span>Next experiment</span><strong>Phase 10R · Frozen holdout</strong><i>→</i>";
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
        <p class="kicker">Why this project exists</p>
        <h2 id="programGoalTitle">Know when the estimate is not good enough.</h2>
        <p>The project keeps asking the same practical question in different ways: when should the landing system believe its own estimate, and when should it stop? Each phase changes one piece of that problem, records what broke, and leaves the result in place.</p>
      </div>
      <div class="program-pillars" aria-label="AegisLand research priorities">
        <div><span>01</span><strong>Compare confidence with measured error</strong></div>
        <div><span>02</span><strong>Stop or abstain when evidence gets weak</strong></div>
        <div><span>03</span><strong>Keep failed tests in the record</strong></div>
        <div><span>04</span><strong>Change one question at a time</strong></div>
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
      badge.innerHTML = "<span>Frozen Phase 10R result</span><strong>Phase 10R · Frozen holdout</strong>";
      copy.prepend(badge);
    }
    const kicker = copy?.querySelector(":scope > .kicker");
    if (kicker) kicker.textContent = "Protected holdout · frozen without retuning";

    const object = hero.querySelector(".object");
    if (object) {
      object.className = "object signature-visual signature-phase10 signature-phase10r";
      object.removeAttribute("aria-hidden");
      object.setAttribute("role", "img");
      object.setAttribute("aria-label", "Phase 10R frozen holdout reliability result");
      object.innerHTML = `
        <div class="frontier-topline"><span>PHASE 10R RESULT</span><strong>FROZEN HOLDOUT</strong></div>
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
        <div class="frontier-foot"><span>Average error improved strongly</span><strong>The tail and coverage gates still failed.</strong></div>`;
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
