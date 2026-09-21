"""셀러KIM 실사 사진 생성 (Gemini). 스톡에 없는 장면에만 쓴다 — GUIDE §2-⑤ 참고.
사용: python3 genphoto.py <이름>=<프롬프트> ...
"""
import base64, json, os, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "magazine/img"

def key() -> str:
    k = os.environ.get("GEMINI_API_KEY")
    if k:
        return k
    for line in (ROOT / ".env").read_text().splitlines():
        n, _, v = line.partition("=")
        if n.strip() == "GEMINI_API_KEY" and v.strip():
            return v.strip().strip("\"'")
    raise SystemExit("GEMINI_API_KEY 없음")

# GUIDE 고정 문구 — 스톡 사진과 톤을 맞추려면 그대로 붙인다
STYLE = ("Photorealistic editorial lifestyle photograph, shot on a 35mm lens, soft natural window light, "
         "warm neutral color grade, shallow depth of field, candid and unposed, muted tones, "
         "no text, no letters, no logos, no brand names, no watermark. Horizontal 3:2 composition.")
MODEL = os.environ.get("IMG_MODEL", "gemini-2.5-flash-image")

def gen(name: str, prompt: str) -> None:
    req = tempfile.mktemp(suffix=".json"); out = tempfile.mktemp(suffix=".json")
    pathlib.Path(req).write_text(json.dumps({"contents": [{"parts": [{"text": prompt + " " + STYLE}]}]}))
    subprocess.run(["curl", "-s", "-X", "POST",
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key()}",
        "-H", "Content-Type: application/json", "--data-binary", "@" + req, "-o", out],
        check=True, timeout=300)
    d = json.loads(pathlib.Path(out).read_text())
    for p in d.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in p:
            dst = OUT / f"{name}.png"
            dst.write_bytes(base64.b64decode(p["inlineData"]["data"]))
            print(f"{name}: {dst.stat().st_size/1e6:.1f}MB → {dst.name}")
            return
    print(f"{name}: 이미지 없음 — {json.dumps(d)[:200]}", file=sys.stderr)

for arg in sys.argv[1:]:
    n, _, p = arg.partition("=")
    gen(n, p)
