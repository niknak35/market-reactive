from datetime import datetime,timezone
import pandas as pd
from market import ROUTE, FollowSun, session, readings, idle, schedule
UTC=timezone.utc

def at(value): return datetime.fromisoformat(value).replace(tzinfo=UTC)

def test_route_overlap_and_close():
    f=FollowSun()
    assert f.select(at('2026-10-20T01:00:00')).code=='ASX'
    assert f.select(at('2026-10-20T04:00:00')).code=='ASX'
    # Sydney's official close can include the closing auction; use after it.
    assert f.select(at('2026-10-20T05:30:00')).code=='JPX'
    assert f.select(at('2026-10-20T07:00:00')).code=='HKEX'
    assert f.select(at('2026-10-20T08:30:00')).code=='LSE'
    assert f.select(at('2026-10-20T16:00:00')).code=='NYSE'
    assert f.select(at('2026-10-20T21:00:00')) is None

def test_weekend_and_holiday():
    assert FollowSun().select(at('2026-10-18T12:00:00')) is None
    ny=ROUTE[-1]
    assert session(ny,at('2026-12-25T16:00:00')) is None
    assert session(ny,at('2026-11-27T18:01:00')) is None
    assert session(ny,at('2026-11-27T17:59:00')) is not None

def test_daylight_saving():
    ny=ROUTE[-1]
    assert session(ny,at('2026-10-30T13:35:00')) is not None
    assert session(ny,at('2026-11-02T13:35:00')) is None
    assert session(ny,at('2026-11-02T14:35:00')) is not None

def test_lunch_does_not_handover():
    f=FollowSun((ROUTE[1],ROUTE[2]))
    assert f.select(at('2026-10-20T01:00:00')).code=='JPX'
    e=f.select(at('2026-10-20T03:00:00'))
    assert e.code=='JPX'
    assert readings(e,at('2026-10-20T03:00:00'),pd.DataFrame())['status']=='break'

def fixture():
    e=ROUTE[-1];now=at('2026-10-20T16:00:00')
    cal=__import__('pandas_market_calendars').get_calendar('NYSE')
    rows=[]
    for _,s in cal.schedule('2026-10-01','2026-10-20').iterrows():
        for i,t in enumerate(pd.date_range(s.market_open,s.market_close,freq='5min',inclusive='left')):
            rows.append((t,100.+i*.01,1000.))
    frame=pd.DataFrame(rows,columns=['time','Close','Volume']).set_index('time')
    return e,now,frame

def test_metrics_and_staleness():
    e,now,frame=fixture()
    out=readings(e,now,frame,100.77)
    assert out['status']=='delayed' and out['relative_volume']==1.
    assert out['observed_at']<=int(now.timestamp())
    assert 0<=out['turbulence']<=1
    assert readings(e,now,frame[frame.index<pd.Timestamp(now)-pd.Timedelta(hours=1)],100.77)['status']=='stale'
    assert readings(e,now,pd.DataFrame())['status']=='unavailable'

def test_incomplete_bar_excluded():
    e,now,frame=fixture()
    before=readings(e,now,frame,100.77)
    frame.loc[pd.Timestamp(now),'Close']=100000
    frame.loc[pd.Timestamp(now),'Volume']=100000
    assert readings(e,now,frame,100.77)==before

def test_missing_baseline_does_not_invent_volume():
    e,now,frame=fixture()
    frame=frame[frame.index>pd.Timestamp('2026-10-19',tz='UTC')]
    assert readings(e,now,frame,100.77)['status']=='warming'
