"""One command: Sketchfab-style zip/glb -> wearable DayZ item (MLOD _m/_f/_g + paa + rvmat) + proof renders.

python build_vest.py --config <mod>/forge.json --src <zip|glb> --name <prefix>_<name> [--kind vest|top|backpack]
                     [--meshes ALL] [--texture source|bake] [--work DIR]
python build_vest.py --config <mod>/forge.json --check-config     (resolve and check every path, then stop)

forge.json (one per mod, see ../config/forge.example.json) gives the machine tools, the vanilla rig/bodies and
where the mod wants the files. Empty "blender", "dayz_tools_bin" and "p_drive_real" are detected (see
load_config). Writes:
  <data_dir>/    <name>_{m,f,g}.p3d MLOD (the PBO tool binarizes them, with cwd P:\\), model.cfg (created from
                 ../templates/model_skeleton.cfg if missing, classes added), <name>_{co,nohq,smdi}.paa,
                 <name>{,_damage,_destruct}.rvmat
  <source_dir>/  textures/<name>_*.png, preview_<name>.png (renders rebuilt FROM the written p3d)
The binarize step here only VALIDATES: the ODOL stays in the work dir, never in the mod.
The config.cpp class is NOT written here (stats are a design decision): see CONFIG.md in the docs.
Docs (steps, conventions, measured lessons, in-game test, config): skills/dayz-model-forge/references/
at the plugin root (../../../skills/dayz-model-forge/references/ from this file).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(HERE, "..", "templates")
# filled from forge.json by load_config()
SOURCE = DATA = RIG = TEXP = BLENDER = TOOLS = IMAGE2PAA = BINARIZE = None
P_DRIVE, P_REAL = "P:\\", None


def detect_blender():
    """blender on PATH, else a default 'Blender Foundation' install (4.4 first: the tested version)."""
    found = shutil.which("blender")
    if found:
        return found
    for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        base = os.path.join(root or "", "Blender Foundation")
        if not root or not os.path.isdir(base):
            continue
        for d in ["Blender 4.4"] + sorted(os.listdir(base), reverse=True):
            exe = os.path.join(base, d, "blender.exe")
            if os.path.exists(exe):
                return exe
    return ""


def detect_dayz_tools():
    """'DayZ Tools\\Bin' in the Steam libraries (Steam root from the registry, libraries from libraryfolders.vdf)."""
    roots = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            roots.append(os.path.normpath(winreg.QueryValueEx(k, "SteamPath")[0]))
    except (ImportError, OSError):
        pass
    roots.append(os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Steam"))
    libs = []
    for r in roots:
        libs.append(r)
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        if os.path.exists(vdf):
            txt = open(vdf, encoding="utf-8", errors="replace").read()
            libs += [m.replace("\\\\", "\\") for m in re.findall(r'"path"\s+"([^"]+)"', txt)]
    for lib in libs:
        b = os.path.join(lib, "steamapps", "common", "DayZ Tools", "Bin")
        if os.path.isdir(b):
            return b
    return ""


def detect_p_real(p_drive):
    """the folder behind a subst-mounted P: drive ('subst' prints 'P:\\: => <folder>'); None if not subst."""
    try:
        out = subprocess.run(["subst"], capture_output=True, text=True, errors="replace").stdout
    except OSError:
        return None
    for line in out.splitlines():
        m = re.match(r"\s*([A-Za-z]):\\:\s*=>\s*(.+?)\s*$", line)
        if m and m.group(1).upper() == p_drive[:1].upper():
            return m.group(2)
    return None


def load_config(path, create_dirs=True):
    """Read forge.json and set the module paths. Relative paths are relative to the json file; %VARS% expand.
    Empty or missing "blender" / "dayz_tools_bin" / "p_drive_real" are detected on this machine."""
    global SOURCE, DATA, RIG, TEXP, BLENDER, TOOLS, IMAGE2PAA, BINARIZE, P_DRIVE, P_REAL
    if not os.path.exists(path):
        raise SystemExit("forge.json not found: %s (copy config/forge.example.json next to your mod)" % path)
    cfg = json.load(open(path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(path))

    def p(key):
        if key not in cfg:
            raise SystemExit("forge.json: missing key \"%s\" (see config/forge.example.json)" % key)
        v = os.path.expandvars(cfg[key])
        return os.path.normpath(v if os.path.isabs(v) else os.path.join(base, v))

    def p_or_detect(key, detect):
        return p(key) if cfg.get(key) else detect()

    mod_root = p("mod_root")
    DATA = os.path.normpath(os.path.join(mod_root, cfg["data_dir"]))
    SOURCE = os.path.normpath(os.path.join(mod_root, cfg["source_dir"]))
    RIG = p("rig_blend")
    BLENDER = p_or_detect("blender", detect_blender)
    TOOLS = p_or_detect("dayz_tools_bin", detect_dayz_tools)
    IMAGE2PAA = os.path.join(TOOLS, "ImageToPAA", "ImageToPAA.exe")
    BINARIZE = os.path.join(TOOLS, "Binarize", "binarize.exe")
    P_DRIVE = cfg.get("p_drive") or "P:\\"
    P_REAL = cfg.get("p_drive_real") or detect_p_real(P_DRIVE)
    os.environ["FORGE_BODY_MALE"] = p("body_male")
    os.environ["FORGE_BODY_FEMALE"] = p("body_female")
    for k, v in (("blender", BLENDER), ("rig_blend", RIG), ("ImageToPAA", IMAGE2PAA), ("binarize", BINARIZE),
                 ("body_male", os.environ["FORGE_BODY_MALE"]), ("body_female", os.environ["FORGE_BODY_FEMALE"]),
                 ("p_drive (mounted work drive)", P_DRIVE)):
        if not v or not os.path.exists(v):
            raise SystemExit("forge.json: %s not found: %s" % (k, v or "(not set and not detected)"))
    TEXP = cfg.get("pbo_path") or pbo_path_of(DATA, mod_root)
    if create_dirs:
        os.makedirs(DATA, exist_ok=True)
    print("config: data %s | pbo path %s | rig %s" % (DATA, TEXP, RIG))
    print("tools: blender %s | DayZ Tools %s | work drive %s%s" % (
        BLENDER, TOOLS, P_DRIVE, (" = subst of " + P_REAL) if P_REAL else ""))


def pbo_path_of(folder, stop):
    """PBO path of a folder = $PBOPREFIX$ of the PBO that contains it + the rest of the path (game paths use \\)."""
    d = os.path.normpath(folder)
    while True:
        f = os.path.join(d, "$PBOPREFIX$")
        if os.path.exists(f):
            prefix = open(f, encoding="utf-8").read().strip().strip("\\")
            rel = os.path.relpath(folder, d)
            return prefix if rel == "." else prefix + "\\" + rel.replace("/", "\\")
        if os.path.normcase(d) == os.path.normcase(os.path.normpath(stop)) or os.path.dirname(d) == d:
            raise SystemExit("no $PBOPREFIX$ above %s - set \"pbo_path\" in forge.json" % folder)
        d = os.path.dirname(d)


def to_p_drive(path):
    """binarize resolves materials only with cwd P:\\ and P: paths; map the subst target back to P:"""
    if P_REAL and os.path.normcase(path).startswith(os.path.normcase(os.path.normpath(P_REAL))):
        return os.path.join(P_DRIVE, os.path.relpath(path, P_REAL))
    return path


def run(cmd, cwd=None, check_out=None):
    print(">", " ".join(os.path.basename(c) if i == 0 else c for i, c in enumerate(cmd))[:220], flush=True)
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace")
    out = r.stdout + r.stderr
    if r.returncode != 0 or "Traceback" in out or (check_out and not re.search(check_out, out)):
        print(out[-4000:])
        raise SystemExit("step failed: %s" % cmd[:4])
    for line in out.splitlines():
        if re.match(r"(FIT|after|pads|PAD_IDLE|LOD ratio|wrote|normal map|PARITY|WARNING|co=|sleeve|reposed|scale estimate|ambient|pbr|subdivided|push it|body-driven|clearance|body shells|transfer|visible skin|atlas|size:|harness|bag top|hung|rigid bag|bag moved)", line.strip()):
            print("   ", line.strip()[:200])
    return out


def blender(script, *args, blend=None):
    cmd = [BLENDER, "-b"] + ([blend] if blend else []) + ["--python", os.path.join(HERE, script), "--"] + list(args)
    return run(cmd)


RVMAT = """ambient[]={1,1,1,1};
diffuse[]={1,1,1,1};
forcedDiffuse[]={0,0,0,0};
emmisive[]={0,0,0,1};
specular[]={0.32941177,0.32941177,0.32156864,1};
specularPower=20;
PixelShaderID="Super";
VertexShaderID="Super";
class Stage1
{
	texture="%(p)s\\%(n)s_nohq.paa";
	uvSource="tex";
	class uvTransform
	{
		aside[]={1,0,0};
		up[]={0,1,0};
		dir[]={0,0,0};
		pos[]={0,0,0};
	};
};
class Stage2
{
	texture="#(argb,8,8,3)color(%(dt)s,%(dt)s,%(dt)s,1,DT)";
	uvSource="tex";
	class uvTransform
	{
		aside[]={1,0,0};
		up[]={0,1,0};
		dir[]={0,0,0};
		pos[]={0,0,0};
	};
};
class Stage3
{
	texture="%(mc)s";
	uvSource="tex";
	class uvTransform
	{
		aside[]={1,0,0};
		up[]={0,1,0};
		dir[]={0,0,0};
		pos[]={0,0,0};
	};
};
class Stage4
{
	texture="#(argb,8,8,3)color(1,1,1,1,AS)";
	uvSource="tex";
	class uvTransform
	{
		aside[]={1,0,0};
		up[]={0,1,0};
		dir[]={0,0,0};
		pos[]={0,0,0};
	};
};
class Stage5
{
	texture="%(p)s\\%(n)s_smdi.paa";
	uvSource="tex";
	class uvTransform
	{
		aside[]={1,0,0};
		up[]={0,1,0};
		dir[]={0,0,0};
		pos[]={0,0,0};
	};
};
class Stage6
{
	texture="#(ai,64,64,1)fresnel(1,0.7)";
	uvSource="none";
};
class Stage7
{
	texture="dz\\data\\data\\env_land_co.paa";
	uvSource="tex";
	class uvTransform
	{
		aside[]={1,0,0};
		up[]={0,1,0};
		dir[]={0,0,0};
		pos[]={0,0,0};
	};
};
"""

MODELCFG_HEAD = """
class CfgModels
{
	class Default
	{
		sections[] = {};
		sectionsInherit = "";
		skeletonName = "";
	};
};
"""

MODELCFG_CLASSES = """	class %(n)s_m: Default
	{
		skeletonName = "DayzTemporarySkeleton";
		sections[] = {"camo"};
	};
	class %(n)s_f: Default
	{
		skeletonName = "DayzTemporarySkeleton";
		sections[] = {"camo"};
	};
	class %(n)s_g: Default
	{
		sections[] = {"camo"};
	};
"""


PAD_BACK_START = 15.0     # degrees; s03 rotates the pads back about the arm axis by this much past lateral
PAD_TOL_MM = 3.0          # stop when the pad sticks out the same in front of and behind the arm (+-3 mm)
PAD_TILT_TOL = 2.0        # (kept for the report) long axis vs arm in the side view
PAD_TILT_FIXED = 16.0     # bottom of the pad back, about its own centre: 3rd in-game test, the user's outline
                          # (pad parallel to the arm) vs the print = ~10 deg; 4th test: "a bit more" -> 16
PAD_MM_PER_DEG = 2.1      # first-step slope (~2 x pad radius 6 cm x 1 deg); later steps use the secant


def calibrate_pads(sx, work):
    """Run s03; if the vest has shoulder pads, tilt them by PAD_TILT_FIXED (bottom back, about the shell's own
    centre - a fixed design value from the 3rd in-game test) and calibrate only the twist about the arm axis so
    that, with the arm down (s09 'idle_game'), they stick out equally in front of and behind the visible arm.
    That balance measure matched the in-game tests of 03/10/2026: +76 mm 'in front', +42 'almost', +15/+18 still
    forward. The tilt measure did NOT match the game, so it is only reported."""
    fit = os.path.join(work, "fit_%s.blend" % sx)
    skin = os.path.join(work, "skin_%s.blend" % sx)
    state = {"back": PAD_BACK_START, "tilt": 0.0}
    runs = []

    def evaluate():
        os.environ["KV_PAD_BACK_DEG"] = "%.2f" % state["back"]
        os.environ["KV_PAD_TILT_DEG"] = "%.2f" % state["tilt"]
        out = blender("s03_skin.py", skin, blend=fit)
        if "pads left" not in out and "pads right" not in out:
            return None                                # no shoulder pads on this vest
        meas = blender("s09_pad_idle_angle.py", skin, sx, blend=RIG)
        bal = float(re.search(r"BALANCE_MM=(\S+)", meas).group(1))
        tl = float(re.search(r"TILT_DEG=(\S+)", meas).group(1))
        print("    pads %s: back %.1f deg, tilt %.1f deg -> balance %+.1f mm, tilt error %+.1f deg" % (
            sx, state["back"], state["tilt"], bal, tl))
        runs.append((dict(state), bal, tl))
        return bal, tl

    def solve(key, err_index, tol, first_slope, lo, hi):
        """1-D secant on one parameter while the other stays fixed (the joint 2-D update diverged)"""
        hist = []
        for _ in range(4):
            r = evaluate()
            if r is None:
                return None
            e = r[err_index]
            hist.append((state[key], e))
            if abs(e) <= tol:
                return r
            if len(hist) >= 2 and hist[-1][1] != hist[-2][1]:
                (x0, e0), (x1, e1) = hist[-2], hist[-1]
                nxt = x1 - e1 * (x1 - x0) / (e1 - e0)
            else:
                nxt = state[key] + e / first_slope
            state[key] = max(lo, min(hi, nxt))
        return evaluate()

    # TILT is a fixed design value, not calibrated: the emulated idle reproduces the in-game front/back
    # offset (balance) but NOT the in-game lean - its silhouette tilt read only +2.5/+4.8 deg on the file
    # whose in-game print (3rd test) showed ~10 deg, and a joint 2-D calibration diverged (03/10/2026).
    state["tilt"] = PAD_TILT_FIXED
    r = solve("back", 0, PAD_TOL_MM, PAD_MM_PER_DEG, -30.0, 75.0)
    if r is None or abs(r[0]) <= PAD_TOL_MM:
        return
    # not converged: keep the best run seen, never just the last one
    best = min(runs, key=lambda t: abs(t[1]))
    state.update(best[0])
    print("    pads %s: did not fully converge, using the best run %s" % (sx, best))
    evaluate()


def main():
    ap = argparse.ArgumentParser(
        description="3D model (.glb or Sketchfab .zip) -> wearable DayZ item: MLOD _m/_f/_g p3d, paa, rvmat, "
                    "model.cfg, a binarize check and proof renders. Windows + Blender 4.4 + DayZ Tools + P: drive.",
        epilog="Status: vest and top validated in-game; backpack ~90%; other item types not supported yet. "
               "Check the model's license before building. Docs: skills/dayz-model-forge/references/ at the plugin root (PIPELINE, LESSONS, INGAME-TEST, CONFIG).")
    ap.add_argument("--config", default="forge.json", help="the mod's forge.json (see ../config/forge.example.json)")
    ap.add_argument("--src", help="the source model: a .glb or the .zip downloaded from Sketchfab")
    ap.add_argument("--name", help="output file prefix, e.g. abc_platecarrier -> abc_platecarrier_m.p3d")
    ap.add_argument("--meshes", default="ALL", help="comma-separated mesh names to keep (default: ALL, joined)")
    ap.add_argument("--texture", choices=("source", "bake"), default="source",
                    help="source: the model's own maps (DayZ _co/_nohq/_smdi or glTF PBR). "
                         "bake: procedural camo for a model that came without textures")
    ap.add_argument("--kind", choices=("vest", "top", "backpack"), default="vest",
                    help="vest: rigid, height-band weights, shoulder pads. top: cloth with sleeves (jacket/shirt). "
                         "backpack: rigid bag on Spine3 + harness over the shoulders")
    ap.add_argument("--work", default=None, help="work dir for the intermediate .blend/.json/ODOL (default: a temp dir)")
    ap.add_argument("--check-config", action="store_true",
                    help="resolve and check every path in forge.json (tools, rig, bodies, work drive), then stop")
    a = ap.parse_args()
    if a.check_config:
        load_config(a.config, create_dirs=False)
        try:
            import PIL  # noqa: F401  (sheet.py, the preview contact sheet, runs in this Python)
        except ImportError:
            raise SystemExit("Pillow is missing in this Python: python -m pip install Pillow")
        print("config OK")
        return
    if not (a.src and a.name):
        ap.error("--src and --name are required (or use --check-config)")
    load_config(a.config)
    n = a.name
    work = a.work or tempfile.mkdtemp(prefix="vest_%s_" % n)
    os.makedirs(work, exist_ok=True)
    print("work dir:", work)
    texdir = os.path.join(SOURCE, "textures")
    os.makedirs(texdir, exist_ok=True)

    fm, ff = os.path.join(work, "fit_male.blend"), os.path.join(work, "fit_female.blend")
    sm, sf = os.path.join(work, "skin_male.blend"), os.path.join(work, "skin_female.blend")
    if a.kind == "backpack":
        print("[1] backpack on the vanilla male body (harness side to the body, hung on the shoulders, loop opened)")
        blender("s02d_place_backpack.py", fm, a.src, a.meshes)
        print("[2] harness pushed off the skin; bag rigid on Spine3, harness on the skin under it")
        os.environ["KV_MODE"] = "backpack"
        blender("s03_skin.py", sm, blend=fm)
        print("[2b] female: carried over from the male (the bag as one block, the harness on her skin)")
        blender("s02c_transfer.py", ff, blend=sm)
        blender("s03_skin.py", sf, blend=ff)
    elif a.kind == "top":
        # the female top is CARRIED OVER from the finished male one (s02c): fitted on its own with a uniform
        # scale it came out as a man's jacket on a woman, hem 8 cm high (in-game test 04/10/2026)
        print("[1] fit to the vanilla male body")
        blender("s02_fit.py", "male", fm, a.src, a.meshes)
        print("[1b] sleeves into the rig's A-pose (measure, pose the rig, copy skin weights, inverse skinning)")
        blender("s02b_repose.py", RIG, fm, "male", blend=fm)
        print("[2] anti-clip push off the whole body + weights copied from the skin")
        os.environ["KV_MODE"] = "top"
        blender("s03_skin.py", sm, blend=fm)
        print("[2b] female: the male garment carried over to the female body, then push + her skin weights")
        blender("s02c_transfer.py", ff, blend=sm)
        blender("s03_skin.py", sf, blend=ff)
    else:
        print("[1] fit to the vanilla bodies")
        for sx in ("male", "female"):
            blender("s02_fit.py", sx, os.path.join(work, "fit_%s.blend" % sx), a.src, a.meshes)
        print("[2] anti-clip push + weights (+ shoulder pad calibration in the emulated in-game idle)")
        os.environ["KV_MODE"] = "vest"
        for sx in ("male", "female"):
            calibrate_pads(sx, work)
    print("[3] textures (%s)" % a.texture)
    if a.texture == "source":
        blender("s05b_source_tex.py", a.src, os.path.join(work, "tex"), n)
    else:
        blender("s05_texture.py", os.path.join(work, "tex"), "2048", blend=os.path.join(work, "skin_male.blend"))
        for t in ("co", "nohq", "smdi"):
            shutil.copy(os.path.join(work, "tex", "bake_%s.png" % t), os.path.join(work, "tex", "%s_%s.png" % (n, t)))
    for t in ("co", "nohq", "smdi"):
        png = os.path.join(work, "tex", "%s_%s.png" % (n, t))
        shutil.copy(png, texdir)
        run([IMAGE2PAA, png, os.path.join(DATA, "%s_%s.paa" % (n, t))])
        if not os.path.exists(os.path.join(DATA, "%s_%s.paa" % (n, t))):
            raise SystemExit("ImageToPAA produced nothing for " + png)
    for suf, dt, mc in (("", "0.5", "#(argb,8,8,3)color(0,0,0,0,MC)"),
                        ("_damage", "0.4", r"dz\characters\vests\data\vests_damage_mc.paa"),
                        ("_destruct", "0.3", r"dz\characters\vests\data\vests_destruct_mc.paa")):
        open(os.path.join(DATA, n + suf + ".rvmat"), "w").write(RVMAT % {"p": TEXP, "n": n, "dt": dt, "mc": mc})
    print("[4] LODs + MLOD")
    os.environ["KV_INNER_SHELL"] = "1" if a.kind in ("top", "backpack") else "0"   # single-surface cloth/straps need their back side
    os.environ["KV_GROUND_BACK_UP"] = "1" if a.kind == "backpack" else "0"     # backpack on the ground: pockets up
    for sx in ("male", "female"):
        blender("s07_export.py", os.path.join(work, "lods_%s.json" % sx), blend=os.path.join(work, "skin_%s.blend" % sx))
    run([sys.executable, os.path.join(HERE, "mlod_write.py"), os.path.join(work, "lods_male.json"),
         os.path.join(work, "lods_female.json"), DATA, TEXP, n])
    mc = os.path.join(DATA, "model.cfg")
    if not os.path.exists(mc):                       # new mod: DayZ character skeleton + empty CfgModels
        sk = open(os.path.join(TEMPLATES, "model_skeleton.cfg"), encoding="utf-8").read()
        open(mc, "w", encoding="utf-8").write(sk.rstrip() + MODELCFG_HEAD)
    t = open(mc, encoding="utf-8").read()
    if "class %s_m:" % n not in t:
        i = t.rstrip().rfind("};")
        t = t[:i] + MODELCFG_CLASSES % {"n": n} + "};\n"
        open(mc, "w", encoding="utf-8").write(t)
    print("[5] binarize CHECK (cwd P:\\ so the materials load; the ODOL stays in the work dir)")
    odol = os.path.join(work, "odol")
    os.makedirs(odol, exist_ok=True)
    src_p = to_p_drive(DATA)
    for s in ("m", "f", "g"):
        f = "%s_%s.p3d" % (n, s)
        out = run([BINARIZE, "-silent", "-always", "-norecurse", src_p, odol, f], cwd=P_DRIVE)
        if "Material not loaded" in out:
            raise SystemExit("binarize could not load a material for " + f)
        data = open(os.path.join(odol, f), "rb").read()
        if data[:4] != b"ODOL" or (n + "_nohq").encode() not in data:
            raise SystemExit("bad ODOL for " + f)
        if s != "g" and b"DayzTemporarySkeleton" not in data:
            raise SystemExit("no skeleton in " + f)
        print("    %s binarizes OK (ODOL %d bytes in the work dir, material + skeleton present)" % (f, len(data)))
    print("[6] proof renders from the written p3d")
    co = os.path.join(texdir, "%s_co.png" % n)
    ver = os.path.join(work, "verify")
    jobs = [("m", 0, "male", "m_lod1"), ("m", 2, "male", "m_lod3"), ("f", 0, "female", "f_lod1"), ("g", 0, "ground", "g_lod1")]
    for s, lod, sex, pre in jobs:
        blender("s08_verify_p3d.py", os.path.join(DATA, "%s_%s.p3d" % (n, s)), str(lod), co, ver, pre, sex, blend=RIG)
    shots = ["m_lod1_rest_front", "m_lod1_rest_back", "m_lod1_posed_q34", "m_lod1_posed_side",
             "f_lod1_rest_front", "f_lod1_posed_q34", "m_lod3_rest_q34", "g_lod1_q34"]
    run([sys.executable, os.path.join(HERE, "sheet.py"), os.path.join(SOURCE, "preview_%s.png" % n), "4", "0.45"]
        + [os.path.join(ver, s + ".png") for s in shots])
    print("DONE:", n, "->", DATA)


if __name__ == "__main__":
    main()
