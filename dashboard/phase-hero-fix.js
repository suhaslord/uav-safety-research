(() => {
  const MOBILE_MAX = 767;
  const OVERRIDES = [
    ["position", "relative"], ["inset", "auto"], ["right", "auto"], ["bottom", "auto"],
    ["width", "100%"], ["max-width", "none"], ["min-height", "280px"], ["aspect-ratio", "auto"],
    ["opacity", "1"], ["margin", "0"], ["padding", "10px 0 4px"], ["transform", "none"],
    ["overflow", "hidden"], ["pointer-events", "auto"]
  ];
  const properties = OVERRIDES.map(([name]) => name).concat(["display"]);

  function apply() {
    const visual = document.querySelector("#phaseHero .signature-visual");
    if (!visual) return;
    if (window.innerWidth <= MOBILE_MAX) {
      for (const [name, value] of OVERRIDES) visual.style.setProperty(name, value, "important");
      if (visual.classList.contains("signature-phase10")) {
        visual.style.setProperty("display", "grid", "important");
        visual.style.setProperty("min-height", "0", "important");
        visual.style.setProperty("padding", "18px", "important");
      } else {
        visual.style.setProperty("display", "flex", "important");
      }
    } else {
      for (const name of properties) visual.style.removeProperty(name);
    }
  }

  let raf = 0;
  const schedule = () => {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(apply);
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", schedule, {once: true});
  else schedule();
  window.addEventListener("resize", schedule, {passive: true});
})();
