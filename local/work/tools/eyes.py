# Brightened side-by-side of a left/right eye pair, plus each eye's mean level.
import sys
import numpy as np
from PIL import Image
a, b, out = sys.argv[1:4]
gain = float(sys.argv[4]) if len(sys.argv) > 4 else 4.0
ims = [np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255 for p in (a, b)]
for p, im in zip((a, b), ims):
    print(p.split("\\")[-1].split("/")[-1], "mean", round(float(im.mean()), 4), "p99", round(float(np.percentile(im, 99)), 3))
both = np.concatenate(ims, axis=1)
both = 1 - np.exp(-both * gain)  # brighten dark scene, keep highlights
Image.fromarray((both * 255).astype(np.uint8)).save(out)
