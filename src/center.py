"""
    流量调配中心
"""

import json
import time
from copy import deepcopy
from queue import Queue as Queue
from route import Route
from flow import Flow
from generate import Information
from generate import load as gload
from algorithms.var import VaR
from scipy.stats import chi2_contingency as ccy


class TrafficCenter:
    def __init__(self, _method):
        self.method = _method
        self.info = Information()
        gload(self.info)
        # 流量矩阵
        self.trf_pt = 1  # 指示读到哪条流量需求
        self.trf_mat = [[[Flow(-1, -1, -1, 0.0)] for nn in self.info.nodes] for n in self.info.nodes]  # 流量矩阵
        # 故障链路记录
        self.down_edges = [False for e in self.info.edges]
        self.fe_pt = 1  # 指示读到哪条故障
        # 初始化联合故障概率模型
        self.frate = [-1 for e in self.info.edges]
        self.flog = self.info.flog
        if self.method == 'rfrr':
            self.union_frate()
        # 预配置: 节点 a 到 b 走哪些路径，每个路径上分配的百分比
        self.sr = [[[Route(-1, -1, [-1, -1], -1)] for nn in self.info.nodes] for n in self.info.nodes]
        self.segr()
        # 时间片
        self.trf_num = self.info.interval  # 每个时间片的流量需求数目
        # 实验信息记录
        self.trf_rr = []  # 被重新调度的流量规模（数量）
        self.trf_avgutl = []  # 每轮调度过后，网络的平均利用率
        self.rr_failtimes = 0  # 重路由失败次数
        self.notrf_times = 1  # 没有流量跑在当前故障链路上
        self.time_consp = []  # 计算恢复方案的路由耗时，毫秒为单位

    # 预计算配置
    def segr(self):
        for e in self.info.edges:
            src, des = e[0], e[1]
            self.sr[src][des] = [Route(src, des, [src, des], 1.0)]
        # 选定 src 到 des 的路
        for src in self.info.nodes:
            for des in self.info.nodes:
                if src == des or (src, des) in self.info.edges:
                    continue
                path, num = self.bfspath()
                for p in path:
                    route = Route(src, des, p, 1.0 / num)  # 负载均衡
                    self.sr[src][des].append(Route(src, des, [src, des], 1.0))

    '''
        寻路
    '''

    # BFS，从src到des的路径，默认3条path
    def bfspath(self, src, des, n=3):
        cnt = 0
        p = []  # 搜索结果
        q = Queue()
        q.put([src])
        vis = [False for e in self.info.edges]
        while cnt < n and not q.empty():
            t = q.get()
            h = t[-1]
            for e in self.info.edges:
                eid = self.info.edges.index(e)
                if e[0] != h or self.down_edges[eid] or vis[eid]:
                    continue
                tt = deepcopy(t)
                tt.append(e[1])
                if e[1] == des:
                    p.append(tt)
                    cnt += 1
                else:
                    q.put(tt)
                    vis[eid] = True
        return p, cnt

    '''
        流量调配
    '''

    # 正常运转
    def run(self):
        while self.trf_pt < len(self.info.traffic):
            # 处理上一轮的流量
            for n1 in self.info.nodes:
                for n2 in self.info.nodes:
                    if n1 == n2:
                        continue
                    for flow in self.trf_mat[n1][n2]:
                        if flow.des == -1:  # 占空流
                            continue
                        p = self.sr[flow.src][flow.des][flow.rid].path
                        if flow.des != p[-1]:
                            flow.pt += 1
                            next_node = p[flow.pt]
                            # 放到链路上
                            self.trf_mat[n2][next_node].append(flow)
                        # 从上一段链路移除
                        self.trf_mat[n1][n2].remove(flow)
            # 读取新的流量需求并装载
            trf_cnt = 0
            while trf_cnt < self.trf_num:
                trf_cnt += 1
                trf = self.info.traffic[str(self.trf_pt)]
                src, des, trf_size = trf[0], trf[1], trf[2]
                self.trf_place(src, des, trf_size)
                self.trf_pt += 1
            # 判断故障并进行恢复
            if self.fe_pt < len(self.info.fevent) and \
                    self.info.fevent[str(self.fe_pt)]:
                # 启动计时，性能计数器
                start_time = time.perf_counter()
                flist = self.info.fevent[str(self.fe_pt)]  # 本次故障的链路
                self.trf_rr.append(0.0)
                # 更新联合故障概率模型
                if self.method == 'rfrr':
                    self.fmodel(flist)
                    start_time = time.perf_counter()
                if self.method == 'gs':
                    self.fmodel(flist)
                for flink in flist:
                    self.down_edges[flink] = True
                    if self.method == 'rfrr':
                        self.trf_rr[-1] += self.rfrr(flink)
                    elif self.method == 'pca2sr':
                        self.trf_rr[-1] += self.frr(flink)
                    elif self.method == 'gs':
                        self.trf_rr[-1] += self.gs(flink)
                    else:
                        raise ValueError("unknown method name!")
                # 停止计时
                end_time = time.perf_counter()
                self.time_consp.append((end_time - start_time) * 1000)
            self.fe_pt += 1
            # 记录本轮的网络利用率
            trf_utl = 0.0
            for n1 in self.info.nodes:
                for n2 in self.info.nodes:
                    if n1 == n2:
                        continue
                    for f in self.trf_mat[n1][n2]:
                        if f.des == -1:
                            continue
                        edge = (n1, n2)
                        if edge in self.info.edges and \
                                self.down_edges[self.info.edges.index(edge)]:
                            continue
                        trf_utl += f.trf
            avt_utl = trf_utl / sum([1 if not es else 0 for es in self.down_edges])
            self.trf_avgutl.append(avt_utl)
        # 累积，将+0的空流情况视为+1
        for rrid in range(len(self.trf_rr)):
            self.trf_rr[rrid] += 1.0
        for rrid in range(1, len(self.trf_rr)):
            self.trf_rr[rrid] += self.trf_rr[rrid - 1]

    # 放置新流量：src→des，大小为trf
    def trf_place(self, src, des, trf):
        for p in self.sr[src][des]:
            if p.src == -1:  # 占空路径
                continue
            pid = self.sr[src][des].index(p)
            trf_aloc = trf * p.ratio
            # ========暂时不进行带宽溢出判断========
            f = Flow(_src=src, _des=des, _rid=pid, _trf=trf_aloc)
            self.trf_mat[p.path[0]][p.path[1]].append(f)

    '''
        故障恢复选项，返回本次受调度的流量任务数量
    '''

    def frr(self, eid):
        e = self.info.edges[eid]
        src, des = e[0], e[1]
        trf_rr = 0.0
        # 将当前的流量路由到新路径上
        for flow in self.trf_mat[src][des]:
            trf_rr += flow.trf
            new_f = Flow(src, des, 0, flow.trf)
            self.trf_mat[src][des].append(new_f)
            self.trf_mat[src][des].remove(flow)
        # 找路
        paths, cnt = self.bfspath(src, des, n=1)
        if not paths:
            print("frr failed. no path available.")
            self.rr_failtimes += 1
            return trf_rr
        path = paths[0]
        # 更新 src->des 的路由表
        self.sr[src][des].clear()
        self.sr[src][des].append(Route(src, des, path, 1.0))
        # 更新途径 src->des 的路由表
        for n1 in self.info.nodes:
            for n2 in self.info.nodes:
                if n1 == n2:
                    continue
                for rot in self.sr[n1][n2]:
                    p = rot.path
                    for i in range(len(p) - 1):
                        # 途径，需要绕过该链路
                        # 只有一条路，所以直接在原路径上扩充即可
                        if p[i] == src and p[i + 1] == des:
                            ipos = i
                            for i in range(1, len(path) - 1):
                                p.insert(ipos + 1, path[i])
                                ipos += 1
        return trf_rr

    def rfrr(self, eid):
        e = self.info.edges[eid]
        src, des = e[0], e[1]
        trf_rr = 0.0  # 受重调度的流量规模（任务数量）
        # 搜集故障链路上的流量任务，每个demand就是一个flow
        demand = []
        for flow in self.trf_mat[src][des]:
            if flow.des == -1:
                continue
            demand.append(flow.trf)
        trf_rr += sum(demand)
        if len(demand) == 0:
            print("no traffic on failure link. link: " + str(e))
            self.notrf_times += 1
            return trf_rr
        # 找路
        paths, cnt = self.bfspath(src, des)  # paths 中是以节点表示的链路，每相邻两个节点组成一个链路
        reroute = []  # 路径，以链路list方式
        rfrate = []  # 路径的联合故障概率
        lfrate = {}  # 链路的联合故障概率
        for p in paths:
            if len(p) < 2:
                continue
            rr = []
            rfr = 1.0
            for i in range(1, len(p)):
                eid = self.info.edges.index((p[i - 1], p[i]))  # 节点对表示的链路的序号
                rr.append(eid)
                rfr *= 1 - self.frate[eid]
                lfrate[eid] = self.frate[eid]
            reroute.append(rr)
            rfrate.append(1 - rfr)
        return self.var_risk(paths, src, des, demand, reroute, rfrate, lfrate, trf_rr)

    # var 独立出来的部分，方便全局和局部调度使用
    def var_risk(self, paths, src, des, demand, reroute, rfrate, lfrate, trf_rr):
        # VaR 获取流量任务在paths上的分配比例
        var = VaR(_demand=demand, _route=reroute, _rfrate=rfrate, _lfrate=lfrate)
        x = var.lp()
        all_trf = sum(sum(x[i]) for i in range(len(demand))) if x else 0
        if all_trf == 0:
            print("rfrr failed, no suitable reroute.")
            self.rr_failtimes += 1
            return trf_rr
        # 把 flow 分配到新的路径上
        for i in range(len(demand)):
            flow = self.trf_mat[src][des][i]
            if flow.des == -1:
                continue
            for p in x[i]:
                pid = x[i].index(p)
                if p == 0.0:
                    continue
                new_flow = Flow(src, des, pid, p * flow.trf)
                self.trf_mat[paths[pid][0]][paths[pid][1]].append(new_flow)
        self.trf_mat[src][des].clear()
        # 更新路由表
        self.sr[src][des].clear()
        alloc = []
        # 分配比例
        for j in range(len(paths)):
            alloc.append(sum(x[i][j] for i in range(len(demand))) / all_trf)
        # 加入新路由
        for p in paths:
            pid = paths.index(p)
            self.sr[src][des].append(Route(src, des, p, alloc[pid]))
        # # 更新途径 src->des 的路由
        # for n1 in self.info.nodes:
        #     for n2 in self.info.nodes:
        #         if n1 == n2:
        #             continue
        #         # 搜索路径
        #         for rot in self.sr[n1][n2]:
        #             p = rot.path
        #             for i in range(len(p) - 1):
        #                 if p[i] == src and p[i + 1] == des:
        #                     for new_p in paths:
        #                         new_rot = deepcopy(rot)
        #                         new_rot.ratio *= alloc[paths.index(new_p)]
        #                         ipos = i
        #                         for j in range(1, len(new_p) - 1):
        #                             new_rot.path.insert(ipos + 1, new_p[j])
        #                             ipos += 1
        #                         self.sr[n1][n2].append(new_rot)
        #                     self.sr[n1][n2].remove(rot)
        #                     break
        # 途径 src->des 的流数据无需更改，因为：
        # 当pt指向src之前，则后续根据新路由绕过src->des
        # 当pt指向src之后，则已经经过了src->des，不需要再变更了
        return trf_rr

    # 全局调度算法
    def gs(self, eid):
        trf_rr = 0.0
        e = self.info.edges[eid]
        src, des = e[0], e[1]
        trf_rr = 0.0  # 受重调度的流量规模（任务数量）
        # 搜集故障链路上的流量任务，每个demand就是一个flow
        demand = []
        for flow in self.trf_mat[src][des]:
            if flow.des == -1:
                continue
            demand.append(flow.trf)
        trf_rr += sum(demand)
        if len(demand) == 0:
            print("no traffic on failure link. link: " + str(e))
            self.notrf_times += 1
            return trf_rr
        # 找路
        paths, cnt = self.bfspath(src, des, n=4)  # paths 中是以节点表示的链路，每相邻两个节点组成一个链路
        reroute = []  # 路径，以链路list方式
        rfrate = []  # 路径的联合故障概率
        lfrate = {}  # 链路的联合故障概率
        for p in paths:
            if len(p) < 2:
                continue
            rr = []
            rfr = 1.0
            for i in range(1, len(p)):
                eid = self.info.edges.index((p[i - 1], p[i]))  # 节点对表示的链路的序号
                rr.append(eid)
                rfr *= 1 - self.frate[eid]
                lfrate[eid] = self.frate[eid]
            reroute.append(rr)
            rfrate.append(1 - rfr)
        return self.var_risk(paths, src, des, demand, reroute, rfrate, lfrate, trf_rr)

    # 从 flog 生成联合故障概率
    def union_frate(self):
        # 计算 e1 的联合故障概率,O(|E|²)
        for e1 in self.info.edges:
            e1id = self.info.edges.index(e1)
            if self.down_edges[e1id]:
                continue
            plus = 0.0
            for e2 in self.info.edges:
                e2id = self.info.edges.index(e2)
                if self.down_edges[e2id] or e1id == e2id:
                    continue
                pvalue = ccy([self.flog[e1id], self.flog[e2id]])[1]
                if pvalue < 0.05:
                    continue
                plus *= pvalue * (1 - self.info.frate[str(e2id)])
            # 加到 e1 的故障概率上
            self.frate[e1id] = self.info.frate[str(e1id)] + plus
        # SRLG 联合概率
        for sg in self.info.srlg:
            plus = 1.0
            for e in sg:
                eid = self.info.edges.index(e)
                if self.down_edges[eid]:
                    break
                plus *= 1 - self.frate[eid]
            for e in sg:
                eid = self.info.edges.index(e)
                self.frate[eid] = 1 - plus

    # 更新联合故障概率模型
    def fmodel(self, felist: list):
        # self.frate = [self.info.frate[ek] for ek in self.info.frate]
        # return
        # 更新 flog
        for eidkey in self.flog:
            if eidkey in felist:
                self.flog[eidkey][0] += 1
            else:
                self.flog[eidkey][1] += 1
            # else:
            #     self.flog[eidkey].append(1e-5)
        # 更新故障概率模型
        self.union_frate()

    # 打印信息
    def write_info(self):
        print("=== traffic reroute size ===")
        print(self.trf_rr)
        print("=== average utilization ===")
        print(self.trf_avgutl)
        print("=== " + self.method + " reroute failed rate ===")
        print(self.rr_failtimes / len(self.info.fevent))
        print("=== " + self.method + " time consumption ===")
        print(self.time_consp)

        with open('../result/log/rrsize' + str(self.method) + '.json', 'w') as f:
            wt_rr = {self.method: self.trf_rr}
            json.dump(wt_rr, f, indent=4, ensure_ascii=False)
        with open('../result/log/avgutl' + str(self.method) + '.json', 'w') as f:
            wt_avgutl = {self.method: self.trf_avgutl}
            json.dump(wt_avgutl, f, indent=4, ensure_ascii=False)
        with open('../result/log/rrfailrate' + str(self.method) + '.json', 'w') as f:
            wt_rrfailrate = {self.method: self.rr_failtimes / len(self.info.fevent)}
            json.dump(wt_rrfailrate, f, indent=4, ensure_ascii=False)
        with open('../result/log/notrftimes' + str(self.method) + '.json', 'w') as f:
            wt_ntf = {self.method: self.notrf_times}
            json.dump(wt_ntf, f, indent=4, ensure_ascii=False)
        with open('../result/log/timeconsp' + str(self.method) + '.json', 'w') as f:
            wt_tc = {self.method: self.time_consp}
            json.dump(wt_tc, f, indent=4, ensure_ascii=False)

if __name__ == '__main__':
    c = TrafficCenter('rfrr')
