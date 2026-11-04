import json
import os
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import redis
from rabbithole.cache import SearchCache


def main():
    client=redis.Redis.from_url(os.getenv('REDIS_URL','redis://127.0.0.1:6379/0'))
    client.ping()
    namespace='verification-'+str(time.time_ns())
    cache=SearchCache(namespace,client=client,ttl=1)
    calls=[]
    def compute():
        calls.append(1)
        return {'papers':['W1'],'snapshot':namespace}
    first=cache.get_or_compute({'q':'music'},compute)
    started=time.perf_counter()
    repeat=[cache.get_or_compute({'q':'music'},compute)[1] for _ in range(20)]
    latency=(time.perf_counter()-started)*1000/20
    time.sleep(1.1)
    expired=cache.get_or_compute({'q':'music'},compute)
    assert first[1]=='redis-miss' and set(repeat)=={'redis-hit'} and expired[1]=='redis-miss' and len(calls)==2
    for key in client.scan_iter('rabbithole:search-v2:'+namespace+':*'):client.delete(key)
    result=dict(redis_version=client.info('server')['redis_version'],real_server=True,cache_hits=20,
                expiry_verified=True,mean_hit_ms=latency,scope='Local cache protocol check, not production search latency')
    (ROOT/'outputs/cache_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
