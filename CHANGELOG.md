# Changelog

## 0.1.0 (2026-11-25)

First public version.

- The skill text: one bridge rule, the tested setup, angles measured from the bed, narrow fillets are not shallow roofs, a dated note on MakerWorld, and guidance for other printers and materials.
- `check.py`: one command, a verdict per part (FAIL, INCOMPLETE or PASS with exit codes 1, 2 and 0) and a JSON report.
- The layer check: features under 0.8 mm, outlines that start in mid-air, flat ledges over 2 mm, bridges over 30 mm, and a warning on ceilings over 12 mm.
- Limits in one file, with tables in SKILL.md generated from it.
- Installs as a Claude Code plugin.

Not yet automated: the post, slope, overhang-angle, corner, support and slicer checks.
