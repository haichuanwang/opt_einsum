import numpy as np
import pandas as pd
import sys, traceback
import timeit

import test_helper as th
from opt_einsum import opt_einsum
pd.set_option('display.width', 200)

import resource
rsrc = resource.RLIMIT_DATA
limit = int(1e10)
resource.setrlimit(rsrc, (limit, limit))

test_einsum = False
test_paths = False

#scale_list = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
scale_list = [1]

out = []
for key in th.tests.keys():
    sum_string, index_size = th.tests[key]
    for scale in scale_list:
        views = th.build_views(sum_string, index_size, scale=scale)

        # At this point lets assume everything works correctly
        opt_path = opt_einsum(sum_string, *views, path='optimal', return_path=True)
        opp_path = opt_einsum(sum_string, *views, path='opportunistic', return_path=True)

        # If identical paths lets just skip them
        if all(x==y for x, y in zip(opp_path, opt_path)):
            break

        setup = "import numpy as np; from opt_einsum import opt_einsum; \
                 from __main__ import sum_string, views, opt_path, opp_path"
        opportunistic_string = "opt_einsum(sum_string, *views, path=opp_path)"
        optimal_string = "opt_einsum(sum_string, *views, path=opt_path)"

        # Optional test
        if test_paths:
            opp = opt_einsum(sum_string, *views, path=opp_path)
            opt = opt_einsum(sum_string, *views, path=opt_path)
            assert np.allclose(opp, opt)
        if test_einsum and test_paths:
            assert np.allclose(opp, np.einsum(sum_string, *views))

        num_loops = 5
        optimal_time = timeit.timeit(opportunistic_string, setup=setup, number=num_loops) / num_loops
        opportunistic_time = timeit.timeit(optimal_string, setup=setup, number=num_loops) / num_loops

        out.append([key, sum_string, scale, optimal_time, opportunistic_time])

df = pd.DataFrame(out)
df.columns = ['Key', 'String', 'Scale', 'Optimal time', 'Opportunistic time']
df['Ratio'] = np.around(df['Opportunistic time']/df['Optimal time'], 2)

df = df.set_index(['Key', 'Scale'])
df = df.sort_index()
print df


print '\nDescription of speedup:'
print df['Ratio'].describe()
print '\nNumber of optimal paths slower than opportunistic paths: %d.' % np.sum(df['Ratio']<0.8)

