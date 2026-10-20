from fastapi.testclient import TestClient
import app as service
from market import ROUTE, FollowSun

class Selected:
    def select(self,now): return ROUTE[0]

def test_health():
    assert TestClient(service.app).get('/health').json()['status']=='ok'

def test_failure_is_explicit_and_cached(monkeypatch):
    monkeypatch.setattr(service,'selector',Selected())
    monkeypatch.setattr(service,'cache',None)
    monkeypatch.setattr(service,'frames',{})
    calls=[]
    class BadFeed:
        def history(self,**kwargs):
            calls.append(1)
            raise RuntimeError('upstream failed')
    monkeypatch.setattr(service.yf,'Ticker',lambda _:BadFeed())
    client=TestClient(service.app)
    first=client.get('/v1/market')
    assert first.status_code==200
    data=first.json()
    assert data['status']=='unavailable' and data['observed_at']==0
    assert 'upstream' not in first.text
    assert client.get('/v1/market').json()==data
    assert len(calls)==1
