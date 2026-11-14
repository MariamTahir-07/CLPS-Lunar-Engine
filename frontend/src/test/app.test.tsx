import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { runs } from '../components/Charts'
import { planSamples } from '../utils'
const sites=[{id:'malapert',name:'Malapert Massif',lat:-86,lon:0,provenance:'x',coordinates_verified:false,data_support:{terrain:'synthetic (illustrative)',psr_map:'not loaded'}}]
const w={windows:[{start:'2026-11-14T06:00:00+00:00',end:'2026-11-14T18:00:00+00:00',duration_h:12}],n_windows:1,truncated:false,longest_window_h:12,longest_gap_h:6}
const result={site:{id:'malapert',name:'Malapert Massif',lat:-86,lon:0},labels:{terrain:'illustrative synthetic DEM',geometry:'illustrative analytic model',radius_m:3000,psr_km:'no PSR data loaded',observer_height_m:2,observer_height_label:'configurable engineering assumption'},
 window:{start:'2026-11-14T00:00:00+00:00',end:'2026-11-14T12:00:00+00:00',step_hours:6,n_samples:3,days:0.75},
 slope:{max_deg:4.2,mean_deg:1.1,valid_fraction:1},horizon:{azimuth_deg:[0,90,180,270],elevation_deg:[1,null,0,1],unknown_fraction:0.25,incomplete_fraction:0.5,coverage_min_m:900,coverage_max_m:1000},
 timeline:{time_iso:['2026-11-14T00:00:00+00:00','2026-11-14T06:00:00+00:00','2026-11-14T12:00:00+00:00'],sun_el:[1,-1,2],sun_az:[0,90,180],sun_visible:[true,false,true],sun_above_geometric_horizon:[true,false,true],sun_unknown:[false,false,false],earth_el:[1,1,-1],earth_az:[0,0,0],earth_visible:[true,true,false],earth_unknown:[false,false,false]},
 windows:{sun:w,earth:w},
 decision:{criteria:{slope_deg:{value:4.2,status:'Favorable'},solar_pct:{value:66.7,status:'Marginal'},earth_pct:{value:55.5,status:'Favorable'},psr_km:{value:null,status:'Insufficient data'}},overall:'Insufficient data',disclaimer:'Screening only'}}
const cmpResult={data_mode:'demonstration',real_data:false,notice:'ILLUSTRATIVE ONLY: synthetic terrain.',sites:[{id:'malapert',name:'Malapert Massif',slope_max_deg:9.5,solar_pct:40,earth_pct:61.7,psr_km:null,overall:'Unfavorable',longest_sun_gap_h:30,terrain:'synthetic'}]}
const mockFetch=(fn:(u:string,init?:any)=>any)=>vi.stubGlobal('fetch',vi.fn(async(u:string,i?:any)=>fn(u,i)))
const ok=(j:any)=>({ok:true,status:200,json:async()=>j}), bad=(s:number,j:any)=>({ok:false,status:s,json:async()=>j})
const route=(u:string)=>u.includes('analyze')?ok(result):u.includes('compare')?ok(cmpResult):ok(sites)
const ready=async()=>{ await waitFor(()=>expect(screen.getByRole('option',{name:'Malapert Massif'})).toBeInTheDocument()) }
test('navigation + mode switch',async()=>{
  mockFetch(()=>ok(sites)); render(<App/>); const u=userEvent.setup()
  await u.click(screen.getByText('Data & Methodology')); expect(screen.getByText(/unverified/)).toBeInTheDocument()
  await u.click(screen.getByText('Public Explorer')); await u.click(screen.getByText('Overview'))
  expect(screen.getByText(/Explore how sunlight/)).toBeInTheDocument()
})
test('run analysis shows decision without fake GO',async()=>{
  mockFetch(route); render(<App/>); const u=userEvent.setup(); await ready()
  await u.click(screen.getByText('Run analysis')); await u.click(screen.getByText('Decision Support'))
  await waitFor(()=>expect(screen.getAllByText('Insufficient data').length).toBeGreaterThan(0)); expect(screen.queryByText(/^GO$/)).toBeNull()
})
test('API error message shown',async()=>{
  mockFetch((url:string)=>url.includes('analyze')?bad(422,{detail:'Too many steps'}):ok(sites)); render(<App/>); const u=userEvent.setup(); await ready()
  await u.click(screen.getByText('Run analysis')); expect(await screen.findByText(/Analysis failed: Too many steps/)).toBeInTheDocument()
})
test('backend down shows retry',async()=>{
  mockFetch(()=>{throw new Error('Failed to fetch')}); render(<App/>)
  expect(await screen.findByText(/Cannot reach backend/)).toBeInTheDocument(); expect(screen.getByText('Retry')).toBeInTheDocument()
})
test('simulation page runs the backend and shows ACTUAL returned results',async()=>{
  const f=vi.fn((u:string,i?:any)=>route(u)); mockFetch(f); render(<App/>); const u=userEvent.setup(); await ready()
  await u.click(screen.getByText('Mission Simulation')); expect(screen.getByText(/This run will compute 120 samples/)).toBeInTheDocument()
  await u.click(screen.getByRole('button',{name:'Run simulation'}))
  expect(await screen.findByText('Samples: 3 (every 6 h)')).toBeInTheDocument()
  expect(screen.getByText('66.7%', {selector:'h3'})).toBeInTheDocument(); expect(screen.getByText('55.5%', {selector:'h3'})).toBeInTheDocument()   // Sun and Earth values come straight from the backend payload
  expect(screen.getByText(/Terrain data gaps: 50%/)).toBeInTheDocument()            // data gaps surfaced, not hidden
  const call=f.mock.calls.find(c=>String(c[0]).includes('analyze'))!; const body=JSON.parse((call[1] as any).body)
  expect(body).toMatchObject({site_id:'malapert',start:'2026-11-14T00:00:00Z',days:30,step_hours:6})
})
test('simulation blocks impossible step/duration before calling API',async()=>{
  const f=vi.fn((u:string)=>route(u)); mockFetch(f); render(<App/>); const u=userEvent.setup(); await ready()
  await u.click(screen.getByText('Mission Simulation'))
  const days=screen.getByLabelText('Duration days'); await u.clear(days); await u.type(days,'1')
  await u.selectOptions(screen.getByLabelText('Step hours'),'48')
  expect(screen.getByRole('alert')).toHaveTextContent(/too large/); expect(screen.getByRole('button',{name:'Run simulation'})).toBeDisabled()
  expect(f.mock.calls.some(c=>String(c[0]).includes('analyze'))).toBe(false)
})
test('simulation presets apply',async()=>{
  mockFetch(route); render(<App/>); const u=userEvent.setup(); await ready()
  await u.click(screen.getByText('Mission Simulation')); await u.click(screen.getByText('7 d · 1 h'))
  expect(screen.getByText(/This run will compute 168 samples/)).toBeInTheDocument()
})
test('site comparison is labelled illustrative and unranked',async()=>{
  mockFetch(route); render(<App/>); const u=userEvent.setup(); await ready()
  await u.click(screen.getByText('Lunar Site Explorer')); expect(screen.getByText('coordinates unverified')).toBeInTheDocument()
  await u.click(screen.getByText('Compare all sites'))
  const note=await screen.findByRole('note'); expect(note).toHaveTextContent('ILLUSTRATIVE ONLY')
  expect(screen.getByText(/No ranking is offered/)).toBeInTheDocument()
})
test('comparison error is shown',async()=>{
  mockFetch((u:string)=>u.includes('compare')?bad(422,{detail:'bad period'}):ok(sites)); render(<App/>); const u=userEvent.setup(); await ready()
  await u.click(screen.getByText('Lunar Site Explorer')); await u.click(screen.getByText('Compare all sites'))
  expect(await screen.findByText(/Comparison failed: bad period/)).toBeInTheDocument()
})
test('terrain page warns about unknown horizon azimuths',async()=>{
  mockFetch(route); render(<App/>); const u=userEvent.setup(); await ready()
  await u.click(screen.getByText('Run analysis')); await u.click(screen.getByText('Terrain Analysis'))
  expect(await screen.findByText(/Terrain gaps: horizon unknown for 25%/)).toBeInTheDocument()
})
test('planSamples mirrors backend rules',()=>{
  expect(planSamples(2,6)).toEqual({n:8,error:null}); expect(planSamples(1,12).n).toBe(2)
  expect(planSamples(1,48).error).toMatch(/too large/); expect(planSamples(1,13).error).toMatch(/too large/)
  expect(planSamples(120,0.5).error).toMatch(/Too many/); expect(planSamples(NaN,6).error).toBeTruthy(); expect(planSamples(0.5,0.5).n).toBe(24)
})
test('runs() merges contiguous true samples',()=>{ expect(runs([true,true,false,true])).toEqual([[0,2],[3,4]]); expect(runs([])).toEqual([]) })
