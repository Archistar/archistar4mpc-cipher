#! /usr/bin/env python3
# coding: utf-8

from mpyc.runtime import mpc
import math
import copy
import time

n = 129
assert n % 2 == 1
sec = mpc.SecFld(2**n)
rounds = math.ceil(n / math.log2(3))
s = ((2 ** (n + 1)) - 1) // 3

def encrypt(m, key, constants):
  m = copy.copy(m)
  for r in range(rounds):
    m = m + key + constants[r]
    m = m ** 3
  m = m + key
  return m

def decrypt(m, key, constants):
  m = copy.copy(m)
  m = m + key
  for r in range(rounds - 1, -1, -1):
    m = m ** s
    m = m + key + constants[r]
  return m

async def main():
  await mpc.start()
  constants = [0] + [ mpc.random.getrandbits(sec, n) for _ in range(rounds - 1) ]
  key = mpc.random.getrandbits(sec, n)
  inp = mpc.random.getrandbits(sec, n)
  plain = await mpc.output(inp)
  print("encoding ... ", end='', flush=True)
  t1 = time.perf_counter()
  enc = encrypt(inp, key, constants)
  temp = await mpc.output(enc)
  t2 = time.perf_counter()
  print(f"took {(t2 - t1):.2} seconds")
  print("decoding ... ", end='', flush=True)
  t1 = time.perf_counter()
  dec = decrypt(enc, key, constants)
  res = await mpc.output(dec)
  t2 = time.perf_counter()
  print(f"took {(t2 - t1):.3} seconds")
  print("checking ... ", end='', flush=True)
  assert plain == res, f"{l.value.value} not equal {r.value.value}"
  print("ok!")
  await mpc.shutdown()

if __name__ == '__main__':
  mpc.run(main())
