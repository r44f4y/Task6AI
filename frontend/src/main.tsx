import { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Activity, ArrowRight, Building2, ChevronDown, CircleHelp, ClipboardCheck, ClipboardList, Cpu, FileArchive, FileText, FlaskConical, History, Inbox, LayoutDashboard, Menu, Moon, Plus, Radio, Search, Settings2, ShieldCheck, Sun, Upload, Workflow as WorkflowIcon, Zap } from 'lucide-react'
import { api, localDate, modeName } from './api'
import { AuditList, Button, Empty, Modal, Notice, Progress, Status } from './components'
import { Builder } from './Builder'
import { Dashboard } from './Dashboard'
import { Workspace } from './Workspace'
import type { CaseDetail, CaseSummary, DocumentSource, Health, Metrics, Mode, Scenario, Workflow } from './types'
import './styles.css'

const nav=[
  ['Overview',LayoutDashboard],['Unified Inbox',Inbox],['Requests',ClipboardList],['Approval Centre',ClipboardCheck],
  ['Documents and Exports',FileArchive],['Workflow Builder',WorkflowIcon],['Analytics',Activity],['Audit Trail',History],
  ['Demo Scenarios',FlaskConical],['Settings',Settings2],
] as const
const featured=['ontario_bulk-001','ontario_bulk-002','ontario_bulk-003','grandieu-001','fbw_law-001','enabled_talent-001','enabled_talent-002','harbor_repair-001']
const featureDescription=[
  'Check a complete order against the original time and location.',
  'Draft, approve and send a simulated clarification, then process the reply.',
  'Flag an appointment time with no AM or PM and apply a confirmed reply.',
  'Use the synthetic flyer catalogue to answer pricing questions and confirm size.',
  'Calculate a fictional ledger and review two illustrative legal drafts.',
  'Edit and approve a practical plan for a fictional customer support role.',
  'Flag missing information about the employer’s accessibility provisions.',
  'Process an equipment request with a configuration-only workflow.',
]

function App(){
  const [workflows,setWorkflows]=useState<Workflow[]>([])
  const [org,setOrg]=useState(()=>localStorage.getItem('relay-org')||'ontario_bulk')
  const [health,setHealth]=useState<Health|null>(null)
  const [screen,setScreen]=useState('Overview')
  const [origin,setOrigin]=useState('Requests')
  const [records,setRecords]=useState<CaseSummary[]>([])
  const [metrics,setMetrics]=useState<Metrics|null>(null)
  const [scenarioList,setScenarios]=useState<Scenario[]>([])
  const [references,setReferences]=useState<DocumentSource[]>([])
  const [record,setRecord]=useState<CaseDetail|null>(null)
  const [search,setSearch]=useState('')
  const [filter,setFilter]=useState('all')
  const [error,setError]=useState('')
  const [notification,setNotification]=useState('')
  const [theme,setTheme]=useState(()=>localStorage.getItem('relay-theme')||'light')
  const [menu,setMenu]=useState(false)
  const [intake,setIntake]=useState(false)
  const [showReset,setShowReset]=useState(false)
  const [working,setWorking]=useState(false)
  const [model,setModel]=useState('')
  const [mode,setMode]=useState<Mode>('local_ai')
  const [refKind,setRefKind]=useState('Approved reference')
  const selected=workflows.find(w=>w.id===org)||workflows[0]
  const requestToken=useRef(0)

  const loadWorkflows=async()=>setWorkflows(await api<Workflow[]>('/workflows'))
  const loadHealth=async()=>{
    const payload=await api<Health>('/health')
    setHealth(payload);setMode(payload.mode);setModel(payload.model)
  }
  const loadScenarios=async()=>setScenarios(await api<Scenario[]>('/scenarios'))
  async function refreshOrg(target:string){
    const [items,figures,docs]=await Promise.all([
      api<CaseSummary[]>('/orgs/'+target+'/requests'),api<Metrics>('/orgs/'+target+'/metrics'),api<DocumentSource[]>('/orgs/'+target+'/references'),
    ])
    if(localStorage.getItem('relay-org')===target){setRecords(items);setMetrics(figures);setReferences(docs)}
  }
  useEffect(()=>{localStorage.setItem('relay-org',org);void refreshOrg(org).catch(e=>setError(e.message))},[org])
  useEffect(()=>{void Promise.all([loadWorkflows(),loadHealth(),loadScenarios()]).catch(e=>setError(e.message))},[])
  useEffect(()=>{localStorage.setItem('relay-theme',theme);document.documentElement.dataset.theme=theme},[theme])

  function navigate(target:string){
    requestToken.current+=1
    setScreen(target);setRecord(null);setError('');setNotification('');setSearch('');setFilter('all');setMenu(false)
    void refreshOrg(org).catch(e=>setError(e.message))
  }
  function switchOrg(target:string){
    requestToken.current+=1
    setOrg(target);setRecords([]);setMetrics(null);setReferences([]);setRecord(null);setSearch('');setError('');setNotification('')
    if(screen==='Workspace')setScreen('Requests')
  }
  async function open(id:string,target=org){
    const request=++requestToken.current
    setError('');setNotification('');setMenu(false)
    try{
      const detail=await api<CaseDetail>('/orgs/'+target+'/requests/'+id)
      if(request!==requestToken.current)return
      setOrg(target);setRecord(detail);setOrigin(screen==='Workspace'?'Requests':screen);setScreen('Workspace')
      if(detail.unread) await api('/orgs/'+target+'/requests/'+id+'/read','POST')
    }catch(e){if(request===requestToken.current)setError((e as Error).message)}
  }
  function updated(value:CaseDetail){
    setRecord(current=>current?.id===value.id?value:current)
    void refreshOrg(value.org).catch(e=>setError(e.message))
  }
  async function refreshCase(){
    if(record)updated(await api<CaseDetail>('/orgs/'+record.org+'/requests/'+record.id))
  }
  async function run(fn:()=>Promise<void>){
    setWorking(true);setError('');setNotification('')
    try{await fn()}catch(e){setError((e as Error).message)}finally{setWorking(false)}
  }
  async function saveMode(e:React.FormEvent){
    e.preventDefault()
    await run(async()=>{
      const result=await api<Health>('/settings','PUT',{mode,model})
      setHealth(result);setNotification('Processing settings saved.')
    })
  }
  async function uploadReference(file:File){
    const data=new FormData();data.append('file',file);data.append('kind',refKind)
    await run(async()=>{await api('/orgs/'+org+'/references','POST',data);await refreshOrg(org);setNotification('Reference stored locally.')})
  }
  const isList=['Unified Inbox','Requests','Approval Centre','Documents and Exports'].includes(screen)
  const filtered=records.filter(r=>(filter==='all'||(filter==='unread'?r.unread:r.status===filter))&&
    (r.subject+' '+r.sender+' '+r.id).toLowerCase().includes(search.toLowerCase())&&
    (screen==='Approval Centre'?['READY_FOR_REVIEW','APPROVED','REJECTED','EXPORTED'].includes(r.status):
      screen==='Documents and Exports'?['READY_FOR_REVIEW','APPROVED','EXPORTED'].includes(r.status):true))

  return <div className="shell">
    {menu&&<button className="mobile-overlay" aria-label="Close navigation" onClick={()=>setMenu(false)}/>}
    <aside className={'sidebar '+(menu?'is-open':'')}>
      <button className="brand" onClick={()=>navigate('Overview')}><span className="brand-logo"><Zap size={22} fill="currentColor"/></span><span><strong>Relay AI</strong><small>WORKFLOW OPERATIONS</small></span></button>
      <label className="org-switch"><span className="org-icon"><Building2 size={18}/></span><span><small>Organisation</small><select aria-label="Organisation" value={org} onChange={e=>switchOrg(e.target.value)}>{workflows.map(w=><option key={w.id} value={w.id}>{w.name}</option>)}</select></span><ChevronDown size={15}/></label>
      <nav aria-label="Main navigation">{nav.map(([name,Icon],i)=><button key={name} className={(screen===name||screen==='Workspace'&&name===origin?'selected ':'')+(i===8?'nav-separated':'')} onClick={()=>navigate(name)}><Icon size={18}/><span>{name}</span>{name==='Unified Inbox'&&records.some(x=>x.unread)&&<small>{records.filter(x=>x.unread).length}</small>}</button>)}</nav>
      <div className="sidebar-footer"><span className="footer-icon"><ShieldCheck size={17}/></span><div><strong>Local workspace</strong><small>Simulated communications</small></div></div>
    </aside>
    <div className="main-column">
      <header className="topbar"><div><button className="icon-btn mobile-menu" aria-label="Open navigation" onClick={()=>setMenu(true)}><Menu size={21}/></button><span className="top-org">{selected?.name||'Relay AI'}</span><span className="slash">/</span><span>{screen==='Workspace'?'Request workspace':screen}</span></div>
        <div><button className={'mode-pill '+(health?.mode==='offline_demo'?'demo':'')} onClick={()=>navigate('Settings')}><Radio size={15}/>{health?modeName(health.mode):'Checking mode'}</button>
          <span className="health-text"><i className={health?.ready?'online':''}/>{!health?'Checking Ollama':health.ready?health.model:health.available?'Model unavailable':'Ollama offline'}</span>
          <button className="icon-btn theme-button" aria-label={'Switch to '+(theme==='light'?'dark':'light')+' theme'} onClick={()=>setTheme(theme==='light'?'dark':'light')}>{theme==='light'?<Moon size={18}/>:<Sun size={18}/>}</button>
        </div>
      </header>
      <main className={'page '+(screen==='Workspace'?'workspace-page':'')}>
        {error&&<Notice message={error}/>}
        {notification&&<Notice type="success" message={notification}/>}
        {!selected&&!error&&<Empty title="Loading workspace"/>}
        {selected&&(screen==='Overview'||screen==='Analytics')&&metrics&&<Dashboard workflow={selected} metrics={metrics} open={open} navigate={navigate} analytics={screen==='Analytics'}/>}
        {selected&&screen==='Workspace'&&record&&<Workspace key={record.id} record={record} health={health} back={()=>navigate(origin==='Workspace'?'Requests':origin)} backLabel={origin.toLowerCase()} refresh={refreshCase} updated={updated}/>}
        {selected&&isList&&<>
          <div className="page-heading"><div><div className="eyebrow">{selected.title}</div><h1>{screen}</h1><p>{screen==='Unified Inbox'?'Review incoming correspondence and open the associated request.':screen==='Approval Centre'?'Open a record to review its evidence, output and revision history.':screen==='Documents and Exports'?'Manage local reference documents and open records for export.':'Find requests and track progress through the workflow.'}</p></div>
            {['Unified Inbox','Requests'].includes(screen)&&<Button kind="primary" onClick={()=>setIntake(true)}><Plus size={18}/> New intake</Button>}
          </div>
          {screen==='Documents and Exports'&&<section className="card reference-card">
            <div className="card-heading"><h2><FileText size={18}/> Workflow references</h2><div className="inline-form">
              <select aria-label="Reference type" value={refKind} onChange={e=>setRefKind(e.target.value)}>{['Approved reference','Service requirements','Price list','Legal precedent','Accommodation guidance'].map(item=><option key={item}>{item}</option>)}</select>
              <label className="btn secondary upload-label"><Upload size={16}/> Upload reference<input type="file" aria-label="Upload reference" disabled={working} accept=".pdf,.docx,.txt,.csv,.xlsx" onChange={e=>{if(e.target.files?.[0])void uploadReference(e.target.files[0]);e.target.value=''}}/></label></div></div>
            <div className="panel-body">{references.length?references.map(d=><details className="reference" key={d.id}><summary>{d.filename} <small>{d.kind} · v{d.version} · {localDate(d.created)}</small></summary>{d.warning&&<Notice message={d.warning}/>}<p className="message-text">{d.pages.map(p=>p.text).join('\n\n')}</p><a className="link" href={'/api/orgs/'+org+'/documents/'+d.id}>Download original</a></details>):<Empty title="No uploaded references" description="The demonstration workflows include labelled synthetic reference rules."/>}</div>
          </section>}
          <section className="card">
            <div className="table-tools"><div className="search"><Search size={17}/><input placeholder="Search requests…" aria-label="Search requests" value={search} onChange={e=>setSearch(e.target.value)}/></div>
              <select aria-label="Filter requests" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">All statuses</option>{screen==='Unified Inbox'&&<option value="unread">Unread</option>}
                {Array.from(new Set(records.map(r=>r.status))).map(status=><option key={status} value={status}>{status.toLowerCase().replaceAll('_',' ')}</option>)}</select>
              <span className="muted count">{filtered.length} requests</span></div>
            {filtered.length?<div className="table-scroll"><table><thead><tr><th>{screen==='Unified Inbox'?'Message':'Request'}</th><th>Channel</th><th>Status</th><th>Completeness</th><th>{screen==='Approval Centre'?'Reviewer':'Updated'}</th><th><span className="sr-only">Open</span></th></tr></thead>
              <tbody>{filtered.map(r=><tr key={r.id}><td><button className="request-link" onClick={()=>open(r.id)}>{r.unread&&screen==='Unified Inbox'&&<i/>}<span><strong>{r.subject}</strong><small>{r.sender}{r.fixture?' · Synthetic':''}</small></span></button></td><td>{r.channel}</td><td><Status status={r.status}/></td><td><div className="mini-progress"><Progress done={r.resolved} total={r.required}/><small>{r.required?r.resolved+'/'+r.required:'—'}</small></div></td><td>{screen==='Approval Centre'?r.reviewer:localDate(r.updated)}</td><td><button className="icon-btn" aria-label={'Open '+r.subject} onClick={()=>open(r.id)}><ArrowRight size={17}/></button></td></tr>)}</tbody>
            </table></div>:<Empty title="No matching requests" description="Change the filters or try a demo scenario."/>}
          </section>
        </>}
        {selected&&screen==='Workflow Builder'&&<Builder workflow={selected} workflowList={workflows} onSelect={switchOrg} onSaved={async w=>{setOrg(w.id);await loadWorkflows()}} open={open}/>}
        {screen==='Audit Trail'&&metrics&&<><div className="page-heading"><div><div className="eyebrow">Activity</div><h1>Audit Trail</h1><p>Follow intake, processing, human review and export events.</p></div></div><section className="card panel-body"><AuditList items={metrics.activity} open={open}/></section></>}
        {screen==='Demo Scenarios'&&<>
          <div className="page-heading"><div><div className="eyebrow">Brampton AI Innovator · Challenge 6</div><h1>Demo Scenarios</h1><p>{scenarioList.length} fictional scenarios across the four challenge cards and one configuration-only workflow.</p></div><Button onClick={()=>setShowReset(true)}>Reset synthetic demo</Button></div>
          <div className="scenario-grid">{featured.map((id,index)=>{
            const item=scenarioList.find(s=>s.id===id)
            return item&&<div className="card scenario" key={id}><div className="scenario-meta"><span className="stat-icon blue"><FlaskConical size={19}/></span><small>{workflows.find(w=>w.id===item.org)?.name}</small></div><h2>{item.title}</h2><p>{featureDescription[index]}</p><Button onClick={()=>open(item.case_id,item.org)}>Open scenario</Button></div>
          })}</div>
          <details className="card panel-body extra-scenarios"><summary>Browse all seeded scenarios</summary>
            <div className="form-stack"><div className="search"><Search size={16}/><input aria-label="Search scenarios" placeholder="Search scenarios…" value={search} onChange={e=>setSearch(e.target.value)}/></div>
              {scenarioList.filter(s=>(s.title+s.org).toLowerCase().includes(search.toLowerCase())).map(s=><button className="record-link" key={s.id} onClick={()=>open(s.case_id,s.org)}><span>{s.title}</span><small>{workflows.find(w=>w.id===s.org)?.name}</small></button>)}
            </div></details>
        </>}
        {screen==='Settings'&&<>
          <div className="page-heading"><div><div className="eyebrow">Local runtime</div><h1>Settings</h1><p>Choose a processing mode and configure the local Ollama model.</p></div><Button onClick={()=>run(loadHealth)}>Refresh model status</Button></div>
          <div className="settings-grid"><section className="card"><div className="card-heading"><h2><Cpu size={18}/> Processing mode</h2></div><form className="panel-body form-stack" onSubmit={saveMode}>
            <div className="mode-options">{(['local_ai','offline_demo'] as const).map(x=><label className={'mode-option '+(x===mode?'chosen':'')} key={x}><input type="radio" name="mode" checked={x===mode} onChange={()=>setMode(x)}/><span><strong>{modeName(x)}</strong><small>{x==='local_ai'?'Structured extraction and clarification opening generated by Ollama.':'Deterministic extraction from labelled input. Customer replies are prerecorded.'}</small></span></label>)}</div>
            <label>Local model name<input required value={model} onChange={e=>setModel(e.target.value)} list="models"/><datalist id="models">{health?.models.map(x=><option value={x} key={x}/>)}</datalist></label>
            <Button kind="primary" type="submit" busy={working}>Save settings</Button>
          </form></section>
          <section className="card"><div className="card-heading"><h2><ShieldCheck size={18}/> Local connection</h2></div><div className="panel-body form-stack"><dl className="calculation"><div><dt>Ollama service</dt><dd>{health?.available?'Reachable':'Offline'}</dd></div><div><dt>Configured model</dt><dd>{health?.model||'—'}</dd></div><div><dt>Model ready</dt><dd>{health?.ready?'Yes':'No'}</dd></div><div><dt>Endpoint</dt><dd>127.0.0.1:11434</dd></div></dl><p className="muted">Local AI surfaces connection failures. Select Offline demo explicitly to continue with deterministic processing.</p></div></section></div>
        </>}
      </main>
    </div>
    {intake&&selected&&<IntakeForm workflow={selected} close={()=>setIntake(false)} open={(id)=>{setIntake(false);void open(id)}}/>}
    {showReset&&<Modal title="Reset synthetic demo" close={()=>{if(!working)setShowReset(false)}}><div className="form-stack"><p>Restore the seeded scenarios to their original state. This removes changes to seeded requests. Manual requests, saved workflows, reference documents and existing local export files are preserved.</p><div className="form-actions"><Button onClick={()=>setShowReset(false)} disabled={working}>Cancel</Button><Button kind="danger" busy={working} onClick={()=>run(async()=>{await api('/scenarios/reset','POST');await loadScenarios();await refreshOrg(org);setShowReset(false);setNotification('Synthetic demo reset.')})}>Reset scenarios</Button></div></div></Modal>}
  </div>
}

function IntakeForm({workflow,close,open}:{workflow:Workflow;close:()=>void;open:(id:string)=>void}){
  const [channel,setChannel]=useState(workflow.channels[0])
  const [subject,setSubject]=useState('')
  const [sender,setSender]=useState('')
  const [body,setBody]=useState('')
  const [thread,setThread]=useState('')
  const [file,setFile]=useState<File|null>(null)
  const [working,setWorking]=useState(false)
  const [error,setError]=useState('')
  async function submit(e:React.FormEvent){
    e.preventDefault();setWorking(true);setError('')
    try{
      let result:{request:CaseDetail;duplicate:boolean}
      if(file){
        const data=new FormData();data.append('file',file);data.append('org',workflow.id)
        result=await api('/intake/eml','POST',data)
      }else result=await api('/intake','POST',{org:workflow.id,channel,subject,sender,body,thread:thread||null})
      open(result.request.id)
    }catch(e){setError((e as Error).message)}finally{setWorking(false)}
  }
  return <Modal title="New intake" close={()=>{if(!working)close()}}><form className="form-stack" onSubmit={submit}>
    {error&&<Notice message={error}/>}
    {workflow.channels.includes('Email')&&<label>Import .eml (optional)<input type="file" accept=".eml" onChange={e=>setFile(e.target.files?.[0]||null)}/></label>}
    {!file&&<><label>Channel<select value={channel} onChange={e=>setChannel(e.target.value)}>{workflow.channels.map(c=><option key={c}>{c}</option>)}</select></label><label>Subject<input required value={subject} onChange={e=>setSubject(e.target.value)}/></label><label>Sender or customer identifier<input required value={sender} onChange={e=>setSender(e.target.value)}/></label><label>Body<textarea required rows={6} value={body} onChange={e=>setBody(e.target.value)}/></label><label>Existing thread ID (optional)<input value={thread} onChange={e=>setThread(e.target.value)}/></label></>}
    <div className="form-actions"><Button type="button" onClick={close} disabled={working}>Cancel</Button><Button type="submit" kind="primary" busy={working}>Open request</Button></div>
  </form></Modal>
}

createRoot(document.getElementById('root')!).render(<App/>)
