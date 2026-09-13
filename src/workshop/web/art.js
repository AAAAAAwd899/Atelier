/* Six original engraved bindings. Project titles are live text, never painted labels. */
(() => {'use strict';
let seq=0;
const path=(d,extra='')=>`<path d="${d}" ${extra}/>`;
function botanical(){
 let s=path('M110 165Q110 100 130 47 M110 132Q82 101 61 89 M117 99Q152 92 171 66 M112 148Q144 138 162 119');
 [[110,135,-38],[119,111,28],[112,93,-38],[129,76,26],[82,111,-66],[64,93,-68],[146,87,54],[159,123,58],[118,148,32]].forEach(([x,y,r])=>{
 s+=`<g transform="translate(${x} ${y}) rotate(${r})">${path('M0 0Q-15-10-8-36Q14-19 0 0Z','fill="currentColor" fill-opacity=".07"')}${path('M0 0-8-33 M-4-12 2-22 M-5-17-11-24','opacity=".7"')}</g>`;
 });
 s+='<circle cx="130" cy="46" r="5"/><circle cx="130" cy="46" r="9" opacity=".25"/>';
 return s+path('M90 168h42 M101 173h20');
}
function celestial(){
 let s='<circle cx="110" cy="102" r="65"/><circle cx="110" cy="102" r="59" opacity=".45"/><circle cx="110" cy="102" r="34"/><ellipse cx="110" cy="102" rx="63" ry="20" transform="rotate(-24 110 102)"/><ellipse cx="110" cy="102" rx="19" ry="58" transform="rotate(-24 110 102)"/>';
 for(let i=0;i<48;i++){let t=i*Math.PI/24,x=Math.cos(t),y=Math.sin(t);s+=path(`M${110+x*66} ${102+y*66}L${110+x*(i%4?69:73)} ${102+y*(i%4?69:73)}`,'opacity=".65"');}
 s+=path('M110 17v13 M110 174v13 M23 102h12 M185 102h12 M105 24h10 M105 180h10');
 [[52,42],[173,153],[176,49],[48,154]].forEach(([x,y])=>{s+=path(`M${x-4} ${y}h8 M${x} ${y-4}v8`);});
 return s+`<circle cx="110" cy="102" r="8" fill="currentColor" fill-opacity=".12"/>`;
}
function cartography(){
 let s='';
 for(let j=0;j<7;j++)s+=path(`M30 ${53+j*15}Q74 ${23+j*17} 98 ${49+j*15}T188 ${46+j*18}`,'opacity=".45"');
 s+=path('M38 155 72 101 96 127 136 60 181 148 M57 126l15-25 10 14 M117 91l19-31 15 24','stroke-width="1.4"');
 s+=path('M47 160Q88 120 112 150T171 130','stroke-dasharray="2 4"');
 s+=`<g transform="translate(173 41)">${path('M0-21 4-4 18 0 4 4 0 21-4 4-18 0-4-4Z','fill="currentColor" fill-opacity=".1"')}<circle r="6"/>${path('M0-26v52 M-24 0h48','opacity=".4"')}</g>`;
 return s+path('M32 171h56 M32 169v4 M60 169v4 M88 169v4');
}
function architect(){
 let s=path('M47 160V65l63-33 63 33v95Z M35 160h150 M41 165h138 M47 65h126 M47 71h126 M47 78h126 M76 160V94a34 34 0 0 1 68 0v66 M89 160V102a21 21 0 0 1 42 0v58 M110 33v127','stroke-width="1.15"');
 for(let x of [55,63,155,163])s+=path(`M${x} 82v73 M${x-3} 84h6 M${x-3} 151h6`);
 s+=path('M30 30v151 M23 39h14 M23 160h14 M29 51l-4 6 M29 131l-4 6','opacity=".45"');
 s+='<circle cx="110" cy="54" r="8"/>'+path('M105 54h10 M110 49v10');
 return s;
}
function ocean(){
 let s='';
 for(let j=0;j<9;j++)s+=path(`M25 ${110+j*8}C43 ${90+j*8} 60 ${91+j*8} 72 ${105+j*8}S101 ${127+j*8} 120 ${110+j*8}S159 ${93+j*8} 195 ${108+j*8}`,'opacity="'+(.35+j*.065)+'"');
 s+='<circle cx="143" cy="51" r="19"/>'+path('M41 82q8-9 16 0 M76 64q6-8 12 0 M141 90v-5');
 for(let i=0;i<9;i++){let t=i*Math.PI/8;s+=path(`M${143+Math.cos(t)*25} ${51-Math.sin(t)*25}l${Math.cos(t)*7} ${-Math.sin(t)*7}`,'opacity=".6"');}
 return s+path('M26 95h37 M156 87h34');
}
function manuscript(){
 let s=path('M50 166q31-67 89-124 M71 136Q58 67 178 32Q164 132 83 136 M92 112 95 79 M113 91l5-38 M135 69l7-26 M98 107l49-7 M114 89l41-6','stroke-width="1.2"');
 s+=path('M42 174q16-14 30-5t25-3 M124 143h58 M125 153h44 M125 163h51','opacity=".7"');
 s+='<circle cx="61" cy="40" r="13"/><circle cx="61" cy="40" r="9" opacity=".4"/>'+path('M61 32v16 M57 36l4-4 4 4');return s;
}
const motifs={botanical,celestial,cartography,architect,ocean,manuscript};
window.WSArt={
 motif(name){return `<svg viewBox="0 0 220 200" class="binding-art" fill="none" aria-hidden="true"><g stroke="currentColor" stroke-width=".85" stroke-linecap="round" stroke-linejoin="round">${(motifs[name]||botanical)()}</g></svg>`;},
 seal(){return '<svg viewBox="0 0 48 48" class="workshop-seal" aria-hidden="true"><g fill="none" stroke="currentColor"><circle cx="24" cy="24" r="22" stroke-width=".7"/><circle cx="24" cy="24" r="18" stroke-width=".4"/><path d="M13 17c4-1 7 0 11 2 4-2 7-3 11-2v15c-4-1-7 0-11 2-4-2-7-3-11-2Z M24 19v15 M18 13h12" stroke-width="1.15"/></g></svg>';},
 empty(){return `<div class="empty-object" aria-hidden="true"><div class="empty-book back"></div><div class="empty-book front">${this.motif('botanical')}</div><div class="empty-ribbon"></div></div>`;}
};})();
