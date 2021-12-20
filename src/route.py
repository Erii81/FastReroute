class Route:
    def __init__(self, _src, _des, _path: list, _ratio):
        self.src = _src
        self.des = _des
        self.path = _path       # 经过哪些链路
        self.ratio = _ratio     # 分配的带宽占任务的带宽需求的比例，不是占链路带宽的比例
