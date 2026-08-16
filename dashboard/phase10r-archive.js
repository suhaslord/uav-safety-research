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
    if (!map || document.getElementById("phase10rArchiveEra")) return;

    const big = document.querySelector(".index-hero .big");
    if (big) big.textContent = "From early supervisory safety experiments through PX4/Gazebo camera evidence, temporal metric perception, and the final Phase 10R frozen holdout. Positive results, mismatches, failed gates, and the naming gap all stay visible.";

    const era = document.createElement("section");
    era.className = "era";
    era.id = "phase10rArchiveEra";
    era.innerHTML = `
      <header><span>04</span><h2>Current frontier</h2></header>
      <div class="track">
        <a class="phase-link" href="${FRONTIER_URL}">
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

  function patchPhase10Next() {
    const phase = document.body.dataset.signaturePhase || location.pathname.match(/phase\d+[a-z]?/i)?.[0]?.toLowerCase();
    if (phase !== "phase10") return;
    const next = document.getElementById("nextPhase");
    if (!next) return;
    next.href = FRONTIER_URL;
    next.innerHTML = "<span>Latest published frontier</span><strong>Phase 10R · Frozen holdout</strong><i>→</i>";
  }

  function install() {
    patchHeader();
    patchIndex();
    patchRail();
    patchPhase10Next();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => requestAnimationFrame(install), {once:true});
  else requestAnimationFrame(install);
})();
