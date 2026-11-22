import { useEffect, useState } from 'react'
import { ArrowLeft, BookOpen, Check, ClipboardList, Download, FileText, Mail, MessageSquare, Paperclip, Pencil, Send, ShieldCheck, Sparkles, TriangleAlert } from 'lucide-react'
import { api, label, localDate, modeName, saveBlob } from './api'
import { AuditList, Button, Empty, Modal, Notice, Progress, Status } from './components'
import type { CaseDetail, Evidence, FieldSpec, Health, Output, Value } from './types'

export const textValue=(value:Value|undefined)=>value === true ? 'Yes' : value === false ? 'No' : value ?? ''
type Props={record:CaseDetail;health:Health|null;back:()=>void;backLabel:string;refresh:()=>Promise<void>;updated:(r:CaseDetail)=>void}
type Dialog='correction'|'review'|'export'|'staff'|'reply'|null

function revealInPanel(target:Element|null,panelClass:string){
  if(!target)return
  const panel=target.closest(panelClass)
  if(panel && panel.scrollHeight>panel.clientHeight){
    const offset=target.getBoundingClientRect().top-panel.getBoundingClientRect().top
    panel.scrollTo({top:Math.max(0,panel.scrollTop+offset-8)})
  }else{
    target.scrollIntoView({block:'nearest'})
  }
}

export function Workspace({record,health,back,backLabel,refresh,updated}:Props) {
  const [busy,setBusy]=useState('')
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const [section,setSection]=useState('Fields')
  const [sourceTab,setSourceTab]=useState('Conversation')
  const [activeSource,setActiveSource]=useState('')
  const [activeField,setActiveField]=useState('')
  const [field,setField]=useState<FieldSpec|null>(null)
  const [dialog,setDialog]=useState<Dialog>(null)
  const [entry,setEntry]=useState('')
  const [comment,setComment]=useState('')
  const [reviewDecision,setReviewDecision]=useState('approve')
  const [draft,setDraft]=useState('')
  const [prior,setPrior]=useState<number|null>(null)
  const base='/orgs/'+record.org+'/requests/'+record.id
  const currentDraft=record.state.draft
  const draftVersion={draft_id:currentDraft?.id,draft_version:currentDraft?.edit_version??1}
  const output=record.state.output
  const selectedOutput=prior===null ? output : record.state.output_history[prior]
  const approved=['APPROVED','EXPORTED'].includes(record.status)
  const ready=record.status==='READY_FOR_REVIEW'
  const pending=record.status==='NEW'
  const canReply=record.reply_available &&
    ((currentDraft?.status==='sent'&&!currentDraft.reply_received) || (record.reply_without_draft && !pending))
  const review={revision:record.revision,role:record.workflow.reviewer,comment,decision:reviewDecision}

  useEffect(()=>{setDraft(currentDraft?.text||'')},[currentDraft?.text])
  async function perform(title:string,run:()=>Promise<void>) {
    setError('');setNotice('');setBusy(title)
    try{await run()}catch(err){setError((err as Error).message)}finally{setBusy('')}
  }
  const mutate=(action:string,title:string,data?:unknown,method='POST')=>perform(title,async()=>{
    updated(await api<CaseDetail>(base+action,method,data))
  })
  async function upload(file:File){
    const data=new FormData();data.append('file',file)
    await mutate('/attachments','attachment',data)
    setSourceTab('Attachments')
  }
  function evidence(e:Evidence){
    setSourceTab(e.page!==null || record.attachments.some(a=>e.source.startsWith(a.id+':'))?'Attachments':'Conversation')
    setActiveSource(e.source.split(':')[0])
  }
  function edit(f:FieldSpec){
    setField(f);setEntry(String(textValue(record.fields[f.key]?.value ?? record.fields[f.key]?.raw)));setComment('');setDialog('correction')
  }
  function requestReview(decision:string){
    setReviewDecision(decision);setComment('');setDialog('review')
  }
  async function submitDialog(event:React.FormEvent){
    event.preventDefault()
    await perform(dialog||'',async()=>{
      if(dialog==='correction'&&field){
        updated(await api(base+'/fields/'+field.key,'PATCH',{revision:record.revision,value:entry||null,reason:comment}))
      }else if(dialog==='review'){
        updated(await api(base+'/review','POST',review))
      }else if(dialog==='export'){
        const zip=await api<Blob>(base+'/export','POST',{directory:entry.trim()||null})
        saveBlob(zip,'relay-'+record.id+'.zip')
        await refresh()
        setNotice('Approved package saved locally and downloaded.')
      }else if(dialog==='staff'){
        updated(await api(base+'/output','PATCH',{text:entry,revision:record.revision}));setPrior(null)
      }else if(dialog==='reply'){
        await api('/intake','POST',{org:record.org,channel:record.channel,subject:record.subject,sender:record.sender,body:entry,thread:record.thread})
        await refresh()
      }
      setDialog(null)
    })
  }
  useEffect(()=>{
    if(activeSource)revealInPanel(document.querySelector('[data-source-id="'+activeSource+'"]'),'.source-list')
  },[activeSource,sourceTab])
  useEffect(()=>{
    if(activeField&&section==='Fields')revealInPanel(document.querySelector('[data-field-key="'+activeField+'"]'),'.field-list')
  },[activeField,section])
  const errorMessage=error||record.processing_error
  return <div className="workspace">
    <div className="breadcrumb"><button className="link" onClick={back}><ArrowLeft size={15}/> Back to {backLabel}</button><span>/</span><span>{record.id.slice(0,8).toUpperCase()}</span></div>
    <div className="page-heading request-heading">
      <div><div className="eyebrow">{record.channel} · Workflow v{record.version}{record.fixture?' · Synthetic case':''}</div><h1>{record.subject}</h1><p>{record.sender} <span className="divider-dot">·</span> {localDate(record.created,true)}</p></div>
      <div className="heading-actions"><Status status={busy==='process'?'PROCESSING':record.status}/><Button kind="primary" busy={busy==='process'} disabled={Boolean(busy)||!pending} onClick={()=>mutate('/process','process')}><Sparkles size={16}/>Process request</Button></div>
    </div>
    {errorMessage && <Notice message={errorMessage}/>}
    {notice && <Notice message={notice} type="success"/>}
    {busy==='process' && <div className="processing-banner"><Sparkles size={16}/> Processing with {modeName(health?.mode||'local_ai')}…</div>}
    <div className="workspace-grid">
      <section className="card source-panel">
        <div className="card-heading"><h2><Mail size={18}/> Source material</h2><label className="icon-btn upload-icon" title="Attach supporting file"><Paperclip size={18}/><input type="file" aria-label="Attach supporting file" accept=".pdf,.docx,.txt,.csv,.xlsx,.png" onChange={e=>{if(e.target.files?.[0]) void upload(e.target.files[0]);e.target.value=''}}/></label></div>
        <div className="tabs">{['Conversation','Attachments'].map(tab=><button key={tab} className={sourceTab===tab?'active':''} onClick={()=>setSourceTab(tab)}>{tab}{tab==='Attachments' && <span>{record.attachments.length}</span>}</button>)}</div>
        <div className="source-list">
          {sourceTab==='Conversation'?record.messages.map(m=><article key={m.id} data-source-id={m.id} className={'message '+(activeSource===m.id?'highlight ':'')+(m.direction==='outgoing'?'outgoing':'')}>
            <div className="message-meta"><span className="message-icon">{m.direction==='outgoing'?<Send size={15}/>:<Mail size={15}/>}</span><div><strong>{m.sender}</strong><small>{m.direction==='outgoing'?'Simulated outgoing':m.historical?'Fictional incoming':'Local incoming'} · {localDate(m.created,true)}</small></div></div>
            <p className="message-text">{m.body}</p>
          </article>):record.attachments.length?record.attachments.map(a=><article key={a.id} data-source-id={a.id} className={'message '+(activeSource===a.id?'highlight':'')}>
            <div className="message-meta"><span className="message-icon"><FileText size={15}/></span><div><strong>{a.filename}</strong><small>{a.kind} · {a.pages.length} source segment(s)</small></div></div>
            {a.warning&&<Notice message={a.warning}/>}
            {a.filename.toLowerCase().endsWith('.png')&&<img className="attachment-preview" src={'/api/orgs/'+record.org+'/documents/'+a.id+'?inline=true'} alt={'Design preview for '+a.filename}/>}
            {a.pages.map((p,index)=><details key={index} open={activeSource===a.id||undefined}><summary>{p.page?'Page '+p.page:'Extracted text'}</summary><p className="message-text">{p.text}</p></details>)}
            <a className="link" href={'/api/orgs/'+record.org+'/documents/'+a.id}><Download size={15}/> Download source</a>
          </article>):<Empty title="No attachments"/>}
        </div>
        {sourceTab==='Conversation'&&<div className="panel-footer"><Button onClick={()=>{setEntry('');setDialog('reply')}}><MessageSquare size={15}/> Add local reply</Button></div>}
      </section>
      <section className="card facts-panel">
        <div className="card-heading"><h2><ClipboardList size={18}/> Request record</h2><span className="plain-chip">Rev {record.revision}</span></div>
        <div className="tabs">{['Fields','Output','History'].map(tab=><button key={tab} className={section===tab?'active':''} onClick={()=>setSection(tab)}>{tab}</button>)}</div>
        {section==='Fields'&&<>
          <div className="completeness"><div><strong>Required information</strong><span>{record.resolved} / {record.required||record.workflow.fields.filter(f=>f.required).length}</span></div><Progress done={record.resolved} total={record.required}/></div>
          <div className="field-list">{record.workflow.fields.map(spec=>{
            const fact=record.fields[spec.key]
            const required=spec.required || (spec.when&&record.fields[spec.when.field]?.value===spec.when.equals)
            const status=fact?.status||(required?'MISSING':'NOT_APPLICABLE')
            return <div key={spec.key} data-field-key={spec.key} className={'field-row '+(activeField===spec.key?'focused-field':'')}>
              <div className="field-top"><strong>{spec.label}{required && <span className="required-mark"> *</span>}</strong><Status status={status}/>
                <button className="icon-btn" aria-label={'Edit '+spec.label} title={'Edit '+spec.label} disabled={pending||Boolean(busy)} onClick={()=>edit(spec)}><Pencil size={15}/></button>
              </div>
              <div className="field-value">{textValue(fact?.value)|| (fact?.value===0?0:<span className="muted">Unresolved</span>)}</div>
              {fact?.raw!==null&&fact?.raw!==undefined&&String(fact.raw)!==String(fact.value)&&<small className="muted">Original wording · {String(textValue(fact.raw))}</small>}
              {fact?.reason&&<small className="muted">Human review · {fact.reason}</small>}
              {Boolean(fact?.evidence.length)&&<details className="evidence"><summary><BookOpen size={14}/>{fact.evidence.length} {fact.evidence.length===1?'source':'sources'}</summary>{fact.evidence.map((e,i)=><button key={i} onClick={()=>evidence(e)} className="evidence-quote"><q>{e.quote}</q><small>{e.label}{e.page?' · p. '+e.page:''} · {e.origin==='literal_source'?'Literal source check':modeName(e.mode)}</small></button>)}</details>}
              {Boolean(fact?.history.length)&&<details className="evidence"><summary>Previous values</summary><ul>{fact.history.map((h,i)=><li key={i}>{String(textValue(h.value??h.raw))} · {label(h.status)}</li>)}</ul></details>}
            </div>
          })}</div>
        </>}
        {section==='Output'&&<div className="panel-body output-panel">
          {record.state.output_history.length>0&&<label>Record revision<select value={prior??''} onChange={e=>setPrior(e.target.value===''?null:Number(e.target.value))}><option value="">Current output</option>{record.state.output_history.map((item,index)=><option value={index} key={index}>Revision {item.revision}</option>)}</select></label>}
          {selectedOutput?<><OutputPreview output={selectedOutput} approved={approved&&prior===null}/>
            {record.workflow.adapter==='accommodation'&&prior===null&&<Button onClick={()=>{setEntry(selectedOutput.staff_edit||Object.entries(selectedOutput.sections).map(([k,v])=>k+'\n'+v).join('\n\n'));setDialog('staff')}}><Pencil size={15}/> Edit plan text</Button>}</>:<Empty title="No output prepared" description="Complete validation, then generate a reviewable output."/>}
        </div>}
        {section==='History'&&<div className="panel-body"><h3>Review decisions</h3>{record.approvals.length?record.approvals.map((a,i)=><div className="history-row" key={i}><strong>{label(a.decision)} · {a.role}</strong><small>Revision {a.revision} · {localDate(a.at,true)} {a.active?'· Current':''}</small>{a.comment&&<p>{a.comment}</p>}</div>):<p className="muted">No review decisions.</p>}<h3>Audit events</h3><AuditList items={[...record.audit].reverse()}/></div>}
      </section>
      <aside className="action-panel">
        <section className="card">
          <div className="card-heading"><h2><TriangleAlert size={18}/> Validation</h2><span className="plain-chip">{record.issues.length}</span></div>
          <div className="panel-body">
            {pending?<p className="muted">Process the incoming sources to check this request.</p>:record.issues.length?record.issues.map((issue,index)=><div key={index} className={'issue '+(issue.kind==='CONFLICTING'?'danger':'')}>{record.workflow.fields.some(f=>f.key===issue.key)?<button className="issue-link" onClick={()=>{setActiveField(issue.key);setSection('Fields')}}>{issue.label}</button>:<strong>{issue.label}</strong>}<small>{issue.detail}</small></div>):<p className="all-clear"><ShieldCheck size={18}/> All required checks passed.</p>}
            <Button disabled={Boolean(busy)||pending} busy={busy==='validate'} onClick={()=>mutate('/validate','validate')}>Revalidate</Button>
          </div>
        </section>
        <section className="card">
          <div className="card-heading"><h2><MessageSquare size={18}/> Follow-up</h2></div>
          <div className="panel-body action-stack">
            {currentDraft&&<><small className="muted">{modeName(currentDraft.mode)} · {label(currentDraft.status)}</small>
              <textarea aria-label="Clarification draft" rows={7} value={draft} disabled={currentDraft.status==='sent'} onChange={e=>setDraft(e.target.value)}/>
              {currentDraft.status!=='sent'&&draft!==currentDraft.text&&<Button disabled={Boolean(busy)||!draft.trim()} onClick={()=>mutate('/draft','save draft',{...draftVersion,revision:record.revision,text:draft},'PATCH')}>Save draft changes</Button>}
              {currentDraft.status==='draft'&&<Button disabled={Boolean(busy)||draft!==currentDraft.text} onClick={()=>mutate('/draft/approve','approve draft',{...review,...draftVersion})}><Check size={16}/> Approve message</Button>}
              {currentDraft.status==='approved'&&<Button disabled={Boolean(busy)||draft!==currentDraft.text} onClick={()=>mutate('/draft/send','send',{...review,...draftVersion})}><Send size={15}/> Simulate send</Button>}
            </>}
            <Button disabled={Boolean(busy)||pending||(!record.issues.length&&record.workflow.adapter!=='print')} busy={busy==='draft'} onClick={()=>mutate('/draft','draft')}><Sparkles size={15}/>{currentDraft?'Regenerate follow-up':'Generate follow-up'}</Button>
            {record.duplicate_available&&<Button disabled={Boolean(busy)} onClick={()=>perform('duplicate',async()=>{
              updated(await api<CaseDetail>(base+'/duplicate','POST'))
              setNotice('Duplicate message matched the existing request.')
            })}>Simulate duplicate message</Button>}
            {record.reply_available&&<><Button disabled={Boolean(busy)||!canReply} onClick={()=>mutate('/reply','reply')}>Simulate customer reply</Button><small className="muted">Injects the next prerecorded fictional reply.</small></>}
          </div>
        </section>
        <section className="card">
          <div className="card-heading"><h2><ShieldCheck size={18}/> Review & export</h2></div>
          <div className="panel-body action-stack">
            <p className="muted">Simulated reviewer · {record.workflow.reviewer}</p>
            <Button disabled={Boolean(busy)||!ready} busy={busy==='output'} onClick={()=>{setSection('Output');setPrior(null);void mutate('/output','output')}}><FileText size={16}/> Generate output</Button>
            {output&&<Button onClick={()=>{setSection('Output');setPrior(null)}}>View current output</Button>}
            <Button kind="primary" disabled={!ready||!output||Boolean(busy)} onClick={()=>requestReview('approve')}><Check size={16}/> Approve request</Button>
            <div className="review-links"><button className="link" disabled={pending||Boolean(busy)} onClick={()=>requestReview('return')}>Request corrections</button><button className="link danger-text" disabled={pending||Boolean(busy)} onClick={()=>requestReview('reject')}>Reject</button></div>
            <Button disabled={!approved||Boolean(busy)} onClick={()=>{setEntry('');setDialog('export')}}><Download size={16}/> Export approved record</Button>
            {record.state.exports.length>0&&<small className="muted path">Saved in {record.state.exports.at(-1)?.path}</small>}
          </div>
        </section>
      </aside>
    </div>
    {dialog&&<Modal title={dialog==='correction'?'Correct '+field?.label:dialog==='review'?label(reviewDecision)+' request':dialog==='export'?'Export approved record':dialog==='staff'?'Edit accommodation plan':'Add a local reply'} close={()=>{if(!busy)setDialog(null)}}>
      <form className="form-stack" onSubmit={submitDialog}>
        {error&&<Notice message={error}/>}
        {dialog==='correction'&&<><label>Reviewed value<input value={entry} onChange={e=>setEntry(e.target.value)}/></label><label>Reason for change<textarea required minLength={3} rows={3} value={comment} onChange={e=>setComment(e.target.value)}/></label></>}
        {dialog==='review'&&<><p>Revision {record.revision} · {record.workflow.reviewer} (simulated)</p><label>Review comment<textarea rows={3} value={comment} onChange={e=>setComment(e.target.value)}/></label></>}
        {dialog==='export'&&<label>Existing local directory (optional)<input placeholder="Default project exports folder" value={entry} onChange={e=>setEntry(e.target.value)}/></label>}
        {dialog==='staff'&&<label>Staff-reviewed plan<textarea rows={13} required maxLength={2500} value={entry} onChange={e=>setEntry(e.target.value)}/></label>}
        {dialog==='reply'&&<label>Reply from {record.sender}<textarea rows={7} required value={entry} onChange={e=>setEntry(e.target.value)}/></label>}
        <div className="form-actions"><Button type="button" onClick={()=>setDialog(null)} disabled={Boolean(busy)}>Cancel</Button><Button type="submit" kind="primary" busy={Boolean(busy)}>{dialog==='export'?'Export ZIP':'Confirm'}</Button></div>
      </form>
    </Modal>}
  </div>
}

function OutputPreview({output,approved}:{output:Output;approved:boolean}){
  return <article className="output-preview"><div className="eyebrow">{approved?'Approved revision':'Pending review'} · {output.format.toUpperCase()}</div>
    <h2>{output.title}</h2><p className="message-text">{output.summary}</p>
    {output.staff_edit?<p className="message-text">{output.staff_edit}</p>:Object.entries(output.sections).map(([title,text])=><div className="output-section" key={title}><h3>{title}</h3><p className="message-text">{text}</p></div>)}
    {Object.keys(output.calculation).length>0&&<dl className="calculation">{Object.entries(output.calculation).map(([key,value])=><div key={key}><dt>{label(key)}</dt><dd>{textValue(value)}</dd></div>)}</dl>}
  </article>
}
