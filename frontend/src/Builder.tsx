import { useEffect, useState } from 'react'
import { FlaskConical, Plus, Save, Trash2 } from 'lucide-react'
import { api, label } from './api'
import { Button, Notice } from './components'
import type { CaseDetail, FieldSpec, FieldType, Workflow } from './types'

const blankField=():FieldSpec=>({key:'',label:'',type:'text',required:true,options:[]})
const blankWorkflow=():Workflow=>({id:'',name:'',title:'',industry:'',channels:['Email'],description:'',reviewer:'',output:'json',fields:[blankField()],version:0})
const fieldTypes:FieldType[]=['text','number','currency','date','time','boolean','email','phone','address','select']

export function Builder({workflow,workflowList,onSelect,onSaved,open}:{workflow:Workflow;workflowList:Workflow[];onSelect:(org:string)=>void;onSaved:(w:Workflow)=>Promise<void>;open:(id:string,org:string)=>void}){
  const [form,setForm]=useState<Workflow>(workflow)
  const [error,setError]=useState('')
  const [success,setSuccess]=useState('')
  const [busy,setBusy]=useState(false)
  const [versions,setVersions]=useState<Workflow[]>([])
  const [example,setExample]=useState('')
  useEffect(()=>{
    setForm(workflow);setSuccess('');setError('');setExample('')
    void api<Workflow[]>('/workflows/'+workflow.id+'/versions').then(setVersions).catch(e=>setError(e.message))
  },[workflow])
  const patch=(data:Partial<Workflow>)=>setForm(f=>({...f,...data}))
  const patchField=(index:number,data:Partial<FieldSpec>)=>setForm(f=>({...f,fields:f.fields.map((v,i)=>i===index?{...v,...data}:v)}))
  async function save(e:React.FormEvent){
    e.preventDefault();setBusy(true);setError('');setSuccess('')
    try{
      const saved=await api<Workflow>('/workflows','POST',form)
      await onSaved(saved)
      setSuccess('Saved workflow version '+saved.version+'. New requests use this version.')
    }catch(err){setError((err as Error).message)}finally{setBusy(false)}
  }
  async function processExample(){
    setBusy(true);setError('')
    try{
      const sample=await api<{request:CaseDetail}>('/intake','POST',{org:form.id,channel:form.channels[0],sender:'builder-demo@example.com',subject:'Workflow Builder example',body:example})
      await api('/orgs/'+form.id+'/requests/'+sample.request.id+'/process','POST')
      open(sample.request.id,form.id)
    }catch(err){setError((err as Error).message)}finally{setBusy(false)}
  }
  function newWorkflow(){setForm(blankWorkflow());setVersions([]);setExample('');setError('');setSuccess('')}
  return <>
    <div className="page-heading"><div><div className="eyebrow">Configuration</div><h1>Workflow Builder</h1><p>Define how an organisation collects, validates and reviews its requests.</p></div><Button onClick={newWorkflow}><Plus size={17}/> New organisation</Button></div>
    {error&&<Notice message={error}/>}
    {success&&<Notice message={success} type="success"/>}
    <div className="builder-grid">
      <form onSubmit={save} className="card builder-form">
        <div className="card-heading"><h2>Workflow configuration</h2>{form.version>0&&<span className="plain-chip">Version {form.version}</span>}</div>
        <div className="panel-body form-stack">
          <div className="form-cols">
            <label>Organisation name<input required value={form.name} onChange={e=>patch({name:e.target.value,...(!form.version?{id:e.target.value.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'')}: {})})}/></label>
            <label>Organisation ID<input required disabled={Boolean(form.version)} pattern="[a-z][a-z0-9_]{0,49}" value={form.id} onChange={e=>patch({id:e.target.value})}/></label>
            <label>Workflow name<input required value={form.title} onChange={e=>patch({title:e.target.value})}/></label>
            <label>Industry<input required value={form.industry} onChange={e=>patch({industry:e.target.value})}/></label>
            <label>Input channels<input required defaultValue={form.channels.join(', ')} key={form.id+'-channels-'+form.version} onBlur={e=>patch({channels:e.target.value.split(',').map(s=>s.trim()).filter(Boolean)})}/></label>
            <label>Approval role<input required value={form.reviewer} onChange={e=>patch({reviewer:e.target.value})}/></label>
            <label>Output format<select value={form.output} onChange={e=>patch({output:e.target.value})}>{['json','csv','xlsx','docx','pdf','zip'].map(v=><option key={v} value={v}>{v.toUpperCase()}</option>)}</select></label>
          </div>
          <label>Workflow description<textarea rows={2} value={form.description} onChange={e=>patch({description:e.target.value})}/></label>
          <label>Clarification guidance<textarea rows={2} value={form.clarification||''} onChange={e=>patch({clarification:e.target.value})}/></label>
          <label>Output template<textarea rows={2} placeholder="Use {field_key} to include reviewed information" value={form.template||''} onChange={e=>patch({template:e.target.value})}/></label>
          <div className="section-title"><h3>Field definitions</h3><Button type="button" onClick={()=>patch({fields:[...form.fields,blankField()]})}><Plus size={16}/> Add field</Button></div>
          {form.fields.map((field,index)=>{
            const builtIn=Boolean(form.adapter && workflow.fields.some(f=>f.key===field.key))
            return <div className="builder-field" key={index}>
              <div className="form-cols"><label>Field label<input required disabled={builtIn} value={field.label} onChange={e=>patchField(index,{label:e.target.value,...(!field.key || field.key===field.label.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/_$/,'')?{key:e.target.value.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/_$/,'')}: {})})}/></label>
                <label>Field key<input required disabled={builtIn} pattern="[a-z][a-z0-9_]{0,49}" value={field.key} onChange={e=>patchField(index,{key:e.target.value})}/></label>
                <label>Type<select value={field.type} disabled={builtIn} onChange={e=>patchField(index,{type:e.target.value as FieldType})}>{fieldTypes.map(t=><option key={t} value={t}>{label(t)}</option>)}</select></label>
                <div className="field-actions"><label className="checkbox"><input type="checkbox" disabled={builtIn} checked={field.required} onChange={e=>patchField(index,{required:e.target.checked})}/> Required</label><button type="button" className="icon-btn" title="Remove field" aria-label={'Remove field '+(index+1)} disabled={builtIn||form.fields.length<2} onClick={()=>patch({fields:form.fields.filter((_,i)=>i!==index)})}><Trash2 size={17}/></button></div>
              </div>
              <details><summary>Validation & conditions</summary>
                <div className="form-cols subform">
                  {field.type==='select'&&<label>Allowed values (comma separated)<input disabled={builtIn} key={form.version+'-'+index} defaultValue={field.options.join(', ')} onBlur={e=>patchField(index,{options:e.target.value.split(',').map(s=>s.trim()).filter(Boolean)})}/></label>}
                  {['number','currency'].includes(field.type)&&<>
                    <label>Minimum<input disabled={builtIn} type="number" step="any" value={field.minimum??''} onChange={e=>patchField(index,{minimum:e.target.value===''?null:Number(e.target.value)})}/></label>
                    <label>Maximum<input disabled={builtIn} type="number" step="any" value={field.maximum??''} onChange={e=>patchField(index,{maximum:e.target.value===''?null:Number(e.target.value)})}/></label>
                    <label className="checkbox"><input disabled={builtIn} type="checkbox" checked={Boolean(field.integer)} onChange={e=>patchField(index,{integer:e.target.checked})}/> Whole numbers</label>
                  </>}
                  <label>Required when<select disabled={builtIn} value={field.when?.field||''} onChange={e=>patchField(index,{when:e.target.value?{field:e.target.value,equals:form.fields.find(f=>f.key===e.target.value)?.type==='boolean'?true:''}:null})}><option value="">No condition</option>{form.fields.filter((f,i)=>i!==index&&f.key).map(f=><option key={f.key} value={f.key}>{f.label||f.key}</option>)}</select></label>
                  {field.when&&<label>Equals<input disabled={builtIn} value={String(field.when.equals??'')} onChange={e=>{
                    const trigger=form.fields.find(f=>f.key===field.when?.field)
                    const raw=e.target.value
                    const comparable=trigger?.type==='boolean'&&['true','false'].includes(raw.toLowerCase())?raw.toLowerCase()==='true':
                      trigger?.type==='number'&&raw.trim()&&Number.isFinite(Number(raw))?Number(raw):raw
                    patchField(index,{when:{field:field.when!.field,equals:comparable}})
                  }}/></label>}
                </div>
              </details>
            </div>
          })}
          <div className="form-actions"><Button type="submit" kind="primary" busy={busy}><Save size={17}/> Save workflow</Button></div>
        </div>
      </form>
      <aside className="action-panel">
        <div className="card"><div className="card-heading"><h2>Saved workflows</h2></div><div className="panel-body form-stack">
          <label>Organisation<select value={form.version?form.id:''} onChange={e=>onSelect(e.target.value)}><option value="" disabled>Select an organisation</option>{workflowList.map(w=><option key={w.id} value={w.id}>{w.name}</option>)}</select></label>
          {versions.map(v=><button key={v.version} className="record-link" onClick={()=>setForm(v)}><span>Version {v.version}</span><small>{v.version===workflow.version?'Current version':'Load configuration'}</small></button>)}
        </div></div>
        <div className="card"><div className="card-heading"><h2><FlaskConical size={17}/> Try an example</h2></div><div className="panel-body form-stack">
          <p className="muted">Save the workflow, then add a fictional request. Offline demo mode reads lines in the form <strong>Field label: value</strong>.</p>
          <label>Example request<textarea value={example} rows={8} placeholder={form.fields.map(f=>f.label||'Field label').join(': …\n')+': …'} onChange={e=>setExample(e.target.value)}/></label>
          <Button disabled={!form.version||!example.trim()} busy={busy} onClick={processExample}>Process example</Button>
        </div></div>
      </aside>
    </div>
  </>
}
