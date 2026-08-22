# Visual Bugs Report - AegisLand Research Cockpit

## Summary
This report documents visual bugs observed on the AegisLand Research Cockpit website at both desktop (1280x800) and mobile (iPhone XR - 414x896) viewports.

## Pages Tested
1. Homepage: https://aegisland-research-cockpit.vercel.app/
2. Phase 11 Page: https://aegisland-research-cockpit.vercel.app/phases/phase11/

## Screenshots Captured
- `homepage-desktop.png` - Desktop view of landing page
- `homepage-mobile.png` - Mobile view of landing page
- `phase11-desktop.png` - Desktop view of Phase 11 page
- `phase11-mobile.png` - Mobile view of Phase 11 page

---

## HOMEPAGE VISUAL BUGS

### Desktop View (1280x800)

#### 1. Header Logo Overlap Issue
**Severity:** Medium
**Location:** Top-left header
**Description:** The "AEGISLAND" text logo in the header appears to have decorative geometric shapes (gray triangular/rectangular elements) that are positioned in the top-left corner. These shapes appear to be purely decorative but lack clear purpose and create visual clutter.

#### 2. Hero Card Positioning
**Severity:** Low
**Location:** Main content area (left side)
**Description:** The white hero card containing "AegisLand" branding and action buttons is positioned on the left side of the viewport, leaving a large asymmetric layout with the rotated 3D geometric visualization taking up most of the right side and center. The layout feels unbalanced.

#### 3. 3D Visualization Rotation/Transform
**Severity:** Low
**Location:** Center-right of page
**Description:** The large black and gray geometric 3D visualization is heavily rotated/transformed, which while potentially intentional for visual interest, makes it difficult to understand what the shapes represent. The rotation appears arbitrary.

#### 4. Bottom Text Truncation
**Severity:** Medium
**Location:** Bottom of viewport
**Description:** Text at the bottom reads "Phase 9", "external_perception_seen", "safety acceptance: false" and "Current CI green - evidence frozen". This information appears cut off at the bottom of the fold, with text continuing below "Phase 9 camera target" and "visual motif: raw evidence remains traceable below". The text is partially hidden and requires scrolling to see fully.

#### 5. Status Dropdown Alignment
**Severity:** Low
**Location:** Top-right navigation
**Description:** The "Status" dropdown with down arrow appears in the navigation but doesn't align perfectly with other navigation items due to the dropdown indicator.

### Mobile View (iPhone XR - 414x896)

#### 1. Header Menu Button Spacing
**Severity:** Low
**Location:** Top-right header
**Description:** The "Menu" button in mobile view appears properly positioned but the header overall feels slightly cramped with "AEGISLAND" text taking up significant space.

#### 2. Hero Card Width
**Severity:** Low
**Location:** Main content area
**Description:** The hero card with "AegisLand" branding takes up appropriate mobile width, but the "Read protocol" button is a text link with lower visual hierarchy than the primary "Explore the result" button, which may confuse the content priority.

#### 3. 3D Visualization Mobile Scaling
**Severity:** Medium
**Location:** Below hero card
**Description:** The rotated 3D geometric visualization maintains its desktop rotation on mobile, causing it to take up excessive vertical space and making it difficult to parse the shapes. The rotation that works on desktop creates awkward negative space on mobile.

#### 4. Bottom Status Text Readability
**Severity:** Medium  
**Location:** Bottom of visualization
**Description:** The status text "Phase 9", "external_perception_seen", "safety acceptance: false", and "Current CI green - evidence frozen" is displayed in very small text below the 3D visualization, making it hard to read on mobile screens.

---

## PHASE 11 PAGE VISUAL BUGS

### Desktop View (1280x800)

#### 1. Navigation Tab Hover States Unclear
**Severity:** Low
**Location:** Main navigation (Result, Telemetry, Geometry, Lineage, Provenance)
**Description:** The navigation tabs appear as plain text links without visible borders, hover states, or clear indication of which tab is currently active. The "Result" tab appears to be active but lacks clear visual differentiation.

#### 2. Stats Grid Inconsistent Spacing
**Severity:** Medium
**Location:** Below hero section (Protected availability, Lateral 95% coverage, etc.)
**Description:** The four-column statistics grid showing percentages (98.53%, 96.17%, 95.82%, 94.63%) uses a light gray background but lacks clear visual separation between columns. The spacing feels uneven, and the grid blends into the background too much.

#### 3. Three-Column Cards Lack Borders
**Severity:** Medium
**Location:** "Three bounded changes define P14R" section
**Description:** The three cards showing "Bounded primary path", "Independent rescue", and "Robust uncertainty envelope" lack visible borders or shadows. They appear as plain text blocks with headings, making it difficult to distinguish them as separate card components. The lack of visual hierarchy makes the content hard to scan.

#### 4. Right Sidebar Content Box Styling
**Severity:** Low
**Location:** Right side - "Protected result" box
**Description:** The right sidebar shows "10 / 11 gate families", "Safety status: Not accepted", etc. in what appears to be a card, but it lacks clear borders or shadows to separate it from the main content. The boundary between sidebar and main content is unclear.

#### 5. Section Heading Hierarchy
**Severity:** Low
**Location:** Throughout page
**Description:** Section labels like "What changed", "Fresh seen transfer", "Protected boundary", and "Provenance" use a small, light gray font that lacks visual weight. These section headings blend into the body text and don't provide clear content hierarchy.

#### 6. Statistics Grid Label Alignment
**Severity:** Low
**Location:** "Availability recovered without giving up coverage" section
**Description:** The stats grid in this section shows labels like "Useful availability", "Lateral 95% coverage", etc. aligned to the left, with values on the right. However, the two-column layout creates uneven visual rhythm with some labels being much longer than others.

#### 7. Large Number Display (2.435×)
**Severity:** Low
**Location:** "One locked lateral-tail component" section
**Description:** The large "2.435×" statistic is displayed prominently but without sufficient context or visual styling to indicate what the multiplication factor represents. It appears isolated from its descriptive text "Lateral p95 interval width / p95 error".

### Mobile View (iPhone XR - 414x896)

#### 1. Header Logo/Menu Balance
**Severity:** Low
**Location:** Top header
**Description:** Similar to homepage, the "AEGISLAND" branding and "Menu" button compete for header space, with the logo taking significant width.

#### 2. Single Column Stack Spacing
**Severity:** Medium
**Location:** Main content area
**Description:** All content stacks into a single column on mobile, but the spacing between sections feels inconsistent. Some sections have generous padding while others feel cramped. The "View the evidence" and "Read final report" buttons have good spacing, but the stats sections below feel compressed.

#### 3. Statistics Grid Mobile Layout
**Severity:** Medium
**Location:** Stats sections (Protected availability, etc.)
**Description:** The four-column desktop stats grid doesn't adapt well to mobile. On the mobile view, the stats appear to stack vertically but maintain the same gray background, creating long blocks of gray that reduce readability and make the page feel monotonous.

#### 4. Right Sidebar Mobile Placement
**Severity:** Low
**Location:** "Protected result" section on mobile
**Description:** The right sidebar content ("10 / 11 gate families", "Safety status: Not accepted") moves below the main content on mobile, which is appropriate, but it maintains the same styling as desktop without adjusting for the narrower viewport. The section could benefit from better mobile-specific styling.

#### 5. Long Text Line Length
**Severity:** Medium
**Location:** Paragraph text throughout
**Description:** Some paragraph text maintains desktop line length on mobile, causing text to wrap in ways that reduce readability. The description under "Independent rescue + robust uncertainty transfer" has particularly long lines that are hard to read on a narrow screen.

#### 6. Button Group Responsiveness
**Severity:** Low
**Location:** "View the evidence" and "Read final report" buttons
**Description:** The two buttons maintain their side-by-side layout on mobile, which works acceptably but causes the buttons to be narrow. Stacking them vertically would improve touch target size and readability.

---

## COMMON ISSUES ACROSS PAGES

### 1. Typography Contrast
**Severity:** Medium
**Description:** Small text labels, section headings, and metadata (like "simulation-only research prototype", "Current research frontier", etc.) use light gray color that may not meet WCAG AA contrast requirements. This reduces readability, especially for users with visual impairments.

### 2. Hover/Focus States
**Severity:** Medium
**Description:** Interactive elements like navigation links, buttons, and links lack clear hover and focus states. This makes it difficult for keyboard users and reduces overall usability.

### 3. Card/Section Boundaries
**Severity:** Medium
**Description:** Throughout both pages, content sections and cards lack clear visual boundaries (borders, shadows, or background contrast). This makes it difficult to distinguish between different content blocks and reduces scannability.

### 4. Responsive Breakpoint Gaps
**Severity:** Medium
**Description:** The transition from desktop to mobile layout appears to use a single breakpoint. A tablet/medium breakpoint (768px-1024px) would help the layout adapt more gracefully across device sizes.

### 5. Status Indicator Consistency
**Severity:** Low
**Description:** Status indicators like "Phase 7", "Phase 9", "Phase 11" appear in various locations with different styling and prominence. A consistent status component would improve visual coherence.

---

## RECOMMENDATIONS SUMMARY

### High Priority
1. Improve color contrast for small text to meet WCAG AA standards
2. Add clear visual boundaries (borders/shadows) to cards and sections
3. Fix statistics grid spacing and mobile layout
4. Improve responsive typography and spacing for mobile views

### Medium Priority
1. Add hover and focus states to all interactive elements
2. Establish clearer visual hierarchy for section headings
3. Add tablet breakpoint for better responsive behavior
4. Improve 3D visualization mobile scaling and rotation

### Low Priority
1. Refine header logo and decorative element positioning
2. Enhance button group mobile layouts
3. Standardize status indicator styling
4. Adjust large number (2.435×) presentation with better context

---

## Testing Notes
- Screenshots captured on Linux desktop with 1280x800 viewport
- Mobile testing used Chrome DevTools device emulation (iPhone XR preset)
- Both pages tested on August 22, 2026
- Browser: Google Chrome (latest version)
- No animations or interactive states were tested in depth

