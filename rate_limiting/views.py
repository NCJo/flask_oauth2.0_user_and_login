from redis import Redis
redis = Redis()

import time
from functools import update_wrapper
from flask import request, g
from flask import Flask, jsonify

app = Flask(__name__)



class RateLimit(object):
    # Give extra 10 sec for possibility of badly synchronous redis
    expiration_window = 10

    # key_prefix: string that keep track of rate limit from each request
    # limit: allowing rate limit
    # per: allowing rate limit
    # send_x_headers:  bool options allow us to inject into each response headers the number of request they can make before hit limit
    def __init__(self, key_prefix, limit, per, send_x_headers):
        # When time limit can reset itself and pin it to my key
        self.reset = (int(time.time()) // per) * per + per
        self.key = key_prefix + str(self.reset)

        self.limit = limit
        self.per = per
        self.send_x_headers = send_x_headers
        p = redis.pipeline()
        p.incr(self.key)
        p.expireat(self.key, self.reset + self.expiration_window)
        self.current = min(p.execute()[0], limit)

    # Calculate how many request I have left
    remaining = property(lambda x: x.limit - x.current)
    # Return true of hit rate limit
    over_limit = property(lambda x: x.current >= x.limit)

def get_view_rate_limit():
    return getattr(g, '_view_rate_limit', None)

def on_over_limit(limit):
    # 429 means too many requests
    return (jsonify({'data':'You hit the rate limit','error':'429'}),429)

def ratelimit(limit, per=300, send_x_headers=True,
              over_limit=on_over_limit,
              scope_func=lambda: request.remote_addr,
              key_func=lambda: request.endpoint):
    def decorator(f):
        def rate_limited(*args, **kwargs):
            key = 'rate-limit/%s/%s/' % (key_func(), scope_func())
            rlimit = RateLimit(key, limit, per, send_x_headers)
            g._view_rate_limit = rlimit
            if over_limit is not None and rlimit.over_limit:
                return over_limit(rlimit)
            return f(*args, **kwargs)
        return update_wrapper(rate_limited, f)
    return decorator





@app.after_request
def inject_x_rate_headers(response):
    limit = get_view_rate_limit()
    if limit and limit.send_x_headers:
        h = response.headers
        h.add('X-RateLimit-Remaining', str(limit.remaining))
        h.add('X-RateLimit-Limit', str(limit.limit))
        h.add('X-RateLimit-Reset', str(limit.reset))
    return response

@app.route('/rate-limited')
# 300 requests per 30 seconds
@ratelimit(limit=300, per=30 * 1)
def index():
    return jsonify({'response':'This is a rate limited response'})

if __name__ == '__main__':
	app.secret_key = 'super_secret_key'
	app.debug = True
	app.run(host = '0.0.0.0', port = 5000)
