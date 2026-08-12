(() => {
  const header = document.getElementById("siteHeader");
  if (!header) return;

  let queued = false;

  function sectionUnderHeader() {
    const sections = [...document.querySelectorAll("main .viewport-section")];
    if (!sections.length) return null;

    const headerRect = header.getBoundingClientRect();
    const probeY = Math.min(window.innerHeight - 1, Math.max(1, headerRect.bottom + 2));

    for (const section of sections) {
      const rect = section.getBoundingClientRect();
      if (rect.top <= probeY && rect.bottom > probeY) return section;
    }

    let best = null;
    let bestDistance = Infinity;
    for (const section of sections) {
      const rect = section.getBoundingClientRect();
      const distance = Math.min(Math.abs(rect.top - probeY), Math.abs(rect.bottom - probeY));
      if (distance < bestDistance) {
        bestDistance = distance;
        best = section;
      }
    }
    return best;
  }

  function syncHeaderSurface() {
    queued = false;
    const section = sectionUnderHeader();
    const dark = Boolean(section?.classList.contains("dark"));
    header.classList.toggle("on-dark", dark);
    header.dataset.surface = dark ? "dark" : "light";
    header.dataset.section = section?.id || (section?.classList.contains("hero") ? "hero" : "section");
  }

  function scheduleHeaderSync() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(syncHeaderSurface);
  }

  function enhanceLineage() {
    const source = document.querySelector(".lineage-list");
    if (!source || source.dataset.enhanced === "true") return;

    const items = [...source.children].filter(node => node.tagName === "LI");
    if (items.length < 11) return;

    const eras = [
      {
        number: "01",
        title: "Foundation",
        description: "Protocol through the frozen V1–V3 supervisor evolution.",
        items: items.slice(0, 4)
      },
      {
        number: "02",
        title: "Perception + robustness",
        description: "Stress testing, image perception, and the frozen Phase 6B study.",
        items: items.slice(4, 7)
      },
      {
        number: "03",
        title: "External validation",
        description: "Development stress, trace validation, and genuine PX4/Gazebo evidence.",
        items: items.slice(7, 10)
      },
      {
        number: "04",
        title: "Current frontier",
        description: "Phase 9 camera evidence remains draft, seen, and explicitly non-safety-accepted.",
        items: items.slice(10, 11),
        current: true
      }
    ];

    const map = document.createElement("div");
    map.className = "lineage-map";
    map.setAttribute("aria-label", "AegisLand research lineage by era");

    eras.forEach(era => {
      const section = document.createElement("section");
      section.className = `lineage-era${era.current ? " lineage-era-current" : ""}`;

      const heading = document.createElement("div");
      heading.className = "lineage-era-heading";
      heading.innerHTML = `<span>${era.number}</span><h3>${era.title}</h3><p>${era.description}</p>`;

      const list = document.createElement("ol");
      list.className = "lineage-era-list";
      list.style.setProperty("--era-count", String(Math.max(1, era.items.length)));
      era.items.forEach(item => list.appendChild(item));

      section.append(heading, list);
      map.appendChild(section);
    });

    source.dataset.enhanced = "true";
    source.replaceWith(map);
  }

  function buildMobileMenu() {
    if (document.querySelector(".mobile-menu-toggle")) return;

    const toggle = document.createElement("button");
    toggle.className = "mobile-menu-toggle";
    toggle.type = "button";
    toggle.textContent = "Menu";
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-controls", "mobileMenuSheet");
    header.appendChild(toggle);

    const sheet = document.createElement("nav");
    sheet.className = "mobile-menu-sheet";
    sheet.id = "mobileMenuSheet";
    sheet.setAttribute("aria-label", "Mobile navigation");
    sheet.innerHTML = `
      <div class="mobile-menu-head">
        <span class="mobile-menu-brand">AEGISLAND</span>
        <button class="mobile-menu-close" type="button" aria-label="Close menu">Close</button>
      </div>
      <div class="mobile-menu-primary">
        <a href="#result">Result</a>
        <a href="#telemetry">Telemetry</a>
        <a href="#geometry">Geometry</a>
        <a href="#timeline">Lineage</a>
        <a href="#provenance">Provenance</a>
      </div>
      <div class="mobile-menu-secondary">
        <a href="https://github.com/suhaslord/uav-safety-research" target="_blank" rel="noreferrer">GitHub</a>
        <a href="https://www.linkedin.com/in/suhas-beemineni-1984763b8/" target="_blank" rel="noreferrer">LinkedIn</a>
        <a href="phase7.html">Phase 7</a>
        <button type="button" data-mobile-status>Status</button>
      </div>`;
    document.body.appendChild(sheet);

    const closeButton = sheet.querySelector(".mobile-menu-close");
    const mobileStatus = sheet.querySelector("[data-mobile-status]");
    const desktopStatus = document.getElementById("refreshStatus");

    const setOpen = open => {
      sheet.classList.toggle("is-open", open);
      document.body.classList.toggle("mobile-menu-open", open);
      toggle.setAttribute("aria-expanded", String(open));
      if (open) {
        requestAnimationFrame(() => closeButton?.focus());
      } else {
        toggle.focus({preventScroll: true});
      }
    };

    toggle.addEventListener("click", () => setOpen(!sheet.classList.contains("is-open")));
    closeButton?.addEventListener("click", () => setOpen(false));
    sheet.querySelectorAll("a").forEach(link => link.addEventListener("click", () => setOpen(false)));
    mobileStatus?.addEventListener("click", () => {
      desktopStatus?.click();
      setOpen(false);
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && sheet.classList.contains("is-open")) setOpen(false);
    });
    window.matchMedia("(min-width: 768px)").addEventListener("change", event => {
      if (event.matches && sheet.classList.contains("is-open")) setOpen(false);
    });
  }

  window.addEventListener("scroll", scheduleHeaderSync, {passive: true});
  window.addEventListener("resize", scheduleHeaderSync, {passive: true});
  window.addEventListener("load", syncHeaderSurface, {once: true});
  document.addEventListener("DOMContentLoaded", () => {
    syncHeaderSurface();
    enhanceLineage();
    buildMobileMenu();
    setTimeout(syncHeaderSurface, 0);
    setTimeout(syncHeaderSurface, 120);
  }, {once: true});
})();