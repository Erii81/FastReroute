"""
    画实验图
"""

import json
import numpy as np
from generate import Information, load as gload
from matplotlib import pyplot as plt

legend_size = 18
xylabel_size = 15
xyticks_size = 13
title_size = 20
colors = ['k', 'b', 'orange']
markers = ['*', '3', '8', '^']
lstyles = ['-', '--', '-.', ':']
hatches = ['', '\\', '/']


class Draw:
    def __init__(self, _methods: list = ['UFRA', 'PCA2SR', 'GS'], _mask: list = ['rfrr', 'pca2sr', 'gs']):
        self.methods = _methods
        self.mask = _mask
        self.metric = ['rrsize', 'avgutl']
        self.rr_size = {}
        self.avgutil = {}
        self.rrfailrate = {}
        self.notrftimes = {}
        self.tconsp = {}

        for met in _methods:
            msk = self.mask[_methods.index(met)]
            with open('../result/log/rrsize' + str(msk) + '.json', 'r') as f:
                self.rr_size[met] = json.load(f)[msk]
            with open('../result/log/avgutl' + str(msk) + '.json', 'r') as f:
                self.avgutil[met] = json.load(f)[msk]
            with open('../result/log/rrfailrate' + str(msk) + '.json', 'r') as f:
                self.rrfailrate[met] = json.load(f)[msk]
            with open('../result/log/notrftimes' + str(msk) + '.json', 'r') as f:
                self.notrftimes[met] = json.load(f)[msk]
            with open('../result/log/timeconsp' + str(msk) + '.json', 'r') as f:
                self.tconsp[met] = json.load(f)[msk]

    # 平均链路利用率
    def draw_avgutl(self):
        fqdb = 500
        ttimes = [i for i in range(1, 1 + len(self.avgutil[self.methods[0]]))]
        for met in self.methods:
            idx = self.methods.index(met)
            x = [i * fqdb for i in ttimes]
            y = self.avgutil[met]
            plt.plot(x, y, label=met, linestyle=lstyles[idx], color=colors[idx])
        # 作一条利用率为1的标记线
        xx = [i * fqdb for i in ttimes]
        yy = [1 for i in ttimes]
        plt.plot(xx, yy, color='y', linestyle='-', linewidth=3)
        # 标题等
        plt.xticks(fontsize=xyticks_size)
        plt.yticks(fontsize=xyticks_size)
        plt.xlabel('Traffic Request', fontsize=xylabel_size)
        plt.ylabel('MLU', fontsize=xylabel_size)
        # plt.title('Network Utilization', fontsize=title_size)
        plt.legend(fontsize=legend_size)
        plt.savefig('../result/photo/avgutl.png')
        plt.show()

    # 重路由流量规模
    def draw_rrsize(self):
        ftimes = [i for i in range(1, 1 + len(self.rr_size[self.methods[0]]))]
        for met in self.methods:
            idx = self.methods.index(met)
            x = ftimes
            y = self.rr_size[met]
            plt.plot(x, y, label=met, linestyle=lstyles[idx], color=colors[idx])
        # 刻度线
        for yl in [20, 40, 60, 80, 100]:
            xx = ftimes
            yy = [yl for i in xx]
            plt.plot(xx, yy, color='y', linestyle=':', linewidth=2)
        # 标题等
        plt.xticks(fontsize=xyticks_size)
        plt.yticks(fontsize=xyticks_size)
        plt.xlabel('Failure', fontsize=xylabel_size)
        plt.ylabel('Accumulated Size(10GB)', fontsize=xylabel_size)
        # plt.title('Reroute Traffic Size', fontsize=title_size)
        plt.legend(fontsize=legend_size)
        plt.savefig('../result/photo/rrsize.png')
        plt.show()

    # 重路由耗时
    def draw_timeconsp(self):
        # 包含 GS
        ftimes = [i for i in range(1, 1 + len(self.tconsp[self.methods[0]]))]
        for met in self.methods:
            idx = self.methods.index(met)
            x = ftimes
            y = [yy / 1000 for yy in self.tconsp[met]]
            # y = self.tconsp[met]
            plt.plot(x, y, label=met, linestyle=lstyles[idx], color=colors[idx])
        # 标题等
        plt.xticks(fontsize=xyticks_size)
        plt.yticks(fontsize=xyticks_size)
        plt.xlabel('Failure', fontsize=xylabel_size)
        plt.ylabel('Time Consumption(s)', fontsize=xylabel_size)
        # plt.title('Reroute Traffic Size', fontsize=title_size)
        plt.legend(fontsize=legend_size)
        plt.savefig('../result/photo/tconsp1.png')
        plt.show()
        # 不包含 GS
        ftimes = [i for i in range(1, 1 + len(self.tconsp[self.methods[0]]))]
        for met in self.methods:
            idx = self.methods.index(met)
            if met == 'GS':  # GS 耗时太高，作两幅图，一副不包含 GS
                continue
            x = ftimes
            y = self.tconsp[met]
            plt.plot(x, y, label=met, linestyle=lstyles[idx], color=colors[idx])
        # 标题等
        plt.xticks(fontsize=xyticks_size)
        plt.yticks(fontsize=xyticks_size)
        plt.xlabel('Failure', fontsize=xylabel_size)
        plt.ylabel('Time Consumption(ms)', fontsize=xylabel_size)
        # plt.title('Reroute Traffic Size', fontsize=title_size)
        plt.legend(fontsize=legend_size)
        plt.savefig('../result/photo/tconsp2.png')
        plt.show()

    # 重路由时没有流量跑在该链路上
    def draw_notrf(self):
        y = []
        width = 0.25
        for met in self.methods:
            y.append(self.notrftimes[met])
        x = range(len(self.methods))
        plt.figure(figsize=(4, 5))
        for i in range(len(x)):
            plt.bar(x[i], y[i], hatch=hatches[i], color='0.5')
        plt.xticks(x, self.methods, fontsize=xyticks_size)
        plt.yticks(fontsize=xyticks_size)
        plt.ylabel('Number of Links', fontsize=xylabel_size)
        plt.title('Failing Links with Few Traffic(< 1GB)', fontsize=14, x=0.4)
        # plt.legend(self.methods)
        plt.show()

    # 重路由规模，以 GS 为度量
    def draw_rrsize_gsmark(self):
        ftimes = [i for i in range(1, 1 + len(self.rr_size[self.methods[0]]))]
        for met in ['UFRA', 'PCA2SR']:
            idx = self.methods.index(met)
            x = ftimes
            y = []
            for i in range(0, len(self.rr_size['GS'])):
                y.append(self.rr_size[met][i] - self.rr_size['GS'][i])
            plt.plot(x, y, label=met, linestyle=lstyles[idx], color=colors[idx])
        # # 刻度线
        # for yl in [20, 40, 60, 80, 100]:
        #     xx = ftimes
        #     yy = [yl for i in xx]
        #     plt.plot(xx, yy, color='y', linestyle=':', linewidth=2)
        # 标题等
        plt.xticks(fontsize=xyticks_size)
        plt.yticks(fontsize=xyticks_size)
        plt.xlabel('Failure', fontsize=xylabel_size)
        plt.ylabel('Relative Size(10GB)', fontsize=xylabel_size)
        # plt.title('Reroute Traffic Size', fontsize=title_size)
        plt.legend(fontsize=legend_size)
        plt.savefig('../result/photo/rrsize_gsmark.png')
        plt.show()


# 故障和链路的变化关系
def draw_flink():
    info = Information()
    gload(info)
    lnumber = len(info.edges)
    fnumber = 0
    llog, flog = [lnumber], [fnumber]
    for fpt in info.fevent:
        if not info.fevent[fpt]:
            continue
        fnumber += 1
        lnumber -= len(info.fevent[fpt])
        llog.append(lnumber)
        flog.append(fnumber)
    plt.plot(flog, llog)
    plt.xticks(fontsize=xyticks_size)
    plt.yticks(fontsize=xyticks_size)
    plt.xlabel('Failure', fontsize=xylabel_size)
    plt.ylabel('Available Link Number', fontsize=xylabel_size)
    # plt.title('Network Utilization', fontsize=title_size)
    plt.savefig('../result/photo/flink.png')
    plt.show()


def draw(d: Draw):
    d.draw_avgutl()
    d.draw_rrsize()
    d.draw_rrsize_gsmark()
    d.draw_timeconsp()
    # draw_flink()


if __name__ == '__main__':
    # draw_flink()
    d = Draw()
    draw(d)
