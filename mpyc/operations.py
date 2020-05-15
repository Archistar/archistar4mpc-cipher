#! /usr/bin/env python3
# coding: utf-8

from mpyc.runtime import mpc

import csv
import functools
import operator
import secrets
import subprocess
import sys
import time

loop = 100
sec = mpc.SecInt(32)

async def main():
  await mpc.start()
  with open(f"icissp2020-{len(mpc.parties)}_parties-output.csv", 'w', newline='') as csvfile:
    print(f"running benchmarks; output will be in {csvfile.name}")
    print("clearing netem delay just in case ...")
    subprocess.run(["sudo", "tc", "qdisc","del","dev","lo","root","netem","delay", '0ms'])
    subprocess.run(["sudo", "tc", "qdisc","del","dev","lo","root","netem","loss", '0%'])
    fieldnames = ["length","delay","loss","addition","mpc.vector_add()","summation","mpc.sum()","multiplication","mpc.schur_prod()","product","mpc.prod()"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for d in range(0,55,5):
      for p in range(0,11,1):
        for length in [1,10,100]:
          print("generating random inputs ...")
          a = [ [ mpc.input(sec(secrets.randbits(sec.bit_length)))[0] for _ in range(length) ] for _ in range(loop) ]
          b = [ [ mpc.input(sec(secrets.randbits(sec.bit_length)))[0] for _ in range(length) ] for _ in range(loop) ]
          r1 = [None] * loop
          r2 = [None] * loop
          res = [None] * 8
          for i in range(loop):
            await mpc.output(a[i])
            await mpc.output(b[i])
          time.sleep(1)
          print(f"comparing {loop} runs on vectors of length {length} with latency {d*2}ms and {p}% loss\n")

          subprocess.run(["sudo", "tc", "qdisc","add","dev","lo","root","netem","delay", f"{d}ms"])
          subprocess.run(["sudo", "tc", "qdisc","add","dev","lo","root","netem","loss", f"{p}%"])

          print("elementwise addition".ljust(32), end='', flush=True)
          t1 = time.perf_counter()
          for i in range(loop):
            r = list(map(operator.add, a[i], b[i]))
            r1[i] = await mpc.gather(r)
          t2 = time.perf_counter()
          print(f"{(t2 - t1):.5} seconds")
          res[0] = f"{(t2 - t1):f}"
          time.sleep(1)

          print("mpc.vector_add()".ljust(32), end='', flush=True)
          t1 = time.perf_counter()
          for i in range(loop):
            r = mpc.vector_add(a[i], b[i])
            r2[i] = await mpc.gather(r)
          t2 = time.perf_counter()
          print(f"{(t2 - t1):.5} seconds")
          res[1] = f"{(t2 - t1):f}"
          time.sleep(1)

          print("summation".ljust(32), end='', flush=True)
          t1 = time.perf_counter()
          for i in range(loop):
            r = functools.reduce(operator.add, a[i])
            r1[i] = await mpc.gather(r)
          t2 = time.perf_counter()
          print(f"{(t2 - t1):.5} seconds")
          res[2] = f"{(t2 - t1):f}"
          time.sleep(1)

          print("mpc.sum()".ljust(32), end='', flush=True)
          t1 = time.perf_counter()
          for i in range(loop):
            r = mpc.sum(a[i])
            r2[i] = await mpc.gather(r)
          t2 = time.perf_counter()
          print(f"{(t2 - t1):.5} seconds")
          res[3] = f"{(t2 - t1):f}"
          time.sleep(1)

          print("elementwise multiplication".ljust(32), end='', flush=True)
          t1 = time.perf_counter()
          for i in range(loop):
            r = list(map(operator.mul, a[i], b[i]))
            r1[i] = await mpc.gather(r)
          t2 = time.perf_counter()
          print(f"{(t2 - t1):.5} seconds")
          res[4] = f"{(t2 - t1):f}"
          time.sleep(1)

          print("mpc.schur_prod()".ljust(32), end='', flush=True)
          t1 = time.perf_counter()
          for i in range(loop):
            r = mpc.schur_prod(a[i], b[i])
            r2[i] = await mpc.gather(r)
          t2 = time.perf_counter()
          print(f"{(t2 - t1):.5} seconds")
          res[5] = f"{(t2 - t1):f}"
          time.sleep(1)

          print("product".ljust(32), end='', flush=True)
          t1 = time.perf_counter()
          for i in range(loop):
            r = functools.reduce(operator.mul, a[i])
            r1[i] = await mpc.gather(r)
          t2 = time.perf_counter()
          print(f"{(t2 - t1):.5} seconds")
          res[6] = f"{(t2 - t1):f}"
          time.sleep(1)

          print("mpc.prod()".ljust(32), end='', flush=True)
          t1 = time.perf_counter()
          for i in range(loop):
            r = mpc.prod(a[i])
            r2[i] = await mpc.gather(r)
          t2 = time.perf_counter()
          print(f"{(t2 - t1):.5} seconds")
          res[7] = f"{(t2 - t1):f}"
          time.sleep(1)

          subprocess.run(["sudo", "tc", "qdisc","del","dev","lo","root","netem","delay", "0ms"])
          subprocess.run(["sudo", "tc", "qdisc","del","dev","lo","root","netem","loss", "0%"])

          writer.writerow({
            'length': f"{length}",
            'delay': f"{d*2}",
            'loss': f"{p}",
            'addition': res[0],
            'mpc.vector_add()': res[1],
            'summation': res[2],
            'mpc.sum()': res[3],
            'multiplication': res[4],
            'mpc.schur_prod()': res[5],
            'product': res[6],
            'mpc.prod()': res[7]
            })
  await mpc.shutdown()

if __name__ == '__main__':
  mpc.run(main())
