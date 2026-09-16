"""셀러킴 코너 헤더 일러스트 생성 (Gemini 2.5 Flash Image)."""
import base64, json, os, sys, subprocess, tempfile, pathlib, re

ROOT = pathlib.Path("/Volumes/ExtraSSD/itemscout/62. 트랜드 스카우트/16.new_trend_scout")
OUT = ROOT / "trend_radar/magazine/img"
KEY = re.search(r"^GEMINI_API_KEY=(.+)$", (ROOT / "worker/.env").read_text(), re.M).group(1).strip().strip('"\'')

STYLE = ("Flat editorial magazine illustration. Muted palette: deep teal, terracotta red, "
         "sage green, warm off-white background. Clean simple line work, minimal detail, "
         "gentle grain texture, calm and friendly mood. Absolutely no text, no letters, "
         "no numbers, no signage anywhere in the image. Wide horizontal 16:9 composition, "
         "generous empty space.")

JOBS = {
 "ill_c1": "A wide ocean strip separating two homes: on the left an American porch with pumpkins, "
           "a lantern and fallen leaves; on the right a plain Korean apartment balcony with laundry "
           "and a single potted plant, no decoration. The contrast between the decorated and the bare.",
 "ill_c2": "A desk seen from above: last week's open notebook with a few hand-drawn arrows going up and "
           "down, a magnifying glass resting on it, a cooling cup of coffee. Someone checking back on "
           "what they wrote before.",
 "ill_c3": "A busy street market stall from the front, crowded with many different small goods stacked "
           "together - clothes on a rail, jars, boxes, a crab crate - and a small crowd of simple "
           "faceless shoppers browsing. Lively but not chaotic.",
 "ill_c4": "Three mysterious closed parcels of different shapes on a plain table, each wrapped in paper "
           "and string, with a large question mark shape formed by the shadow they cast. Curiosity.",
 "ill_c5": "A cargo ship and a small airplane crossing a calm sea, with a postcard floating in the "
           "foreground sky. Far shoreline with simple buildings on both edges of the frame.",
 "ill_c6": "A wall calendar with pages lifting in the wind, and beside it a coat rack where a thin "
           "summer shirt is being replaced by a thick winter coat. A cold blue breeze entering from "
           "the right side of the frame.",
}

MODEL = os.environ.get("IMG_MODEL", "gemini-2.5-flash-image")

def gen(name, prompt):
    body = json.dumps({"contents": [{"parts": [{"text": prompt + " " + STYLE}]}]})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write(body); req_path = f.name
    out_path = tempfile.mktemp(suffix=".json")
    subprocess.run(["curl", "-s", "-X", "POST",
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}",
        "-H", "Content-Type: application/json", "--data-binary", "@" + req_path,
        "-o", out_path], check=True, timeout=300)
    d = json.loads(pathlib.Path(out_path).read_text())
    for p in d["candidates"][0]["content"]["parts"]:
        if "inlineData" in p:
            dst = OUT / f"{name}.png"
            dst.write_bytes(base64.b64decode(p["inlineData"]["data"]))
            print(f"{name}: {dst.stat().st_size/1e6:.1f}MB")
            return
    print(f"{name}: NO IMAGE", file=sys.stderr)

for n, p in JOBS.items():
    try:
        gen(n, p)
    except Exception as e:
        print(f"{n}: ERROR {e}", file=sys.stderr)
