export interface Site { id:string; name:string; lat:number; lon:number; provenance:string; coordinates_verified:boolean; data_support:Record<string,string> }
export interface Criterion { value:number|null; status:string }
export interface Windows { windows:{start:string;end:string;duration_h:number}[]; n_windows:number; truncated:boolean; longest_window_h:number; longest_gap_h:number }
export interface Analysis {
  site:{id:string;name:string;lat:number;lon:number}; labels:Record<string,string|number>;
  window:{start:string;end:string;step_hours:number;n_samples:number;days:number};
  slope:{max_deg:number|null;mean_deg:number|null;valid_fraction:number};
  horizon:{azimuth_deg:number[];elevation_deg:(number|null)[];unknown_fraction:number;incomplete_fraction:number;coverage_min_m:number;coverage_max_m:number};
  timeline:{time_iso:string[];sun_el:number[];sun_az:number[];sun_visible:boolean[];sun_above_geometric_horizon:boolean[];sun_unknown:boolean[];earth_el:number[];earth_az:number[];earth_visible:boolean[];earth_unknown:boolean[]};
  windows:{sun:Windows;earth:Windows};
  decision:{criteria:Record<string,Criterion>;overall:string;disclaimer:string};
}
export interface Params { site_id:string; start:string; days:number; step_hours:number }
export interface CompareRow { id:string; name:string; slope_max_deg:number|null; solar_pct:number|null; earth_pct:number|null; psr_km:number|null; overall:string; longest_sun_gap_h:number; terrain:string }
export interface Comparison { data_mode:string; real_data:boolean; notice:string; sites:CompareRow[] }
async function parse(r:Response){
  if(!r.ok){ const j=await r.json().catch(()=>null); const d=j?.detail
    throw new Error(typeof d==='string'?d:d?JSON.stringify(d):`Server error ${r.status}`) }
  return r.json()
}
const post=(url:string,body:unknown)=>fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
export async function getSites():Promise<Site[]>{ return parse(await fetch('/api/sites')) }
export async function analyze(p:Params):Promise<Analysis>{ return parse(await post('/api/analyze',p)) }
export async function compare(p:Omit<Params,'site_id'>):Promise<Comparison>{ return parse(await post('/api/compare',p)) }
