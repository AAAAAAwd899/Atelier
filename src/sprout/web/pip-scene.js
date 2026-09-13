/* Exam Sprout 0.9.7 · Pip's local, rigged 3D habitat.
   Real WebGL2 meshes, per-part movement, physical highlights. No CDN, tracking,
   card access, grade access or scheduler access. Own and dispose every resource. */
(()=>{'use strict';
const TAU=Math.PI*2, clamp=(x,a,b)=>Math.max(a,Math.min(b,x)), mix=(a,b,t)=>a+(b-a)*t;
const smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);};
const I=()=>new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);
function mul(a,b){const o=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)o[c*4+r]=a[r]*b[c*4]+a[4+r]*b[c*4+1]+a[8+r]*b[c*4+2]+a[12+r]*b[c*4+3];return o;}
function transform(p=[0,0,0],s=[1,1,1],r=[0,0,0]){const [x,y,z]=r,cx=Math.cos(x),sx=Math.sin(x),cy=Math.cos(y),sy=Math.sin(y),cz=Math.cos(z),sz=Math.sin(z);return new Float32Array([(cy*cz)*s[0],(cx*sz+sx*sy*cz)*s[0],(sx*sz-cx*sy*cz)*s[0],0,(-cy*sz)*s[1],(cx*cz-sx*sy*sz)*s[1],(sx*cz+cx*sy*sz)*s[1],0,sy*s[2],-sx*cy*s[2],cx*cy*s[2],0,...p,1]);}
function normalMatrix(m){const a=[m[0],m[1],m[2]],b=[m[4],m[5],m[6]],c=[m[8],m[9],m[10]];const x=cross(b,c),y=cross(c,a),z=cross(a,b),d=dot(a,x)||1;return new Float32Array([...x,...y,...z].map(v=>v/d));}
const vsub=(a,b)=>a.map((v,i)=>v-b[i]), cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]], norm=a=>{const l=Math.hypot(...a)||1;return a.map(v=>v/l);}, dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
function view(eye,at){const z=norm(vsub(eye,at)),x=norm(cross([0,1,0],z)),y=cross(z,x);return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);}
function ortho(l,r,b,t,n,f){return new Float32Array([2/(r-l),0,0,0,0,2/(t-b),0,0,0,0,-2/(f-n),0,-(r+l)/(r-l),-(t+b)/(t-b),-(f+n)/(f-n),1]);}
const vertex=`#version 300 es
precision highp float;
layout(location=0) in vec3 position;layout(location=1) in vec3 normal;
uniform mat4 model;uniform mat4 camera;uniform mat3 normalModel;
uniform mat4 lightCamera;out vec4 shadowPos;out vec3 pos;out vec3 n;out vec3 local;
void main(){vec4 w=model*vec4(position,1.);pos=w.xyz;local=position;n=normalize(normalModel*normal);gl_Position=camera*w;shadowPos=lightCamera*w;}`;
const fragment=`#version 300 es
precision highp float;
in vec3 pos;in vec3 n;in vec3 local;
uniform vec3 color;uniform vec3 eye;uniform vec4 surface;uniform sampler2D shadowMap;uniform float hasShadow;in vec4 shadowPos;
out vec4 outColor;
float sat(float x){return clamp(x,0.,1.);}
vec3 light(vec3 N,vec3 V,vec3 L,vec3 tint,float strength){
 vec3 H=normalize(V+L);float nl=sat(dot(N,L)),nv=max(.01,sat(dot(N,V))),nh=sat(dot(N,H)),vh=sat(dot(V,H));
 float rough=surface.x,a=rough*rough,a2=a*a,d=a2/(3.1415926*pow(nh*nh*(a2-1.)+1.,2.)+.0001);
 float k=pow(rough+1.,2.)/8.,g=nl/(nl*(1.-k)+k)*nv/(nv*(1.-k)+k);
 vec3 base=pow(color,vec3(2.2));vec3 f0=mix(vec3(.045),base,surface.y),f=f0+(1.-f0)*pow(1.-vh,5.);
 vec3 spec=d*g*f/(4.*nl*nv+.002);
 return (base*(1.-surface.y)*nl*.72+spec*nl*.38)*tint*strength;
}
void main(){
 vec3 N=normalize(n),V=normalize(eye-pos);if(!gl_FrontFacing)N=-N;
 vec3 base=pow(color,vec3(2.2));vec3 c=base*(vec3(.16,.20,.24)+vec3(.16,.17,.10)*sat(N.y*.5+.5));
 vec3 sh=shadowPos.xyz/shadowPos.w*.5+.5;float visibility=1.;
 if(hasShadow>.5&&sh.x>0.&&sh.x<1.&&sh.y>0.&&sh.y<1.){
 visibility=0.;float bias=max(.00065,.0018*(1.-dot(N,normalize(vec3(-3.5,5.,5.5)))));
 for(int y=-2;y<=2;y++)for(int x=-2;x<=2;x++){float depth=texture(shadowMap,sh.xy+vec2(x,y)*1.5/1024.).r;visibility+=sh.z-bias<=depth?1.:0.;}visibility/=25.;}

 c+=light(N,V,normalize(vec3(-3.5,5.,5.5)),vec3(1.,.93,.73),1.90)*(.18+.82*visibility);
 c+=light(N,V,normalize(vec3(3.5,2.,1.5)),vec3(.57,.78,1.),.46);
 c+=light(N,V,normalize(vec3(0.,3.,-3.)),vec3(.85,1.,.59),1.45);
 if(surface.x<.25){vec3 R=reflect(-V,N);float a=pow(max(0.,dot(R,normalize(vec3(-1.,2.5,5.)))),65.);float b=pow(max(0.,dot(R,normalize(vec3(3.,2.,5.)))),110.);c+=vec3(.9,.95,1.)*(a*.45+b*.22);}
 float rim=pow(1.-sat(dot(N,V)),3.);c+=base*rim*.1;
 c*=mix(.76,1.,smoothstep(.17,1.4,pos.y));
 if(surface.w>.5){float blush=exp(-pow((abs(local.x)-.64)*8.,2.)-pow((local.y+.06)*11.,2.));c=mix(c,vec3(.96,.53,.36),blush*.19);c*=.94+.08*local.y;}
 c=mix(c,color,surface.z);c=c/(c+vec3(.42));c=pow(c,vec3(1./2.2));outColor=vec4(c,1.);
}`;
function geometrySurface(fn,nu=32,nv=20){const p=[],n=[],idx=[];for(let j=0;j<=nv;j++){let v=j/nv;for(let i=0;i<=nu;i++){let u=i/nu;const a=fn(u,v),du=vsub(fn(u+.0002,v),fn(u-.0002,v)),dv=vsub(fn(u,v+.0002),fn(u,v-.0002));let normal=norm(cross(du,dv));if(!Math.hypot(...normal))normal=norm(a);p.push(...a);n.push(...normal);}}
for(let j=0;j<nv;j++)for(let i=0;i<nu;i++){const a=j*(nu+1)+i,b=a+nu+1;idx.push(a,a+1,b,b,a+1,b+1);}return {p,n,idx};}
function sphere(){return geometrySurface((u,v)=>{const phi=TAU*u,theta=Math.PI*v,s=Math.sin(theta);return [s*Math.cos(phi),Math.cos(theta),s*Math.sin(phi)];},40,28);}
function pear(){return geometrySurface((u,v)=>{const phi=TAU*u,theta=Math.PI*v,y=Math.cos(theta),s=Math.sin(theta),w=1-.14*y;return [s*Math.cos(phi)*w,y,s*Math.sin(phi)*(.96-.05*y)];},52,36);}
function tube(points,radius=.014,sides=8){const p=[],n=[],idx=[];for(let i=0;i<points.length;i++){let d=norm(vsub(points[Math.min(i+1,points.length-1)],points[Math.max(0,i-1)])),x=norm(cross(d,Math.abs(d[1])>.9?[0,0,1]:[0,1,0])),y=cross(d,x);for(let k=0;k<=sides;k++){let a=TAU*k/sides,normal=x.map((x,j)=>x*Math.cos(a)+y[j]*Math.sin(a));p.push(...points[i].map((v,j)=>v+normal[j]*radius));n.push(...normal);}}
for(let i=0;i<points.length-1;i++)for(let k=0;k<sides;k++){let a=i*(sides+1)+k,b=a+sides+1;idx.push(a,b,a+1,b,b+1,a+1);}return {p,n,idx};}
function leafShape(width=.28,bend=.18){return geometrySurface((u,v)=>{let t=v,a=(u-.5)*2,w=width*Math.pow(Math.max(0,Math.sin(Math.PI*t)),.8),x=a*w,y=t,z=bend*Math.sin(Math.PI*t)+.065*(1-a*a)*Math.sin(Math.PI*t);return [x,y,z];},12,24);}
function ring(){return geometrySurface((u,v)=>{const a=TAU*u,b=TAU*v,r=.75+.16*Math.cos(b);return [r*Math.cos(a),r*Math.sin(a),.16*Math.sin(b)];},32,10);}
const palette={skin:[.49,.67,.21],leaf:[.20,.40,.10],bright:[.43,.63,.16],dark:[.12,.29,.10],vein:[.36,.51,.13],eye:[.021,.010,.007],iris:[.30,.092,.019],light:[1.,.94,.72],wood:[.32,.145,.055],bark:[.18,.080,.035],stone:[.22,.18,.12],moss:[.18,.31,.07]};
class Scene{
 constructor(canvas,options={}){
  this.canvas=canvas;this.options=options;this.stage=clamp(Number(options.stage)||1,1,4);this.time=0;this.age=0;this.last=0;this.draws=0;this.action='idle';this.actionStart=0;this.pointer=[0,0];this.gaze=[0,0];this.yaw=-.12;this.turn=-.12;this.nodes=[];this.resources=[];this.paused=false;this.hidden=false;this.disposed=false;this.resizeCount=0;this.shadowDraws=0;this.duration=6;this.lastMotionTime=null;this.nextBlink=4.9;this.blinkStart=-10;this.blinkIndex=0;
  const gl=canvas.getContext('webgl2',{alpha:true,antialias:true,premultipliedAlpha:false,powerPreference:'low-power',preserveDrawingBuffer:!!options.capture});if(!gl)throw new Error('WebGL 2 is unavailable');this.gl=gl;
  try{
  const vs=this.shader(gl.VERTEX_SHADER,vertex),fs=this.shader(gl.FRAGMENT_SHADER,fragment),program=gl.createProgram();gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);gl.deleteShader(vs);gl.deleteShader(fs);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));this.program=program;this.u={};for(const k of ['model','normalModel','camera','eye','color','surface','lightCamera','shadowMap','hasShadow'])this.u[k]=gl.getUniformLocation(program,k);
  gl.enable(gl.DEPTH_TEST);gl.clearColor(0,0,0,0);this.geo={sphere:this.upload(sphere()),small:this.upload(geometrySurface((u,v)=>[Math.sin(Math.PI*v)*Math.cos(TAU*u),Math.cos(Math.PI*v),Math.sin(Math.PI*v)*Math.sin(TAU*u)],16,12)),pear:this.upload(pear()),ring:this.upload(ring())};this.build();this.unbatchedNodes=this.nodes.length;this.batch();this.makeShadow();this.resize();
  this.onResize=()=>{if(this.resize())this.render(this.time);};this.ro=new ResizeObserver(this.onResize);this.ro.observe(canvas);
  this.onLoss=e=>{e.preventDefault();this.stop();options.onLost?.();};canvas.addEventListener('webglcontextlost',this.onLoss);
  this.render(0);this.start();
  }catch(error){this.dispose();throw error;}
 }
 shader(type,src){const g=this.gl,s=g.createShader(type);g.shaderSource(s,src);g.compileShader(s);if(!g.getShaderParameter(s,g.COMPILE_STATUS)){const msg=g.getShaderInfoLog(s);g.deleteShader(s);throw new Error(msg);}return s;}
 upload({p,n,idx}){const g=this.gl,v=g.createVertexArray();g.bindVertexArray(v);const resources=[v];for(const [i,data]of [[0,p],[1,n]]){const b=g.createBuffer();g.bindBuffer(g.ARRAY_BUFFER,b);g.bufferData(g.ARRAY_BUFFER,new Float32Array(data),g.STATIC_DRAW);g.enableVertexAttribArray(i);g.vertexAttribPointer(i,3,g.FLOAT,false,0,0);resources.push(b);}const b=g.createBuffer();g.bindBuffer(g.ELEMENT_ARRAY_BUFFER,b);g.bufferData(g.ELEMENT_ARRAY_BUFFER,new Uint16Array(idx),g.STATIC_DRAW);resources.push(b);const geo={vao:v,count:idx.length,buffers:resources.slice(1),data:{p,n,idx}};this.resources.push(geo);return geo;}
 add(geo,p,s,col,part='body',rotation=[0,0,0],rough=.53,metal=0,emissive=0,skin=0){const node={geo:typeof geo==='string'?this.geo[geo]:geo,p,s,col,part,rotation,rough,metal,emissive,skin};node.matrix=transform(p,s,rotation);this.nodes.push(node);return node;}
 orb(p,s,c,part='body',r=[0,0,0],rough=.53){return this.add(Math.max(...s)<.12?'small':'sphere',p,s,c,part,r,rough);}
 line(points,r,c,part='body'){return this.add(this.upload(tube(points,r)),[0,0,0],[1,1,1],c,part);}
 leaf(p,len,w,rotation,col,part='crown',veins=true){const g=this.upload(leafShape(w,.18));this.add(g,p,[1,len,1],col,part,rotation,.40);const m=transform(p,[1,len,1],rotation);const conv=v=>[m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12],m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13],m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];
 const center=Array.from({length:16},(_,i)=>{let t=.06+.85*i/15;return conv([0,t,.248*Math.sin(Math.PI*t)]);});this.line(center,.010,palette.vein,part);
 if(veins)for(let j=0;j<3;j++){let t=.25+j*.17;for(let sign of [-1,1])this.line([conv([0,t,.25*Math.sin(Math.PI*t)]),conv([sign*w*.5,t+.07,.235*Math.sin(Math.PI*(t+.07))]),conv([sign*w*.75,t+.15,.215*Math.sin(Math.PI*(t+.15))])],.0045,palette.vein,part);}}
 build(){const p=palette;
  if(this.options.habitat!==false){
   for(const sign of [-1,1]){
    this.line([[sign*1.35,-.7,-.8],[sign*1.23,.5,-.9],[sign*1.26,1.5,-1.0],[sign*1.13,2.5,-1.2],[sign*1.31,4.4,-1.4]],.10,[.048,.11,.13],'background');
    this.line([[sign*1.25,1.4,-1.05],[sign*1.08,2.1,-1.1],[sign*.79,2.52,-1.3],[sign*.65,3.2,-1.4]],.046,[.045,.095,.12],'background');
    this.line([[sign*1.45,.3,-1.8],[sign*1.66,2.0,-2.1],[sign*1.38,4.,-2.2]],.19,[.052,.115,.13],'background');
   }
  }
  // One coherent living sprout at every stage. The leaf mantle grows, not a new face.
  this.add('pear',[0,1.17,0],[.67,.77,.52],p.skin,'body',[0,0,0],.52,0,0,1);
  for(const sign of [-1,1]){
   this.orb([sign*.36,.39,.26],[.205,.185,.27],p.dark,'foot'+sign,[0,sign*.12,sign*-.2]);
   this.leaf([sign*.57,1.39,.02],.62,.19,[-.38,0,sign*-2.70],p.leaf,'arm'+sign,false);
   // Dark glossy eyes with amber limbal ring, small pupils and reflected softboxes.
   this.orb([sign*.239,1.29,.491],[.112,.145,.053],p.eye,'eye'+sign,[0,sign*.12,sign*.02],.17);
   this.orb([sign*.239,1.268,.537],[.068,.078,.010],p.iris,'eye'+sign,[0,0,0],.20);
   this.orb([sign*.239,1.293,.547],[.048,.065,.011],p.eye,'pupil'+sign,[0,0,0],.15);
   this.add('sphere',[sign*.239-.032,1.35,.550],[.026,.035,.014],p.light,'eye'+sign,[0,0,-.3],.2,0,.85);
   this.add('sphere',[sign*.239+.029,1.278,.550],[.010,.014,.005],p.light,'eye'+sign,[0,0,0],.2,0,.6);
   this.orb([sign*.395,1.119,.438],[.066,.034,.013],[.91,.40,.28],'body',[0,sign*.18,0],.65);
  }
  const smile=Array.from({length:19},(_,i)=>{let a=Math.PI+Math.PI*i/18;return [.087*Math.cos(a),1.110+.052*Math.sin(a),.553];});this.line(smile,.012,p.eye);
  // Overlapping, softly cupped real leaf surfaces form the hood.
  this.leaf([-.04,1.83,.1],.66,.26,[-.55,-.15,2.3],p.leaf,'crown');
  this.leaf([.05,1.86,.05],.66,.28,[-.70,.15,-2.25],p.bright,'crown');
  this.leaf([.08,1.94,.20],.55,.25,[-.74,.18,3.02],p.bright,'crown');
  this.leaf([-.15,1.86,-.13],.62,.24,[.15,1.1,2.15],p.dark,'crown');
  this.leaf([.23,1.82,-.06],.61,.24,[.2,-.5,-2.11],p.leaf,'crown');
  this.line([[0,1.81,0],[.015,2.05,0],[.07,2.21,.01]],.038,p.dark,'crown');
  this.leaf([.045,2.07,0],.65,.21,[-.06,.03,.92],p.bright,'sprout');
  this.leaf([.065,2.1,0],.78,.25,[-.10,-.14,-.68],p.bright,'sprout');
  // Small woodland acorn pin; diamond-cap texture is geometry, not a painted toy.
  this.orb([.49,1.85,.20],[.14,.18,.13],p.wood,'crown',[0,0,-.60]);
  this.orb([.56,1.94,.19],[.162,.077,.138],p.bark,'crown',[0,0,-.60]);
  for(let i=0;i<5;i++)for(let j=0;j<3;j++){let a=i/5*TAU,t=j/3;this.orb([.56+.132*Math.cos(a)*(1-t*.40),1.943+t*.048,.19+.108*Math.sin(a)*(1-t*.40)],[.018,.009,.016],[.40,.22,.10],'crown',[0,0,-.60]);}
  this.line([[.579,1.98,.19],[.607,2.045,.17],[.655,2.06,.17]],.021,p.wood,'crown');
  // Leaf apron and subtle rooted feet replace fuzzy texture and plastic blob shape.
  for(let sign of [-1,1])this.leaf([sign*.27,.74,.40],.36,.18,[-.16,sign*.18,sign*2.74],p.leaf,'body',false);
  if(this.stage>=2){this.leaf([-.03,2.1,-.03],.9,.23,[.45,0,.18],p.leaf,'sprout');this.leaf([-.52,.82,-.22],.43,.17,[-.5,-.5,1.6],p.bright,'crown',false);}
  if(this.stage>=3){this.leaf([.12,2.05,-.20],.89,.28,[.55,.3,-1.06],p.leaf,'sprout');this.leaf([-.10,2.07,-.23],.88,.29,[.44,.4,1.18],p.bright,'sprout');}
  if(this.stage>=4){this.leaf([.01,2.14,-.27],1.05,.30,[.32,-.5,-.35],p.bright,'sprout');this.leaf([-.13,1.91,-.32],.68,.24,[.8,0,2.0],p.leaf,'crown');for(let sign of [-1,1])this.orb([sign*.32,2.10,.075],[.052,.062,.05],[.66,.36,.08],'crown');}
  // Low moss bed with stones and clover: no flat green toy pedestal.
  this.orb([0,.17,-.03],[.91,.18,.62],p.stone,'ground');this.orb([0,.267,-.04],[.87,.11,.59],p.moss,'ground');
  let rand=(()=>{let s=719;return()=>{s=(1664525*s+1013904223)>>>0;return s/4294967296;};})();
  for(let i=0;i<30;i++){const a=rand()*TAU,r=.65+rand()*.18;this.orb([Math.cos(a)*r,.255+rand()*.047,Math.sin(a)*r*.63],[.06+rand()*.055,.034,.041+rand()*.04],[.14+rand()*.13,.25+rand()*.15,.04+rand()*.04],'ground');}
  for(let side of [-1,1]){this.leaf([side*.69,.29,.17],.21,.07,[0,0,side*-.66],p.bright,'ground',false);this.leaf([side*.73,.29,.17],.18,.06,[.20,0,side*.9],p.leaf,'ground',false);}
  for(const q of [[-.71,.335,.33],[.60,.31,.42]]){for(let i=0;i<5;i++)this.orb([q[0]+Math.cos(i*TAU/5)*.035,q[1]+.02,q[2]+Math.sin(i*TAU/5)*.025],[.027,.010,.025],[.94,.88,.65],'ground');this.orb([q[0],q[1]+.03,q[2]],[.014,.012,.014],[.8,.47,.06],'ground');}
  // Eight restrained fireflies; water and pet effects exist only while interacting.
  for(let i=0;i<8;i++)this.add('sphere',[Math.sin(i*1.7)*1.12,.75+(i%4)*.5,Math.cos(i*1.1)*.25],[.013,.013,.013],[1.,.66,.17],'firefly'+i,[0,0,0],.3,0,.95);
  for(let i=0;i<9;i++)this.add('sphere',[0,3,0],[.021,.047,.021],[.27,.64,.81],'drop'+i,[0,0,0],.15,0,.08);
  this.orb([1.,2.57,.1],[.17,.17,.14],[.18,.41,.37],'can');this.add('ring',[1.15,2.59,.1],[.13,.14,.11],[.47,.57,.38],'can',[0,0,0],.42);this.line([[.86,2.62,.1],[.69,2.57,.13],[.61,2.55,.14]],.047,[.31,.49,.42],'can');
 }
 batch(){
  if(this.options.batch===false)return;
  const groups=new Map();
  for(const n of this.nodes){
   // Skin shading uses object-space coordinates; retain its original geometry.
   const key=n.skin?Symbol():JSON.stringify([n.part,n.col,n.rough,n.metal,n.emissive,n.skin]);
   if(!groups.has(key))groups.set(key,[]);groups.get(key).push(n);
  }
  const output=[];
  for(const group of groups.values()){
   if(group.length===1){output.push(group[0]);continue;}
   let p=[],n=[],idx=[];
   const finish=()=>{if(!p.length)return;const first=group[0];output.push({...first,geo:this.upload({p,n,idx}),matrix:I()});p=[];n=[];idx=[];};
   for(const node of group){const data=node.geo.data,m=node.matrix,N=normalMatrix(m);if(p.length/3+data.p.length/3>65535)finish();const offset=p.length/3;
    for(let i=0;i<data.p.length;i+=3){const x=data.p[i],y=data.p[i+1],z=data.p[i+2];p.push(m[0]*x+m[4]*y+m[8]*z+m[12],m[1]*x+m[5]*y+m[9]*z+m[13],m[2]*x+m[6]*y+m[10]*z+m[14]);const a=data.n[i],b=data.n[i+1],c=data.n[i+2];n.push(...norm([N[0]*a+N[3]*b+N[6]*c,N[1]*a+N[4]*b+N[7]*c,N[2]*a+N[5]*b+N[8]*c]));}
    for(const index of data.idx)idx.push(index+offset);
   }finish();
  }
  const used=new Set(output.map(n=>n.geo)),g=this.gl;
  for(const geo of this.resources)if(!used.has(geo)){g.deleteVertexArray(geo.vao);geo.buffers.forEach(b=>g.deleteBuffer(b));}
  this.resources=this.resources.filter(r=>used.has(r));this.nodes=output;
  for(const geo of this.resources)delete geo.data;
 }
 makeShadow(){const g=this.gl;this.shadowReady=false;this.lightCamera=mul(ortho(-2.25,2.25,-2.25,2.25,.1,16),view([-3.5,6.,5.5],[0,1.4,0]));
 const vs=this.shader(g.VERTEX_SHADER,`#version 300 es\nprecision highp float;layout(location=0)in vec3 position;uniform mat4 camera;uniform mat4 model;void main(){gl_Position=camera*model*vec4(position,1.);}`),fs=this.shader(g.FRAGMENT_SHADER,`#version 300 es\nprecision highp float;void main(){}`);this.sp=g.createProgram();g.attachShader(this.sp,vs);g.attachShader(this.sp,fs);g.linkProgram(this.sp);g.deleteShader(vs);g.deleteShader(fs);if(!g.getProgramParameter(this.sp,g.LINK_STATUS))throw new Error(g.getProgramInfoLog(this.sp));this.sm=g.getUniformLocation(this.sp,'model');this.sc=g.getUniformLocation(this.sp,'camera');
 this.depth=g.createTexture();g.bindTexture(g.TEXTURE_2D,this.depth);g.texImage2D(g.TEXTURE_2D,0,g.DEPTH_COMPONENT24,1024,1024,0,g.DEPTH_COMPONENT,g.UNSIGNED_INT,null);g.texParameteri(g.TEXTURE_2D,g.TEXTURE_MIN_FILTER,g.NEAREST);g.texParameteri(g.TEXTURE_2D,g.TEXTURE_MAG_FILTER,g.NEAREST);g.texParameteri(g.TEXTURE_2D,g.TEXTURE_WRAP_S,g.CLAMP_TO_EDGE);g.texParameteri(g.TEXTURE_2D,g.TEXTURE_WRAP_T,g.CLAMP_TO_EDGE);this.fb=g.createFramebuffer();g.bindFramebuffer(g.FRAMEBUFFER,this.fb);g.framebufferTexture2D(g.FRAMEBUFFER,g.DEPTH_ATTACHMENT,g.TEXTURE_2D,this.depth,0);g.drawBuffers([g.NONE]);g.readBuffer(g.NONE);this.shadowReady=g.checkFramebufferStatus(g.FRAMEBUFFER)===g.FRAMEBUFFER_COMPLETE;g.bindFramebuffer(g.FRAMEBUFFER,null);
 }
 resize(){const c=this.canvas,w=Math.max(1,c.clientWidth||384),h=Math.max(1,c.clientHeight||384),d=clamp(devicePixelRatio||1,1.5,2.5),cw=Math.round(w*d),ch=Math.round(h*d);if(c.width===cw&&c.height===ch&&this.camera)return false;c.width=cw;c.height=ch;this.resizeCount++;this.gl.viewport(0,0,cw,ch);const aspect=w/h,half=1.72;this.eye=[0,2.9,8];this.camera=mul(ortho(-half*aspect,half*aspect,-half,half,.1,30),view(this.eye,[0,1.46,0]));return true;}
 setAction(action){if(!['idle','pet','water','greet'].includes(action))return;if(action==='idle'&&this.action==='idle')return;this.action=action;this.actionStart=this.time;this.render(this.time);}
 setPointer(x,y){this.pointer=[clamp(x,-1,1),clamp(y,-1,1)];}
 setTurn(delta){this.turn=clamp(this.turn+delta,-.65,.65);}
 render(t){if(this.disposed||this.gl.isContextLost())return;const previous=this.lastMotionTime,dt=previous===null?1/60:Math.max(0,Math.min(.25,t-previous));this.lastMotionTime=t;this.time=t;const gl=this.gl,elapsed=t-this.actionStart;const active=this.action!=='idle'&&elapsed<3.2,pet=active&&this.action==='pet',water=active&&this.action==='water',greet=active&&this.action==='greet';if(!active)this.action='idle';const envelope=active?smooth(0,.3,elapsed)*(1-smooth(2.7,3.2,elapsed)):0;const motion=this.options.loopPeriod?t*6/this.options.loopPeriod:t;const wave=Math.sin(motion*TAU/6),breathe=1+.006*wave,ease=1-Math.exp(-8*dt);this.gaze=this.gaze.map((v,i)=>mix(v,this.pointer[i],ease));this.yaw=mix(this.yaw,this.turn,ease);
 const wiggle=pet?Math.sin(elapsed*6)*.055*envelope:0;const root=transform([0,.006*wave,0],[1,breathe,1],[0,this.yaw+this.gaze[0]*.032,wiggle]);
 const crown=mul(root,mul(transform([0,1.80,0],[1,1,1],[0,0,Math.sin(motion*TAU/6)*.022+wiggle*.4]),transform([0,-1.80,0])));
 const sprout=mul(crown,mul(transform([0,2.1,0],[1,1,1],[Math.sin(motion*TAU/3)*.018,0,Math.sin(motion*TAU/3+.5)*.038]),transform([0,-2.1,0])));
 if(t<this.blinkStart-1){this.nextBlink=t+4.9;this.blinkStart=-10;}if(t>=this.nextBlink){this.blinkStart=this.nextBlink;this.nextBlink+=4.3+(Math.sin(++this.blinkIndex*2.4)+1)*1.7;}const blinkBase=this.options.loopPeriod?1-.97*Math.exp(-Math.pow(((motion%6)-4.9)/.095,2)):1-.97*Math.exp(-Math.pow((t-this.blinkStart-.12)/.062,2)),blink=pet?mix(blinkBase,.37,envelope):blinkBase;
 gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(this.program);gl.uniformMatrix4fv(this.u.camera,false,this.camera);gl.uniform3fv(this.u.eye,this.eye);
 const posed=[];for(const n of this.nodes){let parent=root,extra=I();if(n.part==='ground'||n.part==='background')parent=I();else if(n.part==='crown')parent=crown;else if(n.part==='sprout')parent=sprout;
 else if(n.part.startsWith('arm')){const sign=Number(n.part.slice(3));extra=mul(transform([sign*.58,1.40,0],[1,1,1],[0,0,(greet&&sign===1?(Math.sin(elapsed*9)*.24-.68)*envelope:Math.sin(motion*TAU/3)*.022)]),transform([-sign*.58,-1.40,0]));}
 else if(n.part.startsWith('eye')||n.part.startsWith('pupil')){const sign=Number(n.part.replace(/\D/g,''))*(n.part.includes('-')?-1:1);extra=mul(transform([sign*.239,1.29,0],[1,blink,1]),transform([-sign*.239,-1.29,0]));if(n.part.startsWith('pupil'))extra=mul(extra,transform([this.gaze[0]*.012,-this.gaze[1]*.014,0]));}
 else if(n.part.startsWith('firefly')){let i=Number(n.part.slice(7));parent=I();extra=transform([Math.sin((this.options.loopPeriod?motion*TAU/6:t*.53)+i)*.08,Math.cos((this.options.loopPeriod?motion*TAU/6:t*.49)+i)*.07,0],[.70+.30*Math.sin((this.options.loopPeriod?motion*TAU/3:t*1.9)+i)**2,.70+.30*Math.sin((this.options.loopPeriod?motion*TAU/3:t*1.9)+i)**2,1]);}
 else if(n.part.startsWith('drop')){if(!water)continue;const i=Number(n.part.slice(4)),q=(elapsed*.93+i*.11)%1;parent=I();extra=transform([.35+(i%3-1)*.20,2.50-q*1.8-3,.20],[envelope,envelope,envelope]);}
 else if(n.part==='can'){if(!water)continue;parent=mul(transform([1.,2.57,.1],[envelope,envelope,envelope],[0,0,.3+.10*Math.sin(elapsed*4)]),transform([-1.,-2.57,-.1]));}
 const model=mul(parent,mul(extra,n.matrix));posed.push({n,model});
 }
 if(this.shadowReady){gl.bindFramebuffer(gl.FRAMEBUFFER,this.fb);gl.viewport(0,0,1024,1024);gl.clear(gl.DEPTH_BUFFER_BIT);gl.useProgram(this.sp);gl.uniformMatrix4fv(this.sc,false,this.lightCamera);for(const {n,model}of posed){if(n.part.startsWith('firefly')||n.part.startsWith('drop'))continue;gl.bindVertexArray(n.geo.vao);gl.uniformMatrix4fv(this.sm,false,model);gl.drawElements(gl.TRIANGLES,n.geo.count,gl.UNSIGNED_SHORT,0);}gl.bindFramebuffer(gl.FRAMEBUFFER,null);}
 gl.viewport(0,0,this.canvas.width,this.canvas.height);gl.useProgram(this.program);gl.uniformMatrix4fv(this.u.camera,false,this.camera);gl.uniformMatrix4fv(this.u.lightCamera,false,this.lightCamera);gl.uniform3fv(this.u.eye,this.eye);gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,this.depth);gl.uniform1i(this.u.shadowMap,0);gl.uniform1f(this.u.hasShadow,this.shadowReady?1:0);
 for(const {n,model}of posed){gl.bindVertexArray(n.geo.vao);gl.uniformMatrix4fv(this.u.model,false,model);gl.uniformMatrix3fv(this.u.normalModel,false,normalMatrix(model));gl.uniform3fv(this.u.color,n.col);gl.uniform4f(this.u.surface,n.rough,n.metal,n.emissive,n.skin);gl.drawElements(gl.TRIANGLES,n.geo.count,gl.UNSIGNED_SHORT,0);}
 this.draws++;
 }
 start(){if(this.disposed||this.paused||this.hidden||this.raf)return;const frame=now=>{this.raf=0;if(this.disposed||this.paused||this.hidden)return;if(this.last===null)this.last=now;const dt=Math.max(0,Math.min(.25,(now-this.last)/1000));this.last=now;this.render(this.time+dt);this.raf=requestAnimationFrame(frame);};this.last=null;this.raf=requestAnimationFrame(frame);}
 stop(){if(this.raf)cancelAnimationFrame(this.raf);this.raf=0;this.last=null;}
 setPaused(value){this.paused=!!value;if(value)this.stop();else this.start();}
 setHidden(value){this.hidden=!!value;if(value)this.stop();else this.start();}
 dispose(){if(this.disposed)return;this.disposed=true;this.stop();this.ro?.disconnect();this.canvas.removeEventListener('webglcontextlost',this.onLoss);const g=this.gl;for(const r of this.resources){g.deleteVertexArray(r.vao);r.buffers.forEach(b=>g.deleteBuffer(b));}if(this.program)g.deleteProgram(this.program);if(this.sp)g.deleteProgram(this.sp);if(this.depth)g.deleteTexture(this.depth);if(this.fb)g.deleteFramebuffer(this.fb);g.getExtension('WEBGL_lose_context')?.loseContext();this.resources=[];}
 info(){return {renderer:'WebGL2',version:'0.9.7',stage:this.stage,action:this.action,frames:this.draws,time:this.time,drawCalls:this.nodes.length*2,originalNodes:this.unbatchedNodes,buffer:[this.canvas.width,this.canvas.height],resizes:this.resizeCount,nodes:this.nodes.length,triangles:this.nodes.reduce((a,n)=>a+n.geo.count/3,0),paused:this.paused,hidden:this.hidden,disposed:this.disposed};}
}
window.PipScene={Scene,version:'0.9.7'};
})();
