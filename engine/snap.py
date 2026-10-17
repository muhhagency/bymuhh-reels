import sys, os
from playwright.sync_api import sync_playwright
from PIL import Image
page, out = os.path.abspath(sys.argv[1]), sys.argv[2]
ts = [float(x) for x in sys.argv[3].split(",")]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":1080,"height":1920})
    pg.goto("file://"+page); pg.wait_for_timeout(300)
    ims=[]
    for t in ts:
        pg.evaluate(f"window.render({t})"); pg.screenshot(path="/tmp/s.png"); ims.append(Image.open("/tmp/s.png").resize((270,480)).copy())
    b.close()
cols=min(5,len(ims)); rows=(len(ims)+cols-1)//cols
sheet=Image.new('RGB',(280*cols,490*rows),(0,0,0))
for i,im in enumerate(ims): sheet.paste(im,((i%cols)*280,(i//cols)*490))
sheet.save(out)
