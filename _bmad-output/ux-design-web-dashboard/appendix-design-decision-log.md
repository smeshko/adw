# Appendix: Design Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Layout model | Hub-and-spoke (no sidebar) | Content-first; simpler navigation; fewer elements competing for attention |
| Projects page | No dedicated page (filter mechanism) | Project data already surfaces via filtering on Overview, Runs List, and Analytics |
| Separate Runs List | Yes | Enables full filtering, sorting, and pagination that the overview preview can't support |
| Separate Analytics | Yes | Dense enough to warrant its own page; overview shows a compact preview strip |
| Phase accordion lazy-loading | Yes | Keeps Run Detail initial load fast; most users only expand 1-2 phases |
| CSS-only charts | Yes | No JS charting library needed; bar charts are simple enough for CSS; aligns with zero-JS-build philosophy |
| Keyboard shortcuts | Minimal inline JS | ~250 lines; supports chord sequences, terminal/focus mode, row navigation; developer audience expects keyboard navigation |
| Run comparison | Post-MVP | PRD confirms deferral; complex UI that can be added without restructuring existing pages |
| Budget alerts | MVP but deferrable | PRD flags as first-to-cut; section is self-contained and can be added later |
| Light/dark theme toggle | MVP | PRD FR46; brutalist-dark default with light option; DaisyUI makes this trivial |
| Visual identity | Industrial Brutalist Dark | Matches the raw, deterministic nature of the tool. Zero radius, harsh borders, offset shadows create a premium developer-tool aesthetic |
| Typography | Dual monospace (Azeret Mono display + Inconsolata body) | All-monospace reinforces the developer-native feel. Azeret Mono provides visual weight for labels/headings while Inconsolata handles readability for data |
| Shadows | Hard-edged offset (4px 4px 0) in accent red | Brutalist depth cue. Grows on hover to create physical "lift" metaphor. Never blurred. |
| Color scheme | Dark void (#111) + cream (#E8E4DF) borders + red (#C43018) accents | Maximum contrast. Cream-on-void creates "charcoal steel" industrial feel |
| Noise texture | SVG fractal noise at 3% opacity | Adds film-grain rawness without performance cost. Uses inline SVG data URI |
| Section headers | `//` prefix in accent red | References code comments. Reinforces developer aesthetic |
| Badge style | Outline only (transparent bg) | Cleaner than filled badges on dark backgrounds. 2px border provides structure |
| DaisyUI integration | Custom theme via `[data-theme]` selector | Preserves all DaisyUI component semantics while overriding visual appearance. Single CSS file. |
| Terminal Mode | Full-screen log view (key: t) | Power users want raw log output. Hides chrome for immersive monitoring |
| Focus Mode | Pipeline + timer + log (key: f) | Distraction-free active run monitoring. Shows only what matters during execution |
| Phase timeline | Custom CSS (not DaisyUI steps) | DaisyUI steps too limited for the brutalist treatment with colored top borders and status-dependent backgrounds |
| Analytics charts | CSS-only (conic-gradient donut, flex bars, grid heatmap) | Zero JS charting libraries. Brutalist aesthetic benefits from simple geometric shapes |

---

*UX Design Specification updated on 2026-02-12.*
*Covers: Overview, Run Detail, Runs List, Cost & Token Analytics, New Run Flow, Global Elements.*
*PRD reference: 50 FRs, 28 NFRs across 9 capability areas.*
*Updated to reflect Industrial Brutalist Dark design migration from default DaisyUI dark theme.*
