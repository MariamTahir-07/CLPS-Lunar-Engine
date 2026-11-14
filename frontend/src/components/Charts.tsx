import { Analysis } from '../api'
import { fmtUTC } from '../utils'
export function PolarHorizon({az,el}:{az:number[];el:(number|null)[]}){
  if(!az.length) return <p className="mute">No horizon data.</p>
  const R=130,C=150
  const pt=(a:number,e:number)=>{const r=Math.max(0,Math.min(1,(90-e)/90))*R,t=a*Math.PI/180;return `${(C+r*Math.sin(t)).toFixed(1)},${(C-r*Math.cos(t)).toFixed(1)}`}
  const gaps=el.some(v=>v===null)
  const d=az.map((a,i)=>el[i]===null?null:pt(a,el[i] as number))
  const path=d.map((p,i)=>p===null?'':`${i===0||d[i-1]===null?'M':'L'}${p}`).join(' ')+(gaps?'':' Z')
  return <svg viewBox="0 0 300 300" role="img" aria-label="Polar horizon profile" style={{maxWidth:340,width:'100%'}}>
    {[0.33,0.66,1].map(f=><circle key={f} cx={C} cy={C} r={R*f} fill="none" stroke="#243044"/>)}
    <path d={path} fill={gaps?'none':'rgba(110,168,254,.25)'} stroke="#6ea8fe"/>
    {['N','E','S','W'].map((l,i)=><text key={l} x={C+(R+12)*Math.sin(i*Math.PI/2)-4} y={C-(R+12)*Math.cos(i*Math.PI/2)+4} fill="#8b98ad" fontSize="11">{l}</text>)}
  </svg>
}
export function runs(v:boolean[]){ const out:[number,number][]=[]; let s=-1
  v.forEach((x,i)=>{ if(x&&s<0)s=i; if((!x||i===v.length-1)&&s>=0){out.push([s,x?i+1:i]);s=-1} }); return out }
export function Ribbon({label,flags,color}:{label:string;flags:boolean[];color:string}){
  const n=flags.length||1
  return <div><div className="mute">{label}</div>
    <svg viewBox="0 0 600 22" width="100%" role="img" aria-label={label}><rect width="600" height="22" fill="#1b2332" rx="4"/>
      {runs(flags).map(([a,b])=><rect key={a} x={a/n*600} width={Math.max(1,(b-a)/n*600)} height="22" fill={color}/>)}</svg></div>
}
export function TimeAxis({times}:{times:string[]}){
  if(!times.length) return null
  return <div className="mute" style={{display:'flex',justifyContent:'space-between'}}><span>{fmtUTC(times[0])}</span><span>{fmtUTC(times[times.length-1])}</span></div>
}
export function Timeline({tl}:{tl:Analysis['timeline']}){
  return <div><Ribbon label="Sun above geometric horizon" flags={tl.sun_above_geometric_horizon} color="#7a6a2b"/>
    <Ribbon label="Sun visible above terrain" flags={tl.sun_visible} color="#fbbf24"/>
    <Ribbon label="Earth geometrically visible above terrain" flags={tl.earth_visible} color="#6ea8fe"/>
    <TimeAxis times={tl.time_iso}/>
    <p className="mute">Geometric visibility only — not a radio link or usable power. Times are UTC (approximate model).</p></div>
}
export function ElevationChart({times,series}:{times:string[];series:{label:string;values:number[];color:string}[]}){
  const n=times.length
  if(n<2) return <p className="mute">Not enough samples to chart.</p>
  const all=series.flatMap(s=>s.values), lo=Math.min(...all,0), hi=Math.max(...all,0), span=hi-lo||1
  const W=600,H=190,L=34,B=22,T=8
  const x=(i:number)=>L+i/(n-1)*(W-L-6), y=(v:number)=>T+(hi-v)/span*(H-B-T)
  return <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Elevation vs time" width="100%">
    <line x1={L} x2={W-6} y1={y(0)} y2={y(0)} stroke="#8b98ad" strokeDasharray="4 3"/>
    <text x="2" y={y(0)+4} fill="#8b98ad" fontSize="10">0°</text><text x="2" y={T+8} fill="#8b98ad" fontSize="10">{hi.toFixed(0)}°</text>{lo<0&&<text x="2" y={H-B} fill="#8b98ad" fontSize="10">{lo.toFixed(0)}°</text>}
    {series.map(s=><polyline key={s.label} fill="none" stroke={s.color} strokeWidth="1.5" points={s.values.map((v,i)=>`${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')}/>)}
    {series.map((s,i)=><text key={s.label} x={L+8+i*150} y={H-6} fill={s.color} fontSize="11">● {s.label}</text>)}
  </svg>
}
