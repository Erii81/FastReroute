# real-time fast rerouting framework against SRLG

from center import TrafficCenter


def basic(tc: TrafficCenter):
    tc.run()
    tc.write_info()


if __name__ == '__main__':
    # rfrr, pca2sr, gs
    for met in ['rfrr', 'pca2sr', 'gs']:
        tc = TrafficCenter(_method=met)
        basic(tc)
