(() => {
  'use strict';
  const root = document.querySelector('[data-vase-evidence]');
  if (!root) return;

  const buttons = [...root.querySelectorAll('[data-evidence-button]')];
  const panels = [...root.querySelectorAll('[data-evidence-panel]')];
  const activate = (track, focus = false) => {
    const button = buttons.find((item) => item.dataset.evidenceButton === track);
    if (!button) return;
    buttons.forEach((item) => {
      const selected = item === button;
      item.setAttribute('aria-pressed', String(selected));
      if (focus && selected) item.focus();
    });
    panels.forEach((panel) => { panel.hidden = panel.dataset.evidencePanel !== track; });
  };

  buttons.forEach((button, index) => {
    button.addEventListener('click', () => activate(button.dataset.evidenceButton));
    button.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const next = event.key === 'Home' ? 0
        : event.key === 'End' ? buttons.length - 1
        : (index + (event.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length;
      activate(buttons[next].dataset.evidenceButton, true);
    });
  });

  activate('vision');
})();
