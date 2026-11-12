#!/bin/bash
# 用 H3 Image 出两只猫的 8 张数字资产（头像、无头身体、空客厅、道具）。用法：COMFY_URL=http://机器:8188 bash gen_assets.sh [只出某一项的名字]
export COMFY_URL=${COMFY_URL:-http://127.0.0.1:8188} COMFY_CLIENT_ID=h3-video
cd "$(dirname "$0")/../../scripts"
OUT="$(dirname "$0")/资产"
SCENE="an old apartment living room: a worn beige fabric sofa against a cream-white wall with a light-grey knitted blanket on the seat, a window with white sheer curtains on the right letting in warm slanted afternoon sunlight, a small light-wood coffee table in front of the sofa with a black phone lying face-up on it"
STYLE="photorealistic, natural slightly muted colours, soft shadows falling toward the lower left, shot on a phone camera, no text"
ORANGE="a very fat orange tabby cat with a round face, round amber eyes, a pink nose, a white chin and white chest, and a narrow dark-blue collar with a small bell"
BLUE="a very fat British Shorthair cat with solid blue-grey short fur, a round face with big chubby cheeks, round copper-orange eyes, and a narrow red collar"
run() { # name size prompt
  [ -n "$ONLY" ] && [ "$ONLY" != "$1" ] && return
  echo "== $1"; python3 h3_image.py "$3" --size "$2" --seeds 1 --prefix "cats/$1" --wait "$OUT/$1"
}
ONLY="$1"
run 橘猫_头像 2048x2048 "Close-up portrait, eye level, square frame. In $SCENE, $ORANGE sits on the sofa and looks straight into the camera with a lazy, self-satisfied expression, mouth closed, ears up. Head and shoulders fill the frame, fur detail sharp. $STYLE"
run 蓝猫_头像 2048x2048 "Close-up portrait, eye level, square frame. In $SCENE, $BLUE sits on the sofa and looks straight into the camera with a slightly disapproving but caring expression, mouth closed, ears up. Head and shoulders fill the frame, fur detail sharp. $STYLE"
run 橘猫_身体_近景无头 1728x2368 "Medium shot, eye level, vertical frame, framed from the neck down so the head is outside the top edge. In $SCENE, $ORANGE sits upright on the left side of the sofa on the knitted blanket, its big round belly resting on the blanket, front paws together in front of the belly, tail curled beside it. $STYLE"
run 蓝猫_身体_近景无头 1728x2368 "Medium shot, eye level, vertical frame, framed from the neck down so the head is outside the top edge. In $SCENE, $BLUE sits upright on the right side of the sofa on the knitted blanket, chubby body, front paws together, tail curled beside it. $STYLE"
run 橘猫_身体_远景无头 1728x2368 "Wide shot, eye level slightly above, vertical frame, the cat's head cropped out by the top edge of the frame. In $SCENE, $ORANGE sits upright on the left side of the sofa on the knitted blanket, whole body and paws visible, the coffee table and phone in the foreground. $STYLE"
run 蓝猫_身体_远景无头 1728x2368 "Wide shot, eye level slightly above, vertical frame, the cat's head cropped out by the top edge of the frame. In $SCENE, $BLUE sits upright on the right side of the sofa on the knitted blanket, whole body and paws visible, the coffee table and phone in the foreground. $STYLE"
run 背景_客厅 1728x2368 "Wide shot, eye level slightly above, vertical frame. $SCENE, the sofa empty, no animals, no people, nothing on the blanket. $STYLE"
run 道具_手机 2048x2048 "Close-up, slightly above, square frame. A plain black smartphone lying face-up on a light-wood coffee table, its screen dimly lit, warm afternoon sunlight from the right, part of a beige sofa blurred in the background. $STYLE"
