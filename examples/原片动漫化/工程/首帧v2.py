"""v2 首帧：把原片每个镜头的第一帧（全片/原片帧/cNN.png，1280×544）用 H3 Image 原样转成动漫，
人物、构图、服装、面具都保留，只换画风，去掉画面里的文字和水印。

表情规则（2026-11-13 用户纠正后）：每个人的表情只照原片画——笑的就是笑，平静的就是平静，发呆的就是发呆；
不许给任何人加眼泪、咬牙、皱眉、喊叫。只有原片里真在哭、喊的镜头，才在 EXPR 里写强烈表情。

用法：python3 首帧v2.py <机器> <镜头号...>      机器：wj（18188）或 xw（18189）
      python3 首帧v2.py wj odd  / xw even      按奇偶分两台机器跑
      python3 首帧v2.py wj plain / xw faces    plain = 没有近景表情的镜头，faces = 有表情的镜头
输出：../首帧/原始/cNN.png（3072×1312），已存在的跳过；日志 首帧_log_<机器>.txt
"""
import os, subprocess, sys, glob, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # 整活_散户动漫版
SRC = os.path.join(ROOT, "全片", "原片帧")
OUT = os.path.join(os.path.dirname(HERE), "首帧", "原始")
S = os.environ.get("H3_SCRIPTS", os.path.join(HERE, "..", "..", "..", "scripts"))   # 本仓库的 scripts 目录
URL = {"wj": "http://127.0.0.1:18188", "xw": "http://127.0.0.1:18189"}

BASE = ("The entire frame in <Picture 1> is <Subject 1>. The target image is the same frame redrawn as one frame of a "
        "Japanese theatrical action anime film: cel-shaded flat colors with hard-edged shadows, clean bold black line art, "
        "painted anime background{light}. <Subject 1> is fully preserved: the composition, camera angle, framing, and every "
        "person's position, size, pose, face shape, facial features, eyebrows, nose, hairstyle, skin tone, clothing, mask, "
        "gloves and props remain exactly as in <Picture 1>, so each character is instantly recognizable as the same person. "
        "Keep the same framing scale: a face that fills the frame in <Picture 1> fills the frame in the target image. "
        "Every person's facial expression is copied from <Picture 1> exactly as it is, with the same emotion and the same "
        "intensity: a calm face stays calm, a laugh stays a laugh, a smirk stays a smirk, a blank dazed face stays blank, "
        "a closed mouth stays closed. Do not add tears, clenched teeth, a frown, a scream, sweat or any emotion that is not "
        "visible in <Picture 1>; only when <Picture 1> itself shows crying or screaming, draw it with full anime intensity. "
        "Only the rendering changes from a live-action photograph to a hand-drawn anime illustration. All burned-in text, "
        "subtitles, name labels, logos and watermarks from <Picture 1> are removed; nothing else is added.{extra} {lamp}")
LIGHT = {
    "warehouse": (", cool cyan warehouse lighting", "Lighting comes from the high skylights above, casting soft teal light downward with shadows below."),
    "fire": (", the hall lit orange-red by explosions and fire", "Lighting comes from the fireballs and flames, warm orange light with hard dark shadows and flying embers."),
    "street": (", grey overcast daylight on a street outside", "Soft overcast daylight from above, gentle shadows."),
    "bluefire": (", the whole frame washed in cold flickering electric-blue light with a plain blue background, no fire visible", "Cold blue light flickers on his face from the front; the background is a flat blue glow."),
}
EXTRA = {
    59: " The digits on the LCD countdown display are part of the picture, not an overlay: keep them exactly as shown.",
    10: " The police officer stands with both arms hanging down at his sides, hands empty, looking up; he holds nothing, there is no gun anywhere in the picture.",
    11: " Far away on the upper catwalk stand four small figures: a woman in a purple jacket, a man in a red jacket and two men in dark clothes; they are drawn small but crisp and clearly separate, not merged into one blob.",
    15: " This is an extreme high-angle shot: far below near the centre-left of the grating floor stands the tiny police officer; at the top-right edge a dark-clothed figure is caught mid-leap with his legs in the air, motion-blurred exactly as in the photo (he is passing through the frame, not sitting); nobody else is in the picture.",
    22: " The large blurred shape sweeping across the foreground is the falling body of a young male hostage with short black hair in a dark vest, caught in mid-air and motion-blurred exactly like the photo - he is NOT lying on the floor; far behind stand the two small figures as in the photo. No woman, no long hair, nobody else is added.",
    30: " This is a low-angle shot of several hostages hanging upside down from the beams; there is NO police officer, no large face and no person in the foreground - only the hanging hostages and the ceiling.",
    32: " There are exactly two people in the foreground: on the left the police officer (light-blue shirt, dark POLICE vest) is thrown backward with his head flung back, and in the middle the hooded henchman in a yellow-green jacket lunges at him in a blur of motion; a third small figure far right stays as in the photo. There is only ONE police officer in the whole picture.",
    60: " This is an empty wide shot of the warehouse floor, railings and catwalk with a fire starting far away on the right; there are NO people anywhere in the picture, do not add anyone.",
    61: " There is exactly ONE man in the picture, a single close-up face; do not draw a second person or a second face.",
    62: " The police officer is seen from BEHIND, diving forward to the floor with his back to the camera as the fireball surges toward him; his face is not visible at all.",
    64: " This is an empty extreme wide shot of the warehouse with a fireball erupting far away; there are NO people, faces or figures anywhere in the picture.",
    65: " This is an explosion filling the warehouse with no people in it at all; do not add any person, face or figure. The burned-in credit text at the bottom left is removed.",
    67: " A huge fireball fills the frame; the only person is the small dark silhouette of the police officer at the bottom centre, seen from behind, tiny against the blast, with no visible face. Do not add any face or large figure. All burned-in credit text is removed.",
}
# 每个有人的镜头，表情按原片写死（谁笑、谁平静、谁哭）
EXPR = {
    2: "The police officer walks into the warehouse looking up, alert and uneasy: eyebrows raised, eyes searching upward, lips slightly parted. He is not crying and not angry; no tears, no clenched teeth.",
    3: "The hostage hangs upside down in the foreground with blood on his face, eyes narrowed in pain, mouth slightly open; another hostage hangs behind.",
    4: "A close-up of the police officer looking up in shock: mouth hanging open, eyes wide and glistening, brows pulled up, deep creases on the forehead. The face fills the frame as in the photo.",
    5: "A close-up of the police officer looking up with dread: brows knotted, eyes wet, mouth slightly open and trembling. The face fills the frame as in the photo.",
    6: "An upside-down hostage close to the camera, dust and blood on his face, eyes shut, mouth twisted in pain.",
    7: "The hostage hangs upside down close to the camera, blood on his face, eyes screwed shut, mouth twisted in pain.",
    8: "The police officer stands looking up with his mouth open, breathing hard, eyebrows raised in disbelief, eyes wide. No tears, no clenched teeth, no frown.",
    9: "A close-up of an upside-down hostage's head in the lower right, face bruised and in pain, eyes shut; legs and ropes above.",
    10: "The police officer stands looking up, lips parted, brows slightly raised, worried and alert. No tears, no clenched teeth.",
    12: "A medium close-up of the police officer aiming his pistol with both hands: a fierce glare, brows pulled down, eyes narrowed, jaw set, lips pressed tight. His cheeks are dry: NO tears, no crying.",
    13: "The masked woman aims her pistol at the camera with a cold, delighted grin, teeth showing, wet hair clinging to her face.",
    14: "On the right the gang leader stands relaxed and still against the wall, face calm under the mask, mouth closed, no frown. On the left the masked man crouches holding a small silver camcorder up in front of his painted full-face mask; the mask has no real mouth and shows no expression.",
    16: "A wide shot: far away the police officer aims his pistol with both arms extended, face small and tense; the gang leader stands in the right foreground with his back to the camera. Nobody is crying.",
    17: "The gang leader faces the camera with a cruel mocking grin, teeth showing, raising his red-gloved fist; the back of the officer's dark head and his pistol are in the left foreground.",
    18: "A close-up of the police officer aiming the pistol: tense, brows knitted, eyes focused, lips closed. His cheeks are dry: NO tears, no crying.",
    19: "A close-up of the gang leader throwing his head back in a wild, smug laugh: mouth wide open, head tilted back, the mask tilted up, a red glove rising.",
    20: "The masked man stands on the catwalk with his head lowered, gripping the rope; his face is a painted full-face mask with no real mouth and no expression; posture calm.",
    21: "The police officer fires his pistol upward with both arms raised: eyes squinting against the muzzle flash, face strained with effort, mouth closed. No tears.",
    23: "The masked gunman in the red jacket raises his pistol with one hand; his face is a painted orange mask, no expression.",
    24: "The masked woman grins with cold delight behind her gun, wet hair clinging to her face.",
    25: "The hooded henchman in the yellow-green jacket is LAUGHING heartily: head tilted back, mouth wide open in a big laugh, teeth showing, eyes squeezed shut with laughter, shoulders raised, a red visor over his eyes. He is gleeful and relaxed, not angry, not gritting his teeth.",
    26: "The gang leader throws his head back laughing hard, mouth wide open, shoulders shaking.",
    27: "A wide shot: the police officer kneels over the fallen hostage, face urgent and worried, mouth slightly open; no tears.",
    28: "A close-up of the young hostage lying on the floor, blood on his face, eyes shut, mouth slack in pain, the officer's hands supporting his head.",
    29: "A close-up of the police officer frozen in terror: eyes stretched wide with tiny pupils, mouth open, face drained of color; on the right a red-gloved hand presses a pistol to his temple.",
    31: "A close-up of the police officer looking up in horror, head turned, mouth open, brows pulled up in panic.",
    33: "The masked man on the catwalk presses his knife against the rope; painted full-face mask, no visible expression, body leaning into the cut.",
    35: "The police officer sits collapsed on the grating floor, hands on the floor, looking up with a face of utter despair, mouth open, brows pulled up.",
    37: "An extreme close-up of the police officer screaming in agony with everything he has: head thrown slightly back, mouth stretched wide open in a raw scream, eyes squeezed into tight wet slits, eyebrows knotted upward in grief, tears and sweat flying, veins on the temples and neck, a touch of motion blur. The face fills most of the frame as in the photo.",
    38: "The gang leader spreads his arms wide with a smug, taunting grin, chin raised.",
    39: "An extreme close-up of the police officer sobbing: face crumpled, eyes squeezed shut and streaming tears, mouth pulled down and open in a cry, brows knotted upward, cheeks wet. The face fills the frame as in the photo.",
    41: "The police officer stands bent forward with his hands on his knees, head lifted, face twisted in grief: mouth open, eyes wet, brows knotted upward.",
    42: "The gang leader stands talking with a smug, taunting half-smile, chin up, one hand open; a blurred sleeve fills the left foreground.",
    43: "The police officer stands among the fallen hostages, defeated and exhausted: shoulders slack, mouth slightly open, eyes tired and resigned, brows relaxed. No clenched teeth, no tears, no anger.",
    44: "The gang leader raises a black remote control with a smug, menacing smile; the back of the officer's dark head fills the right foreground.",
    45: "On the left the police officer looks toward the right, worried and tense, lips closed, eyes narrowed slightly. Behind him on the right the hooded henchman in the yellow-green jacket stands relaxed with a faint amused smile, one hand at his chest, a red visor mask over his eyes; he is calm, NOT angry, NOT gritting his teeth, NOT shouting.",
    46: "The masked man stands by the rope-hung railing and raises one gloved hand to his head in a salute; his face is a painted full-face mask (blue with wide painted eyes and a green painted mouth) that shows no real expression; posture upright and calm.",
    47: "On the left the police officer turns back, startled, mouth open, brows raised. On the right the hooded henchman stands at ease with a relaxed grin, hands at his pockets, red visor mask over his eyes; he is calm and amused, not angry.",
    48: "A low-angle shot: hostages hang from the beams and start dropping one by one; faces small and pained.",
    49: "On the grating floor the police officer rushes forward, face strained and determined, mouth closed; hostages fall above; the hooded henchman far back stands relaxed. No tears.",
    51: "The police officer dives forward with his back to the camera, arms out; his face is not visible.",
    52: "A wide shot: the police officer stands on the grating floor with his arms out, breathing hard, face small and anguished; the hooded henchman far right watches calmly, relaxed.",
    53: "The police officer runs bent over across the grating floor, face strained with effort, mouth closed. No tears.",
    54: "The police officer runs sideways across the floor looking up, face small and strained. No tears.",
    55: "The police officer throws his arms wide and his head back, screaming at the ceiling, mouth wide open, body arched in despair.",
    56: "A medium close-up of the gang leader laughing maniacally with his head thrown back, mouth wide open.",
    57: "The police officer runs sideways across the floor shouting, face twisted in anguish, mouth wide open, arms pumping, motion blur on the body.",
    58: "Far away under the beams a hostage hangs upside down as a backlit silhouette; no face visible.",
    61: "A close-up of the police officer in cold flickering blue light: his face is dazed and blank, eyes half-open and unfocused, mouth closed, hair blown by the wind. He is NOT crying, NOT angry, NOT gritting his teeth; the face is empty and stunned.",
    66: "The police officer bursts out of the flames bent forward, hair blown flat, mouth open in a yell, eyes squeezed shut against the heat. No tears.",
    68: "Outside by the red fire engine: the police officer sits on the ground covered in grey soot, head bowed, eyes lowered to the ground, face blank and numb, mouth closed; uniformed people stand around him looking down. He is NOT crying, NOT angry, NOT gritting his teeth.",
    69: "A close-up of the soot-covered police officer sitting against the fire engine: head slightly bowed, eyes downcast and empty, mouth closed, face hollow and numb, grey dust on his skin and hair. He is NOT crying, NOT angry, NOT gritting his teeth; he stares at nothing.",
}
FACES = sorted(EXPR)
PLAIN = [n for n in range(1, 70) if n not in EXPR]

# 头像参考图：让中远景的脸和近景是同一个人、主力的面具每张一样。(角色键, 文件) → <Picture 2>, <Picture 3>…
MASTER = {
    "SH": ("散户_头像_A2.png", "the police officer", "The police officer in <Picture {k}> is <Subject {s}>. The police officer in <Picture 1> is drawn with exactly the face of <Subject {s}>: the same face shape, eyebrows, eyes, nose, mouth, skin tone and hairstyle as <Picture {k}>, so he is clearly the same man, while keeping the pose, body size, framing and the EXPRESSION of <Picture 1> - the expression comes only from <Picture 1>, never from <Picture {k}>; nothing else from <Picture {k}> (its gun, hands, background, expression) is copied."),
    "ZL": ("主力_头像.png", "the gang leader", "The masked man in <Picture {k}> is <Subject {s}>. The masked gang leader in <Picture 1> is drawn exactly like <Subject {s}>: the same red-and-gold horned opera mask design, colours and shape, the same jaw, mouth, hair and jacket as <Picture {k}>, while keeping the pose, expression and framing of <Picture 1>; nothing else from <Picture {k}> is copied."),
    "YZ": ("游资_头像.png", "the masked woman", "The masked woman in <Picture {k}> is <Subject {s}>. The masked woman in <Picture 1> is drawn exactly like <Subject {s}>: the same green sequined half-mask, the same long wet dark hair, lips, chin and purple jacket as <Picture {k}>, while keeping the pose, expression and framing of <Picture 1>; nothing else from <Picture {k}> is copied."),
    "LH": ("量化_头像.png", "the man in the full-face mask", "The man in the full-face mask in <Picture {k}> is <Subject {s}>. The masked knife man in <Picture 1> is drawn exactly like <Subject {s}>: the same painted full-face mask (blue with white-ringed eyes, green-blue cheeks, painted red mouth; no real mouth or eyes visible), the same long shaggy hair, beard, tan jacket and blue gloves as <Picture {k}>, while keeping the pose and framing of <Picture 1>; nothing else from <Picture {k}> is copied."),
    "SM": ("神秘机构_头像.png", "the hooded henchman", "The young man in <Picture {k}> is <Subject {s}>. The henchman in the yellow-green jacket in <Picture 1> is drawn exactly like <Subject {s}>: the same slim face, shoulder-length light-brown hair, red tinted visor over the eyes and yellow-green hooded jacket as <Picture {k}>, while keeping the pose, expression and framing of <Picture 1>; nothing else from <Picture {k}> is copied."),
    "KT": ("空头_头像.png", "the masked gunman", "The masked gunman in <Picture {k}> is <Subject {s}>. The gunman in the red jacket in <Picture 1> is drawn exactly like <Subject {s}>: the same spiky orange-red hair, the same orange cat-face painted mask with white eye patches and pink nose, the same pink-red hooded jacket as <Picture {k}>, while keeping the pose and framing of <Picture 1>; nothing else from <Picture {k}> is copied."),
    "CPO": ("CPO_头像.png", "the young hostage", "The injured young man in <Picture {k}> is <Subject {s}>. The young hostage in <Picture 1> is drawn exactly like <Subject {s}>: the same face, thick messy black hair, blood marks, dark police vest and blue shirt as <Picture {k}>, while keeping the pose, expression and framing of <Picture 1>; nothing else from <Picture {k}> is copied."),
    "HZ": ("商业航天_头像.png", "the hanging hostage", "The hostage in <Picture {k}> is <Subject {s}>. The hanging hostage in <Picture 1> is drawn exactly like <Subject {s}>: the same face, short black hair, blood marks and dark uniform as <Picture {k}>, while keeping the upside-down pose, expression and framing of <Picture 1>; nothing else from <Picture {k}> is copied."),
}
REFS = {
    2: ["SH"], 8: ["SH"], 10: ["SH"], 18: ["SH"], 31: ["SH"], 35: ["SH"], 41: ["SH"], 53: ["SH"], 54: ["SH"], 16: ["SH"],
    43: ["SH"], 55: ["SH"], 57: ["SH"], 61: ["SH"], 66: ["SH"], 68: ["SH"], 69: ["SH"],
    4: ["SH"], 5: ["SH"], 12: ["SH"], 29: ["SH"], 37: ["SH"], 39: ["SH"],
    21: ["SH", "CPO"], 27: ["SH", "CPO"], 22: ["CPO"], 28: ["CPO"],
    32: ["SH", "SM"], 45: ["SH", "SM"], 47: ["SH", "SM"], 49: ["SH", "SM"], 52: ["SH", "SM"], 25: ["SM"],
    14: ["ZL", "LH"], 17: ["ZL"], 19: ["ZL"], 26: ["ZL"], 38: ["ZL"], 42: ["ZL"], 44: ["ZL"], 56: ["ZL"],
    13: ["YZ"], 24: ["YZ"], 40: ["YZ", "KT"], 23: ["KT"],
    20: ["LH"], 33: ["LH"], 46: ["LH"],
    9: ["HZ"],
}


def light_of(n):
    if n >= 68:
        return "street"
    if n == 61:
        return "bluefire"
    if n >= 60:
        return "fire"
    return "warehouse"


def prompt_of(n):
    l1, l2 = LIGHT[light_of(n)]
    extra = EXTRA.get(n, "")
    if n in EXPR:
        extra += " What <Subject 1> shows, to be drawn exactly as described and nothing more: " + EXPR[n]
    imgs = [os.path.join(SRC, f"c{n:02d}.png")]
    for i, c in enumerate(REFS.get(n, [])):
        f, _, sent = MASTER[c]
        imgs.append(os.path.join(os.path.dirname(HERE), "角色", f))
        extra += " " + sent.format(k=i + 2, s=i + 2)
    return BASE.format(light=l1, extra=extra, lamp=l2), imgs


def run(machine, shots):
    os.makedirs(OUT, exist_ok=True)
    env = dict(os.environ, COMFY_URL=URL[machine], COMFY_CLIENT_ID="mac-claude")
    log = open(os.path.join(HERE, f"首帧_log_{machine}.txt"), "a")
    tmp = os.path.join(HERE, "_dl_" + machine)
    os.makedirs(tmp, exist_ok=True)
    for n in shots:
        dst = os.path.join(OUT, f"c{n:02d}.png")
        if os.path.exists(dst):
            continue
        prompt, imgs = prompt_of(n)
        args = []
        for im in imgs:
            args += ["--img", im]
        t = time.time()
        r = subprocess.run(["python3", f"{S}/h3_image.py", prompt, *args, "--size", "3072x1312", "--seeds", os.environ.get("FF_SEED", "1"),
                            "--prefix", f"dmv2/ff_c{n:02d}", "--wait", tmp], env=env, capture_output=True, text=True)
        fs = sorted(glob.glob(os.path.join(tmp, f"ff_c{n:02d}_s*_*.png")), key=os.path.getmtime)
        if fs:
            shutil.copy(fs[-1], dst)
        log.write(f"{machine} c{n:02d} {'ok' if fs else 'FAIL'} {time.time() - t:.0f}s {r.stdout[-150:].strip()} {r.stderr[-200:].strip()}\n")
        log.flush()
        print(machine, n, "ok" if fs else "FAIL", f"{time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    m = sys.argv[1]
    sel = sys.argv[2]
    if sel in ("odd", "even"):
        shots = [n for n in range(1, 70) if n % 2 == (1 if sel == "odd" else 0)]
    elif sel == "plain":
        shots = PLAIN
    elif sel == "faces":
        shots = FACES
    else:
        shots = [int(x) for x in sys.argv[2:]]
    run(m, shots)
