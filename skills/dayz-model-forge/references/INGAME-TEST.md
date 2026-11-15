# In-game test: checklist and symptom -> parameter

A clean log proves nothing, and neither does the Blender render. Only the game closes the loop.

## Checklist (male AND female)
1. Wear it from the inventory (right slot, no error in the `.RPT`).
2. Standing, front / side / back: the item rests on the body, neither floating nor clipping.
3. Crouch, go prone, run, aim, raise the arm: nothing tears, the shoulder pad follows the arm.
4. Texture and relief (normal map) visible. If the item looks "flat", the binarize ran outside `P:\`.
5. Inventory icon upright; the dropped item lies flat on the ground, not sinking.

## Symptom -> what to change

| symptom | likely cause | where |
|---|---|---|
| item too big / too small | fit scale | `s02_fit.py` (`GAP_MIN`, `ALLOW`) |
| the body clips through the item when standing | not enough push | `s03_skin.py` (`GAP`, `SIGMA`) |
| tears/stretches when the trunk bends | height bands | `weights_bands.py` (`BAND_Z`, `BAND`) |
| shoulder pad in front of / behind the arm | twist about the arm | calibrated automatically (BALANCE); change the target in `build_vest.py` |
| shoulder pad leaning (bottom forward/back) | tilt | `build_vest.py` `PAD_TILT_FIXED` (+ = bottom back) |
| shoulder pad flares like a wing with the arm down | too little arm weight | `weights_bands.py` `PAD_ARM_BLEND` |
| shoulder pad stays behind when the arm is raised | too little arm weight | `PAD_ARM_BLEND` |
| a strap clips through the biceps | vanilla arm is thicker | `s03_skin.py` (`ARM_SHIFT_MAX`, `ARM_PUSH_MAX`) |
| icon upside down / crooked | `_g` orientation | `mlod_write.py` (ground rotation, memory points) |
| item looks "flat", no relief | ODOL without material | binarize with cwd `P:\` |
| texture with static/noise | noisy normal map | `s05b_source_tex.py` (coherence threshold) |
| sleeve or hem torn into teeth (top) | push through space | already fixed: surface push in `s03_skin.py` (`KV_MODE=top`); check the BACK render |
| jacket looks like a man's on the female (top) | female fitted on its own | already fixed: `_f` comes from `_m` (`s02c_transfer.py`) |

Change ONE parameter per round, run `build_vest.py` again (~2 min per item) and repack. Compare the new render
with the in-game screenshot in the same framing.
