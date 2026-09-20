"""
check_contrast.py - verifies the KrishiAI colour palette against WCAG 2.1 AA.

    python tools/check_contrast.py

Every text/background pair used in src/static/krishiai.css is listed below with
the minimum ratio it must reach (4.5:1 for normal text, 3:1 for UI borders and
focus rings). The script exits with an error if any pair fails, so run it after
changing a colour.
"""
import sys



def lum(h):
    h=h.lstrip('#'); r,g,b=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    f=lambda c: c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4
    return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)
def cr(a,b):
    la,lb=lum(a),lum(b); hi,lo=max(la,lb),min(la,lb); return (hi+0.05)/(lo+0.05)

BG="#F5F8F3"; SURF="#FFFFFF"; SURF2="#EEF4EC"
PAIRS = [
 # (label, fg, bg, min)
 ("body text on page",           "#14261C", BG,   4.5),
 ("body text on card",           "#14261C", SURF, 4.5),
 ("secondary text on card",      "#3F5247", SURF, 4.5),
 ("muted text on card",          "#546B5C", SURF, 4.5),
 ("muted text on page bg",       "#546B5C", BG,   4.5),
 ("muted text on tinted panel",  "#546B5C", SURF2,4.5),
 ("primary button label",        "#FFFFFF", "#17603A", 4.5),
 ("primary button hover",        "#FFFFFF", "#0F4A2C", 4.5),
 ("primary link/text on card",   "#17603A", SURF, 4.5),
 ("primary text on tint",        "#124D2E", "#E3F1E8", 4.5),
 ("sidebar active label",        "#124D2E", "#E3F1E8", 4.5),
 ("info pill",                   "#0F5470", "#E1F0F6", 4.5),
 ("success pill",                "#0F5A32", "#E1F3E8", 4.5),
 ("warning pill",                "#7A4700", "#FDF0D5", 4.5),
 ("danger pill",                 "#A11B12", "#FDE8E6", 4.5),
 ("neutral pill",                "#3F5247", "#EAEFEA", 4.5),
 ("danger text on card",         "#A11B12", SURF, 4.5),
 ("input border vs card (UI 3:1)","#7C9484", SURF, 3.0),
 ("focus ring vs card (UI 3:1)", "#17603A", SURF, 3.0),
 ("meter fill vs track",         "#2E8B57", "#DCE8DF", 3.0),
 ("placeholder on white",        "#5F7566", SURF, 4.5),
 ("GET pill",   "#0F5470", "#E1F0F6", 4.5),
 ("POST pill",  "#0F5A32", "#E1F3E8", 4.5),
 ("PUT pill",   "#7A4700", "#FDF0D5", 4.5),
 ("PATCH pill", "#5B3A8C", "#F0EAFB", 4.5),
 ("DELETE pill","#A11B12", "#FDE8E6", 4.5),
]
if __name__=="__main__":
    bad=0
    for label,fg,bg,mn in PAIRS:
        r=cr(fg,bg); ok=r>=mn; bad+= (not ok)
        print(f"{'PASS' if ok else 'FAIL'}  {r:5.2f}:1 (need {mn})  {label:34s} {fg} on {bg}")
    print("failures:",bad)
    sys.exit(1 if bad else 0)
