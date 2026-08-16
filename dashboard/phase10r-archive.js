(() => {
  const FRONTIER_URL = "/phases/phase10r/";
  const REPO_URL = "https://github.com/suhaslord/uav-safety-research";

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
      if (heading) heading.textContent = "Temporal metric perception";
    }

    if (document.getElementById("phase10rArchiveEra")) return;
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
    if (!rail || rail.querySelector('[href="/phases/phase10r/"]')) return;
    const step = document.createElement("a");
    step.className = "rail-step frontier";
    step.href = FRONTIER_URL;
    step.setAttribute("aria-current", "false");
    step.innerHTML = "<span>12</span><i></i><strong>Phase 10R\nFrozen holdout</strong>";
    rail.appendChild(step);
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

  function install() {
    patchHeader();
    patchIndex();
    patchRail();
    patchPhase10();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => requestAnimationFrame(install), {once:true});
  else requestAnimationFrame(install);
})();
