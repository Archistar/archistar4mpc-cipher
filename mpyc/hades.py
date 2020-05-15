#! /usr/bin/env python3
# coding: utf-8

from mpyc.runtime import mpc
from mpyc import asyncoro
import math
import time

t = 4
p = 0xa1a42c3efd6dbfe08daa6041b36322ef
assert p >= 11
assert t >= 2
assert p % 3 != 1
assert 2 * t + 1 <= p
sec = mpc.SecFld(order = p)
n = math.ceil(math.log2(p)) * t
full1 = 6
full2 = 6
partial = 76
rounds = full1 + partial + full2
s = ((2 * p) - 1) // 3

@asyncoro.mpc_coro
async def mds_matrix(t, start):
  await asyncoro.returnType(sec, t, t)
  one = sec(1)
  xs = [ start + i for i in range(t) ]
  ys = [ start + t + i for  i in range(t) ]
  res = [ [  one / (xs[i] + ys[j]) for j in range(t) ] for i in range(t) ]
  return res

@asyncoro.mpc_coro
async def invert(matrix):
  await asyncoro.returnType(sec, t, t)
  mat = [ m[:] for m in matrix ]
  res = [ [ sec(0) for _ in range(i) ] + [sec(1)] + [ sec(0) for _ in range(i + 1, t) ]  for i in range(t) ]
  length = t
  for i in range(length):
    ###
    if await mpc.is_zero_public(mat[i][i]):
      for j in range(i + 1, length):
        if not await mpc.is_zero_public(mat[j][i]):
          mat[j], mat[i] = mat[i], mat[j]
          res[j], res[i] = res[i], res[j]
          break
      else:
        length -= 1
    elem = mat[i][i]
    ###
    for j in range(t):
      mat[i][j] = mat[i][j] / elem
      res[i][j] = res[i][j] / elem
    ###
    for j in range(length):
      if j != i and not await mpc.is_zero_public(mat[j][i]):
        elem = mat[j][i]
        for k in range(t):
          mat[j][k] -= mat[i][k] * elem
          res[j][k] -= res[i][k] * elem
  return res

def encrypt(text, key, rcs):
  assert len(text) == t
  assert len(key) == t
  assert len(rcs) == t * rounds
  res = text[:]

  lin_matrix = mds_matrix(t, 0)
  key_matrix = mds_matrix(t, 1)

  keys = [key] + ([None] * rounds)
  for r in range(rounds):
    keys[r + 1] = [ mpc.in_prod(key_matrix[i], keys[r]) + rcs[(r * t) + i] for i in range(t) ]
  ###
  for r in range(full1):
    for i in range(t):
      res[i] += keys[r][i]
      res[i] = res[i] ** 3
    res = [ mpc.in_prod(lin_matrix[i], res) for i in range(t) ]
  ###
  for r in range(full1, full1 + partial):
    for i in range(t):
      res[i] += keys[r][i]
    res[0] = res[0] ** 3
    res = [ mpc.in_prod(lin_matrix[i], res) for i in range(t) ]
  ###
  for r in range(full1 + partial, full1 + partial + full2):
    for i in range(t):
      res[i] += keys[r][i]
      res[i] = res[i] ** 3
    res = [ mpc.in_prod(lin_matrix[i], res) for i in range(t) ]
  ###
  for i in range(t):
    res[i] += keys[rounds][i]
  ###
  return res

def decrypt(text, key, rcs):
  res = text[:]

  lin_matrix = invert(mds_matrix(t, 0))
  key_matrix = mds_matrix(t, 1)

  keys = [key] + ([None] * rounds)
  for r in range(rounds):
    keys[r + 1] = [ mpc.in_prod(key_matrix[i], keys[r]) + rcs[(r * t) + i] for i in range(t) ]
  keys.reverse()
  ###
  for i in range(t):
    res[i] -= keys[0][i]
  ###
  for r in range(1, full2 + 1):
    res = [ mpc.in_prod(lin_matrix[i], res) for i in range(t) ]
    for i in range(t):
      res[i] = res[i] ** s
      res[i] -= keys[r][i]
  ###
  for r in range(full2 + 1, full2 + partial + 1):
    res = [ mpc.in_prod(lin_matrix[i], res) for i in range(t) ]
    res[0] = res[0] ** s
    for i in range(t):
      res[i] -= keys[r][i]
  ###
  for r in range(full2 + partial + 1, full2 + partial + full1 + 1):
    res = [ mpc.in_prod(lin_matrix[i], res) for i in range(t) ]
    for i in range(t):
      res[i] = res[i] ** s
      res[i] -= keys[r][i]
  ###
  return res

async def main():
  await mpc.start()

  l = mds_matrix(4, 0)
  r = invert(invert(l))
  l_ = [ await mpc.output(e) for e in l ]
  r_ = [ await mpc.output(e) for e in r ]
  assert l_ == r_, f"{l_} not equal {r_}"

  print("operating on", n, "bits")

  rcs = ['0x4c503069fff4c76d9ec17fdaf8f72935', '0x7434cee1f752f9213f6bf5a17e8ae6c0', '0x4b12e37bb94df63f64a6ffb0c401ac6a', '0x29256290f89b0cf5a2d99cc23292ca25', '0x5b50aa397994bcfe88a063041040610e', '0x4ada642d323689145fb83f3dd8545be4', '0x5b0869c1960f010430a54ade3116ad37', '0x3ff76377c3f6606494aefa73e688c0cd', '0x808a7960c0be4c0ef69dd8a278b7a392', '0x544eca62e24b72273553e263ff120e26', '0x046219129fb93d1e15d7bc80824804fc', '0x376a9ad18f1d0674c2c11538904460a2', '0x592e7900d583be1f34e0f0c8bfa72d58', '0x9648bf09b046764133d3c033c8d97f7d', '0x6500add7d5a745c330340fcbc9126578', '0x7e67505f8c26a48eebbabca514ef6566', '0x618bf9bc9c8a7704944d12fb0aaa0021', '0x35733466dc654b6a86d40c5cb07fa1c9', '0x8eb96046fce386402945496c08b6b4b6', '0x9caef184fd8abc5915b7c5ff85444e81', '0x0136d5b8b3ee212e5efd3181b9cc9c3b', '0x621a72167905a28f4921b73de7e1e9a5', '0x554ee5fae2f8fa0dd3c5d64196af50f5', '0x1634bdc25ef47567dbcb0532e7a4c1b2', '0x14fcf3f6cf3fce5e22548bf57ae39222', '0x788cfb4763a5b81f32d9f87e1de6fd73', '0x57dd343d0e6b23fa8cdd1ca5bd98a530', '0x79ee5d646ff88a1b0a59a4e19dbe32b0', '0x91950f740fd257e7b28a67ac6294f901', '0x113c377c130c5c305bae6827f8385039', '0x7dfe698845d23c3539855f9db7abcb04', '0x4dd736ac6da1b78fb1c4631caec91a97', '0x6dc148e1457f839aff550a801107ece2', '0x2f1688dffe559e44eac749b57d32050d', '0x0a2b98b1b0045f562f552d9701965f6f', '0x3829b0222cf57afbbd239cd51ddd40e5', '0x09e59f53f776e5bf76531025ddd7b5b6', '0x4c63545000362c1205298cde75815fdc', '0x26383d9e83ca0ffd847c75247d18b2a8', '0x92f35cd3fd28f9dcecdfd42ade1251fb', '0x6ea4e44e06d343ed8f8dd85db33b1eff', '0x7fb5690f24cac5af00e2014b855e3f2f', '0x46ba381fe298149fa3a87b153fccbbf7', '0x93fc9902b6b9c2debacee24d6cb5677f', '0x5eb6d1d77287e99c8abbe36bc80550c1', '0x157cfa54be2583be4a80942cb7b2c50a', '0x7a035e53792945b67fc7d7414a042772', '0x1f01ac7549bd32c496f8ebe3c7ead2a8', '0x71a3382d4d28aa27aa5a163fa84c71fb', '0x39e601e5273c7e94d4027cbe471f8d16', '0x55da969e4c7e0783c75315e9c9b2e6a8', '0x8cfbb207b62d9768998899c1aea41688', '0x5a42a10ef149dff526aab0d5486c484f', '0x05afbbdfbb86a071078d3707a18e64a4', '0x3ef30539a794f6ab78277daf6a24ff64', '0x4ddfae66b5611294fb5130945d15c29b', '0x7f72f08e905a2ad7f07ea7cdaaa80e89', '0x5ad82e48a1c182c6fd094ab46bf033f8', '0x47c78a55f28103e35c0b02a35da6ace1', '0x1ff144c8968683557e78a272fbe5edf5', '0x97f3c60ff525a329c3bc2ce7e5ec75a0', '0x8a761d4e69e5da8341ef41e3c66548b8', '0x631e71e14eb8bb361ae58d720d1df872', '0x25fa353f353e3625a56a2d6707ce5d63', '0x8e345750132e75eda946cdcdf07a1db2', '0x04c24ded60a441b7f98628decb8e3eac', '0x63f4ccc7c420dbde7d87cb5e989a8f1f', '0x6ca06c18b3426457a5239a63d68f01ed', '0x7b4f0be1a58fea804498429d1a807620', '0x5536e5078f4ca318d94aa82aaa2d455e', '0x95fb5157b35ce2497f94179b8b40784f', '0x4516a33a823d99e0075cb1e14059c652', '0x581a91fae882573e498d517453ddeebe', '0x64b76ba4ed18b713b6461782ab84b21f', '0xa153885e7d908af82a16e0e7ea62411f', '0x8c84f139c713c9db66c376463e93d123', '0x3ead9bce37ee35bb59fbddbba087f2d6', '0x114726627bc2551850d5711d1bc1badd', '0x87188a17cf6f9011c36689a877c74fe6', '0x05195954e053d1a9bf65b977927d6af4', '0x47b2b3f8b482161ba8397f5b0ffe9fb6', '0x39800552c74fb78597251fc372ecd723', '0x8c37b17c45a116f2dafac76803305b33', '0x8d8480c09835bdf24f2908587edc9cdf', '0x995695c0048fc6f5e4791e926ce1d167', '0x528f824c3bd5e90c731b051c0a1d60d4', '0x4a96391ab7465a449d001bbfedc4830d', '0x9baa35288ca5074211036d12f3c3b4a3', '0x26061978d3d50ae0ad3900a193fe60a0', '0x2cd4b2851bc02312f83656b389373102', '0x07f93db1db820ea003359db7b6a1a697', '0x919b6c6623383ce2990d563f62333ee3', '0x9d85c768f02f486778bf2c96bd5ba030', '0x26138ab579cf54a7099501f48178240c', '0x0f69f5d26c7deb25771c9a820ff7ea0c', '0x3c82d869ae4b33d0836981a1ceb976ed', '0x90023931fb75665f93faf4b7d4e1d573', '0x4c407547e9ac4bcda14983a306a5cb89', '0x5f997ec94e019ee2bfb362ee1b8cf979', '0x9c913b62f383ae992326a3951a42e11a', '0x44622bb9143147c7f9c9e7ac67456a62', '0x0fcef9a26f95af1f8a939e7123635837', '0x96865a5b76cd7a990ce6c419ecaa8016', '0x0cc726a2848e06a8e28e7bad073015cd', '0x7e3e3d6376faf9fc5d689d0da312c552', '0x1cf94a80a4df6c01bcffc95e3aee439f', '0x5c9a7b70e4c2eaaebaea17928a09b317', '0x35944afc0fb0b829aa95012cae2fe0e9', '0x3295a343085c245aea9a7b7ac5731b14', '0x141a0b691f74f60aa0baf86d1fddcdc7', '0x9a693357c3bfbacf44a2c449016651a9', '0x44c2cf63922615a1ed9710493e10d31f', '0x798503a5c640e881b2081cf04cc9ab02', '0x0a9fb7602c20f2f1807dce16a17d09ab', '0x06429d4ed2d17574c98ab92f08d78e56', '0x22349ea534df6ccf7d22fcad89a11985', '0x6968aba053cad6aa9f8ae10021702ab3', '0x30c64afa222ef4072aea28899e17f1a5', '0x7fc8053cc34b2a49b05d270878959df8', '0x1b2fbb00ccbb5f29a12eb04c3a251504', '0x94e6b69872cceeb23158f1d8cc2a21bb', '0x31a43ce32d5115fdac7a1c3ded74b45d', '0x1fa0facf1fd690de04cc4d16358aef4d', '0xa15d21a3daea919e4de62c12d3eaeedb', '0x903761ed2ee504cdad2d5c18639c9f65', '0x406aa83a2f0946606d3a24bcef0f3866', '0x16760a0a78a40e2aafd55401059dc222', '0x72a35f4a237b6bf24eb89dc3f545adfc', '0x0464e623a890f6da6c67e7c5bbbd6417', '0x97fce4adf28975a3b5104252c5dbea01', '0x2eb8ad20df8406c250ea3be2e7f12815', '0x7158506eb4ff896d231936a7406d0437', '0x3012e33afcb2034e9522db1867a42928', '0x4abd4a70d14f38886bee0d31be108649', '0x8488f39a362f771205b033882bc9a9bc', '0x27b879fdff8fb39be066f1418e4fc5fa', '0x83603751f5d379ed608027cd90cebce3', '0x69aee24ccff5b2798f53818d22d4c845', '0x8c15d882ca5a96b27598dc7c9b5050eb', '0x966ee9415fc37a48a985317740e956b1', '0x4a1e6276d61c388e27ebc5e2e42f99d4', '0x273af35d089dbfb945e132190ffe453f', '0x10dc69f9343555aae00f3440f1ba797e', '0x4879c8c61468465dd62c051210bc8821', '0x4c34a92deb8f26729212e4c1f5d68ff2', '0x0d7b122516803c66138454fc923f943d', '0x57557f4874411a266bd9f5868087e319', '0x3f44d45bce80a051203b1c1e2f8f421c', '0x258dc08d53601907067877d12c50b9d2', '0x8e2f11103beaaa5621854f30620d2c8f', '0x1754f94fbb39cb367dfdacd7d80cb31a', '0x7ca5c024fb0ccf658f4a20542c95f7fa', '0x31ff32c4be0445ff1c56d33c0bf0d1e4', '0x3adc594993e15a555d20babf643d5180', '0x33e7cbfd0b8fc99b793481a00937b891', '0x0f747f7687980d9d58a340a9bad08227', '0x07264f9889b21e9dc45bc987c7f12d7a', '0x74aa9a75cc1916daba49531702c039a5', '0x1e7e3a21d42f0b691082a9a2445e9f67', '0x8a723c5458984647cf25a1f66dde95c2', '0x0e310472364579234a975e2e64984e65', '0x0a1b415697cae00a1245e38eb0dfbcfd', '0x165e84bf6ea9a30f5ab99522141eff5f', '0x721b524d01c3af33a027edbb116b6847', '0x5b8826d3ee118b272759b6e9178b8c6c', '0x5f897ae1fa42bfc7357452cff54f6aa8', '0x003ac9aad74f4b7e6e2da7ba2a5ac05f', '0x7bfe93c6926074808efc0c482c6eca36', '0x23414a6303704c5f85bf245612d92079', '0x75115da979d98c5d1419ad73d3c8ba46', '0x049d78f90aa5e5281090041e59d2e45f', '0x729aeff895f3e9b1ab645d3b8cc51006', '0x8f677821e6f3adc4aad395d8a777dd4c', '0x4c0ea7cfd1592f19c824e1b401e3b88a', '0x5025da60daf708c79cd989e87bf27c69', '0x67ab93f5be0463db6549863093eb1564', '0x4a8e76437253f3dfeafa93caf7535875', '0x6a0999a4856da7046cd6c32b54a6dccc', '0x1ef807655e942f053fe6f81ee64262a1', '0x1de4dcf90e05f0d206366f625a93da19', '0x7c9153b6743e28ecc36c88cd1fea8673', '0x2709c9cd97efd3dea826d79778d5ba98', '0x8694c6533ab41ab1e3721488533c3027', '0x16991a34ff0c9f0494f9304d1b7a23c2', '0x30c2c025f970221e6df5bcce76d1faf6', '0x922f4fd2bd629d8c607dc20061bbdef7', '0x321c78bfe54b331d0a7fbd8a2907394b', '0x36220dcbe645d71311629198317415c7', '0x5e92acc5a7c2ab875dd0f4356aacf988', '0x9705f9f0c5e5194cb4adb7ea3e2178b3', '0x134ff50942d6a4695af9b81111511bfc', '0x906df8041b0820bda517eaf34c0efae8', '0x2802605fef929cf8c190ca21d2f0d2b7', '0x6f203fb546b59224c205c93cf99bfcd2', '0x5e15d94f20f55b800a9217e24f030954', '0xa1670cfd7be14a62ec7de151751966b0', '0x5b11db0a095618d756700ca17b5e4d93', '0x711abc12f798d63c9f374a82c348d295', '0x0ee279ab1858a4d6176476989d18c1b3', '0x9fa7cc73dcff26eb19ce2e07c6a62e18', '0x012864e9a27561a1ae8664a74e4ce3b4', '0x60497c73e4241c4b6eab9fea81bfb548', '0x9f6379a3d2f0858a19c855d0515ccd70', '0x4f6387bb26b17fb59a2efb5a4d4c8ec1', '0x34c367e548df2ac7ee3a9c026424d8c6', '0x1a454d99ab37a73c5614625c55d595ce', '0x97f39d95ebdc142e435c5e5040508689', '0x8c2c96279e076aab0006f32d3a660e67', '0x7855f4fa6a9481b1a886d17b9ecc180b', '0x9e012e40b4c38c5cd2d89ee18bd5c64b', '0x8a14ef860dbd3bc6a7a89e495a2ee89d', '0x14fc7d05642ef86f0714e95c1108b9bb', '0x25254ce3e459c4f161bcab74f5948f65', '0x4002c70da0ba62b19ff2e58eb695d684', '0x4f16514633e316d5f53c930abad44061', '0x4429e2df434b295c89b04eb4baf41a45', '0x7e25aa4aa6cab6db09865a00ca285e9b', '0x96f46caee1a5b283c8b39858018db64e', '0x04a41d04ac5188af535c8926a35d5ac1', '0x7a3cac5a8e690ea12f19a01f78dc1396', '0x86b6c17e80449d99dfb91aeecf6d0747', '0x8d64573445e934931f45048a5f9516de', '0x6db3ab04dec2a46f6564ac998c5d3e82', '0x81df6c7a7041d2fba772c71c2d79b9c1', '0x14c75ac91ef7da49740295f938ad32b5', '0x159952549097cb3cebdf8cca4a2e62bc', '0x183d1d19501a875c896765a5a39ab6a2', '0x48d1d35be04951fb287fcbb10b74ccff', '0x8248434506097265b13e9bb59bc6e755', '0xa1404288bf7a09a587c00c365e60b738', '0x7b31eedb8068c0b12e110bbf7e1365f8', '0x6d337a0e4350ff914857f6defccad98d', '0x123d60acc6bf74a738a41b694896659a', '0x64d026c58c8ecf033cb6e607e2dc7742', '0x36e165a948aa9fdf4a88be161b795a77', '0x5a3797fabc57e8653fa2c42cf4edce1a', '0x9d184dd80d1eab51820d017bbf0632a1', '0x30a9dfe9a2bed576b3e6d3eea52c187f', '0x7b351b5898992b3e86c4499490a082e7', '0x90314957b4e6b3f22666c98a2fc92816', '0x17250ded571c6132b4c094c97a9a6f9a', '0x42fb0528d7766e672c919e92eefda581', '0x1236754fe3231ae1d8043eea3d7f6c8a', '0x46714add528fb02ad6a772d1f0744de8', '0x9e1ef7bc80bba8e925a6b877d4d82969', '0x22651131fd7e659664cbe2510b6518b8', '0x9d3856c8e572b072211f5b44c3247f9a', '0x796f4fdfbd2b9cb9c3375e0b7fb8eb6d', '0x5ac2b809f875e22ee123d4bb8d8bfaa2', '0x3825d6c60b5cdd60e1eacd0655be3724', '0x0203b9a4e0b2e3feb7d544009e0d96ee', '0x21df7484c58fd446d40ab6215f9a6eae', '0x5ff848d7a9d71580ec7513fc3dd9fc9e', '0x411a3f6a77ed55525a2fc89fc9e5beb3', '0x84852ec020d34d53523b09278cb0d683', '0x3bb27900e97edae7aacd1ed8f464da2e', '0x685058e229675295773ac8ad0cbecc15', '0x810dcc9a6c5dff4129a26b8903ec38b5', '0x32bfde21efec5177db37318d47f6bfb7', '0x7acdc5c86505ac4a4a8aa1df6038b4e9', '0x703b40011dcad7bade1be9aa1ffc2d00', '0x4c42e696d1c57437a53f224db2acd7d3', '0x11aa3770f1ab3c9c3af9990f06fcc01e',
    '0x2b81c1dd6da893ce3fa956dbb4024e46', '0x96ea7f0900de85abc010e8a7a412ec4f', '0x43a307147a8e38dbd4b506265490492b', '0x8dc5e02ed93607d2dca56424d4054b02', '0x0e9c3329bfd974fd633faf5858045795', '0x3b66f675acd80c59b34714efb50d14dc', '0x56c995d60593a6389a59ec71ff201752', '0x4fff82654f200d7cad0f0088c500a487', '0x0c264e64ed404ef91aa4191f65c20594', '0x7850fdb065545132b4d67ce51b32baee', '0x9541c08b517bd0fcf8df20dfd53404db', '0x4cba9655894da5c9c0b28ea115ff15c5', '0x44a5acc6b079760a4f5ea7fe77591c7a', '0x7917381966f4caea500d41662a000c04', '0x5283cf6c5371aa0d0feec3d5561f9067', '0x5d1af8a4de3733c3e1e54caf48217f02', '0x741e13c979e4e7fe20b4a33e270b59ca', '0x090b391e53408e2baf32da55d7e8a1d8', '0x854f30cfbbcc1524fa2c07bb4e719c82', '0x0f058f366383ae1911384b24a72fa9e6', '0x24bd70ab9cfbf142337c77ab0e15f15d', '0x5dfa65d910872462f094e5718b446f65', '0x0a61864ceaee91820e81ece18110115a', '0x5d8dc26f83e723c3ab49ebfebd79631e', '0x077ca056f71dbbb21f2fca35df23a613', '0x7f08ee83021cf92c94c2826d3a8a9734', '0x41f7edddb4cc569a9b443a3ef857ee2d', '0x984656659260c496caac917b266e1ebe', '0x196be335015ebe1a4ab1427d6c984d93', '0x338357e2e326374007c9bcdfd6df5bf6', '0x5baa2c29290b33effdbf6f2aefff0d80', '0x96981f8b19382079454639610fc21701', '0x2902a8498dd23fa0480acfae6cd23839', '0x612443b32873086e4716c216e23f4890', '0x2269bf764bac34189ae6640195fd0bfb', '0x7718dbc307a574847e5db8a46413d520', '0x1434b1c785ca3b91e2fc71930ad544f3', '0x8a8158d07a15826d78ba9f48a44bc908', '0x1369c9ec93cb22e03a02487274f76705', '0x5cc9d689badec9e595dae087ff5e8c2b', '0x8b55814e83e95112367f26355a673600', '0x3c7565e0662d803f90cf928460c5e2ab', '0x496f69e0af515674e66740985c50c39d', '0x7a0ba22a91305bb004890689bc35bdd0', '0x3bbfc735c9050a7d338c828190388fda', '0x8e32d9a9c45bd86cf73b59341f9cf7d3', '0x9ee9e6dc0eee4b1a5fd74133feb17fc2', '0x6f0216ecb03c814d5bcc43d9903a5c68', '0x06c7aec15c41461b7067257436369ad2', '0x8ccc48e309948893ecf37c1293aa7c88', '0x8f9cd2a13ac787fb0041c9c2a57b735a', '0x0437372476f815a8919c0aac335a34c7', '0x8b81b983d6381d8648be0fa094c82f01', '0x3508a1d037286df969755f90d555ca01', '0x0f9d0a525861ccb553ba8b1af35adb4c', '0x2fdc8d65605c9547e809812d71822376', '0x3c37306151919c9dc8c4941e2a1f2ca0', '0x1161074ba275ec772383b5ab7b86edb1', '0x0acb0457abf6e29cf17433b40022c52d', '0x68ce3692a7f6a280b85d14fb94725af2', '0x70057fe33f74f9ee1855e81a2cb4a7fe', '0x18499dc8222bac8f8d2390b8f477c5ba', '0x06bea64e81307b9f8ed9250e5f9f752d', '0x91c715a74c5f89c3f5366affc97d7731', '0x63e512af11c4e7c1014b87fef311a9ea', '0x3058ced4aff174528b170f2b1a606f31', '0x65dba1b3363e4b42a0cccb7745cd80ae', '0x6891d4d5a87ec81d64c5aa9725a01714', '0x436ea49e7b9258f9999f989476219140', '0x8b9afe1844881662e4dc6ff9e32a3c36', '0x28957c546026bbd7628fe84a368c47d3', '0x72d5a22a040498fa27d10126bfa8221f', '0x0937eb689bd7d3892d2dc9a87050ac37', '0x19c6aa02505a83b4f28c4c1be8eee4a4', '0x8310b4ba47e41992d66a9999c39f2f96', '0x0bab09bba7cbb0320d79ee49d7fd8196', '0x8df4f3241248ae2d75ce9919aaed98f8', '0x31894df6459d38161b17763c09f1872d', '0x80fdeabf795796ff7222d37de5cf82f3', '0x686c2c3d75f27b496fc55b6330b0bc91', '0x9a58ca45145e895630cb0a56592e9744', '0x78577707b0620f83efb7dafd0f20fa8e', '0x7fa22fb1fea6075e8408ef89073e62cf', '0x4b431a51f6a0eea9afa8d4ace9a6fbf6', '0x7ad4bcd4cbac0ad29749fd1f296ae8ae', '0x318ce5d32fd596a76b9bda70977d0c21', '0x2cb55bbdfcb2b1c8d0eb20c3996c3276', '0x9e1000965152ffe8f4a4ac9642a7e1d2', '0x4a78c1fc72a4909441cb6fbf2498fcc6']
  rcs = [ sec(int(n, base=16)) for n in rcs ]
  key = [ mpc.random.getrandbits(sec, sec.bit_length) for _ in range(t) ]
  inp = [ mpc.random.getrandbits(sec, sec.bit_length) for _ in range(t) ]
  plain = await mpc.output(inp)
  print("encoding ... ", end='', flush=True)
  t1 = time.perf_counter()
  enc = encrypt(inp, key, rcs)
  temp = await mpc.output(enc)
  t2 = time.perf_counter()
  print(f"took {(t2 - t1):.2} seconds")
  print("decoding ... ", end='', flush=True)
  t1 = time.perf_counter()
  dec = decrypt(enc, key, rcs)
  res = await mpc.output(dec)
  t2 = time.perf_counter()
  print(f"took {(t2 - t1):.3} seconds")
  print("checking ... ", end='', flush=True)
  assert plain == res, f"{plain} not equal {res}"
  print("ok!")
  await mpc.shutdown()

if __name__ == '__main__':
  mpc.run(main())
