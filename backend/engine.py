from copy import deepcopy
from uuid import uuid4

from sqlalchemy import delete,select

from backend import adapters, ai, validation
from backend.files import fictional_flyer,pdf_bytes,read_document
from backend.store import Case, DocumentSource, Message, WorkflowVersion, latest, now

class Problem(Exception):
    def __init__(self,detail,status=400):
        self.detail=detail
        self.status=status

def uid():
    return uuid4().hex[:16]

def initial_state():
    return dict(status='NEW',revision=0,fields={},issues=[],required=0,resolved=0,audit=[],
        approvals=[],processed=[],draft=None,output=None,output_history=[],runs=[],exports=[],reply_index=0,processing_error=None)

def audit(state,kind,detail,**data):
    state['audit'].append(dict(at=now(),kind=kind,detail=detail,**data))

def cfg_for(s,case):
    return s.get(WorkflowVersion,(case.org,case.version)).config

def by_org(s,model,org,key):
    item=s.get(model,key)
    if item is None or item.org!=org:
        raise Problem('Record not found in this organization.',404)
    return item

def messages(s,case):
    return s.scalars(select(Message).where(Message.case_id==case.id).order_by(Message.created,Message.id)).all()

def documents(s,case):
    return s.scalars(select(DocumentSource).where(DocumentSource.case_id==case.id).order_by(DocumentSource.created)).all()

def message_view(message):
    return {key:getattr(message,key) for key in ('id','external_id','created','sender','body','direction','in_reply_to','historical')}

def doc_view(doc, include_text=True):
    result={key:getattr(doc,key) for key in ('id','filename','kind','created','version','warning')}
    if include_text:
        result['pages']=doc.pages
    return result

def case_view(s,case,detail=True):
    state=case.state
    result={key:getattr(case,key) for key in ('id','org','thread','sender','subject','channel','version','created','updated','fixture','unread')}
    workflow=cfg_for(s,case)
    result['reviewer']=workflow['reviewer']
    if detail:
        result.update(state=state,fields=state['fields'],issues=state['issues'],audit=state['audit'],approvals=state['approvals'],
                      workflow=workflow,messages=[message_view(x) for x in messages(s,case)],
                      attachments=[doc_view(d) for d in documents(s,case)])
    result.update({key:state[key] for key in ('status','revision','required','resolved','processing_error')})
    return result

def settings(s):
    from backend.store import Preference
    return s.get(Preference,1).data

def stamp(case,state):
    case.updated=now()
    case.state=state

def invalidate(state):
    if state['output']:
        state['output_history'].append(state['output'])
    state['output']=None
    for approval in state['approvals']:
        if approval['active']:
            approval['active']=False
            audit(state,'Approval invalidated','Record changed after review.',previous_revision=approval['revision'])
    if state['draft'] and state['draft']['status']!='sent':
        state['draft']=None
    state['revision']+=1

def intake(s,data,fixture=None):
    cfg=latest(s,data['org'])
    if not cfg:
        raise Problem('Unknown organization.',404)
    if data['channel'] not in cfg.config['channels']:
        raise Problem('This intake channel is not configured for the organization.')
    external_id=data.get('message_id') or uid()
    existing=s.scalar(select(Message).where(Message.org==data['org'],Message.external_id==external_id))
    if existing:
        return s.get(Case,existing.case_id),True
    associated=None
    reply_id=data.get('in_reply_to')
    if reply_id:
        parent=s.scalar(select(Message).where(Message.org==data['org'],Message.external_id==reply_id))
        if not parent:
            raise Problem('Reply reference does not identify a message in this organization.',409)
        associated=s.get(Case,parent.case_id)
    thread=data.get('thread')
    if thread:
        thread_case=s.scalar(select(Case).where(Case.org==data['org'],Case.thread==thread))
        if associated and associated!=thread_case:
            raise Problem('Thread and reply reference identify different requests.',409)
        associated=associated or thread_case
    if associated and associated.sender.casefold()!=data['sender'].casefold():
        raise Problem('Reply sender differs from the request contact.',409)
    # A new message is isolated unless an explicit thread or reply reference matches.
    case=associated or Case(id=uid(),org=data['org'],thread=thread or uid(),sender=data['sender'],
             subject=data['subject'],channel=data['channel'],version=cfg.version,created=data.get('timestamp') or now(),
             updated=now(),unread=True,fixture=fixture,state=initial_state())
    if not associated:
        s.add(case)
        s.flush()
    state=deepcopy(case.state)
    if associated:
        invalidate(state)
    body=data['body'].strip()
    message=Message(id=uid(),org=case.org,external_id=external_id,case_id=case.id,
                    created=data.get('timestamp') or now(),sender=data['sender'],body=body,
                    direction='incoming',in_reply_to=reply_id,historical=bool(fixture or data.get('simulated')))
    s.add(message)
    audit(state,'Incoming message','Fictional correspondence received.' if message.historical else 'Local correspondence received.',message=external_id)
    state['status']='NEW'
    state['processing_error']=None
    case.unread=True
    stamp(case,state)
    s.flush()
    return case,False

def attach(s,case,org,filename,data,kind):
    name,pages,warning=read_document(filename,data,references=not case)
    if not case:
        prior=s.scalar(select(DocumentSource).where(DocumentSource.org==org,DocumentSource.case_id.is_(None),
                      DocumentSource.filename==name,DocumentSource.kind==kind).order_by(DocumentSource.version.desc()))
    else:
        prior=None
    doc=DocumentSource(id=uid(),org=org,case_id=case.id if case else None,
                       filename=name,kind=kind,created=now(),content=data,pages=pages,warning=warning,
                       version=prior.version+1 if prior else 1)
    s.add(doc)
    if case:
        state=deepcopy(case.state)
        invalidate(state)
        state['status']='NEW'
        audit(state,'Source attached',name)
        stamp(case,state)
    s.flush()
    return doc

def source_chunks(identity,text,label,kind,page):
    chunks=[]
    remainder=text
    while len(remainder)>2200:
        cut=remainder.rfind('\n',0,2200)
        if cut<=0:
            cut=remainder.rfind(' ',1100,2200)
        if cut<=0:
            cut=2200
        chunks.append(remainder[:cut])
        remainder=remainder[cut:].lstrip('\n')
    chunks.append(remainder)
    return [dict(id=identity if len(chunks)==1 else f'{identity}:{i+1}',text=value,label=label,type=kind,page=page)
            for i,value in enumerate(chunks) if value.strip()]

def source_batch(s,case):
    conversation=[message_view(m) for m in messages(s,case)]
    all_sources=[chunk for m in conversation if m['direction']=='incoming'
                 for chunk in source_chunks(m['id'],m['body'],'Customer message','message',None)]
    all_sources.extend(chunk for d in documents(s,case) for i,p in enumerate(d.pages)
                       for chunk in source_chunks(f"{d.id}:{i+1}",p['text'],d.filename,'attachment',p['page']))
    sources=[x for x in all_sources if x['id'] not in case.state['processed']]
    ref_docs=s.scalars(select(DocumentSource).where(DocumentSource.org==case.org,DocumentSource.case_id.is_(None))
                         .order_by(DocumentSource.version.desc(),DocumentSource.created.desc())).all()
    refs={}
    for ref in ref_docs:
        refs.setdefault((ref.filename,ref.kind),' '.join(p['text'] for p in ref.pages))
    approved=list(refs.values())
    workflow=cfg_for(s,case)
    if workflow.get('adapter')=='print':
        approved.insert(0,adapters.printing_reference(workflow))
    return dict(sources=sources,history=[m['body'] for m in conversation if any(source.split(':')[0]==m['id'] for source in case.state['processed'])],refs=approved)

def verify_review_version(state,revision):
    if state['revision']!=revision:
        raise Problem('The request changed. Refresh it before continuing.',409)

def verify_draft(state,data):
    draft=state['draft']
    if not draft or draft['id']!=data.draft_id or draft.get('edit_version',1)!=data.draft_version or draft['revision']!=data.revision:
        raise Problem('The clarification changed. Refresh it before continuing.',409)
    return draft

def merge_fact(state,spec,fact,source,mode):
    key=fact.key
    raw=fact.raw.strip()
    value,issue=validation.normalize(spec,raw)
    if not issue and fact.issue and 'ambig' in fact.issue.lower() and spec['type'] not in ('time','date'):
        value,issue=None,fact.issue
    status=('AMBIGUOUS' if 'ambiguous' in issue.lower() else 'INVALID') if issue else 'EXTRACTED'
    evidence=dict(source=source['id'],label=source['label'],page=source['page'],quote=fact.quote,
                  raw=raw,value=value,at=now(),mode=mode,origin=fact.origin)
    previous=state['fields'].get(key,{})
    evidence_list=previous.get('evidence',[])+[evidence]
    history=previous.get('history',[])
    same=previous.get('value')==value and value is not None
    if previous.get('status')=='CONFLICTING' or (previous.get('value') is not None and not same):
        if previous.get('status')!='CONFLICTING':
            history=history+[{"raw":previous.get('raw'),"value":previous.get('value'),"status":previous['status']}]
        state['fields'][key]=dict(status='CONFLICTING',raw=raw,value=None,issue='Sources disagree. Review the evidence and record a human correction.',
                                  evidence=evidence_list,history=history)
        audit(state,'Conflict detected',spec['label'],field=key)
    elif same:
        state['fields'][key]={**previous,'evidence':evidence_list}
    else:
        if previous:
            history=history+[{"raw":previous.get('raw'),"value":previous.get('value'),"status":previous['status']}]
        state['fields'][key]=dict(status=status,raw=raw,value=value,issue=issue,evidence=evidence_list,history=history)

def revalidate(s,case,state,*,preserve=False):
    workflow=cfg_for(s,case)
    issues,total,done=validation.evaluate(workflow,state['fields'])
    values=resolved_values(state)
    issues.extend(adapters.checks(workflow,values,[message_view(m) for m in messages(s,case)],
                                  [d.filename for d in documents(s,case)]))
    state.update(issues=issues,required=total,resolved=done)
    if any(x['kind']=='CONFLICTING' for x in issues): status='CONFLICT_DETECTED'
    elif any(x['kind'] in ('AMBIGUOUS','INVALID') for x in issues): status='NEEDS_CLARIFICATION'
    elif issues: status='AWAITING_INFORMATION'
    else: status='READY_FOR_REVIEW'
    if not preserve or state['status'] not in ('APPROVED','EXPORTED','REJECTED') or issues:
        state['status']=status

def resolved_values(state):
    return {k:v['value'] for k,v in state['fields'].items() if v['status'] in ('EXTRACTED','HUMAN_VERIFIED') and v['value'] is not None}

def apply_extraction(s,case,workflow,sources,facts,mode,latency,more_sources=False):
    state=deepcopy(case.state)
    invalidate(state)
    by_source={source['id']:source for source in sources}
    specs={spec['key']:spec for spec in workflow['fields']}
    for fact in facts:
        merge_fact(state,specs[fact.key],fact,by_source[fact.source],mode)
    state['processed']+=list(by_source)
    state['runs'].append(dict(at=now(),mode=mode,elapsed_ms=latency,facts=len(facts),literal_sources=sum(f.origin=='literal_source' for f in facts),success=True))
    state['processing_error']=None
    audit(state,'Sources processed',f'{len(facts)} evidence-backed findings.',mode=mode,elapsed_ms=latency)
    revalidate(s,case,state)
    if more_sources:
        state['status']='NEW'
    stamp(case,state)

def correct(s,case,key,data):
    state=deepcopy(case.state)
    verify_review_version(state,data.revision)
    if not state['processed'] or source_batch(s,case)['sources']:
        raise Problem('Process incoming sources before recording a correction.',409)
    spec=next((f for f in cfg_for(s,case)['fields'] if f['key']==key),None)
    if not spec:
        raise Problem('Unknown workflow field.',404)
    value,issue=validation.normalize(spec,data.value)
    if issue:
        raise Problem(issue,422)
    old=state['fields'].get(key,{})
    invalidate(state)
    state['fields'][key]=dict(value=value,raw=data.value,status='HUMAN_VERIFIED' if value is not None else 'MISSING',
        issue=None,evidence=old.get('evidence',[]),history=old.get('history',[])+([{k:old.get(k) for k in ('value','raw','status')}] if old else []),
        verified_at=now(),reason=data.reason)
    audit(state,'Field corrected',data.reason,field=key,old=old.get('value'),value=value)
    revalidate(s,case,state)
    stamp(case,state)

def ready(s,case,state):
    if source_batch(s,case)['sources'] or not state['processed']:
        raise Problem('Process all incoming sources first.',409)
    revalidate(s,case,state,preserve=True)
    if state['issues']:
        raise Problem('Resolve blocking validation issues before preparing or approving the output.',409)

def attach_fixture(s,case,item):
    if item['kind']=='pdf':
        content=pdf_bytes('Synthetic source',item['text'])
    elif item['kind']=='png':
        content=fictional_flyer(item['width_mm'],item['height_mm'],item['dpi'])
    else:
        content=item['text'].encode()
    attach(s,case,case.org,item['name'],content,'Synthetic source')

def seed(s,fixtures,reset=False):
    if reset:
        s.execute(delete(Case).where(Case.fixture.is_not(None)))
        s.flush()
    existing=set(s.scalars(select(Case.fixture).where(Case.fixture.is_not(None))))
    for fixture in fixtures:
        if fixture['id'] in existing:
            continue
        case,_=intake(s,fixture|{'subject':fixture['title']},fixture=fixture['id'])
        for item in fixture['attachments']:
            attach_fixture(s,case,item)

def simulate_reply(s,case,fixture):
    state=case.state
    index=state['reply_index']
    if not fixture or index>=len(fixture['replies']):
        raise Problem('This scenario has no remaining prerecorded replies.',409)
    if not fixture.get('conflict') and (not state['draft'] or state['draft']['status']!='sent' or state['draft'].get('reply_received')):
        raise Problem('Approve and simulate sending a new clarification first.',409)
    incoming=next((m for m in reversed(messages(s,case)) if m.direction=='incoming'),None)
    if fixture.get('conflict') and state['status']=='NEW':
        raise Problem('Process the original request first.',409)
    updated,_=intake(s,dict(org=case.org,channel=case.channel,subject=case.subject,sender=case.sender,body=fixture['replies'][index],
        thread=case.thread,message_id=f'{case.fixture}-reply-{index+1}',in_reply_to=incoming.external_id,simulated=True))
    for item in fixture['reply_attachments'].get(str(index+1),[]):
        attach_fixture(s,updated,item)
    state=deepcopy(updated.state)
    if state['draft'] and state['draft']['status']=='sent':
        state['draft']['reply_received']=True
    state['reply_index']=index+1
    audit(state,'Prerecorded reply','Injected the next fictional response.')
    stamp(updated,state)
    return updated
