import gurobipy as gp
import numpy as np
from copy import deepcopy as dc

class VaR:
    def __init__(self,
                 _demand: list,
                 _route: list,
                 _rfrate: list,
                 _lfrate: dict):
        self.demand = _demand
        self.route = _route
        self.rfrate = _rfrate
        self.lfrate = _lfrate
        # 建立 scenarios, 在某个情况下，route的可用性矩阵,True为路径可用
        self.scenarios, self.sce_probs = [], []
        self.gen_sce()

    # 生成
    def gen_sce(self):
        downedges = {}
        for e in self.lfrate:
            downedges[e] = False
        self.dfs_sce(downedges, 0, 1.0)

    def dfs_sce(self, downedges, pos, prob):
        if prob < 1e-6:
            return
        if pos == len(self.lfrate):
            avlroute = [True for r in self.route]
            for eid in downedges:
                if not downedges[eid]:
                    continue
                for r in self.route:
                    rid = self.route.index(r)
                    if not avlroute[rid]:
                        continue
                    if eid in r:
                        avlroute[rid] = False
                        break
            for sce in self.scenarios:
                if sce == avlroute:
                    sid = self.scenarios.index(sce)
                    self.sce_probs[sid] += prob
                    return
            self.scenarios.append(avlroute)
            self.sce_probs.append(prob)
            return
        for t in [True, False]:
            downedges[pos] = t
            lfr = self.lfrate[list(self.lfrate.keys())[pos]]
            p = prob * (t * lfr + (1 - t) * (1 - lfr))
            self.dfs_sce(downedges, pos + 1, p)

    # 线性规划
    def lp(self):
        nflows = len(self.demand)
        nroute = len(self.route)
        nsce = len(self.scenarios)

        m = gp.Model("var")
        x = m.addMVar(shape=(nflows, nroute), lb=0, vtype=gp.GRB.SEMICONT, name='x')
        theta = m.addMVar(shape=(nsce, 1), lb=0, vtype=gp.GRB.SEMICONT, name='theta')

        # for q in range(nsce):
        #     loss = 0.0
        #     for fid in range(nflows):
        #         floss = 0.0
        #         for rid in range(nroute):
        #             floss += x[fid, rid] * self.scenarios[q][rid]
        #         loss += floss/self.demand[fid]
        #     m.addConstr(theta[q] >= 1-loss)
        m.addConstrs(theta[q] >=
                     sum(sum(x[fid, rid] * self.scenarios[q][rid] for rid in range(nroute)) / (self.demand[fid] + 1e-5)
                         for fid in range(nflows))
                     for q in range(nsce))
        m.addConstrs(sum(x[fid, rid] for rid in range(nroute)) >= self.demand[fid] for fid in range(nflows))
        m.addConstrs(sum(x[fid, rid] for fid in range(nflows)) <= 1 for rid in range(nroute))

        m.setObjective(sum(theta[q] * self.sce_probs[q] for q in range(nsce)),
                       gp.GRB.MINIMIZE)
        m.optimize()
        if m.status == gp.GRB.OPTIMAL:
            res = x.x.tolist()
            for flw in res:
                t = sum(flw)
                if t == 0.0:
                    continue
                for i in range(len(flw)):
                    flw[i] /= t
            return res
        else:
            return []


if __name__ == '__main__':
    demand = [0.5, 1.0]
    route = [
        [1, 2, 3],
        [3, 4, 5],
        [1, 3, 5]
    ]
    rfrate = [0.496, 0.79, 0.685]
    lfrate = {
        1: 0.1,
        2: 0.2,
        3: 0.3,
        4: 0.4,
        5: 0.5,
    }
    var = VaR(demand, route, rfrate, lfrate)
    x = var.lp()
    print(x)
