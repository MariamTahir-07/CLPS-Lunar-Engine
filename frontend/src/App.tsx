import { useEffect, useState } from 'react'
import { analyze, compare, getSites, Analysis, Comparison, Site } from './api'
import * as P from './pages/pages'
import Simulation, { SimParams } from './pages/Simulation'
import { planSamples, toApiStart } from './utils'
const NAV=['Overview','Lunar Site Explorer','Terrain Analysis','Solar Analysis','Earth / DTE Analysis','Mission Simulation','Decision Support','Data & Methodology']
export default function App(){
  const [page,setPage]=useState(0), [mode,setMode]=useState<P.Mode>('planner')
  const [sites,setSites]=useState<Site[]>([]), [sitesErr,setSitesErr]=useState<string|null>(null)
  const [sim,setSim]=useState<SimParams>({site:'connecting_ridge',start:'2026-11-14T00:00',days:30,step:6})
  const [a,setA]=useState<Analysis|null>(null), [loading,setLoading]=useState(false), [err,setErr]=useState<string|null>(null)
  const [cmp,setCmp]=useState<Comparison|null>(null), [cmpErr,setCmpErr]=useState<string|null>(null), [cmpLoading,setCmpLoading]=useState(false)
  const loadSites=()=>{setSitesErr(null);getSites().then(list=>{setSites(list);setSim(s=>list.length&&!list.some(x=>x.id===s.site)?{...s,site:list[0].id}:s)}).catch(e=>setSitesErr(e.message))}
  useEffect(loadSites,[])
  const plan=planSamples(sim.days,sim.step)
  const run=async()=>{ if(plan.error){setErr(plan.error);return}
    setLoading(true); setErr(null)
    try{ setA(await analyze({site_id:sim.site,start:toApiStart(sim.start),days:sim.days,step_hours:sim.step})) }catch(e){ setErr((e as Error).message) } finally{ setLoading(false) } }
  const doCompare=async()=>{ setCmpLoading(true); setCmpErr(null)
    try{ setCmp(await compare({start:toApiStart(sim.start),days:sim.days,step_hours:sim.step})) }catch(e){ setCmp(null); setCmpErr((e as Error).message) } finally{ setCmpLoading(false) } }
  const common={a,mode}
  const pages=[<P.Overview mode={mode}/>,<P.Explorer sites={sites} site={sim.site} onSelect={id=>setSim({...sim,site:id})} cmp={cmp} cmpErr={cmpErr} cmpLoading={cmpLoading} onCompare={doCompare}/>,
    <P.Terrain {...common}/>,<P.Solar {...common}/>,<P.Earth {...common}/>,
    <Simulation sites={sites} p={sim} setP={setSim} onRun={run} loading={loading} a={a} mode={mode}/>,<P.Decision {...common}/>,<P.Methodology/>]
  return <div><header><b>CLPS Lunar Engine</b><div>
    <button className={mode==='planner'?'on':''} onClick={()=>setMode('planner')}>Mission Planner</button>{' '}
    <button className={mode==='public'?'on':''} onClick={()=>setMode('public')}>Public Explorer</button></div></header>
    <nav aria-label="Main">{NAV.map((n,i)=><button key={n} className={i===page?'on':''} onClick={()=>setPage(i)}>{n}</button>)}</nav>
    <main>
      <div className="card"><label>Site <select aria-label="Site" value={sim.site} onChange={e=>setSim({...sim,site:e.target.value})}>
        {sites.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>{' '}
        <button onClick={run} disabled={loading||!sites.length||!!plan.error}>{loading?'Running…':'Run analysis'}</button>{' '}
        <span className="mute">{sim.start.replace('T',' ')} UTC · {sim.days} d · {sim.step} h step (edit on Mission Simulation)</span></div>
      {sitesErr&&<div className="card err" role="alert">Cannot reach backend: {sitesErr} <button onClick={loadSites}>Retry</button></div>}
      {err&&<div className="card err" role="alert">Analysis failed: {err}</div>}
      {pages[page]}
    </main></div>
}
