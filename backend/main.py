import os
from copy import deepcopy
from email import policy
from email.parser import BytesParser
from html import escape
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend import adapters, ai, engine as flow
from backend.files import MAX_FILE, output_files, safe_name, zip_bytes
from backend.schema import Correction, DraftEdit, DraftReview, ExportDestination, Intake, Review, Settings, TextEdit, Workflow
from backend.store import Case, DocumentSource, Message, Preference, WorkflowVersion, connect, latest, now, write_lock
from synthetic_data.catalog import ROOT,catalog

FIXTURES={f['id']:f for f in catalog()}

def create_app(db_path=None,seed_demo=True):
    app=FastAPI(title='Relay AI',version='1.0',docs_url=None,redoc_url=None)
    db=connect(db_path)
    frontend_origin=os.getenv('RELAY_FRONTEND_ORIGIN','http://127.0.0.1:5173')
    allowed_origins={frontend_origin,frontend_origin.replace('127.0.0.1','localhost')}
    if seed_demo:
        with Session(db) as s:
            write_lock(s)
            flow.seed(s,FIXTURES.values())
            s.commit()

    @app.middleware('http')
    async def loopback_only(request:Request,call_next):
        via=request.headers.get('origin')
        authority=request.headers.get('host','')
        host=authority.split(':')[0]
        if host not in ('127.0.0.1','localhost','testserver') or (via and via not in allowed_origins and via!=f'http://{authority}'):
            return JSONResponse(status_code=403,content={'detail':'Open Relay AI from its local address.'})
        return await call_next(request)

    @app.exception_handler(flow.Problem)
    async def problem_handler(_,err):
        return JSONResponse(status_code=err.status,content={'detail':err.detail})

    @app.exception_handler(ValueError)
    async def value_handler(_,err):
        return JSONResponse(status_code=422,content={'detail':str(err)})

    @app.get('/docs',response_class=HTMLResponse,include_in_schema=False)
    def docs():
        paths=app.openapi()['paths']
        rows=''.join(f'<tr><td>{escape(method.upper())}</td><td><code>{escape(path)}</code></td><td>{escape(operation["summary"])}</td></tr>'
                     for path,methods in paths.items() for method,operation in methods.items())
        return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Relay AI API</title>'
                '<style>body{font:16px system-ui;margin:2rem;color:#19253b}td,th{padding:.5rem;border-bottom:1px solid #ccd6e5;text-align:left}</style>'
                '<h1>Relay AI API</h1><p><a href="/openapi.json">OpenAPI schema</a></p>'
                '<table><thead><tr><th>Method</th><th>Path</th><th>Operation</th></tr></thead><tbody>'
                +rows+'</tbody></table></html>')

    @app.get('/api/metrics/organizations')
    def organization_counts():
        with Session(db) as s:
            counts=dict(s.execute(select(Case.org,func.count(Case.id)).group_by(Case.org)).all())
            return [{'org':cfg['id'],'name':cfg['name'],'count':counts.get(cfg['id'],0)} for cfg in workflows()]

    @app.get('/api/health')
    def health():
        with Session(db) as s:
            settings=flow.settings(s)
        return settings|ai.health(settings['model'])

    @app.put('/api/settings')
    def save_settings(data:Settings):
        with Session(db) as s:
            write_lock(s)
            s.get(Preference,1).data=data.model_dump()
            s.commit()
        return health()

    @app.get('/api/workflows')
    def workflows():
        with Session(db) as s:
            revisions=s.scalars(select(WorkflowVersion).order_by(WorkflowVersion.org,WorkflowVersion.version.desc()))
            current={}
            for item in revisions:
                current.setdefault(item.org,item.config)
            order=['ontario_bulk','grandieu','fbw_law','enabled_talent','harbor_repair']
            return sorted(current.values(),key=lambda item:(order.index(item['id']) if item['id'] in order else 99,item['name']))

    @app.get('/api/workflows/{org}/versions')
    def versions(org:str):
        with Session(db) as s:
            return [w.config for w in s.scalars(select(WorkflowVersion).where(WorkflowVersion.org==org)
                        .order_by(WorkflowVersion.version.desc()))]

    @app.post('/api/workflows')
    def save_workflow(config:Workflow):
        with Session(db) as s:
            write_lock(s)
            previous=latest(s,config.id)
            original=previous.config if previous else {}
            new=config.model_dump()
            new.update(adapter=original.get('adapter'),prices=original.get('prices'),version=(previous.version+1 if previous else 1))
            if original.get('adapter'):
                baseline=s.get(WorkflowVersion,(config.id,1)).config
                incoming={f['key']:f for f in new['fields']}
                if any(incoming.get(f['key'])!=f for f in baseline['fields']):
                    raise flow.Problem('This adapter requires its built-in field definitions. Add custom fields or create a separate workflow.',409)
            s.add(WorkflowVersion(org=config.id,version=new['version'],config=new))
            s.commit()
            return new

    @app.get('/api/scenarios')
    def scenarios():
        with Session(db) as s:
            cases={c.fixture:c.id for c in s.scalars(select(Case).where(Case.fixture.is_not(None)))}
        return [{key:f[key] for key in ('id','org','title','missing','ambiguous','conflict','unsupported')}|
                 {'case_id':cases.get(f['id']),'replies':len(f['replies'])} for f in FIXTURES.values()]

    @app.post('/api/scenarios/reset')
    def reset():
        with Session(db) as s:
            write_lock(s)
            flow.seed(s,FIXTURES.values(),reset=True)
            s.commit()
            return {'count':len(FIXTURES)}

    @app.post('/api/intake')
    def intake(data:Intake):
        with Session(db) as s:
            write_lock(s)
            case,duplicate=flow.intake(s,data.model_dump())
            s.commit()
            return {'request':flow.case_view(s,case),'duplicate':duplicate}

    @app.post('/api/intake/eml')
    def intake_eml(org:str=Form(...),file:UploadFile=File(...)):
        with Session(db) as s:
            write_lock(s)
            config=latest(s,org)
            if not config or 'Email' not in config.config['channels']:
                raise flow.Problem('This workflow does not accept email.',422)
            data=file.file.read(MAX_FILE+1)
            if not file.filename.lower().endswith('.eml') or not data or len(data)>MAX_FILE:
                raise flow.Problem('Upload a .eml file no larger than 5 MB.',422)
            parsed=BytesParser(policy=policy.default).parsebytes(data)
            part=parsed.get_body(preferencelist=('plain',))
            if part is None:
                raise flow.Problem('The email must include a plain-text body.',422)
            model=Intake(org=org,channel='Email',subject=str(parsed['Subject'] or 'Imported email'),
                         sender=(parsed['From'].addresses[0].addr_spec if parsed['From'] and parsed['From'].addresses else 'import@example.com'),
                         body=part.get_content(),message_id=str(parsed['Message-ID'] or '') or None,
                         in_reply_to=str(parsed['In-Reply-To'] or '').split()[0] if parsed['In-Reply-To'] else None)
            case,duplicate=flow.intake(s,model.model_dump())
            if not duplicate:
                for item in parsed.iter_attachments():
                    payload=item.get_payload(decode=True)
                    if payload:
                        flow.attach(s,case,org,item.get_filename() or 'attachment.txt',payload,'Email attachment')
            s.commit()
            return {'request':flow.case_view(s,case),'duplicate':duplicate}

    @app.get('/api/orgs/{org}/requests')
    def requests(org:str):
        with Session(db) as s:
            return [flow.case_view(s,c,False) for c in s.scalars(select(Case).where(Case.org==org).order_by(Case.updated.desc()))]

    @app.get('/api/orgs/{org}/requests/{rid}')
    def request_detail(org:str,rid:str):
        with Session(db) as s:
            case=flow.by_org(s,Case,org,rid)
            result=flow.case_view(s,case)
            result['reply_available']=bool(case.fixture and case.state['reply_index']<len(FIXTURES[case.fixture]['replies']))
            result['reply_without_draft']=bool(case.fixture and FIXTURES[case.fixture]['conflict'])
            result['duplicate_available']=bool(case.fixture and FIXTURES[case.fixture]['duplicate'])
            return result

    @app.post('/api/orgs/{org}/requests/{rid}/read')
    def mark_read(org:str,rid:str):
        with Session(db) as s:
            write_lock(s)
            flow.by_org(s,Case,org,rid).unread=False
            s.commit()
            return {'read':True}

    @app.post('/api/orgs/{org}/requests/{rid}/process')
    def process(org:str,rid:str):
        with Session(db) as s:
            case=flow.by_org(s,Case,org,rid)
            revision=case.state['revision']
            batch=flow.source_batch(s,case)
            settings=flow.settings(s)
            workflow=flow.cfg_for(s,case)
            existing=case.state['fields']
        if not batch['sources']:
            return request_detail(org,rid)
        # Model context is bounded. Commit only sources that were actually in this run.
        sources=batch['sources'] if settings['mode']=='offline_demo' else [item for item in batch['sources'] if item['id'] in {
            src['id'] for src in ai.bounded_sources(batch['sources'])}]
        try:
            facts,latency=ai.extract(settings,workflow,sources,existing,batch['history'],batch['refs'])
        except ai.ProviderError as err:
            with Session(db) as s:
                write_lock(s)
                case=flow.by_org(s,Case,org,rid)
                if revision==case.state['revision']:
                    state=deepcopy(case.state)
                    state['processing_error']=str(err)
                    state['runs'].append(dict(at=now(),mode=settings['mode'],success=False))
                    flow.audit(state,'Processing failed',str(err),mode=settings['mode'])
                    flow.stamp(case,state)
                    s.commit()
            raise flow.Problem(str(err),503) from err
        with Session(db) as s:
            write_lock(s)
            case=flow.by_org(s,Case,org,rid)
            flow.verify_review_version(case.state,revision)
            flow.apply_extraction(s,case,workflow,sources,facts,settings['mode'],latency,more_sources=len(sources)<len(batch['sources']))
            s.commit()
        return request_detail(org,rid)

    @app.patch('/api/orgs/{org}/requests/{rid}/fields/{key}')
    def correct(org:str,rid:str,key:str,data:Correction):
        with Session(db) as s:
            write_lock(s)
            flow.correct(s,flow.by_org(s,Case,org,rid),key,data)
            s.commit()
        return request_detail(org,rid)

    @app.post('/api/orgs/{org}/requests/{rid}/validate')
    def validate(org:str,rid:str):
        with Session(db) as s:
            write_lock(s)
            case=flow.by_org(s,Case,org,rid)
            state=deepcopy(case.state)
            flow.revalidate(s,case,state,preserve=True)
            if flow.source_batch(s,case)['sources']:
                state['status']='NEW'
            flow.audit(state,'Revalidated','Checked the current record against workflow rules.')
            flow.stamp(case,state)
            s.commit()
        return request_detail(org,rid)

    @app.post('/api/orgs/{org}/requests/{rid}/draft')
    def draft(org:str,rid:str):
        with Session(db) as s:
            case=flow.by_org(s,Case,org,rid)
            if flow.source_batch(s,case)['sources']:
                raise flow.Problem('Process incoming sources first.',409)
            settings=flow.settings(s)
            workflow=flow.cfg_for(s,case)
            revision=case.state['revision']
            issues=[item for item in case.state['issues'] if item['key']!='__scope']
            notes=adapters.printing_reference(workflow) if workflow.get('adapter')=='print' else ''
            if not issues and not notes:
                raise flow.Problem('No customer clarification is required.',409)
            subject=case.subject
            prior=case.state['draft']
        try:
            content=ai.draft_message(settings,workflow,subject,issues,notes)
        except ai.ProviderError as err:
            raise flow.Problem(str(err),503) from err
        with Session(db) as s:
            write_lock(s)
            case=flow.by_org(s,Case,org,rid)
            state=deepcopy(case.state)
            flow.verify_review_version(state,revision)
            if state['draft']!=prior:
                raise flow.Problem('The clarification changed while generating. Refresh and retry.',409)
            state['draft']=dict(text=content,mode=settings['mode'],status='draft',revision=revision,id=flow.uid(),edit_version=1)
            flow.audit(state,'Draft prepared','Clarification awaits human review.',mode=settings['mode'])
            flow.stamp(case,state)
            s.commit()
        return request_detail(org,rid)

    @app.patch('/api/orgs/{org}/requests/{rid}/draft')
    def edit_draft(org:str,rid:str,data:DraftEdit):
        with Session(db) as s:
            write_lock(s)
            case=flow.by_org(s,Case,org,rid)
            state=deepcopy(case.state)
            flow.verify_review_version(state,data.revision)
            flow.verify_draft(state,data)
            if state['draft']['status']=='sent':
                raise flow.Problem('Generate a new draft first.',409)
            state['draft'].update(text=data.text,status='draft',edit_version=data.draft_version+1)
            flow.audit(state,'Draft edited','Human updated the outgoing message.')
            flow.stamp(case,state)
            s.commit()
        return request_detail(org,rid)

    @app.post('/api/orgs/{org}/requests/{rid}/draft/{action}')
    def draft_action(org:str,rid:str,action:str,data:DraftReview):
        with Session(db) as s:
            write_lock(s)
            case=flow.by_org(s,Case,org,rid)
            state=deepcopy(case.state)
            workflow=flow.cfg_for(s,case)
            flow.verify_review_version(state,data.revision)
            if data.role!=workflow['reviewer']:
                raise flow.Problem('Select the configured reviewer role.',403)
            item=flow.verify_draft(state,data)
            if action=='approve' and item['status']=='draft':
                item.update(status='approved',reviewer=data.role,edit_version=data.draft_version+1)
                flow.audit(state,'Message approved',data.role)
            elif action=='send' and item['status']=='approved':
                item.update(status='sent',edit_version=data.draft_version+1)
                last=next((m for m in reversed(flow.messages(s,case)) if m.direction=='incoming'),None)
                s.add(Message(id=flow.uid(),external_id=f"simulated-{item['id']}",org=org,case_id=rid,created=now(),
                    sender=workflow['name'],body=item['text'],direction='outgoing',in_reply_to=last.external_id if last else None,historical=True))
                flow.audit(state,'Simulated send','Message saved to the local conversation.')
            else:
                raise flow.Problem('This clarification action is unavailable in its current state.',409)
            flow.stamp(case,state)
            s.commit()
        return request_detail(org,rid)

    @app.post('/api/orgs/{org}/requests/{rid}/reply')
    def reply(org:str,rid:str):
        with Session(db) as s:
            write_lock(s)
            case=flow.by_org(s,Case,org,rid)
            flow.simulate_reply(s,case,FIXTURES.get(case.fixture))
            s.commit()
        return request_detail(org,rid)

    @app.post('/api/orgs/{org}/requests/{rid}/duplicate')
    def simulate_duplicate(org:str,rid:str):
        with Session(db) as s:
            write_lock(s)
            case=flow.by_org(s,Case,org,rid)
            fixture=FIXTURES.get(case.fixture)
            if not fixture or not fixture['duplicate']:
                raise flow.Problem('This scenario has no duplicate message simulation.',409)
            target,duplicate=flow.intake(s,fixture|{'subject':fixture['title']},fixture=fixture['id'])
            if not duplicate or target.id!=case.id:
                raise flow.Problem('The message did not match this thread.',409)
            state=deepcopy(case.state)
            flow.audit(state,'Duplicate ignored','Existing message ID matched. The request and extracted values were preserved.')
            flow.stamp(case,state)
            s.commit()
        return request_detail(org,rid)

    @app.post('/api/orgs/{org}/requests/{rid}/output')
    def output(org:str,rid:str):
        with Session(db) as s:
            write_lock(s)
            case=flow.by_org(s,Case,org,rid)
            state=deepcopy(case.state)
            flow.ready(s,case,state)
            if not state['output']:
                state['output']=adapters.make_output(flow.cfg_for(s,case),flow.resolved_values(state))|{'revision':state['revision']}
                flow.audit(state,'Output prepared','Draft available for human review.')
                flow.stamp(case,state)
                s.commit()
        return request_detail(org,rid)

    @app.patch('/api/orgs/{org}/requests/{rid}/output')
    def edit_output(org:str,rid:str,data:TextEdit):
        with Session(db) as s:
            write_lock(s)
            case=flow.by_org(s,Case,org,rid)
            state=deepcopy(case.state)
            flow.verify_review_version(state,data.revision)
            flow.ready(s,case,state)
            if flow.cfg_for(s,case)['adapter']!='accommodation' or not state['output']:
                raise flow.Problem('Only accommodation plan text can be edited directly. Correct facts in the field workspace.',409)
            if len(data.text)>2500 or len(data.text.splitlines())>32:
                raise flow.Problem('Keep the one-page plan to 2,500 characters and 32 lines.',422)
            previous=deepcopy(state['output'])
            flow.invalidate(state)
            state['output']=previous|{'revision':state['revision'],'staff_edit':data.text}
            state['status']='READY_FOR_REVIEW'
            flow.audit(state,'Plan edited','Staff updated the accommodation plan.')
            flow.stamp(case,state)
            s.commit()
        return request_detail(org,rid)

    @app.post('/api/orgs/{org}/requests/{rid}/review')
    def review(org:str,rid:str,data:Review):
        with Session(db) as s:
            write_lock(s)
            case=flow.by_org(s,Case,org,rid)
            state=deepcopy(case.state)
            flow.verify_review_version(state,data.revision)
            workflow=flow.cfg_for(s,case)
            if data.role!=workflow['reviewer']:
                raise flow.Problem('Select the configured reviewer role.',403)
            if data.decision=='approve':
                flow.ready(s,case,state)
                if not state['output'] or state['output']['revision']!=state['revision']:
                    raise flow.Problem('Prepare and review a current output first.',409)
            for approval in state['approvals']:
                approval['active']=False
            state['approvals'].append(dict(at=now(),role=data.role,comment=data.comment,
                decision=data.decision,revision=data.revision,active=data.decision=='approve'))
            state['status']={'approve':'APPROVED','reject':'REJECTED','return':'NEEDS_CLARIFICATION'}[data.decision]
            flow.audit(state,'Review recorded',data.decision,role=data.role,comment=data.comment,revision=data.revision)
            flow.stamp(case,state)
            s.commit()
        return request_detail(org,rid)

    @app.post('/api/orgs/{org}/requests/{rid}/export')
    def export(org:str,rid:str,destination:ExportDestination):
        with Session(db) as s:
            write_lock(s)
            case=flow.by_org(s,Case,org,rid)
            state=deepcopy(case.state)
            if state['status'] not in ('APPROVED','EXPORTED') or not any(
                a['active'] and a['revision']==state['revision'] for a in state['approvals']
            ):
                raise flow.Problem('The current record requires approval before export.',409)
            approved=state['output']
            if not approved or approved['revision']!=state['revision']:
                raise flow.Problem('The approved output is unavailable.',409)
            workflow=flow.cfg_for(s,case)
            if destination.directory:
                base=Path(destination.directory).expanduser()
                if not base.is_absolute() or not base.is_dir():
                    raise flow.Problem('Choose an existing absolute local directory.',422)
                base=base.resolve()
                if base==Path('/') or base==Path.home():
                    raise flow.Problem('Choose a dedicated export directory.',422)
            else:
                base=Path(os.getenv('RELAY_EXPORT_ROOT',ROOT/'exports'))
                base.mkdir(parents=True,exist_ok=True)
                base=base.resolve()
            folder=base/safe_name(workflow['name'])/safe_name(case.sender)/case.id/f"r{state['revision']}-{flow.uid()}"
            if not folder.resolve().is_relative_to(base):
                raise flow.Problem('The export path leaves the selected directory.',422)
            flow.audit(state,'Exported','Approved revision packaged locally.',revision=state['revision'])
            files=output_files(workflow,approved,flow.case_view(s,case)|{'audit':state['audit']},flow.documents(s,case))
            zipped=zip_bytes(files)
            staging=None
            try:
                folder.parent.mkdir(parents=True,exist_ok=True)
                staging=Path(mkdtemp(prefix='.relay-',dir=folder.parent))
                for name,content in files.items():
                    path=staging/name
                    path.parent.mkdir(parents=True,exist_ok=True)
                    with path.open('xb') as stream:
                        stream.write(content)
                staging.rename(folder)
            except OSError as err:
                if staging and staging.exists():
                    rmtree(staging,ignore_errors=True)
                raise flow.Problem('The selected directory could not be written.',422) from err
            state['status']='EXPORTED'
            state['exports'].append(dict(at=now(),path=str(folder),revision=state['revision']))
            flow.stamp(case,state)
            s.commit()
            return Response(zipped,media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="relay-{rid}.zip"'})

    @app.get('/api/orgs/{org}/references')
    def references(org:str):
        with Session(db) as s:
            if not latest(s,org): raise flow.Problem('Unknown organization.',404)
            return [flow.doc_view(d) for d in s.scalars(select(DocumentSource).where(
                DocumentSource.org==org,DocumentSource.case_id.is_(None)).order_by(DocumentSource.created.desc()))]

    @app.post('/api/orgs/{org}/references')
    def add_reference(org:str,file:UploadFile=File(...),kind:str=Form('Approved reference')):
        with Session(db) as s:
            write_lock(s)
            if not latest(s,org): raise flow.Problem('Unknown organization.',404)
            result=flow.attach(s,None,org,file.filename,file.file.read(MAX_FILE+1),kind)
            s.commit()
            return flow.doc_view(result)

    @app.post('/api/orgs/{org}/requests/{rid}/attachments')
    def add_attachment(org:str,rid:str,file:UploadFile=File(...)):
        with Session(db) as s:
            write_lock(s)
            case=flow.by_org(s,Case,org,rid)
            flow.attach(s,case,org,file.filename,file.file.read(MAX_FILE+1),'Supporting document')
            s.commit()
        return request_detail(org,rid)

    @app.get('/api/orgs/{org}/documents/{docid}')
    def download_document(org:str,docid:str,inline:bool=False):
        with Session(db) as s:
            doc=flow.by_org(s,DocumentSource,org,docid)
            if inline and doc.filename.lower().endswith('.png'):
                return Response(doc.content,media_type='image/png',headers={'X-Content-Type-Options':'nosniff'})
            return Response(doc.content,media_type='application/octet-stream',
                            headers={'Content-Disposition':f'attachment; filename="{doc.filename}"'})

    @app.get('/api/orgs/{org}/metrics')
    def metrics(org:str):
        with Session(db) as s:
            cases=s.scalars(select(Case).where(Case.org==org)).all()
            counts,missing,volume,run=[],{},{},[]
            status={}
            timeline=[]
            for case in cases:
                state=case.state
                status[state['status']]=status.get(state['status'],0)+1
                day=case.created[:10]
                volume[day]=volume.get(day,0)+1
                for item in state['issues']:
                    if item['kind']=='MISSING': missing[item['label']]=missing.get(item['label'],0)+1
                run+=state['runs']
                timeline.extend(item|{'subject':case.subject,'id':case.id} for item in state['audit'])
            durations=[r['elapsed_ms'] for r in run if r['success']]
            return dict(total=len(cases),status=status,missing=missing,volume=volume,
                completeness=round(sum(c.state['resolved'] for c in cases)*100/max(1,sum(c.state['required'] for c in cases))),
                processed=sum(c.state['required']>0 for c in cases),runs=run,average_ms=round(sum(durations)/len(durations)) if durations else None,
                activity=sorted(timeline,key=lambda i:i['at'],reverse=True))

    return app
