import { Analysis, Site, Windows } from '../api'
import { ElevationChart, Timeline } from '../components/Charts'
import { STEP_OPTIONS, fmtUTC, planSamples } from '../utils'
export interface SimParams { site:string; start:string; days:number; step:number }
const PRESETS:[string,number,number][]=[['7 d · 1 h',7,1],['30 d · 6 h',30,6],['90 d · 12 h',90,12]]
const f=(v:number|null|undefined,d=1,u='')=>v==null?'n/a':v.toFixed(d)+u
function WindowTable({title,w}:{title:string;w:Windows}){
  return <div><h4>{title}</h4><p className="mute">{w.n_windows} window(s) · longest {f(w.longest_window_h,1,' h')} · longest gap {f(w.longest_gap_h,1,' h')}</p>
    {w.windows.length>0&&<table><thead><tr><th>Start (UTC)</th><th>End (UTC)</th><th>Hours</th></tr></thead><tbody>
      {w.windows.slice(0,10).map(x=><tr key={x.start}><td>{fmtUTC(x.start)}</td><td>{fmtUTC(x.end)}</td><td>{x.duration_h}</td></tr>)}</tbody></table>}
    {w.windows.length>10&&<p className="mute">Showing first 10 of {w.n_windows}.</p>}</div>
}
export default function Simulation({sites,p,setP,onRun,loading,a,mode}:{sites:Site[];p:SimParams;setP:(p:SimParams)=>void;onRun:()=>void;loading:boolean;a:Analysis|null;mode:'planner'|'public'}){
  const plan=planSamples(p.days,p.step)
  const tl=a?.timeline
  return <div>
    <div className="card"><h2>Mission simulation</h2>
      <p className="mute">Sun and Earth geometry over a chosen UTC period, combined with the site’s terrain horizon. Time system: UTC (approximate analytic model). Supported range 2020–2040.</p>
      <div style={{display:'flex',flexWrap:'wrap',gap:12,alignItems:'end'}}>
        <label>Site<br/><select aria-label="Simulation site" value={p.site} onChange={e=>setP({...p,site:e.target.value})}>{sites.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
        <label>Start (UTC)<br/><input aria-label="Start date and time" type="datetime-local" value={p.start} min="2020-01-01T00:00" max="2040-12-31T00:00" onChange={e=>setP({...p,start:e.target.value})}/></label>
        <label>Duration (days)<br/><input aria-label="Duration days" type="number" min={0.5} max={120} step={0.5} value={p.days} style={{width:90}} onChange={e=>setP({...p,days:+e.target.value})}/></label>
        <label>Step (hours)<br/><select aria-label="Step hours" value={p.step} onChange={e=>setP({...p,step:+e.target.value})}>{STEP_OPTIONS.map(s=><option key={s} value={s}>{s}</option>)}</select></label>
        <button onClick={onRun} disabled={loading||!!plan.error||!p.start||!sites.length}>{loading?'Running…':'Run simulation'}</button></div>
      <p style={{marginTop:10}}>{PRESETS.map(([l,d,s])=><button key={l} style={{marginRight:6}} onClick={()=>setP({...p,days:d,step:s})}>{l}</button>)}</p>
      {plan.error?<p className="Unfavorable" role="alert">{plan.error}</p>:<p className="mute">This run will compute {plan.n} samples.</p>}
    </div>
    {!a||!tl?<div className="card"><p>No simulation results yet. Choose parameters and press <b>Run simulation</b>.</p></div>:<>
      <div className="grid">
        <div className="card"><div className="mute">Period</div><div>{fmtUTC(a.window.start)} →<br/>{fmtUTC(a.window.end)}</div><div className="mute">{`Samples: ${a.window.n_samples} (every ${a.window.step_hours} h)`}</div></div>
        <div className="card"><div className="mute">Sun visible above terrain</div><h3>{f(a.decision.criteria.solar_pct.value,1,'%')}</h3><div className="mute">longest dark gap {f(a.windows.sun.longest_gap_h,1,' h')}</div></div>
        <div className="card"><div className="mute">Earth visible above terrain</div><h3>{f(a.decision.criteria.earth_pct.value,1,'%')}</h3><div className="mute">longest gap {f(a.windows.earth.longest_gap_h,1,' h')}</div></div></div>
      {(a.horizon.incomplete_fraction>0||a.horizon.unknown_fraction>0)&&<div className="card err" role="alert">Terrain data gaps: {f(a.horizon.incomplete_fraction*100,0,'%')} of azimuths have incomplete rays and {f(a.horizon.unknown_fraction*100,0,'%')} are unknown; visibility there is a lower bound or excluded.</div>}
      <div className="card"><h3>Elevation above local horizontal</h3>
        <ElevationChart times={tl.time_iso} series={[{label:'Sun',values:tl.sun_el,color:'#fbbf24'},{label:'Earth',values:tl.earth_el,color:'#6ea8fe'}]}/>
        <Timeline tl={tl}/>
        <p className="mute">{mode==='public'?'When a line is above 0° the body is above a flat horizon; the coloured bars show when hills do not block it.':`Sun/Earth centre vs terrain horizon (observer height ${a.labels.observer_height_m} m, ${a.labels.observer_height_label}). Geometry: ${a.labels.geometry}.`}</p></div>
      <div className="card"><WindowTable title="Sun visibility windows" w={a.windows.sun}/><WindowTable title="Earth visibility windows" w={a.windows.earth}/></div>
      <p className="mute">Terrain: {String(a.labels.terrain)}.</p></>}
  </div>
}
