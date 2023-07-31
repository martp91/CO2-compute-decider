# A big job script

import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('arg1')
parser.add_argument('-arg2', default=1)
parser.add_argument('--arg3', action='store_true')

args = parser.parse_args()
print(args)

for i in range(10):
    print(i, end='\r')
    time.sleep(1)