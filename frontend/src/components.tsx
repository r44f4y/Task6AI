import { AlertCircle, CircleCheck, Inbox, LoaderCircle, X } from 'lucide-react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { label, localDate } from './api'
import type { Audit } from './types'

export function Status({status}:{status:string}) {
  const tone = ['READY_FOR_REVIEW','APPROVED','EXPORTED','EXTRACTED','HUMAN_VERIFIED'].includes(status) ? 'green'
    : ['MISSING','AMBIGUOUS','AWAITING_INFORMATION','NEEDS_CLARIFICATION'].includes(status) ? 'amber'
    : ['CONFLICTING','INVALID','CONFLICT_DETECTED','REJECTED'].includes(status) ? 'red' : 'gray'
  return <span className={'status '+tone}><i/>{label(status)}</span>
}
export function Button({children,kind='secondary',busy=false,...props}:ButtonHTMLAttributes<HTMLButtonElement>&{kind?:string;busy?:boolean}) {
  return <button {...props} disabled={props.disabled||busy} className={'btn '+kind+' '+(props.className||'')}>
    {busy && <LoaderCircle size={16} className="spin"/>}{children}
  </button>
}
export function Empty({title,description}:{title:string;description?:string}) {
  return <div className="empty"><Inbox size={27}/><strong>{title}</strong>{description && <p>{description}</p>}</div>
}
export function Progress({done,total}:{done:number;total:number}) {
  const percent=total ? Math.round(done/total*100) : 0
  return <span className="progress"><span style={{width:percent+'%'}}/></span>
}
export function Modal({title,children,close}:{title:string;children:ReactNode;close:()=>void}) {
  return <div className="modal-backdrop" onClick={close}><section role="dialog" aria-modal="true" aria-label={title} className="modal" onClick={e=>e.stopPropagation()}>
    <div className="card-heading"><h2>{title}</h2><button className="icon-btn" aria-label="Close" onClick={close}><X size={19}/></button></div>
    {children}
  </section></div>
}
export function Notice({message,type='error'}:{message:string;type?:'error'|'success'}) {
  return <div role={type==='error'?'alert':'status'} className={'notice '+type}>{type==='error'?<AlertCircle size={17}/>:<CircleCheck size={17}/>}<span>{message}</span></div>
}
export function AuditList({items,open}:{items:Audit[];open?:(id:string)=>void}) {
  if(!items.length) return <Empty title="No activity yet"/>
  return <div className="timeline">{items.map((item,index)=><div key={item.at+index} className="timeline-item"><i/>
    <div><strong>{item.kind}</strong><p>{item.subject && item.id && open ? <button className="link" onClick={()=>open(item.id!)}>{item.subject}</button> : item.detail}</p></div>
    <time>{localDate(item.at,true)}</time>
  </div>)}</div>
}
