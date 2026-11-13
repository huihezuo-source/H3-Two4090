"""v2 全片分段：每段一个 H3 Ref2VA 任务。每个切点锚定一张动漫首帧（AddGuide），整段锁原片音轨（AddGuide 音频，第 0 帧），
不用参考视频。台词是原片台词，H 段第 16、17 句换成新词（seg_H.wav 已经是换好配音的音轨）。
倒计时镜头 c59（121.167–124.133）不生成，拼接时用原片。

用法：python3 分段v2.py                 → 缩首帧到 1056×448、写 jobs/段X.json 和 jobs/farm_jobs.json，打印分段表
      python3 分段v2.py run A B …       → 用 farm.py 分给两台机器跑（不带参数 = 除 H 以外全部），结果在 ../生成/farm/<段>/
      python3 分段v2.py one xw H        → 单段单机
"""
import json, os, subprocess, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.dirname(HERE)                               # v2原角色版
ROOT = os.path.dirname(V)                               # 整活_散户动漫版
S = os.environ.get("H3_SCRIPTS", os.path.join(HERE, "..", "..", "..", "scripts"))   # 本仓库的 scripts 目录
FF_SRC = os.path.join(V, "首帧", "原始")               # 3072×1312
FF = os.path.join(V, "首帧", "生成尺寸")               # 1056×448
M = os.path.join(V, "角色")
A = os.path.join(V, "声音")
FPS, W, H = 24, int(os.environ.get("GEN_W", 1056)), int(os.environ.get("GEN_H", 448))
REF_SRC = os.path.join(V, "原片.mp4") if os.path.exists(os.path.join(V, "原片.mp4")) else os.path.join(V, "原片.mp4")

T0 = {}
for ln in open(os.path.join(ROOT, "全片", "shots.tsv")):
    n, a, b, d = ln.split()
    T0[int(n)] = float(a)
T0[69] = 152.0

CH = {
    "SH": ("散户_头像_A2.png", "the police officer{p}: a middle-aged man with tousled black hair, a light-blue long-sleeve shirt, a dark tie and a dark-blue police tactical vest lettered POLICE"),
    "ZL": ("主力_头像.png", "the gang leader{p}: a young man in an open black suit jacket over a white T-shirt, a red-and-gold horned opera mask covering the upper half of his face, red gloves"),
    "YZ": ("游资_头像.png", "the masked woman{p}: long wet dark hair, a green-and-gold half mask over her eyes, a purple leather jacket with star pins, holding a pistol"),
    "LH": ("量化_头像.png", "the masked knife man{p}: a thin man in a worn tan trench coat, a blue painted mask over his face, blue gloves, carrying a knife"),
    "SM": ("神秘机构_头像.png", "the hooded henchman{p}: a man in a yellow-green jacket with the hood up and a dark mask"),
    "KT": ("空头_头像.png", "the masked gunman{p}: a man in a red jacket wearing an orange painted mask, holding a pistol"),
    "CPO": ("CPO_头像.png", "the young hostage{p}: messy black hair, a dark police vest over a blue shirt, blood and dust on his face"),
}
NAME = {"SH": "the police officer", "ZL": "the gang leader", "YZ": "the masked woman", "LH": "the masked knife man",
        "SM": "the hooded henchman", "KT": "the masked gunman", "CPO": "the young hostage"}
WH = "the abandoned warehouse: a vast cold-cyan industrial hall with skylights casting slanted teal light beams, steel trusses and beams from which hostages in dark police uniforms hang upside down by their bound ankles, metal grating floors, stacks of old tyres, and an upper steel catwalk whose railings are hung with coils of thick rope"
WH_PLAIN = "the abandoned warehouse: a cold-cyan industrial hall of corrugated steel walls and skylights casting slanted teal light; no hostages are visible in this part of the hall"
WH_FIRE = "the warehouse torn apart by explosions, lit orange-red by fireballs, debris and sparks flying"
OUTSIDE = "a grey daytime street outside the ruined warehouse: a red fire engine, uniformed people standing around"

# 台词（原片）：绝对秒, 说话人（_off = 画外，画面里没人张嘴）, 台词
LINES = [
    (27.5, "CPO", "救我！"), (28.72, "ZL_off", "你还没亏爆仓不代表你有本事"), (31.5, "ZL_off", "是我们还没玩够"),
    (33.26, "SH", "你们是什么人？"), (35.32, "YZ", "我们是爱死你们这帮散户的人"),
    (41.1, "ZL", "快点抬轿"), (42.38, "ZL", "你先把肉割了"), (44.3, "ZL_off", "快点！"),
    (59.0, "ZL", "你被套了"),   # 原片 58.8 秒切到主力近景（切点检测漏了），他在画面里说
    (62.0, "SH", "不要啊"), (67.5, "LH", "再见！"), (72.5, "ZL", "你又被套！"),
    (78.0, "SH", "你们杀了我吧！"),
    (80.63, "ZL", "你不是很了不起吗？"), (82.17, "ZL", "说什么顶级牛散，超越周期盈利"),
    (85.25, "ZL", "你现在跟真正的高手差得远呢，人家早就空仓了"),   # 新词（克隆配音，已换进 seg_H.wav）
    (89.75, "ZL", "你呢，追涨杀跌，天天接盘，标准的韭菜"),
    (93.97, "ZL", "恭喜割肉，可惜你割晚了"), (100.0, "ZL", "现在是下午三点零三秒，一秒一个！"),
    (104.0, "LH", "遵命！"),
    (115.8, "SH", "为什么？"), (118.3, "CPO_off", "散户，你走啊"),
]

# 段: 开始, 结束, 场景, 出现的角色, 摘要, [(镜头号, 描述)]
SEGS = {
 "A": (0.0, 12.933, WH, ["SH"], "The officer walks alone into the warehouse and discovers rows of hostages hanging upside down from the beams.", [
   (1, "a high-angle shot looking down over the shoulders and back of {SH} in the lower foreground as he slowly raises his head; far above him a row of hostages hangs upside down from the steel beams, swaying slightly. The camera drifts slowly."),
   (2, "a wide shot: {SH} walks cautiously into the middle of the warehouse between stacks of old tyres, looking up at the hostages with a tense face, lips closed. The camera tracks slowly backward in front of him."),
 ]),
 "B": (12.933, 24.900, WH, ["SH"], "Close-ups alternate between the hanging hostages and the officer staring up in horror.", [
   (3, "a close-up of an upside-down hostage's bloodied face, eyes squeezed shut in pain, swaying slowly; lips closed."),
   (4, "a close-up of {SH} looking straight up in shock, eyes wide, brows pulled up, mouth open, sweat on his face, breathing hard but silent."),
   (5, "a close-up of {SH} looking up in dread, brows knotted, lips trembling then pressed shut."),
   (6, "a close-up of an upside-down hostage with dust and blood on his face, slowly turning on the rope; lips closed."),
   (7, "a close-up of an upside-down hostage's pained face, eyes shut; lips closed."),
   (8, "a medium shot of {SH} standing in the middle of the warehouse, slowly turning his head as he looks up at the hostages; lips closed. The camera slowly pushes in."),
 ]),
 "C": (24.900, 33.000, WH, ["SH"], "A hanging hostage cries for help; a loudspeaker voice taunts the officer while he looks up warily; then a wide view of the silent catwalks.", [
   (9, "a close-up of an upside-down hostage's bruised face in the lower right, legs and ropes above; he is the one who cries out."),
   (10, "a medium shot of {SH} standing in the warehouse looking up, alert, lips closed while the loudspeaker voice speaks."),
   (11, "an extreme wide shot of the warehouse from below: the upper steel catwalks, trusses and slanted skylight beams; several tiny dark figures stand far away on the high platforms. Nobody's mouth is visible."),
 ]),
 "D": (33.000, 40.533, WH, ["SH", "YZ", "LH", "ZL"], "The officer shouts at the gang; the masked woman answers from above with a cold grin; the gang members stand on the catwalk; a high view of the officer alone.", [
   (12, "a medium close-up of {SH} aiming a black pistol with both hands toward the right of frame, eyes fierce, brows slammed down."),
   (13, "a medium shot of {YZ} aiming her pistol down at the camera with a cold delighted grin, wet hair on her face; she is the one who speaks here."),
   (14, "a wide shot: on the left {LH} crouches against a concrete pillar, on the right {ZL} stands by a yellow-black hazard stripe. Neither moves his lips; the woman's voice continues off-screen."),
   (15, "an extreme high-angle wide shot looking straight down: on the metal grating floor far below, a tiny {SH} stands alone, turning around. Nobody speaks."),
 ]),
 "T": (40.533, 50.300, WH, ["SH", "ZL", "LH"], "A standoff: the officer aims at the gang leader, who taunts him, barks an order, laughs and signals the knife man on the catwalk.", [
   (16, "a static wide shot of the warehouse: far middle-left {SH} stands with both arms extended aiming a pistol toward the right foreground; in the right foreground {ZL} stands with his back to the camera, only his hair, the horns of his mask and his black jacket visible. He speaks with his back turned; {SH} keeps his lips closed."),
   (17, "an over-the-shoulder medium shot from behind {SH}: the back of his dark head and light-blue shoulder fill the left foreground, his hands grip the pistol pointed at {ZL} in the right midground. {ZL} faces the camera with a cruel grin and raises his red-gloved fist as he speaks; {SH}, seen from behind, does not speak."),
   (18, "a close-up of {SH} aiming the pistol toward the right: eyes wide, brows knitted, sweat on his forehead, lips pressed tightly shut and jaw clenched; he does not speak while the off-screen voice barks."),
   (19, "a close-up of {ZL}'s masked face: he tilts his head back and bursts into loud smug laughter, then raises his red-gloved right hand high as a signal; the camera tilts up quickly with the rising glove until only the glove shows against the cyan wall."),
   (20, "a low-angle medium shot of {LH} on the upper catwalk, one gloved hand gripping a coil of thick rope tied to the railing, a steel truss crossing diagonally behind him; he does not speak."),
 ]),
 "E": (50.300, 56.733, WH, ["SH", "ZL", "KT", "YZ", "SM", "CPO"], "The officer fires upward, a hostage drops, and the masked gang members appear one by one.", [
   (21, "a low-angle shot: {CPO} hangs upside down on the left with bound ankles; on the right {SH} fires his pistol upward, muzzle flashes."),
   (22, "the blurred falling body of {CPO} sweeps through the foreground in slow motion; far behind stands {ZL}, watching."),
   (23, "a medium shot of {KT} raising a pistol with one hand; an upside-down hostage hangs on the left. His lips are unseen behind the mask."),
   (24, "a medium shot of {YZ} holding her gun and grinning coldly, lips closed."),
   (25, "a medium shot of {SM} beside the stair railing, turning his hooded head toward the camera."),
   (26, "a medium close-up of {ZL} throwing his head back and laughing loudly with an open mouth, no words."),
 ]),
 "E2": (56.733, 61.433, WH, ["SH", "ZL", "CPO"], "The officer kneels over the fallen hostage, then the leader speaks into the camera.", [
   (27, "a wide shot: {SH} kneels on the metal grating and turns over {CPO}, who has fallen flat on his back; the camera stays on this kneeling pair for the whole shot, nobody stands up, no other framing appears."),
   (28, "a close-up of {CPO} lying hurt on the floor, blood on his face, eyes closed in pain, {SH}'s hands supporting his head; at 00:02.067 the shot cuts (as in <Video 1>) to a close-up of {ZL} in his horned mask, who speaks the line with clear mouth movement."),
 ]),
 "F": (61.433, 73.467, WH, ["SH", "ZL", "LH", "SM"], "The leader holds a gun to the officer's head, the officer is kicked down, the knife man cuts the ropes and hostages fall; the officer collapses and the leader mocks him.", [
   (29, "a close-up: {SH} on the left stares in terror, eyes stretched wide; {ZL}'s red-gloved hand on the right presses a pistol to his temple. {SH} is the one who cries out."),
   (30, "a low-angle shot: several hostages hang upside down from the steel beams, swinging in the air."),
   (31, "a close-up of {SH} looking up in horror, head turned, mouth open but silent."),
   (32, "a medium shot with exactly two people: {SH} is kicked backward by {SM}, who lunges at him; anime speed lines. There is only one officer in frame."),
   (33, "a medium shot of {LH} on the catwalk pressing his knife against a thick rope tied to the railing; he speaks one short word and slices the rope."),
   (34, "a low-angle shot: hostages drop from the beams one after another as the ropes go slack."),
   (35, "a medium shot of {SH} thrown down sitting on the metal grating, both hands on the floor, looking up in despair, lips closed."),
   (36, "a low-angle shot of the grating ceiling and beams, only the bound feet of hanging hostages visible."),
   (37, "an extreme close-up of {SH} screaming in agony, eyes squeezed shut, tears and sweat flying, no words."),
   (38, "a medium shot of {ZL} spreading his arms with a smug taunting grin; he is the one who speaks here."),
 ]),
 "G": (73.467, 80.467, WH, ["SH", "YZ", "KT"], "The broken officer sobs, the gang watches from above, and he begs them to come at him instead.", [
   (39, "an extreme close-up of {SH} sobbing, face crumpled, tears streaming, lips trembling, no words."),
   (40, "a high-angle medium shot of {YZ} and {KT} standing on the high platform looking down; neither speaks."),
   (41, "a medium shot of {SH} standing bent forward with his hands on his knees, head lifted, face twisted in grief; he shouts the line upward."),
 ]),
 "H": (80.467, 92.800, WH_PLAIN, ["ZL"], "The leader stands and lectures the officer, mocking him; one locked-off medium shot, no camera move.", [
   (42, "one continuous medium shot of {ZL} standing on the right of frame and talking with a smug half-smile, gesturing with his open red-gloved hand; the blurred grey sleeve of the officer stays in the left foreground for the whole shot. The camera does not move, pan, pull back or reveal anything: the framing of the anchored first frame is held for all 12 seconds, {ZL} stays the same size and keeps the mask on. His mouth opens and closes clearly and widely with every syllable he speaks, like an anime character delivering a speech."),
 ]),
 "I": (92.800, 101.367, WH, ["SH", "ZL"], "The officer stands among fallen hostages; the leader pulls out a remote control and announces the countdown.", [
   (43, "a medium shot of {SH} standing in the warehouse among several fallen hostages lying on the floor, lips closed while the off-screen voice finishes a sentence."),
   (44, "a medium shot of {ZL} raising a black remote control in his right hand with a smug smile; the back of {SH}'s dark head fills the right foreground. {ZL} speaks both lines here with clear mouth movements; {SH}, seen from behind, does not speak."),
 ]),
 "J": (101.367, 111.733, WH, ["SH", "SM", "LH"], "The knife man obeys, hostages fall one after another, and the officer runs to catch them.", [
   (45, "a medium shot: {SH} on the left stares in fear to the right; {SM} stands right behind him. Neither speaks."),
   (46, "a medium shot of {LH} standing by the railing hung with thick ropes; he answers with one short word."),
   (47, "a medium shot: {SH} on the left turns back; {SM} stands on the right."),
   (48, "a low-angle shot: hostages hang from the beams and start dropping one by one."),
   (49, "a wide shot: on the grating floor {SH} rushes forward while hostages fall from above; {SM} stands far back."),
   (50, "a high-angle shot of the grating floor and beams: a hostage falls headfirst with speed lines."),
   (51, "a wide shot: {SH} dives forward with his back to the camera, arms out to catch a falling hostage."),
   (52, "a wide shot: {SH} stands on the grating floor breathing hard; {SM} watches from far away."),
 ]),
 "K": (111.733, 121.167, WH, ["SH", "ZL", "CPO"], "The officer runs back and forth in vain, collapses screaming, and the last hostage begs him to leave.", [
   (53, "a wide shot: {SH} runs bent over across the grating floor."),
   (54, "a wide shot: {SH} runs sideways, looking up."),
   (55, "a medium shot: {SH} throws his arms wide and his head back, screaming without words."),
   (56, "a medium close-up of {ZL} throwing his head back in maniacal laughter, no words."),
   (57, "a medium shot of {SH} sprinting to the right, face twisted in anguish; he shouts the line."),
   (58, "a low-angle shot: far away under the beams {CPO} hangs alone upside down, a backlit silhouette against the skylight, his face not visible; his weak voice is heard."),
 ]),
 "L": (124.133, 132.800, WH_FIRE, ["SH"], "The bomb goes off: fire spreads, the officer stares, then dives as the blast rolls over him.", [
   (60, "a wide shot of the warehouse: crates on the floor far away catch fire, smoke spreading; the light is still cyan."),
   (61, "a close-up of {SH} lit by flickering blue light, staring ahead with a dazed broken face, lips closed."),
   (62, "a wide shot: {SH} throws himself to the floor with his back to the camera as a huge fireball surges toward him, everything turning orange."),
   (63, "a huge explosion engulfs the frame; in the middle {SH}'s silhouette is lifted by the shock wave, debris flying, slow motion."),
 ]),
 "M": (132.800, 142.800, WH_FIRE, ["SH"], "Chain explosions tear the warehouse apart; the officer staggers out of the fireball.", [
   (64, "an extreme wide shot of the warehouse: a fireball erupts far away and rises to the roof."),
   (65, "a wide shot: chain explosions rip through the empty warehouse, debris and sparks flying; nobody is in frame."),
   (66, "a huge fireball and flying debris fill the frame; {SH} bursts out of the flames bent forward, hair blown flat and smoking."),
 ]),
 "N": (142.800, 157.000, WH_FIRE, ["SH"], "The warehouse collapses in flames; afterwards the officer sits dazed on the street beside a fire engine, and the camera settles on his empty face.", [
   (67, "a wide shot: the warehouse collapses in the explosions, flames shooting up, debris flying."),
   (68, f"a daytime exterior medium shot on {OUTSIDE}: {{SH}} sits on the ground beside the red fire engine, covered in grey soot, staring blankly; uniformed people stand around him. Nobody speaks."),
   (69, "a medium close-up of {SH} sitting against the fire engine, soot on his face, eyes wet and unfocused, utterly still; the camera very slowly pushes in. Nobody speaks."),
 ]),
}


# 补充锚点：(绝对秒, 文件名, 类型 cut/mid, 提示词里怎么说)。文件在 首帧/原始/
EXTRA_ANCHORS = [
    (8.70, "c02_8.70", "cut", "an extreme high-angle shot looking straight down at the small police officer walking across the floor past the tyre stacks"),
    (22.30, "c08_22.30", "mid", ""),
    (23.60, "c08_23.60", "mid", ""),   # B2 第一版 23.15 秒起提前插了仓库全景，补锚压住
    (24.50, "c08_24.50", "mid", ""),   # B2 三版都在 24.0 秒提前切镜，再按一张
    (49.33, "c20_49.33", "cut", "a low-angle wide shot looking up at the catwalk and trusses, the masked knife man small on the railing"),
    (51.80, "c22_51.80", "cut", "a wide shot: the police officer stands in the middle distance, the gang leader farther away near the back wall"),
    (57.50, "c27_57.50", "mid", ""),
    (58.80, "c28_58.80", "cut", "a medium close-up of the gang leader in his horned mask, speaking"),
    (86.50, "c42_86.50", "mid", ""),
 (89.30, "c42_89.30", "mid", ""),
    (97.50, "c44_97.50", "mid", ""),
    (128.00, "c62_128.00", "midx", ""),
    (136.60, "c65_136.60", "cut", "a wide shot of a huge fireball erupting in the warehouse, nobody in frame"),
    (140.30, "c66_140.30", "mid", ""),   # M 第一版 139.8–142.1 秒插了仓库全景，补锚压住
    (142.20, "c66_142.20", "mid", ""),   # 原片 142.2 秒只是火光闪白不是切镜：标成 cut 后 M2 真的切了个脸部特写
    (145.00, "c67_145.00", "mid", ""),   # N1 首帧漏了跪在底部中间的散户，补一张带他的锚帧
]

ANCHOR_T = {fn: t for t, fn, _, _ in EXTRA_ANCHORS}   # 锚帧名 → 绝对秒（拆分段用锚帧当首帧）


def _sub(parent, a, b, want, summ, chars=None):
    """从整段切出子段：A/B/F/H/N 超过 250 帧（1056×448 + 参考视频 + 头像母版）会把 24G 显存挤爆，每步慢十倍以上，
    所以按真实切点拆成 10 秒以内的小段。want 是镜头号或锚帧名；参考角色只保留在子段里出镜的。"""
    pa, pb, scene, pchars, psumm, shots = SEGS[parent]
    bym = {n: d for n, d in shots}
    sub_shots = []
    for n in want:
        if isinstance(n, str):   # 锚帧名：用该锚帧当这一子段的首帧，描述沿用所属镜头
            d = bym[int(n[1:3])]
        else:
            d = bym[n]
        sub_shots.append((n, d.replace("for all 12 seconds", "for the whole segment")))
    chars = chars or [c for c in pchars if any("{" + c + "}" in d for _, d in sub_shots)]
    return (a, b, scene, chars, summ, sub_shots)


SEGS["A1"] = _sub("A", 0.0, 5.667, [1], "Seen from behind and above, the officer slowly raises his head toward rows of hostages hanging upside down from the beams.")
SEGS["A2"] = _sub("A", 5.667, 12.933, [2], "The officer walks cautiously into the middle of the warehouse between stacks of tyres, looking up at the hostages; then a high-angle view looking straight down at him crossing the floor.")
SEGS["B1"] = _sub("B", 12.933, 18.033, [3, 4, 5, 6], "Close-ups alternate between hanging hostages and the officer staring up in horror.")
SEGS["B2"] = _sub("B", 18.033, 24.900, [7, 8], "A close-up of a hanging hostage, then a medium shot of the officer slowly turning his head as he looks up; at the end the shot cuts to a close-up of a hanging hostage.")
# 两版 B2 都在 c08 末尾（23.15 / 24.03 秒）自己编了一个仓库全景：模型知道 24.9 秒要切镜就提前乱切。
# 多生成到 25.4 秒并把真正的下一镜 c09 锚在 24.9 秒，让它切到对的镜头；成片只取到 24.9 秒。
SEGS["B2"] = SEGS["B2"][:1] + (25.400,) + SEGS["B2"][2:5] + (SEGS["B2"][5] + [(9, "a close-up of an upside-down hostage's bruised face in the lower right, legs and ropes above; lips closed.")],)
SEGS["F1"] = _sub("F", 61.433, 67.800, [29, 30, 31, 32, 33], "The leader holds a gun to the officer's head; the officer looks up in horror and is kicked down; the knife man cuts a rope.")
SEGS["F2"] = _sub("F", 67.800, 73.467, [34, 35, 36, 37, 38], "Hostages drop from the beams; the officer sits collapsed on the floor and screams; the leader mocks him.")
SEGS["H1"] = _sub("H", 80.467, 89.550, [42], "The leader stands and lectures the officer, mocking him; one locked-off medium shot, no camera move.")   # 多出 0.25 秒给拼接溶接
SEGS["H2"] = _sub("H", 89.300, 92.800, ["c42_89.30"], "The leader keeps lecturing the officer in the same locked-off medium shot, no camera move.")
# M 两个种子都在 139.8–142.1 秒（散户冲出火海的镜头中段）插进仓库全景，140.3 秒的锚帧也压不住：拆成 M1（两个爆炸空镜）和 M2（只有 c66 一个镜头，提示词里没有全景可串）
SEGS["M1"] = _sub("M", 132.800, 138.533, [64, 65], "Chain explosions tear the empty warehouse apart: a fireball erupts far away and rises to the roof, then blasts rip through the hall with debris and sparks flying; nobody is in frame.")
SEGS["M2"] = _sub("M", 138.533, 142.800, [66], "One continuous close shot: the officer bursts out of the flames toward the camera, bent forward and gripping a railing, hair blown flat and smoking, fire and flying debris filling the frame behind him for the whole shot; the camera never cuts away to a wide view.")
SEGS["N1"] = _sub("N", 142.800, 147.133, [67], "The warehouse collapses in the explosions, flames shooting up and debris flying; {SH} kneels small at the bottom centre of the frame in front of the blast, a fallen hostage beside him.")
SEGS["N1"] = SEGS["N1"][:3] + (["SH"],) + SEGS["N1"][4:5] + ([(67, "a wide shot: the warehouse collapses in the explosions, flames shooting up, debris flying; {SH} kneels small at the bottom centre of the frame, seen from the front, with a fallen hostage on the floor beside him; nobody speaks.")],)
SEGS["N2"] = _sub("N", 147.133, 157.000, [68, 69], "Daytime exterior: the officer sits dazed on the street beside a fire engine, and the camera settles on his empty face.")


def ts(x):
    return f"00:{int(x):02d}.{int(round((x - int(x)) * 1000)):03d}"


def first_frame_named(fn):
    src = os.path.join(FF_SRC, fn + ".png")
    out = os.path.join(FF, fn + ".png")
    if not os.path.exists(src):
        raise SystemExit(f"缺补充锚点 {src}")
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", f"scale={W}:{H}:flags=lanczos", out], check=True)
    return out


def first_frame(n):
    src = os.path.join(FF_SRC, f"c{n:02d}.png")
    out = os.path.join(FF, f"c{n:02d}.png")
    if not os.path.exists(src):
        raise SystemExit(f"缺首帧 {src}")
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", f"scale={W}:{H}:flags=lanczos", out], check=True)
    return out


def build(k, lines=None):
    a, b, scene, chars, summ, shots = SEGS[k]
    lines = LINES if lines is None else lines
    length = int(round((b - a) * FPS)) + 1
    imgs, subj, defs = [], {}, []
    for c in chars:
        f, desc = CH[c]
        mp = os.path.join(M, f)
        subj[c] = f"<Subject {len(subj) + 1}>"
        if os.path.exists(mp):
            imgs.append(mp)
            defs.append(f"{subj[c]} is " + desc.format(p=f" (his or her face, hair and mask exactly as in the head portrait <Picture {len(imgs)}>; clothing and body as in the anchored frames)") + ".")
        else:
            defs.append(f"{subj[c]} is " + desc.format(p=" as drawn in the anchored first frames") + ".")
    if "SH" in chars and os.path.exists(os.path.join(M, "散户_全身.png")):
        imgs.append(os.path.join(M, "散户_全身.png"))
        defs.append(f"<Picture {len(imgs)}> is the full-body view of {subj['SH']}: in every wide or distant shot his whole figure, proportions, hair and face follow this picture so that his face stays the same face even when small.")
    wn = f"<Subject {len(subj) + 1}>"
    defs.append(f"{wn} is " + scene + ".")
    if not imgs:   # 没有角色母版时，把第一镜的首帧当唯一参考图（画风参考），节点至少要一张参考图
        imgs.append(first_frame(shots[0][0]))
        defs.append(f"<Picture 1> is the anchored first frame of Shot 1 and the art-style reference for the whole segment: every frame is drawn in exactly this anime style.")
    fmt = dict(subj)
    for c in CH:
        fmt.setdefault(c, NAME[c])
    # 这段里的台词
    seg_lines = [(t - a, sp, txt) for t, sp, txt in lines if a - 0.3 <= t < b]
    line_txt = []
    for t, sp, txt in seg_lines:
        if sp.endswith("_off"):
            line_txt.append(f"At {ts(max(t, 0))}, an off-screen voice ({NAME[sp[:-4]]}, not visible) says <d>[Chinese] {txt}</d> Nobody on screen moves their lips.")
        else:
            who = fmt[sp]
            line_txt.append(f"At {ts(max(t, 0))}, {who} says <d>[Chinese] {txt}</d> Only {who}'s mouth moves, in sync with the words.")
    guides, desc_lines, appear = [], [], {c: [] for c in chars}
    for i, (n, d) in enumerate(shots):
        t = (T0[n] if isinstance(n, int) else ANCHOR_T[n]) - a
        fr = int(round(t * FPS))
        guides.append({"image": first_frame(n) if isinstance(n, int) else first_frame_named(n), "frame": fr})
        txt = d.format(**fmt)
        for c in chars:
            if subj[c] in txt:
                appear[c].append(f"[Shot {i + 1}]")
        if i == 0:
            desc_lines.append(f"[Shot 1] The shot begins from its anchored first frame: {txt}")
        else:
            desc_lines.append(f"[Shot {i + 1}] At {ts(t)}, the shot cuts to its anchored first frame: {txt}")
    for t, fn, kind, d in EXTRA_ANCHORS:
        if a + 0.05 <= t < b - 0.2:   # 正好在段起点的锚帧由 shots 表当首帧，不重复
            guides.append({"image": first_frame_named(fn), "frame": int(round((t - a) * FPS))})
            if kind == "cut":
                desc_lines.append(f"[Shot {len(desc_lines) + 1}] At {ts(t - a)}, the shot cuts (exactly as <Video 1> does) to its anchored first frame: {d}.")
    guides.append({"audio": os.path.join(A, f"seg_{k}.wav"), "frame": 0})
    ret = []
    for c in chars:
        ret.append(f"{subj[c]} (appears in {', '.join(appear[c]) or 'background'}): fully_preserved - the face, hair, mask, clothing and colours exactly as in the anchored frames are kept.")
    ret.append(f"{wn} (appears in all shots): fully_preserved - the location, lighting and colours are kept.")
    videos = []
    if os.environ.get("USE_REF"):
        rv = os.path.join(HERE, "refvid", f"{k}_ref.mp4")
        if not os.path.exists(rv):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", REF_SRC,
                            "-vf", f"crop=1280:544:0:88,scale={W}:{H}:flags=lanczos,fps={FPS}", "-an", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", rv], check=True)
        videos = [rv]
        defs.insert(0, "<Video 1> is the live-action source clip of this exact segment: it provides the shot order, cut timing, camera framing, camera movement, every character's position, body motion, head turns and the timing of every mouth movement for the whole segment.")
        ret.insert(0, "<Video 1> (motion and staging reference for every shot): partially_preserved - the cuts, framing, camera moves, blocking, gestures, head motion and the timing of every mouth movement are followed exactly; its live-action photographic look, real faces, film grain and burned-in text are NOT reproduced - every single frame, including the parts between anchored frames and every shot after a cut, is redrawn as flat cel-shaded anime with black outlines exactly like the anchored frames; no frame may look like live-action footage.")
    voice_note = (" The soundtrack is locked to the original audio; the listed characters speak their lines in sync with it and everyone else keeps their lips closed."
                  if seg_lines else " Nobody speaks in this segment; every visible mouth stays closed.")
    prompt = "\n".join([
        "subject_definitions:", *defs, "",
        "summary:",
        f"[reference generation{' + motion reference' if videos else ''}] {summ} Drawn as Japanese theatrical action anime exactly in the style of the anchored first frames. Every shot starts from its anchored first frame and cuts exactly at the listed times" + (", and moves exactly as <Video 1> does: nobody is added or removed relative to <Video 1>, and a mouth moves only when it moves in <Video 1>" if videos else "") + f".{voice_note}", "",
        "retention_analysis:", *ret, "",
        "detailed_description:",
        "The target video is Japanese theatrical action anime matching the anchored frames: cel shading, hard shadows, clean black outlines, expressive faces that keep the intensity of the anchored frames" + (", cold cyan-teal light falling from the skylights" if scene in (WH, WH_PLAIN) else "") + ". There is no on-screen text, subtitle, logo or watermark anywhere.",
        *desc_lines, *line_txt, "",
        "overall_soundscape:",
        "Locked to the original soundtrack.", "",
        "non_diegetic_music:", "N/A",
    ])
    job = {"prompt": prompt, "width": W, "height": H, "length": length, "steps": int(os.environ.get("GEN_STEPS", 20)), "turbo": bool(os.environ.get("GEN_TURBO")), "seed": int(os.environ.get("SEED_BASE", 500)) + list(SEGS).index(k),
           "prefix": f"dmv2/{'ref_' if videos else ''}seg_{k}", "images": imgs, "anchor_frames": [], "guides": guides, "audios": [], "videos": videos}
    os.makedirs(os.path.join(HERE, "jobs"), exist_ok=True)
    p = os.path.join(HERE, "jobs", f"段{k}.json")
    json.dump(job, open(p, "w"), ensure_ascii=False, indent=1)
    return p, length


if __name__ == "__main__":
    os.makedirs(FF, exist_ok=True)
    env = dict(os.environ, COMFY_CLIENT_ID="mac-claude")
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        keys = sys.argv[2:] or [k for k in SEGS if k != "H"]
        jobs = [{"name": f"seg_{k}", "job": build(k)[0]} for k in keys]
        jp = os.path.join(HERE, "jobs", "farm_jobs.json")
        json.dump(jobs, open(jp, "w"), ensure_ascii=False, indent=1)
        out = os.path.join(V, "生成", os.environ.get("FARM_OUT", "farm"))
        os.makedirs(out, exist_ok=True)
        subprocess.run(["python3", f"{S}/farm.py", jp, out], env=env)
    elif len(sys.argv) > 1 and sys.argv[1] == "one":
        m, k = sys.argv[2], sys.argv[3]
        env["COMFY_URL"] = {"wj": "http://127.0.0.1:18188", "xw": "http://127.0.0.1:18189"}[m]
        p, L = build(k)
        out = os.path.join(V, "生成", os.environ.get("FARM_OUT", "farm"), f"seg_{k}")
        os.makedirs(out, exist_ok=True)
        subprocess.run(["python3", f"{S}/h3_ref2va.py", p, "--wait", out], env=env)
    else:
        for k in SEGS:
            try:
                p, L = build(k)
            except SystemExit as e:
                print(k, "跳过：", e)
                continue
            a, b = SEGS[k][:2]
            print(k, f"{a:.2f}-{b:.2f}", f"{b - a:.2f}s", L, "帧，镜头", [n for n, _ in SEGS[k][5]])
