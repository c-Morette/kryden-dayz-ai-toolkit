"""Vest bone weights by height bands (pattern measured on 3 working mod vests: JPC, IOTV, 6B23).
Input points in BLENDER space (z up = p3d y), body-space metres. Returns (N, len(ALLOWED)) normalised weights."""
import numpy as np

ALLOWED = ["Pelvis", "Spine", "Spine1", "Spine2", "Spine3", "Neck", "LeftShoulder", "RightShoulder", "LeftArm", "RightArm",
           "LeftArmRoll", "RightArmRoll", "LeftArmExtra", "RightArmExtra",    # roll/extra: shoulder pads, sleeves
           # sleeves of tops (appended at the end so the vest outputs stay byte-identical)
           "LeftForeArm", "RightForeArm", "LeftForeArmRoll", "RightForeArmRoll", "LeftForeArmExtra", "RightForeArmExtra",
           "LeftElbowExtra", "RightElbowExtra", "LeftWristExtra", "RightWristExtra", "LeftHand", "RightHand"]


def skin_bone(name):
    """body bone/selection name -> ALLOWED bone for garments that copy the skin (tops). None = ignore."""
    l = name.lower()
    for a in ALLOWED:
        if l == a.lower():
            return a
    for side in ("left", "right"):
        S = side.capitalize()
        if l.startswith(side):
            r = l[len(side):]
            if r.startswith("hand"):                       # fingers -> hand
                return S + "Hand"
            if r.startswith(("upleg", "leg", "knee", "foot", "toe", "hip")):
                return "Pelvis"
    if l in ("neck1", "head") or l.startswith("face"):
        return "Neck"
    return None
BAND_Z = [0.90, 1.00, 1.06, 1.14, 1.24, 1.34, 1.50, 1.62]
BAND = {
    "Pelvis": [1.00, 0.45, 0.10, 0.00, 0.00, 0.00, 0.00, 0.00],
    "Spine":  [0.00, 0.35, 0.30, 0.05, 0.00, 0.00, 0.00, 0.00],
    "Spine1": [0.00, 0.20, 0.40, 0.35, 0.05, 0.00, 0.00, 0.00],
    "Spine2": [0.00, 0.00, 0.20, 0.55, 0.55, 0.25, 0.05, 0.00],
    "Spine3": [0.00, 0.00, 0.00, 0.05, 0.40, 0.75, 0.95, 1.00],
}


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def band_weights(P):
    P = np.asarray(P, float)
    z = P[:, 2]; ax = np.abs(P[:, 0]); left = P[:, 0] > 0      # +x = character's left (LeftArm head x=+0.16)
    W = np.zeros((len(P), len(ALLOWED)))
    for b, row in BAND.items():
        W[:, ALLOWED.index(b)] = np.interp(z, BAND_Z, row)
    sh = 0.30 * smoothstep(1.20, 1.50, z) * smoothstep(0.03, 0.15, ax)   # shoulders: top and away from mid line
    am = 0.08 * smoothstep(1.38, 1.52, z) * smoothstep(0.10, 0.20, ax)   # upper arm: top of the straps only
    nk = 0.35 * smoothstep(1.50, 1.62, z) * (1 - smoothstep(0.12, 0.22, ax))  # neck: collar only
    W *= (1 - sh - am - nk)[:, None]
    for m, side in ((left, "Left"), (~left, "Right")):
        W[m, ALLOWED.index(side + "Shoulder")] += sh[m]
        W[m, ALLOWED.index(side + "Arm")] += am[m]
    W[:, ALLOWED.index("Neck")] += nk
    W[W < 0.02] = 0
    order = np.argsort(-W, 1)
    rows = np.arange(len(W))[:, None]
    W[rows, order[:, 4:]] = 0                                           # max 4 influences (vanilla body: <= 4)
    return W / np.maximum(W.sum(1, keepdims=True), 1e-9)


# Upper arm joint and direction of the vanilla rig (RIG.blend, Blender space, left side; right = mirror x).
ARM_JOINT = np.array([0.16, 0.01, 1.44])                       # LeftArm head
ARM_DIR = np.array([0.149, 0.047, -0.125]) / np.linalg.norm([0.149, 0.047, -0.125])   # -> LeftArmRoll head
# Shoulder pads copy the weights of the vanilla deltoid/biceps skin under them (s03). History, measured:
# a fixed 0.7 LeftArm lagged 18 deg behind a 60 deg arm raise; a fixed 0.9-1.0 LeftArm followed the raise
# but took the WHOLE arm twist of the idle pose, while the skin shares it with LeftArmRoll/LeftArmExtra -
# in game (03/10/2026) the pads ended up in front of the arm. Strap towards the collar fades to the clavicle:
ARM_FADE_T = [-0.08, 0.0]      # metres along the arm from the joint: 0 -> clavicle only, >= 0 -> skin weights
# 2nd in-game test (03/10/2026): with pure skin weights (~0.44 Arm + 0.42 ArmExtra) the pads sat on the side
# but flared out ~12 deg at the bottom with the arm down - ArmExtra (deltoid helper) only follows ~half of
# the arm drop. Blend this share of the skin weights into the plain upper-arm bone so the pad hugs the arm.
PAD_ARM_BLEND = 0.75   # 0.5 still flared in the emulated in-game idle; 0.75 hugs the arm


def arm_axis(side_sign):
    """joint and unit direction of the upper arm for +1 (left) / -1 (right), Blender space"""
    S = np.array([side_sign, 1.0, 1.0])
    return ARM_JOINT * S, ARM_DIR * S
