"""
    统计各项数据
"""

import json


class Statistic:
    def __init__(self):
        self.folder = ['single', 'light01', 'severe02']
        self.method = ['rfrr', 'gs', 'pca2sr']
        self.metric = ['avgutl', 'rrsize', 'timeconsp']
        self.log = {}
        self.summa = {}

        for fd in self.folder:
            if fd not in self.log:
                self.log[fd] = {}
            for mc in self.metric:
                if mc not in self.log[fd]:
                    self.log[fd][mc] = {}
                for met in self.method:
                    if met not in self.summa:
                        self.summa[met] = {}
                    if mc not in self.summa[met]:
                        self.summa[met][mc] = 0.0
                    with open('./' + fd + '/log/' + mc + met + '.json') as f:
                        self.log[fd][mc][met] = sum(json.load(f)[met])
                        self.summa[met][mc] += self.log[fd][mc][met]

    def print_res(self):
        for fd in self.folder:
            print("\n In " + fd + " \n")
            print("==== avgutl ====")
            au = self.log[fd]['avgutl']
            print("to gs: " + str((au['gs'] - au['rfrr']) / au['gs']))
            print("to pca2sr: " + str((au['pca2sr'] - au['rfrr']) / au['pca2sr']))
            print("==== rrsize ====")
            rrs = self.log[fd]['rrsize']
            print("to gs: " + str((rrs['gs'] - rrs['rfrr']) / rrs['gs']))
            print("to pca2sr: " + str((rrs['pca2sr'] - rrs['rfrr']) / rrs['pca2sr']))
            print("==== timeconsp ====")
            tcs = self.log[fd]['timeconsp']
            print("to gs: " + str((tcs['gs'] - tcs['rfrr']) / tcs['gs']))
        print("\n====== overall ======\n")
        print("==== avgutl ====")
        print("to gs: " + str((self.summa['gs']['avgutl'] - self.summa['rfrr']['avgutl']) / self.summa['gs']['avgutl']))
        print("to pca2sr: " + str((self.summa['pca2sr']['avgutl'] - self.summa['rfrr']['avgutl']) / self.summa['pca2sr']['avgutl']))
        print("==== rrsize ====")
        print("to gs: " + str((self.summa['gs']['rrsize'] - self.summa['rfrr']['rrsize']) / self.summa['gs']['rrsize']))
        print("to pca2sr: " + str((self.summa['pca2sr']['rrsize'] - self.summa['rfrr']['rrsize']) / self.summa['pca2sr']['rrsize']))
        print("==== timeconsp ====")
        print("to gs: " + str((self.summa['gs']['timeconsp'] - self.summa['rfrr']['timeconsp']) / self.summa['gs']['timeconsp']))


if __name__ == '__main__':
    Statistic().print_res()
