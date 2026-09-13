"""Original local vector environment, no labels, controls, fonts or imported art."""
from pathlib import Path
import random
random.seed(103)
out=Path(__file__).resolve().parents[1]/'src/web/world-art/midnight.svg'
svg=['''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
<defs><linearGradient id="sky" x2="0" y2="1"><stop stop-color="#061427"/><stop offset=".56" stop-color="#29445e"/><stop offset=".79" stop-color="#aa8393"/><stop offset="1" stop-color="#d9ab91"/></linearGradient>
<linearGradient id="lake" x2="0" y2="1"><stop stop-color="#778a9f"/><stop offset="1" stop-color="#081b2a"/></linearGradient>
<radialGradient id="light"><stop stop-color="#f7d5b6" stop-opacity=".7"/><stop offset="1" stop-color="#ddb59c" stop-opacity="0"/></radialGradient></defs>
<path fill="url(#sky)" d="M0 0h1600v900H0z"/><ellipse cx="1080" cy="555" rx="560" ry="300" fill="url(#light)"/>''']
for _ in range(115):
 x=random.randrange(1600); y=random.randrange(430);r=random.choice([.6,.9,1.3]);svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#dae9f4" opacity="{random.uniform(.2,.75):.2f}"/>')
svg+=['''<path d="M0 520 160 397 243 447 395 202 559 439 687 349 816 478 939 378 1090 505 1260 316 1470 490 1600 440V750H0Z" fill="#4c607f"/>
<path d="m273 350 122-148 130 188-88-61-43-80-40 84-32-15zM1165 415l95-99 105 134-91-69-20-31-28 58z" fill="#adb7c9"/>
<path d="M0 598 194 481 343 590 504 434 627 571 789 476 995 606 1161 511 1325 565 1495 431 1600 502V820H0Z" fill="#253d58"/>
<path d="M0 695Q270 603 576 676T1130 666t470-17V900H0Z" fill="url(#lake)"/>
<path d="M630 719q320-20 670 1m-560 23q214-12 590 2m-617 36q223-9 418 4m-350 43 221 0" fill="none" stroke="#b5bcc1" stroke-opacity=".2" stroke-width="2"/>
<path d="M0 600q224 69 461 214l330 86H0ZM1600 614q-210 50-372 188l-280 98h652Z" fill="#0d2533"/>''']
for side in [0,1]:
 for i in range(36):
  x=random.randrange(520);x=x if side==0 else 1600-x
  y=680+int((x if side==0 else 1600-x)*.38)+random.randrange(-35,36)
  h=random.randrange(70,235);w=h*.28
  svg.append(f'<g fill="#081d29"><path d="M{x} {y-h}l{-w*.65} {h*.48}h{w*.22}l{-w*.5} {h*.28}h{w*.28}l{-w*.4} {h*.24}h{w*2.1}l{-w*.4} {-h*.24}h{w*.28}l{-w*.5} {-h*.28}h{w*.22}Z"/><path d="M{x-2} {y-30}h4v50h-4z"/></g>')
svg.append('</svg>');out.write_text(''.join(svg),encoding='utf8')
