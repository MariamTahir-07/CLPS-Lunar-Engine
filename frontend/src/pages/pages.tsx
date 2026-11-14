import { Analysis, Comparison, Site } from '../api'
import { PolarHorizon, Timeline } from '../components/Charts'
export type Mode='planner'|'public'
interface P{ a:Analysis|null; mode:Mode }
const f=(v:number|null|undefined,d=1,u='')=>v==null?'n/a':v.toFixed(d)+u
const None=()=><div className="card"><p>No analysis yet. Choose a site and press <b>Run analysis</b>.</p></div>
const Tag=({t}:{t:string})=><span className="tag">{t}</span>
export const Overview=({mode}:{mode:Mode})=><div className="card"><h2>CLPS Lunar Landing Site &amp; Hardware Protection Engine</h2>
  <p>{mode==='public'?'Explore how sunlight and a view of Earth change at candidate spots near the Moon’s south pole.':'Terrain horizon, Sun/Earth geometric visibility and threshold screening for south-polar candidate sites.'}</p>
  <p className="mute">Current build runs in <b>demonstration mode</b>: terrain is synthetic and Sun/Earth geometry is an analytic approximation, not NASA data.</p></div>
export const Explorer=({sites,site,onSelect,cmp,cmpErr,cmpLoading,onCompare}:{sites:Site[];site:string;onSelect:(id:string)=>void;cmp:Comparison|null;cmpErr:string|null;cmpLoading:boolean;onCompare:()=>void})=><div>
  <div className="grid">{sites.map(s=><div className="card" key={s.id} style={s.id===site?{borderColor:'var(--acc)'}:undefined} aria-current={s.id===site}>
    <h3>{s.name} {s.id===site&&<span className="tag">selected</span>}</h3><p>Lat {s.lat}°, Lon {s.lon}°</p>
    <span className="tag">{s.coordinates_verified?'coordinates verified':'coordinates unverified'}</span>
    <ul className="mute">{Object.entries(s.data_support).map(([k,v])=><li key={k}><b>{k.replace(/_/g,' ')}:</b> {v}</li>)}</ul>
    <button className={s.id===site?'on':''} onClick={()=>onSelect(s.id)}>{s.id===site?'Selected':'Select this site'}</button></div>)}</div>
  <div className="card"><h3>Compare sites</h3>
    <p className="mute">Runs the same period and step (set on the Mission Simulation page) for every candidate.</p>
    <button onClick={onCompare} disabled={cmpLoading||!sites.length}>{cmpLoading?'Comparing…':'Compare all sites'}</button>
    {cmpErr&&<p className="Unfavorable" role="alert">Comparison failed: {cmpErr}</p>}
    {cmp&&<><p className={cmp.real_data?'mute':'Marginal'} role="note"><b>{cmp.notice}</b></p>
      <table><thead><tr><th>Site</th><th>Max slope °</th><th>Sun %</th><th>Earth %</th><th>PSR km</th><th>Longest Sun gap h</th><th>Screening</th></tr></thead><tbody>
      {cmp.sites.map(r=><tr key={r.id}><td>{r.name}</td><td>{f(r.slope_max_deg)}</td><td>{f(r.solar_pct)}</td><td>{f(r.earth_pct)}</td><td>{f(r.psr_km)}</td><td>{f(r.longest_sun_gap_h)}</td><td className={r.overall.split(' ')[0]}>{r.overall}</td></tr>)}</tbody></table>
      <p className="mute">{cmp.data_mode==='demonstration'?'All values illustrative. No ranking is offered.':'Values depend on the supplied DEM; no ranking is offered.'}</p></>}
  </div></div>
export const Terrain=({a,mode}:P)=>!a?<None/>:<div className="card"><h2>Terrain &amp; horizon</h2><Tag t={String(a.labels.terrain)}/>
  {(a.horizon.incomplete_fraction>0||a.horizon.unknown_fraction>0)&&<p className="Marginal" role="alert">Terrain gaps: horizon unknown for {f(a.horizon.unknown_fraction*100,0,'%')} of azimuths; {f(a.horizon.incomplete_fraction*100,0,'%')} incomplete (lower bound).</p>}
  <p>Max slope {f(a.slope.max_deg,1,'°')} · mean {f(a.slope.mean_deg,1,'°')} · valid data {f(a.slope.valid_fraction*100,0,'%')}</p>
  <PolarHorizon az={a.horizon.azimuth_deg} el={a.horizon.elevation_deg}/>
  <p className="mute">{mode==='public'?'The blue shape shows how high hills block the sky in each direction. Slope alone does not prove a landing is safe.':`Horizon computed to ${a.labels.radius_m} m radius with exact spherical curvature; ${a.horizon.azimuth_deg.length} azimuths; coverage ${f(a.horizon.coverage_min_m,0)}–${f(a.horizon.coverage_max_m,0)} m.`}</p></div>
const pct=(v:boolean[])=>v.length?100*v.filter(Boolean).length/v.length:null
export const Solar=({a,mode}:P)=>!a?<None/>:<div className="card"><h2>Solar visibility</h2><Tag t={String(a.labels.geometry)}/>
  <p>Above geometric horizon: {f(pct(a.timeline.sun_above_geometric_horizon),1,'%')} · Visible above terrain: <b>{f(a.decision.criteria.solar_pct.value,1,'%')}</b></p>
  <Timeline tl={a.timeline}/><p className="mute">{mode==='public'?'Yellow = the Sun can be seen from the site. This is not electricity: panels, angle and efficiency are not modelled.':'Electrical power is not computed (no hardware assumptions).'}</p></div>
export const Earth=({a,mode}:P)=>!a?<None/>:<div className="card"><h2>Earth / DTE geometry</h2><Tag t={String(a.labels.geometry)}/>
  <p>Earth visible above terrain: <b>{f(a.decision.criteria.earth_pct.value,1,'%')}</b></p><Timeline tl={a.timeline}/>
  <p className="mute">{mode==='public'?'Seeing Earth is necessary but does not guarantee radio contact.':'No link budget, antenna or frequency modelled; geometric line of sight only.'}</p></div>
export const Decision=({a,mode}:P)=>!a?<None/>:<div className="card"><h2>Screening result: <span className={a.decision.overall.split(' ')[0]}>{a.decision.overall}</span></h2>
  <table><thead><tr><th>Criterion</th><th>Value</th><th>Status</th></tr></thead><tbody>
  {Object.entries(a.decision.criteria).map(([k,c])=><tr key={k}><td>{k}</td><td>{f(c.value,1)}</td><td className={c.status.split(' ')[0]}>{c.status}</td></tr>)}</tbody></table>
  <p className="mute">{a.decision.disclaimer} Thresholds are configurable engineering assumptions. {a.labels.psr_km}.{mode==='public'?' “Insufficient data” means we cannot judge yet.':''}</p></div>
export const Methodology=()=><div className="card"><h2>Data &amp; methodology</h2><ul>
  <li><Tag t="illustrative"/> Terrain: seeded synthetic DEM (not LOLA).</li><li><Tag t="illustrative"/> Sun/Earth: simplified analytic model (not SPICE/DE440).</li>
  <li><Tag t="calculated"/> Slope (finite differences), horizon (ray march with d²/2R curvature), visibility masks, threshold classification.</li>
  <li><Tag t="assumption"/> Decision thresholds from the project architecture guide; not NASA requirements.</li>
  <li>The ~870 m PA→ME displacement is <b>unverified</b> here; it must be computed from NAIF frame kernels.</li></ul></div>
