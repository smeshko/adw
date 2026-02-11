# Appendix: Design Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Layout model | Hub-and-spoke (no sidebar) | Content-first; simpler navigation; fewer elements competing for attention |
| Projects page | No dedicated page (filter mechanism) | Project data already surfaces via filtering on Overview, Runs List, and Analytics |
| Separate Runs List | Yes | Enables full filtering, sorting, and pagination that the overview preview can't support |
| Separate Analytics | Yes | Dense enough to warrant its own page; overview shows a compact preview strip |
| Phase accordion lazy-loading | Yes | Keeps Run Detail initial load fast; most users only expand 1-2 phases |
| CSS-only charts | Yes | No JS charting library needed; bar charts are simple enough for CSS; aligns with zero-JS-build philosophy |
| Keyboard shortcuts | Minimal inline JS | ~30 lines; the only client-side JS beyond HTMX and theme toggle; developer audience expects keyboard navigation |
| Run comparison | Post-MVP | PRD confirms deferral; complex UI that can be added without restructuring existing pages |
| Budget alerts | MVP but deferrable | PRD flags as first-to-cut; section is self-contained and can be added later |
| Light/dark theme toggle | MVP | PRD FR46; dark default with light option; DaisyUI makes this trivial |

---

*UX Design Specification completed on 2026-02-10.*
*Covers: Overview, Run Detail, Runs List, Cost & Token Analytics, New Run Flow, Global Elements.*
*PRD reference: 50 FRs, 28 NFRs across 9 capability areas.*
