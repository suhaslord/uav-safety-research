---
name: AegisLand Homepage
description: Image-led research chapters with a restrained neutral interface.
colors:
  action: "#3e6ae1"
  action-hover: "#3457b8"
  ink: "#171a20"
  body: "#393c41"
  muted: "#5c5e62"
  white: "#fff"
  ash: "#f4f4f4"
  control: "#e8e8e8"
  divider: "#dedfe2"
typography:
  display:
    fontFamily: '"Helvetica Neue", Arial, Helvetica, sans-serif'
    fontSize: "clamp(44px, 4.5vw, 64px)"
    fontWeight: 500
    lineHeight: 1.06
    letterSpacing: "-.025em"
  headline:
    fontFamily: '"Helvetica Neue", Arial, Helvetica, sans-serif'
    fontSize: "clamp(32px, 3.5vw, 48px)"
    fontWeight: 500
    lineHeight: 1.12
    letterSpacing: "-.025em"
  body:
    fontFamily: '"Helvetica Neue", Arial, Helvetica, sans-serif'
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.65
  action:
    fontSize: "14px"
    fontWeight: 600
  fine:
    fontSize: "12px"
    lineHeight: 1.5
rounded:
  flat: "0"
  control: "4px"
spacing:
  compact: "8px"
  control: "12px"
  gutter: "20px"
  block: "24px"
  wide: "32px"
  chapter-gap: "48px"
  mobile-section: "64px"
components:
  button-primary:
    backgroundColor: "{colors.action}"
    textColor: "{colors.white}"
    typography: "{typography.action}"
    rounded: "{rounded.control}"
    padding: "12px 20px"
  button-primary-hover:
    backgroundColor: "{colors.action-hover}"
  button-secondary:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    typography: "{typography.action}"
    rounded: "{rounded.control}"
    padding: "12px 20px"
  button-secondary-hover:
    backgroundColor: "{colors.control}"
  condition-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.white}"
    rounded: "{rounded.control}"
  condition-unselected:
    backgroundColor: "{colors.control}"
    textColor: "{colors.body}"
    rounded: "{rounded.control}"
---

# Design System: AegisLand Homepage

## Overview

**Creative North Star: "Tesla's image-led research chapters"**

The user-pinned Tesla reference establishes centered, spacious composition, full-bleed imagery, neutral typography, and simple rectangular actions. AegisLand retains its identity, research language, working evidence controls, and explicitly attributed NASA context media.

This is a record of the shipped homepage, not a replacement system for the working prototype or archived research surfaces. Ground truth is `deploy/vercel/index.html` and its stylesheet cascade: the homepage-specific `tesla-home.css` wins through scope and specificity while the final linked `tesla-editorial.css` continues to style the prototype separately. The opening direction contract records the pinned reference override (seed `8f1be4a2`).

**Key Characteristics:**
- Full-width media chapters with centered foreground copy.
- White navigation and open research sections with a pale comparison surface.
- Small-radius controls, flat containers, and clear evidence annotations.
- Visible source attribution, caveats, focus states, and individual film controls.

## Colors

The palette pairs neutral surfaces and text with a blue action accent; camera overlays retain their independent measurement colors.

### Primary
- **Action Blue:** Primary actions, recurring research links styled as buttons, and keyboard focus.
- **Action Blue Hover:** Darker response for those actions.

### Neutral
- **Ink:** Headings, selected condition controls, and dark media backing.
- **Body:** Supporting research text and understated links.
- **Muted:** Caveats, archive descriptions, denominators, and footer text and links.
- **White:** Navigation and open sections; foreground text and secondary actions on media.
- **Ash:** Comparison-section surface and navigation hover.
- **Control:** Unselected condition controls and secondary-action hover.
- **Divider:** Measurement and status separation rather than decorative card outlines.

**The Evidence Color Rule.** Camera annotation, matched-box, and unmatched-box colors keep their existing semantic meaning and legend labels; action blue does not replace them.

Footer text and links explicitly use the muted color with homepage-specific priority. This resolves the inherited pale footer colors; muted on white was verified at 6.50:1 contrast.

## Typography

**Display and Body Font:** Helvetica Neue with Arial, Helvetica, and sans-serif fallbacks. The shared display and body stack is an approved adaptation to the user-pinned Tesla reference, which takes precedence over the general craft-floor preference against system display faces. Preserve this choice for future work within the homepage system.

**Character:** Medium-weight headings with tight tracking and balanced wraps sit above small, plain supporting copy. The ramp is fluid rather than a fixed modular ratio.

### Hierarchy
- **Display:** The frontmatter display role describes the hero. At the mobile breakpoint it becomes `clamp(36px, 8vw, 52px)`.
- **Headline:** The recurring question, finding, and archive headings use the headline role. The question heading becomes `clamp(30px, 6vw, 40px)` on mobile; other chapter headings retain their source-specific fluid sizes.
- **Body:** Research paragraphs use the body role. Media decks use the same size with a tighter leading (1.5); the hero deck becomes smaller (15px) on mobile. Research copy commonly stops at 68ch; the hero deck stops at 62ch and 44ch on mobile.
- **Action:** Buttons and desktop navigation use the action role. Header links reduce to 13px at the compact desktop breakpoint; hero actions reduce to 12px on mobile.
- **Fine:** Caveats and footer copy use small supporting text. Media captions use 11px, reducing to 10px on mobile, with leading (1.5).

## Layout

The fixed white header is 56px tall, with matching main-content offset and scroll padding. Its desktop grid is `1fr auto 1fr`. The shared content width is `min(1200px, calc(100% - 64px))`; full-bleed media chapters escape that container. Content sections center their copy and leave generous open space instead of enclosing each argument in a card.

Media chapters use viewport-aware minimum heights: hero `max(640px, calc(100svh - 56px))`, question `max(680px, calc(100svh - 56px))`, and second film `max(700px, calc(100svh - 56px))`. Paired hero actions remain a two-column grid capped at 560px. Findings use two open figures capped at 680px. Camera panels retain two columns, even on narrow screens; method steps use three columns on desktop.

At 1100px and below, navigation tightens to `auto 1fr auto`, with smaller padding and text. At 768px and below, desktop navigation hides, the independent fixed Menu control appears, and content gutters become 20px. The hero minimum rises to 720px and the question to 800px; the hero footage crop moves to `72% center`. Chapter padding reduces to 64px, film copy uses mobile gutters, and method steps become a single column with a 40px gap. At 600px and below, inherited condition controls form a horizontal scrolling row. Existing unrelated legacy breakpoints are not a homepage scale to copy.

**The Paired Evidence Rule.** Baseline and Phase 23 remain adjacent and comparable; narrow screens retain the pair and compact its labels and metrics.

## Elevation & Depth

The homepage is flat: navigation, actions, media frames, findings, and model containers have no decorative shadows. Full-bleed images and films supply depth. A shared dark gradient keeps white copy and attribution readable: `linear-gradient(180deg, rgb(0 0 0 / 65%), rgb(0 0 0 / 55%) 40%, rgb(0 0 0 / 12%) 58%, rgb(0 0 0 / 80%))`. Foreground copy, source captions, and pause controls occupy separate layers without intercepting unrelated pointer interactions.

**The Media Legibility Rule.** Context media retains its dark foreground treatment, visible attribution, and evidence-boundary caption when used behind text.

## Shapes

Full-bleed media, open findings, method containers, and archive links use flat geometry. Buttons, condition controls, camera frames, and pause controls share the small control radius. Status information uses a light top divider rather than a filled box or accent stripe.

## Components

### Buttons
Rectangular, compact, and centered. Primary actions use action blue on white text; secondary actions use white on ink. Both use the frontmatter control radius and padding, with minimum touch height (44px). Hero actions fill their grid columns. Research-summary and audit actions use wider horizontal padding (24px). Hover changes fill; focus uses an action-blue outline (3px) offset by 4px. Existing action transitions change background, text, and border colors over 180ms with `ease`, without hover movement.

### Condition Controls
Six existing camera conditions use small-radius rectangular buttons. Selected conditions are ink on white text; unselected conditions use the control fill and body text, becoming `#ddd` on hover. They expose `aria-pressed`, retain loading-disabled behavior, and have minimum touch height (44px). They are condition selectors rather than decorative chips.

### Camera Comparison and Checkbox
Open model containers carry a label/verdict header, clipped camera image, overlay layer, and three compact metrics. The camera preserves its original aspect ratio (`1052/961`) and uses `object-fit: contain`, so evidence is not cropped. The legend retains annotation, matched, and unmatched encodings. Its real checkbox toggles boxes, uses a 15px square and a minimum-height label (44px), and inherits the homepage action accent through the overridden editorial variable. Loading text, measurement disclosure, and complete-evidence links remain part of the component.

### Navigation and Footer
The opaque fixed header preserves the AegisLand mark and wordmark. Links use small-radius ash hover and visible keyboard focus. Mobile navigation is an existing full-screen sheet with a separate Menu control; its established open/close behavior remains. Footer content is centered on white, muted text and links share the same accessible color, and link hit areas retain minimum height (44px).

### Context Films
The original aircraft and wind-tunnel footage remains muted, looping, and inline, with an independently labeled Play/Pause button for each figure. Attribution is placed at the lower left and playback control at the lower right. Automatic playback requires at least 20% visibility and pauses offscreen or when the document hides. Reduced-motion and save-data preferences suppress automatic playback; explicit play remains available. Playback failure exposes native controls. Reduced motion also disables homepage transitions and smooth scrolling.

## Do's and Don'ts

### Do:
- **Do** use the scoped homepage cascade as the source of truth for this surface.
- **Do** retain source attribution and evidence caveats beside context media and measurements.
- **Do** preserve paired camera evidence, semantic overlay colors, focus outlines, and film controls.
- **Do** use open sections and small-radius actions with generous chapter spacing.

### Don't:
- **Don't** propagate homepage overrides into the working prototype or archived research UI.
- **Don't** crop recorded camera evidence to imitate the full-bleed context-media treatment.
- **Don't** infer design tokens from overridden legacy declarations or screenshot capture artifacts.

Not canonized: the inherited uppercase overline/hypothesis labels remain preserved build evidence rather than a reusable style for new labels; the full-page capture's mid-page fixed header is a screenshot artifact, not layout guidance. The approved display font stack is part of the homepage system.
