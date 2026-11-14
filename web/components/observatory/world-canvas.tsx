"use client";

import { useEffect, useRef } from "react";
import type { WorldKey } from "./worlds";

const COLORS: Record<WorldKey, [string, string, string]> = {
  neural: ["#A5A2FF", "#64C9F2", "#7157D8"],
  climate: ["#73E1D0", "#65AFF2", "#287B9A"],
  quantum: ["#A2D3FF", "#BEB0FF", "#5272DA"],
  genetics: ["#F4B9CD", "#93D6F1", "#D274AA"],
  immune: ["#F5C68B", "#76D6BC", "#DA946D"],
};
const pi = Math.PI;
const TAU = 2 * pi;
const rng = (n:number) => { const v = Math.sin(n * 127.1 + 311.7) * 43758.5453; return v - Math.floor(v); };
function circle(ctx: CanvasRenderingContext2D, x:number, y:number, r:number, color:string, alpha=1) {
  ctx.globalAlpha=alpha; ctx.beginPath();ctx.arc(x,y,Math.max(r,0.3),0,TAU); ctx.fillStyle=color;ctx.fill();ctx.globalAlpha=1;
}
function line(ctx:CanvasRenderingContext2D, points:Array<[number,number]>, color:string, alpha:number, width=1){
  ctx.beginPath();points.forEach(([x,y],i)=>i===0?ctx.moveTo(x,y):ctx.lineTo(x,y));ctx.strokeStyle=color;ctx.globalAlpha=alpha;ctx.lineWidth=width;ctx.stroke();ctx.globalAlpha=1;
}
function glow(ctx:CanvasRenderingContext2D,x:number,y:number,r:number,color:string,opacity=.36){
  const g=ctx.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,color);g.addColorStop(.19,color+"80");g.addColorStop(1,color+"00");ctx.globalAlpha=opacity;ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,r,0,TAU);ctx.fill();ctx.globalAlpha=1;
}
function drawNeural(ctx:CanvasRenderingContext2D,w:number,h:number,t:number,colors:string[]){
  const seeds=[[.42,.43],[.68,.35],[.30,.72],[.70,.73],[.50,.63]];
  seeds.forEach(([rx,ry],i)=>{
    const x=w*rx,y=h*ry;glow(ctx,x,y,70,colors[i%2],.23);circle(ctx,x,y,5+(1+Math.sin(t*1.3+i))*1.7,colors[i%2],.9);
    for(let b=0;b<9;b++){
      const angle=b/9*TAU+i*.87;const length=48+rng(i*31+b)*Math.min(w,h)*.22;
      const pts:Array<[number,number]>=[];
      for(let s=0;s<18;s++){let q=s/17; let jitter=Math.sin(q*7+b*1.5+i)*q*11;
        pts.push([x+Math.cos(angle)*length*q+Math.cos(angle+pi/2)*jitter,
          y+Math.sin(angle)*length*q+Math.sin(angle+pi/2)*jitter]);}
      line(ctx,pts,colors[i%2],.12+b%3*.035,.75);
      const q=(t*.13+rng(i*32+b))%1;const idx=Math.min(16,Math.floor(q*17));circle(ctx,pts[idx][0],pts[idx][1],1.5+q*1.2,colors[b%3],.35+(Math.sin(t*2+b)+1)*.15);
      if(b%2===0){const tip=pts[17];circle(ctx,tip[0],tip[1],2.1,colors[i%3],.48);}
    }
  });
}
function drawClimate(ctx:CanvasRenderingContext2D,w:number,h:number,t:number,colors:string[]){
  const cx=w*.52,cy=h*.51,r=Math.min(w*.27,h*.41);
  glow(ctx,cx,cy,r*1.6,colors[1],.15);ctx.save();ctx.translate(cx,cy);
  for(let i=-5;i<=5;i++){const lat=i*pi/12;const ry=Math.sin(lat)*r,rx=Math.cos(lat)*r;
    ctx.beginPath();ctx.ellipse(0,ry,Math.max(2,rx),Math.max(1,rx*.11),0,0,TAU);ctx.lineWidth=.8;ctx.strokeStyle=colors[0];ctx.globalAlpha=.07+(5-Math.abs(i))*.012;ctx.stroke();}
  for(let i=0;i<11;i++){const theta=i*pi/11+t*.055;const pts:Array<[number,number]>=[];
    for(let s=0;s<=34;s++){const lat=-pi/2+(s/34)*pi;pts.push([r*Math.cos(lat)*Math.sin(theta),r*Math.sin(lat)]);}
    line(ctx,pts,colors[1],.17,1);
  }
  ctx.beginPath();ctx.arc(0,0,r,0,TAU);ctx.strokeStyle=colors[0];ctx.globalAlpha=.35;ctx.lineWidth=1.4;ctx.stroke();ctx.restore();ctx.globalAlpha=1;
  for(let k=0;k<24;k++){const baseY=h*(.21+k*.025);const pts:Array<[number,number]>=[];
    for(let s=0;s<65;s++){let x=s/64*w;let y=baseY+Math.sin(x*.008+t*.35+k*.18)*11+Math.cos(x*.014-t*.18+k*.6)*7;pts.push([x,y]);}
    line(ctx,pts,colors[k%2],.035+(k%5)*.015,.65);
  }
  for(let k=0;k<15;k++){const x=(rng(k+61)*w+t*(9+k%4))%(w+40)-20;const y=h*(.18+rng(k+9)*.66)+Math.sin(t*.6+k)*7;circle(ctx,x,y,1.3+(k%3),colors[k%3],.17+.19*(1+Math.sin(t+k*2))/2);}
}
function drawQuantum(ctx:CanvasRenderingContext2D,w:number,h:number,t:number,colors:string[]){
  const cx=w*.53,cy=h*.51;glow(ctx,cx,cy,Math.min(w,h)*.45,colors[2],.16);
  for(let k=0;k<34;k++){
    const pts:Array<[number,number]>=[];
    const row=k-17;
    for(let i=0;i<=120;i++){const x=i/120*w;const phase=x*.019;
      const a=Math.sin(phase-t*.57+row*.12)*21;
      const b=Math.sin(phase*.67+t*.42+row*.16)*17;
      const decay=Math.exp(-Math.pow((x-cx)/(w*.47),2));
      pts.push([x,cy+row*5.3+(a+b)*decay]);}
    line(ctx,pts,colors[k%3],.05+(1-Math.abs(row)/17)*.12,.7);
  }
  for(let i=0;i<6;i++){
    ctx.save();ctx.translate(cx,cy);ctx.rotate((i-2.5)*.3+t*.025);ctx.scale(1,.24+i*.035);
    ctx.beginPath();ctx.arc(0,0,52+i*23,0,TAU);ctx.strokeStyle=colors[i%3];ctx.globalAlpha=.12;ctx.lineWidth=1.3;ctx.stroke();ctx.restore();ctx.globalAlpha=1;
  }
  for(let k=0;k<32;k++){const angle=k*2.4+t*.1;const distance=35+Math.sqrt(k/32)*Math.min(w,h)*.40;const x=cx+Math.cos(angle)*distance;const y=cy+Math.sin(angle)*distance*.56;
    circle(ctx,x,y,1.2+k%4*.4,colors[k%3],.22+.2*(1+Math.sin(t*1.5+k))/2);}
}
function drawGenetics(ctx:CanvasRenderingContext2D,w:number,h:number,t:number,colors:string[]){
  glow(ctx,w*.51,h*.52,Math.min(w,h)*.57,colors[2],.20);
  const n=70;const lhs:Array<[number,number]>=[],rhs:Array<[number,number]>=[];
  for(let i=0;i<n;i++){const q=i/(n-1), y=q*h*.91+h*.045;const angle=q*TAU*3-t*.36;
    const x=w*.52+Math.sin(angle)*w*.15;
    const x2=w*.52-Math.sin(angle)*w*.15;
    lhs.push([x,y]);rhs.push([x2,y]);
    if(i%3===0){const a=.13+.3*Math.abs(Math.cos(angle));line(ctx,[[x,y],[x2,y]],colors[(i/3)%2|0],a,1.3);
      circle(ctx,x,y,1.9,colors[0],.65);circle(ctx,x2,y,1.9,colors[1],.65);}
  }
  line(ctx,lhs,colors[0],.68,2);line(ctx,rhs,colors[1],.62,2);
}
function drawImmune(ctx:CanvasRenderingContext2D,w:number,h:number,t:number,colors:string[]){
  const seeds=[[.30,.44,.20],[.65,.64,.26],[.77,.24,.11],[.24,.76,.10]];
  seeds.forEach(([px,py,pr],i)=>{
    const x=px*w,y=py*h,r=pr*Math.min(w,h);
    glow(ctx,x,y,r*1.8,colors[i%3],.14);
    ctx.beginPath();for(let a=0;a<=96;a++){const q=a/96*TAU;const rr=r*(1+.055*Math.sin(q*7+t*.9+i)+.045*Math.sin(q*13-t*.6));const vx=x+Math.cos(q)*rr,vy=y+Math.sin(q)*rr;if(a===0)ctx.moveTo(vx,vy);else ctx.lineTo(vx,vy);}ctx.closePath();ctx.strokeStyle=colors[i%3];ctx.globalAlpha=.43;ctx.lineWidth=1.5;ctx.stroke();ctx.globalAlpha=1;
    circle(ctx,x,y,Math.max(r*.23,6),colors[i%3],.14);
    for(let k=0;k<13;k++){const q=k/13*TAU+t*.06;const rx=x+Math.cos(q)*r*.78;const ry=y+Math.sin(q)*r*.78;circle(ctx,rx,ry,1.5+k%3,colors[(k+i)%3],.28+(1+Math.sin(t+k))/8);}
  });
  for(let i=0;i<20;i++){const x=rng(i+10)*w,y=rng(i+73)*h;circle(ctx,x+Math.sin(t*.3+i)*8,y+Math.cos(t*.25+i)*9,1.4+(i%3),colors[i%3],.24);}
}
type VisualVariant = "hero" | "performance" | "methodology" | "atlas";
function drawPrecisionLayer(ctx:CanvasRenderingContext2D,w:number,h:number,t:number,colors:string[],variant:VisualVariant,stage:number) {
  ctx.save();
  const ink=colors[0],secondary=colors[1];
  if(variant==="hero") {
    // Minimal instrumentation markers. The domain illustration remains primary.
    ctx.strokeStyle=ink;ctx.globalAlpha=.16;ctx.lineWidth=.8;
    for(let k=0;k<3;k++){let y=h*(.14+k*.35);ctx.beginPath();ctx.moveTo(w*.04,y);ctx.lineTo(w*.12,y);ctx.moveTo(w*.88,y);ctx.lineTo(w*.96,y);ctx.stroke();}
  } else if(variant==="performance") {
    // Data-visualization language: calibrated measuring plane with tiny traces.
    ctx.strokeStyle=ink;ctx.lineWidth=.65;ctx.globalAlpha=.085;
    for(let j=0;j<17;j++){const x=w*(j+1)/18;ctx.beginPath();ctx.moveTo(x,h*.09);ctx.lineTo(x,h*.91);ctx.stroke();}
    for(let j=0;j<9;j++){const y=h*(j+1)/10;ctx.beginPath();ctx.moveTo(w*.07,y);ctx.lineTo(w*.93,y);ctx.stroke();}
    ctx.globalAlpha=.34;ctx.strokeStyle=secondary;
    for(let k=0;k<3;k++){ctx.beginPath();for(let j=0;j<80;j++){const x=w*(.12+j/79*.75);const v=Math.sin(j*.17+k*1.7+t*.32)*h*.028;const y=h*(.26+k*.24)+v;j===0?ctx.moveTo(x,y):ctx.lineTo(x,y);}ctx.stroke();}
  } else if(variant==="methodology") {
    // Stage-specific precision motifs, purposefully separate from the world hero.
    const cx=w*.5,cy=h*.44,unit=Math.min(w,h)*.10;
    ctx.strokeStyle=secondary;ctx.lineWidth=1.1;ctx.globalAlpha=.40;
    if(stage===0){for(let k=0;k<6;k++){const x=w*(.17+k*.14);ctx.strokeRect(x,cy+Math.sin(k*1.4)*unit*.6,unit*.38,unit*1.3);}}
    else if(stage===1){for(let k=0;k<5;k++){const a=TAU*k/5;const x=cx+Math.cos(a)*unit*2.35,y=cy+Math.sin(a)*unit*1.5;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(cx,cy);ctx.stroke();circle(ctx,x,y,3.2,ink,.75);}}
    else if(stage===2){for(let k=-3;k<=3;k++){ctx.beginPath();ctx.moveTo(w*.25,cy+k*unit*.37);ctx.bezierCurveTo(w*.42,cy+k*unit*.28,w*.61,cy-k*unit*.28,w*.78,cy-k*unit*.37);ctx.stroke();}}
    else{ctx.beginPath();ctx.arc(cx,cy,unit*1.8,0,TAU);ctx.stroke();ctx.strokeRect(cx-unit*.65,cy-unit*.8,unit*1.3,unit*1.6);ctx.beginPath();ctx.moveTo(cx-unit*.3,cy);ctx.lineTo(cx,cy+unit*.27);ctx.lineTo(cx+unit*.5,cy-unit*.3);ctx.stroke();}
  } else {
    // Atlas backdrop: thinner laboratory reference traces beneath the real data.
    ctx.globalAlpha=.10;ctx.strokeStyle=secondary;ctx.lineWidth=.7;
    for(let i=0;i<9;i++){const y=h*i/8;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
    for(let i=0;i<17;i++){const x=w*i/16;ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}
  }
  ctx.restore();
}
export function WorldCanvas({world,compact=false,variant="hero",stage=0}:{world:WorldKey;compact?:boolean;variant?:VisualVariant;stage?:number}) {

  const ref=useRef<HTMLCanvasElement>(null);
  useEffect(()=>{
    const canvas=ref.current;if(!canvas)return;
    const ctx=canvas.getContext("2d");if(!ctx)return;
    let raf=0,visible=true,w=1,h=1,dpr=1;
    const reduced=window.matchMedia("(prefers-reduced-motion: reduce)");
    const resize=()=>{const bounds=canvas.getBoundingClientRect();w=Math.max(1,bounds.width);h=Math.max(1,bounds.height);dpr=Math.min(window.devicePixelRatio||1,2);canvas.width=Math.floor(w*dpr);canvas.height=Math.floor(h*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);};
    resize();const observer=new ResizeObserver(resize);observer.observe(canvas);
    const paint=(ms:number)=>{
      if(!visible){raf=requestAnimationFrame(paint);return;}
      const t=reduced.matches?2.3:ms/1000;
      ctx.clearRect(0,0,w,h);
      const fog=ctx.createRadialGradient(w*.57,h*.48,0,w*.57,h*.48,Math.max(w,h)*.63);
      fog.addColorStop(0,COLORS[world][2]+"18");fog.addColorStop(1,"#090F1700");ctx.fillStyle=fog;ctx.fillRect(0,0,w,h);
      const colors=COLORS[world];
      if(world==="neural")drawNeural(ctx,w,h,t,colors);
      else if(world==="climate")drawClimate(ctx,w,h,t,colors);
      else if(world==="quantum")drawQuantum(ctx,w,h,t,colors);
      else if(world==="genetics")drawGenetics(ctx,w,h,t,colors);
      else drawImmune(ctx,w,h,t,colors);
      drawPrecisionLayer(ctx,w,h,t,colors,variant,stage);
      if(!reduced.matches)raf=requestAnimationFrame(paint);
    };
    const onVis=()=>{visible=!document.hidden;};document.addEventListener("visibilitychange",onVis);
    raf=requestAnimationFrame(paint);
    return()=>{cancelAnimationFrame(raf);observer.disconnect();document.removeEventListener("visibilitychange",onVis);};
  },[world,variant,stage]);
  return <canvas ref={ref} aria-hidden="true" className={compact?"obs-canvas obs-canvas-small":"obs-canvas"}/>;
}
