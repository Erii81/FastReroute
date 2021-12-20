"""
    生成、写入和读取：网络拓扑、srlg、链路故障概率、
"""

import json
from random import uniform, choice, choices, randint

topo = ['agis', 'att', 'globalcenter', 'ibm']
srlg_num = 10  # SRLG 组数


def duplicate_remove(l):
    return list(set(l))


class Information:
    def __init__(self):
        self.timelen = 50000  # 生成的traffic的数量
        self.interval = 50  # 每个时间片读取的traffic数量，该时间片内只产生一次故障
        self.frate_ub = 0.5  # 链路故障上限
        self.frate_lb = 0.05    # default 0.01
        self.srlg_ub = 4  # 每组 SRLG 的 link 数量上限
        self.srlg_lb = 2
        self.nodes = []
        self.edges = []
        self.srlg = []
        self.frate = {}  # 和 edges 序号对应
        self.fevent = {}
        self.traffic = {}
        self.flog = {}  # edges序号:[故障记录]
        self.feventcnt = 0
        self.ftimes = 0

    '''
        写入信息到 data/info
    '''

    def write_info(self):
        with open('../data/info/srlg.txt', 'w') as f:
            for s in self.srlg:
                f.writelines(str(s) + '\n')
        with open('../data/info/frate.json', 'w') as f:
            json.dump(self.frate, f)
        with open('../data/info/fevent.json', 'w') as f:
            json.dump(self.fevent, f, indent=4, ensure_ascii=False)
        with open('../data/info/traffic.json', 'w') as f:
            json.dump(self.traffic, f, indent=4, ensure_ascii=False)

    '''
        读取信息
    '''

    # 读取节点和边
    def load_topos(self):
        topo_name = topo[2]
        with open('../data/topology/' + topo_name + '/edges.txt', 'r') as f:
            for line in f:
                items = line.strip().split(',')
                node1, node2 = int(items[1]), int(items[2])
                self.nodes.append(node1)
                self.nodes.append(node2)
                self.edges.append((node1, node2))
                self.edges.append((node2, node1))
        self.nodes = list(set(self.nodes))
        for eid in range(len(self.edges)):
            self.flog[eid] = [1e-5, 1e-5]  # [fail times, aval times]

    # 读取 SRLG list
    def load_srlg(self):
        with open('../data/info/srlg.txt', 'r') as f:
            for line in f:
                items = [int(i) for i in line.strip().strip('[]').replace('(', '').replace(')', '').split(',')]
                sg = []
                i = 0
                while i < len(items):
                    sg.append((items[i], items[i + 1]))
                    i += 2
                self.srlg.append(sg)

    # 读取 failure rate
    def load_frate(self):
        with open('../data/info/frate.json', 'r') as f:
            self.frate = json.load(f)

    # 读取 failure event,同时生成 flog
    def load_fevent(self):
        with open('../data/info/fevent.json', 'r') as f:
            self.fevent = json.load(f)
        for fk in self.fevent:
            fe = self.fevent[fk]
            for eid in self.flog:
                if eid in fe:
                    self.flog[eid][0] += 1
                # else:
                #     self.flog[eid].append(1e-5)
                else:
                    self.flog[eid][1] += 1

    # 读取 traffic
    def load_traffic(self):
        with open('../data/info/traffic.json', 'r') as f:
            self.traffic = json.load(f)

    '''
        生成相关信息
    '''

    # 生成流量任务，点到点，一共 timelen 条
    def gen_traffic(self, lower_bound=0.01, upper_bound=0.99):
        cnt = 0
        while cnt < self.timelen:
            from_node = choice(self.nodes)
            if from_node == len(self.nodes) - 1:
                continue
            to_node = choice(self.nodes)
            while to_node == from_node:
                to_node = choice(self.nodes)
            tr = uniform(lower_bound, upper_bound)
            cnt += 1
            self.traffic[cnt] = [from_node, to_node, tr]

    # 指定 SRLGs，获取 k 组
    def gen_srlg(self, k):
        # 分段，避免随机选取重复
        elen = len(self.edges)
        elen_avg = elen // k
        begin = 0
        while begin < elen - elen_avg:
            ls = []
            for i in range(begin, begin + elen_avg):
                ls.append(self.edges[i])
            sg = duplicate_remove(choices(ls, k=randint(self.srlg_lb, self.srlg_ub)))
            if len(sg) < self.srlg_lb:
                continue
            # 是否和现有 SRLG 重合
            flag = False
            for s in sg:
                for sr in self.srlg:
                    if s in sr:
                        flag = True
                        break
                if flag:
                    break
            if flag:
                continue
            # 没有重合，添加到 srlg
            self.srlg.append(sg)
            begin += elen_avg

    # 生成故障概率
    def gen_failrate(self):
        for e_i in range(len(self.edges)):
            t = uniform(self.frate_lb, self.frate_ub)
            self.frate[e_i] = t

    # 生成故障事件
    def gen_fevent(self):
        leng = self.timelen // self.interval  # 总共的故障数目
        vis = [False for e in self.edges]  # 是否已经故障了某条链路
        cnt = 0
        while cnt < leng:
            cnt += 1
            down = []
            fail_level = uniform(0, 10.0)
            for fr_i in range(len(self.edges)):
                if self.frate[fr_i] > fail_level and not vis[fr_i]:
                    vis[fr_i] = True
                    down.append(fr_i)
                    self.feventcnt += 1
                    self.ftimes += 1
                    # SRLG
                    for sr in self.srlg:
                        if self.edges[fr_i] in sr:
                            for s in sr:
                                e_index = self.edges.index(s)
                                if not vis[e_index]:
                                    vis[e_index] = True
                                    down.append(e_index)
                                    self.feventcnt += 1
                    break
            self.fevent[cnt] = down
        print("generate failure event: " + str(self.feventcnt))
        print("generate failure time: " + str(self.ftimes))


def gen(info: Information):
    info.load_topos()
    info.gen_srlg(srlg_num)
    info.gen_failrate()
    info.gen_fevent()
    info.gen_traffic()
    info.write_info()


def load(info: Information):
    info.load_topos()
    info.load_srlg()
    info.load_frate()
    info.load_fevent()
    info.load_traffic()


if __name__ == '__main__':
    i = Information()
    gen(i)
    # load(i)
    # t = [i for i in range(10)]  # end of test
