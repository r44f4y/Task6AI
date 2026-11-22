"""Reproducible fictional intake and independently constructed expectations."""
from datetime import date, timedelta
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

def get_workflows():
    return {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / "workflows").glob("*.json"))}

def catalog():
    workflows = get_workflows()
    fixtures = []
    def add(org, number, name, facts, *, missing=(), ambiguous=None, replies=(),
            attachments=(), reply_attachments=None, conflict=None, preface="", unsupported=False, duplicate=False, style=0):
        workflow = workflows[org]
        labels = {f["key"]: f["label"] for f in workflow["fields"]}
        ambiguous = ambiguous or {}
        def text(values, layout=0):
            separator = "; " if layout == 2 else "\n"
            prefix = "• " if layout == 1 else ""
            return separator.join(
                f"{prefix}{labels[k]}: {v if not isinstance(v, bool) else ('Yes' if v else 'No')}"
                for k,v in values.items())
        initial = {**facts, **ambiguous}
        initial = {k:v for k,v in initial.items() if k not in missing}
        for attachment in attachments:
            for k in attachment["fields"]:
                initial.pop(k, None)
        body = "\n\n".join(x for x in (preface, text(initial, style), "Thanks for checking.\n" if style != 2 else "") if x)
        fixture_id = f'{org}-{number:03}'
        def attachment_spec(a,values):
            out={k:v for k,v in a.items() if k!='fields'}
            out['text']=text({key:values[key] for key in a['fields']})
            return out
        fixtures.append(dict(id=fixture_id, org=org, title=name, sender=f'demo-{org.replace("_","-")}@example.com',
            channel=workflow["channels"][0], body=body, thread=fixture_id,
            message_id=f'{fixture_id}@example.com', timestamp=f'2026-11-21T{14+number//60:02}:{number%60:02}:00Z',
            expected={k:v for k,v in facts.items() if k not in missing and k not in ambiguous},
            missing=list(missing), ambiguous=list(ambiguous), conflict=conflict, unsupported=unsupported, duplicate=duplicate,
            clarification=[f'Provide {labels[k].lower()}.' for k in missing]+[f'Confirm {labels[k].lower()}.' for k in ambiguous],
            replies=[text(r) if isinstance(r,dict) else r for r in replies],
            final={**facts, **{k:v for reply in replies if isinstance(reply, dict) for k,v in reply.items()
                            if k not in ambiguous}},
            attachments=[attachment_spec(a,facts) for a in attachments],
            reply_attachments={str(index):[attachment_spec(a,facts) for a in items]
                               for index,items in (reply_attachments or {}).items()}))
    materials = ['Granular A', 'Clear stone', 'Screened topsoil', 'Recycled concrete', 'Crushed gravel']
    for i in range(1, 61):
        facts = dict(product=materials[(i-1)%5], service_date=str(date(2026,11,23)+timedelta(days=i%25)),
            service_time='07:30' if i%2 else '13:15', service_type='Delivery' if i%4 else 'Pickup',
            site=f'{100+i} Fictional Quarry Way, Exampleton, ON', site_contact=['Nora Slate','Eli Cairn','Jules Paver'][i%3],
            site_phone=f'416-555-01{i:02}', appointment=i==3 or i%3 != 0, client_contact='orders@example.com',
            quantity=12+i%20,unit='tonnes',po=f'DEMO-PO-{i:03}')
        if facts["appointment"]:
            facts["appointment_time"] = '08:00' if i==3 else facts["service_time"]
        options = dict(preface=['Dispatch team, please book this movement.', 'Hey, could you get this on the schedule?',
            'Morning, forwarding the site foreman’s notes from earlier in the week.', 'Order request per the revised job schedule.'][i%4],
            style=i%3)
        titles = f'{facts["product"]} • {facts["service_type"].lower()} request {i:02}'
        if i==2 or 31<=i<=39:
            missing = ('site_contact', 'site_phone') if i in (31,32,33) else ('site_contact',)
            options.update(missing=missing,replies=[{k:facts[k]} for k in missing])
            titles = 'Missing site contact' if i==2 else f'{titles} • contact needed'
        if i==3 or 40<=i<=46:
            key = 'appointment_time' if i==3 else 'service_time'
            hour = '8' if i==3 else '7'
            facts[key] = '08:00' if i==3 else '07:00'
            options.update(ambiguous={key:hour},replies=[{key:f'{hour} in the morning'}])
            titles = 'Appointment at “8”' if i==3 else f'{titles} • confirm time'
        if 47<=i<=51:
            key = ['service_date','site','product','client_contact','appointment_time'][i-47]
            facts.setdefault(key,'08:00')
            if key=='appointment_time':
                facts["appointment"]=True
            options.update(missing=(key,),replies=[{key:facts[key]}])
        if 52<=i<=55:
            options.update(replies=[{'site':f'{300+i} Fictional Haul Lane, Exampleton, ON'}],conflict='site')
            titles = f'{titles} • conflicting site'
        if i in (56,57):
            options.update(preface='Please cancel the existing order. Handle manually.',unsupported=True)
            titles = f'{titles} • cancellation'
        if i==58:
            options.update(duplicate=True)
            titles = f'{titles} • duplicate replay'
        if i in (5,25,59):
            options.update(attachments=[dict(name='delivery-instructions.pdf',kind='pdf',fields=['site','site_phone'])])
        if i==60:
            options.update(attachments=[dict(name='order-notes.txt',kind='txt',fields=['site'])])
        if i==1:
            titles='Complete gravel delivery'
            facts["product"]='Crushed gravel'
        add('ontario_bulk',i,titles,facts,**options)
    for i in range(1,11):
        size = 'A5' if i%2 else 'A6'
        w,h = (148,210) if size=='A5' else (105,148)
        facts = dict(customer=f'Fictional Arts Collective {i:02}', service='Flyer printing', quantity=100*i,
            size=size, colour='Full colour', sides='Double-sided', design=f'event-{i}.png', format='PNG',
            design_width=w,design_height=h,resolution=300,due='2026-12-10')
        missing = {1:('size',),2:('quantity',),3:('design','format','design_width','design_height','resolution'),
            7:('sides',),8:('due',),9:('colour',)}.get(i,())
        if i==4:
            facts.update(design='poster.svg',format='SVG')
        design=dict(name=facts['design'],kind='png',width_mm=w,height_mm=h,dpi=300,
                    fields=['design','format','design_width','design_height','resolution'])
        add('grandieu',i,['Flyer sizes and pricing','Missing flyer quantity','Missing design file','Unsupported design format','Complete flyer order'][min(i-1,4)],
            facts,missing=missing,replies=[{k:facts[k] for k in missing}] if missing else [],
            preface='Hi! What flyer sizes, file formats and prices are available? I haven’t selected a size yet.' if i==1 else 'Hi! Please print flyers for our fictional event.',
            attachments=[design] if i not in (3,4) else [],
            reply_attachments={1:[design]} if i==3 else None)
    for i in range(1,4):
        facts = dict(lender='Example Credit Trust',borrower=f'Fictional Borrower {i}',property=f'{220+i} Sample Title Road, Exampleton, ON',
            legal_description=f'LOT {i} PLAN DEMO-MT',pin=f'DEMO-0000{i}',registration=f'DEMO-MORT-00{i}',registration_date='2021-06-01',
            original_principal='250000.00',principal='174500.00',rate='5.25',default_date='2026-08-15',
            as_of='2026-11-21',payment_history='Demo ledger confirms no payments during calculation period',
            fees='125.00',method='Simple ACT/365')
        if i==3:
            facts.update(transferred_lender='Fictional Transfer Trust',transfer_date='2024-05-02')
        docs = [
            dict(name='registered-mortgage.pdf',kind='pdf',fields=['lender','borrower','registration','registration_date','original_principal','rate','method']),
            dict(name='title-search.pdf',kind='pdf',fields=['property','legal_description','pin']),
            dict(name='ledger.txt',kind='txt',fields=['principal','default_date','as_of','fees']+(['payment_history'] if i!=2 else []))]
        if i==3: docs.append(dict(name='transfer-of-charge.txt',kind='txt',fields=['transferred_lender','transfer_date']))
        add('fbw_law',i,['Complete mortgage file','Payment history unavailable','Transferred mortgage'][i-1],facts,
            missing=('payment_history',) if i==2 else (), attachments=docs,preface='Fictional mortgage file. Please review the attached specimens.')
    for i,(role,needs) in enumerate([
        ('Customer support associate','Low vision. Screen magnification, keyboard navigation and large-print materials requested.'),
        ('Customer support associate','Larger display text and accessible training materials requested.'),
        ('Inventory clerk','Written instructions and visual notifications requested.'),
        ('Program coordinator','Live captions and written meeting summaries requested.'),
        ('Library assistant','Adjustable workstation and scheduled breaks requested.')],1):
        add('enabled_talent',i,['Low vision in customer support','Missing employer provisions','Inventory onboarding','Accessible meetings','Adjustable workstation'][i-1],
            dict(candidate=f'Candidate Demo {i}',role=role,duties='Use the employer portal, attend team onboarding and communicate with coworkers',
                 needs=needs,provisions='Accessibility lead available; assistive technology and setup must be confirmed with IT'),
            missing=('provisions',) if i==2 else (),preface='Fictional pre-hire accessibility intake.')
    add('harbor_repair',1,'Configuration-only equipment workflow',
        dict(asset='DEMO-PUMP-42',fault='Pump loses pressure',requested_date='2026-12-02',
             contact='maintenance@example.com',on_site=True,location='42 Fictional Harbour Road, Exampleton, ON'))
    return fixtures

if __name__ == '__main__':
    for org in get_workflows():
        folder = Path(__file__).parent / org
        folder.mkdir(exist_ok=True)
        data = [case for case in catalog() if case['org']==org]
        (folder / 'scenarios.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
