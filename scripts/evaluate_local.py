"""Measure model-only and cross-checked pipeline extraction on independent expectations."""
import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import mean,median

from backend import adapters,ai,engine,validation
from synthetic_data.catalog import catalog,get_workflows

DEFAULTS=('ontario_bulk-001','ontario_bulk-002','ontario_bulk-003','ontario_bulk-005','ontario_bulk-031',
          'ontario_bulk-040','ontario_bulk-047','ontario_bulk-052','grandieu-001','fbw_law-001',
          'enabled_talent-001','enabled_talent-002','harbor_repair-001','natural-transport')
CRITICAL={'service_date','service_time','site','site_contact','site_phone','appointment','appointment_time',
          'size','quantity','format','lender','borrower','property','principal','rate','fees','role','needs','provisions'}

def load_samples():
    fixtures={x['id']:x for x in catalog()}
    natural=dict(fixtures['ontario_bulk-001'])
    natural.update(id='natural-transport',title='Unlabelled transport prose',missing=[],ambiguous=[],replies=[],attachments=[],
        body=('Please deliver 13 tonnes of crushed gravel to 101 Fictional Quarry Way, Exampleton, ON on 2026-11-24 at 07:30. '
              'This is an appointment and the appointment is also at 07:30. The site contact is Eli Cairn on 416-555-0101. '
              'For the client contact, use orders@example.com. Please put DEMO-PO-001 on the order.'),
        expected=dict(fixtures['ontario_bulk-001']['expected']))
    natural['expected']['product']='crushed gravel'
    fixtures[natural['id']]=natural
    return fixtures

def apply(workflow,state,facts,sources):
    candidates={s['id']:s for s in sources}
    spec={f['key']:f for f in workflow['fields']}
    for f in facts:
        engine.merge_fact(state,spec[f.key],f,candidates[f.source],'local_ai')

def expected_values(workflow,fixture):
    specs={f['key']:f for f in workflow['fields']}
    return {key:validation.normalize(specs[key],value)[0] for key,value in fixture['expected'].items()}

def classify(aggregate,expected,predicted,prefix):
    aggregate[prefix+'_tp']+=len(expected&predicted)
    aggregate[prefix+'_fn']+=len(expected-predicted)
    aggregate[prefix+'_fp']+=len(predicted-expected)
    # The evaluated universe for detection is all workflow fields in each case.
    aggregate[prefix+'_errors']+=len(expected^predicted)

def compare(aggregate,workflow,state,fixture):
    facts=engine.resolved_values(state)
    expected=expected_values(workflow,fixture)
    keys={f['key'] for f in workflow['fields']}
    exact={key for key in expected if facts.get(key)==expected[key]}
    false_extra=set(facts)-set(expected)
    aggregate['correct_fields']+=len(exact)
    aggregate['expected_fields']+=len(expected)+len(false_extra)
    aggregate['correct_critical']+=len(exact&CRITICAL)
    aggregate['expected_critical']+=len((set(expected)|false_extra)&CRITICAL)
    aggregate['detection_fields']+=len(keys)
    issues,*_=validation.evaluate(workflow,state['fields'])
    keyword=lambda kind:{i['key'] for i in issues if i['kind']==kind}
    classify(aggregate,set(fixture['missing']),keyword('MISSING'),'missing')
    classify(aggregate,set(fixture['ambiguous']),keyword('AMBIGUOUS'),'ambiguity')
    good=exact==set(expected) and not false_extra and keyword('MISSING')==set(fixture['missing']) and keyword('AMBIGUOUS')==set(fixture['ambiguous'])
    aggregate['complete_records']+=int(good)
    aggregate['records']+=1
    return dict(exact=good,field_mismatches=sorted(set(expected)-exact|false_extra),
                missing=sorted(keyword('MISSING')),ambiguous=sorted(keyword('AMBIGUOUS')))

def summarize(a):
    def ratio(n,d): return round(n/d,4) if d else None
    return dict(field_accuracy=ratio(a['correct_fields'],a['expected_fields']),
        critical_exact_match=ratio(a['correct_critical'],a['expected_critical']),
        missing_precision=ratio(a['missing_tp'],a['missing_tp']+a['missing_fp']),
        missing_recall=ratio(a['missing_tp'],a['missing_tp']+a['missing_fn']),
        ambiguity_accuracy=ratio(a['detection_fields']-a['ambiguity_errors'],a['detection_fields']),
        ambiguity_recall=ratio(a['ambiguity_tp'],a['ambiguity_tp']+a['ambiguity_fn']),
        conflict_accuracy=ratio(a['conflict_correct'],a['conflict_trials']),
        complete_record_accuracy=ratio(a['complete_records'],a['records']),counts=dict(a))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',default='qwen3:4b')
    parser.add_argument('--output',type=Path,default=Path('.local/evaluation.json'))
    parser.add_argument('--scenarios',nargs='+',default=DEFAULTS)
    args=parser.parse_args()
    settings=dict(mode='local_ai',model=args.model)
    workflows=get_workflows()
    fixtures=load_samples()
    measures={'model_only':Counter(),'pipeline':Counter()}
    latency=[]
    records=[]
    for id in args.scenarios:
        fixture=fixtures[id]
        workflow=workflows[fixture['org']]
        sources=[dict(id='m1',text=fixture['body'],label='Initial message',page=None)]
        sources.extend(dict(id=f'd{i}',text=d['text'],label=d['name'],page=1 if d['kind']=='pdf' else None)
                       for i,d in enumerate(fixture['attachments'],1))
        item=dict(id=id)
        try:
            model,ms=ai.extract(settings,workflow,sources,{},[],[],supplement=False)
            latency.append(ms)
            states={name:engine.initial_state() for name in measures}
            for name,state in states.items():
                selected=model if name=='model_only' else ai.supplement_facts(workflow,sources,model)
                apply(workflow,state,selected,sources)
                item[name]=compare(measures[name],workflow,state,fixture)
                item[name]['literal_checks']=sum(f.origin=='literal_source' for f in selected)
            if fixture['replies']:
                for index,reply in enumerate(fixture['replies'],1):
                    batch=[dict(id=f'm{index+1}',text=reply,label='Customer reply',page=None)]
                    model_reply,took=ai.extract(settings,workflow,batch,states['pipeline']['fields'],[fixture['body']],[],supplement=False)
                    latency.append(took)
                    for name,state in states.items():
                        selected=model_reply if name=='model_only' else ai.supplement_facts(workflow,batch,model_reply)
                        apply(workflow,state,selected,batch)
                for name,state in states.items():
                    issues,*_=validation.evaluate(workflow,state['fields'])
                    observed={i['key'] for i in issues if i['kind']=='CONFLICTING'}
                    expected={fixture['conflict']} if fixture['conflict'] else set()
                    measures[name]['conflict_trials']+=1
                    measures[name]['conflict_correct']+=observed==expected
                    item[name]['after_reply_issues']=[f"{issue['kind']}:{issue['key']}" for issue in issues]
            item['first_run_ms']=ms
        except ai.ProviderError as err:
            for count in measures.values():
                count['provider_failures']+=1
            item['provider_error']=str(err)
        print(json.dumps(item,ensure_ascii=False),flush=True)
        records.append(item)
    result=dict(model=args.model,scenarios=len(records),metrics={name:summarize(a) for name,a in measures.items()},
        latency_ms={'runs':len(latency),'mean':round(mean(latency)) if latency else None,
                    'median':round(median(latency)) if latency else None,'min':min(latency,default=None),'max':max(latency,default=None)},
        failures=[r['id'] for r in records if r.get('provider_error') or not r.get('pipeline',{}).get('exact')],
        records=records)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))

if __name__=='__main__':
    main()
