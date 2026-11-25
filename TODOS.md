# To do

Deferred on purpose. Each entry says why it waits.

## Planned releases
- **0.2**: post, slope, overhang-angle, corner (report only) and support checks; a file for recording intended exceptions; nozzle and layer-height settings; a worked example; the fix for overhangs that stick out past their two supports.
- **0.3**: a real slicer run with PrusaSlicer and OrcaSlicer.

## Later

### Photos in the evidence table
- **What:** a photo or log excerpt for each row of EVIDENCE.md.
- **Why:** "measured" is what sets this skill apart, and a photo makes it checkable.
- **Cost:** someone has to find or take the photos.
- **Depends on:** nothing.

### Agent evals for the skill text
- **What:** three fixed prompts, run with and without the skill, scored by the check command's report.
- **Why:** the tests cover the checks, not whether an agent that reads SKILL.md designs a part that passes.
- **Cost:** model usage on every run.
- **Depends on:** the 0.2 geometry checks.

### Starter helper library
- **What:** a small module of print-safe building blocks (posts, haunches, teardrop holes, anti-warp channels), each tested by the check command.
- **Why:** the skill's workflow asks for one and new users start with none.
- **Cost:** a second codebase to maintain.
- **Depends on:** the 0.2 geometry checks.

### Warning for posts under 4 mm or over 8 times their width
- **What:** a warning that anticipates the slicer's "thin fragile part" alert.
- **Why:** the skill states this tier and no geometry check covers it.
- **Cost:** needs a definition of "free-standing post" that does not fire on short wall stubs.
- **Depends on:** the 0.2 post check.

### Windows
- **What:** run the tests and the command on Windows.
- **Why:** untested today.
