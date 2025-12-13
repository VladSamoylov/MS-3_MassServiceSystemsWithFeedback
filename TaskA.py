import simpy
import numpy as np

COLOR_ANSI_RED = '\033[31m'
COLOR_ANSI_GREEN = '\033[32m'
COLOR_ANSI_BLUE = '\033[34m'
COLOR_ANSI_YELLOW = '\033[33m'
COLOR_ANSI_FIOL = '\033[35m'
COLOR_ANSI_RESET = '\033[0m'

ARRIVEINTERVAL = 115
FIRSTSERVICETIME = 335
SECONDSERVICETIME = 110
FIRSTCAPACITY = 3
SECODCAPACITY = 1
SECONDQUEUELIMIT = 1
SIMTIME = 8 * 3600

class TwoStationSystem:
    def __init__(self, env):
        self.env = env
        self.stationFirst = simpy.Resource(env, capacity = FIRSTCAPACITY)
        self.stationSecond = simpy.Resource(env, capacity = SECODCAPACITY)
        self.queueSecond = simpy.Resource(env, capacity = SECONDQUEUELIMIT)
        self.queueFirstLen = []
        self.queueSecondCount = 0
        self.totalProcessed = 0

    def RequirementProcess(self, reqId):
        with self.stationFirst.request() as req:
            yield req
            self.queueFirstLen.append(len(self.stationFirst.queue))
            yield self.env.timeout(FIRSTSERVICETIME)

        with self.queueSecond.request() as slotReq:
            yield slotReq
            self.queueSecondCount += 1

            with self.stationSecond.request() as req:
                yield req
                yield self.env.timeout(SECONDSERVICETIME)
                self.queueSecondCount -= 1

        self.totalProcessed += 1

def RequirementGenerator(env, system):
    reqId = 1
    while True:
        yield env.timeout(ARRIVEINTERVAL)
        env.process(system.RequirementProcess(reqId))
        reqId += 1

def MonitorQueues(env, system):
    while True:
        currentQueueLen = len(system.stationFirst.queue)
        system.queueFirstLen.append(currentQueueLen)
        system.queueSecondCount = len(system.queueSecond.queue)

        if env.now % 300 == 0:
            print(f"{COLOR_ANSI_YELLOW}{env.now:>8.2f}{COLOR_ANSI_RESET}: Черга 1 ({COLOR_ANSI_RED}{currentQueueLen}{COLOR_ANSI_RESET}) "
                  f"Очікують станцію 2: {COLOR_ANSI_RED}{system.queueSecondCount}{COLOR_ANSI_RESET}")
        
        yield env.timeout(1)

def RunSim():
    env = simpy.Environment()
    system = TwoStationSystem(env)
    env.process(RequirementGenerator(env, system))
    env.process(MonitorQueues(env, system))

    print(f"{COLOR_ANSI_YELLOW}Початок моделювання...{COLOR_ANSI_RESET}")
    env.run(until = SIMTIME)

    print(f"{COLOR_ANSI_FIOL}\n" + "="*50)
    print("РЕЗУЛЬТАТИ МОДЕЛЮВАННЯ")
    print(f"="*50 + f"{COLOR_ANSI_RESET}")

    if system.queueFirstLen:
        avgQueueFirst = np.mean(system.queueFirstLen)
        maxQueueFirst = np.max(system.queueFirstLen)

        print(f"Середня довжина черги станції 1: {COLOR_ANSI_YELLOW}{avgQueueFirst:.2f}{COLOR_ANSI_RESET}")
        print(f"Максимальна довжина черги станції 1: {COLOR_ANSI_RED}{maxQueueFirst}{COLOR_ANSI_RESET}")
        print(f"Оброблено заявок: {COLOR_ANSI_GREEN}{system.totalProcessed}{COLOR_ANSI_RESET}")
    
    return avgQueueFirst, maxQueueFirst

if __name__ == '__main__':
    avgQFirst, maxQFirst = RunSim()
