"""Exercise the complete local-model request loop against an isolated demo database."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import json

from fastapi.testclient import TestClient
from backend.main import create_app

def run():
    with TemporaryDirectory(prefix='relay-local-smoke-') as folder, TestClient(create_app(Path(folder)/'relay.sqlite')) as client:
        def call(method,path,data=None):
            reply=client.request(method,'/api'+path,json=data)
            assert reply.is_success,(path,reply.status_code,reply.text)
            return reply
        health=call('PUT','/settings',dict(mode='local_ai',model='qwen3:4b')).json()
        assert health['ready'],health
        items={x['id']:x for x in call('GET','/scenarios').json()}
        def case(id):
            item=items[id]
            return f"/orgs/{item['org']}/requests/{item['case_id']}"
        def post(path,suffix,data=None):
            return call('POST',path+suffix,data).json()
        path=case('ontario_bulk-002')
        after=post(path,'/process')
        assert [i['key'] for i in after['issues']]==['site_contact'],after['issues']
        assert after['state']['runs'][-1]['mode']=='local_ai'
        draft=post(path,'/draft')['state']['draft']
        assert draft['mode']=='local_ai' and 'site contact' in draft['text'].lower()
        review=dict(revision=after['revision'],role='Dispatcher')
        draft_review=review|dict(draft_id=draft['id'],draft_version=draft['edit_version'])
        approved=post(path,'/draft/approve',draft_review)['state']['draft']
        post(path,'/draft/send',draft_review|{'draft_version':approved['edit_version']})
        post(path,'/reply')
        resolved=post(path,'/process')
        assert resolved['status']=='READY_FOR_REVIEW' and resolved['fields']['site_contact']['value']=='Jules Paver'
        out=post(path,'/output')
        post(path,'/review',review|{'revision':out['revision']})
        package=call('POST',path+'/export',{'directory':folder})
        with ZipFile(BytesIO(package.content)) as zipped:
            record=json.loads(zipped.read('record.json'))
            assert record['values']['site']=='102 Fictional Quarry Way, Exampleton, ON'
            assert record['values']['site_contact']=='Jules Paver'
            assert 'summary.pdf' in zipped.namelist()
        print('PASS Ontario Bulk local AI intake, clarification, reply, approval and ZIP export',flush=True)
        for id in ['grandieu-005','fbw_law-001','enabled_talent-001','harbor_repair-001']:
            path=case(id)
            record=post(path,'/process')
            assert record['status']=='READY_FOR_REVIEW',(id,record['issues'])
            assert post(path,'/output')['state']['output']['values'],id
            print('PASS local AI intake and generated output',id,flush=True)

if __name__=='__main__':
    run()
