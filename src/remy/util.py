def generate_unique_label(seed=''):
    import datetime
    import hashlib
    import sys
    import time

    m = hashlib.sha256(seed.encode('utf-8'))
    m.update(str(datetime.datetime.now(datetime.timezone.utc)).encode('utf-8'))
    m.update(time.perf_counter_ns().to_bytes(8, sys.byteorder))

    return m.hexdigest()
