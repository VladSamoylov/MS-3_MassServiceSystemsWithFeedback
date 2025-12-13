import simpy
import numpy as np
from collections import defaultdict

COLOR_ANSI_RED = '\033[31m'
COLOR_ANSI_GREEN = '\033[32m'
COLOR_ANSI_BLUE = '\033[34m'
COLOR_ANSI_YELLOW = '\033[33m'
COLOR_ANSI_FIOL = '\033[35m'
COLOR_ANSI_RESET = '\033[0m'

SIMTIME = 450

CategoryParams = {
    1: {'ARRIVEINTERVAL': 2, 'SERVICETIME': 2},
    2: {'ARRIVEINTERVAL': 5, 'SERVICETIME': 7},
}

class TwoStationSystem:
    def __init__(self, env):
        self.env = env
        self.stationFirst = simpy.PriorityResource(env, capacity = 1)
        self.stationSecond = simpy.Resource(env, capacity = 1)
        self.stationSecondWorking = False
        self.stationSecondBusy = env.event()
        self.queueFirstLen = []
        self.queueSecondLen = []
        self.firstProcessed = 0
        self.secondProcessed = 0
        self.currentFirstProcess = None
        self.waitTimes = defaultdict(list)
        
    def SecondProcess(self, reqId, category):
        with self.stationSecond.request() as req:
            queueStart = self.env.now
            yield req
            waitTime = self.env.now - queueStart
            print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
                  f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_YELLOW}почала{COLOR_ANSI_RESET} обслуговування " 
                  f"(очікувала {COLOR_ANSI_RED}{waitTime}{COLOR_ANSI_RESET} сек)")
            self.stationSecondWorking = True
            self.stationSecondBusy.succeed()
            self.stationSecondBusy = self.env.event()
            yield self.env.timeout(CategoryParams[category]['SERVICETIME'])
            print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
                  f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_GREEN}закінчила{COLOR_ANSI_RESET} обслуговування")
            self.stationSecondWorking = False
            if self.currentFirstProcess is not None:
                self.currentFirstProcess.interrupt()
            self.secondProcessed += 1

        self.waitTimes[category].append(waitTime)
        
    def FirstProcess(self, reqId, category):
        arriveTime = self.env.now
        remainingWork = CategoryParams[category]['SERVICETIME']
        interrupt = False
        startWork = None
        priority = 1
        waitTimesInterrupt = 0

        while remainingWork > 0:
            with self.stationFirst.request(priority = priority) as req:
                queueStart = self.env.now
                if not self.stationSecondWorking:
                    print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
                        f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_FIOL}чекає{COLOR_ANSI_RESET} поки станція 2 почне роботу")
                    yield self.stationSecondBusy
                try:
                    yield req
                    if not self.stationSecondWorking: 
                        req.resource.release(req)
                        continue
                    self.currentFirstProcess = self.env.active_process
                    waitTime = self.env.now - queueStart
                    if not interrupt:
                        print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
                            f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_YELLOW}почала{COLOR_ANSI_RESET} обслуговування " 
                            f"(очікувала {COLOR_ANSI_RED}{waitTime}{COLOR_ANSI_RESET} сек)")
                    else:
                        print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
                            f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_FIOL}відновила обслуговування після перериваня{COLOR_ANSI_RESET} " 
                            f"(очікувала {COLOR_ANSI_RED}{waitTime}{COLOR_ANSI_RESET} сек) / залишок роботи - {COLOR_ANSI_YELLOW}{remainingWork}{COLOR_ANSI_RESET}")
                    startWork = self.env.now
                    yield self.env.timeout(remainingWork)
                    print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
                        f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_GREEN}закінчила{COLOR_ANSI_RESET} обслуговування")
                    self.firstProcessed += 1
                    remainingWork = 0
                    self.currentFirstProcess = None
                except simpy.Interrupt:
                    interrupt = True
                    priority = 0
                    if startWork is None:
                        print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
                        f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_RED}прервана, бо станція 2 вільна{COLOR_ANSI_RESET} ")
                        continue
                    worked = self.env.now - startWork
                    remainingWork -= worked
                    if remainingWork == 0:
                        print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
                        f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_GREEN}закінчила{COLOR_ANSI_RESET} обслуговування")
                        self.firstProcessed += 1
                    else:
                        print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
                            f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_RED}прервана, бо станція 2 вільна{COLOR_ANSI_RESET} "
                            f"залишилось виконати - {COLOR_ANSI_YELLOW}{remainingWork}{COLOR_ANSI_RESET} сек")
                        waitTimesInterrupt += waitTime
                    startWork = None
                    self.currentFirstProcess = None
        
        self.waitTimes[category].append(waitTime + waitTimesInterrupt)
        # if(reqId == 66):
        #     print(f"66 (1) queue wait + interrupt - {waitTimesInterrupt + waitTime}")
        #     print(f"66 (1) Total wait - {self.env.now - (arriveTime + CategoryParams[category]['SERVICETIME']) }")


def RequirementGenerator(env, system, category):
    reqId = 1
    while True:
        yield env.timeout(CategoryParams[category]["ARRIVEINTERVAL"])
        if category == 1: env.process(system.FirstProcess(reqId, category))
        else: env.process(system.SecondProcess(reqId, category))
        reqId += 1

def MonitorQueues(env, system):
    while True:
        system.queueFirstLen.append(len(system.stationFirst.queue))
        system.queueSecondLen.append(len(system.stationSecond.queue))

        if env.now % 25 == 0:
            print(f"{COLOR_ANSI_YELLOW}{env.now:>8.2f}{COLOR_ANSI_RESET}: {COLOR_ANSI_YELLOW}Черга на 2 прилад{COLOR_ANSI_RESET} ({COLOR_ANSI_RED}{len(system.stationSecond.queue)}{COLOR_ANSI_RESET}) "
                  f"/ {COLOR_ANSI_YELLOW}Очікують 2 прилад{COLOR_ANSI_RESET}: {COLOR_ANSI_RED}{len(system.stationFirst.queue)}{COLOR_ANSI_RESET} (заявки 1 типу)")
        
        yield env.timeout(1)

def RunSim():
    env = simpy.Environment()
    system = TwoStationSystem(env)
    env.process(RequirementGenerator(env, system, 2))
    env.process(RequirementGenerator(env, system, 1))
    env.process(MonitorQueues(env, system))

    print(f"{COLOR_ANSI_FIOL}Початок моделювання...{COLOR_ANSI_RESET}")
    env.run(until = SIMTIME)

    print(f"{COLOR_ANSI_FIOL}\n" + "="*50)
    print(f"РЕЗУЛЬТАТИ МОДЕЛЮВАННЯ / час моделювання - {SIMTIME} сек")
    print(f"="*50 + f"{COLOR_ANSI_RESET}")

    avgQueueFirstLen = np.mean(system.queueFirstLen) if system.queueFirstLen else 0
    avgQueueSecondLen = np.mean(system.queueSecondLen) if system.queueSecondLen else 0

    print(f"Загальна кількість обслужених заявок : {COLOR_ANSI_GREEN}{system.firstProcessed + system.secondProcessed}{COLOR_ANSI_RESET}")
    print(f"З них 1 типу : {COLOR_ANSI_YELLOW}{system.firstProcessed}{COLOR_ANSI_RESET}")
    print(f"З них 2 типу : {COLOR_ANSI_YELLOW}{system.secondProcessed}{COLOR_ANSI_RESET}")
    print(f"Середня довжина черги 2 приладу : {COLOR_ANSI_RED}{avgQueueSecondLen:.2f}{COLOR_ANSI_RESET}")
    print(f"Середня довжина черги 1 приладу : {COLOR_ANSI_RED}{avgQueueFirstLen:.2f}{COLOR_ANSI_RESET}")
    print(f"Середній час очікування заявки типу 2 : {COLOR_ANSI_YELLOW}{np.mean(system.waitTimes[2]):.1f}{COLOR_ANSI_RESET} сек")
    print(f"Середній час очікування заявки типу 1 : {COLOR_ANSI_YELLOW}{np.mean(system.waitTimes[1]):.1f}{COLOR_ANSI_RESET} сек")

if __name__ == '__main__':
    RunSim()
