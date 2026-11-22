import { useEffect, useState } from 'react'
import { Activity, ArrowDownRight, ArrowUpRight, ChartNoAxesColumn, CheckCheck, CircleHelp, ClipboardList, Clock3, Inbox, ShieldCheck } from 'lucide-react'
import { api, label, localDate, modeName } from './api'
import { AuditList, Button, Empty } from './components'
import type { Metrics, Workflow } from './types'

export function Dashboard({workflow,metrics,open,navigate,analytics=false}:{workflow:Workflow;metrics:Metrics;open:(id:string)=>void;navigate:(screen:string)=>void;analytics?:boolean}){
  const [organizations,setOrganizations]=useState<{org:string;name:string;count:number}[]>([])
  useEffect(()=>{
    if(analytics)void api<typeof organizations>('/metrics/organizations').then(setOrganizations).catch(()=>setOrganizations([]))
  },[analytics,workflow.id,metrics.total])
  const queued=(metrics.status.AWAITING_INFORMATION||0)+(metrics.status.NEEDS_CLARIFICATION||0)+(metrics.status.CONFLICT_DETECTED||0)
  const cards=[
    {title:'Total requests',value:metrics.total,detail:(metrics.status.NEW||0)+' new in inbox',icon:Inbox,tone:'blue'},
    {title:'Needs attention',value:queued,detail:'Missing, ambiguous or conflicting',icon:CircleHelp,tone:'amber'},
    {title:'Ready for review',value:metrics.status.READY_FOR_REVIEW||0,detail:workflow.reviewer+' queue',icon:ShieldCheck,tone:'violet'},
    {title:'Approved',value:(metrics.status.APPROVED||0)+(metrics.status.EXPORTED||0),detail:(metrics.status.EXPORTED||0)+' exported locally',icon:CheckCheck,tone:'green'},
  ]
  const status=Object.entries(metrics.status)
  const missing=Object.entries(metrics.missing).sort((a,b)=>b[1]-a[1]).slice(0,5)
  return <>
    <div className="page-heading"><div><div className="eyebrow">{workflow.industry} operations</div><h1>{analytics?'Analytics':'Workflow overview'}</h1><p>{workflow.description}</p></div>
      {!analytics&&<Button kind="primary" onClick={()=>navigate('Unified Inbox')}><Inbox size={17}/> Open unified inbox</Button>}
    </div>
    {!analytics&&<section className="overview-banner"><div><span className="banner-label"><span/> Active workflow</span><h2>{workflow.title}</h2><p>{workflow.channels.join(' · ')} intake <span> / </span> {workflow.reviewer} review <span> / </span> {workflow.output.toUpperCase()} export</p></div><div className="banner-art" aria-hidden="true"><span><Inbox/></span><b/><span><ClipboardList/></span><b/><span><ShieldCheck/></span></div></section>}
    <div className="metric-grid">{cards.map(({title,value,detail,icon:Icon,tone})=><div className="card metric" key={title}><div className="metric-top"><span className={'stat-icon '+tone}><Icon size={19}/></span><span>{title}</span></div><strong>{value}</strong><small>{detail}</small></div>)}</div>
    <div className="dashboard-grid">
      <section className="card"><div className="card-heading"><h2><ChartNoAxesColumn size={18}/> Request status</h2><span className="plain-chip">{metrics.total} total</span></div><div className="panel-body chart-body">
        {status.length?status.map(([key,value])=><div className="bar-row" key={key}><span>{label(key)}</span><div><i style={{width:value/metrics.total*100+'%'}}/></div><strong>{value}</strong></div>):<Empty title="No requests yet"/>}
      </div></section>
      <section className="card"><div className="card-heading"><h2><Activity size={18}/> Processing activity</h2></div><div className="panel-body processing-metrics">
        <div><span className="stat-icon green"><CheckCheck size={19}/></span><div><strong>{metrics.completeness}%</strong><small>Required fields resolved</small></div></div>
        <div><span className="stat-icon blue"><Clock3 size={19}/></span><div><strong>{metrics.average_ms===null?'—':(metrics.average_ms/1000).toFixed(2)+'s'}</strong><small>Average measured processing time</small></div></div>
        <div><span className="stat-icon violet"><ArrowDownRight size={19}/></span><div><strong>{metrics.processed}</strong><small>Requests with validation results</small></div></div>
      </div></section>
    </div>
    {analytics&&<div className="dashboard-grid">
      <section className="card"><div className="card-heading"><h2>Most frequently missing</h2></div><div className="panel-body chart-body">{missing.length?missing.map(([key,value])=><div className="bar-row" key={key}><span>{key}</span><div><i style={{width:value/Math.max(...missing.map(i=>i[1]))*100+'%'}}/></div><strong>{value}</strong></div>):<Empty title="No missing fields recorded"/>}</div></section>
      <section className="card"><div className="card-heading"><h2>Request volume</h2></div><div className="panel-body chart-body">{Object.entries(metrics.volume).sort().map(([key,value])=><div className="bar-row" key={key}><span>{key}</span><div><i style={{width:value/metrics.total*100+'%'}}/></div><strong>{value}</strong></div>)}</div></section>
      <section className="card"><div className="card-heading"><h2>Requests by organisation</h2></div><div className="panel-body chart-body">{organizations.length?organizations.map(item=><div className="bar-row" key={item.org}><span>{item.name}</span><div><i style={{width:item.count/Math.max(1,...organizations.map(o=>o.count))*100+'%'}}/></div><strong>{item.count}</strong></div>):<Empty title="No organisation counts available"/>}</div></section>
      <section className="card"><div className="card-heading"><h2>Recent measured runs</h2></div><div className="panel-body">{metrics.runs.length?metrics.runs.slice(-8).reverse().map((r,i)=><div className="record-link" key={i}><span>{modeName(r.mode)} · {localDate(r.at,true)}</span><small>{r.success?(r.elapsed_ms||0)+' ms':'Failed'}</small></div>):<Empty title="No processing runs"/>}</div></section>
    </div>}
    <section className="card"><div className="card-heading"><h2><Activity size={18}/> Recent activity</h2><button className="link" onClick={()=>navigate('Audit Trail')}>View audit trail <ArrowUpRight size={15}/></button></div><div className="panel-body"><AuditList items={metrics.activity.slice(0,6)} open={open}/></div></section>
  </>
}
