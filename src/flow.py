"""
    流的数据结构
"""


class Flow:
    def __init__(self, _src, _des, _rid, _trf):
        self.src = _src
        self.des = _des
        self.rid = _rid     # 指向路由表的哪条路径
        self.pt = 0         # 走到路径的哪个位置
        self.trf = _trf     # 数据的实际大小

    def fprint(self):
        print("reached: " + str(self.pt))
        print(self.path)
        print("size: " + self.trf)
