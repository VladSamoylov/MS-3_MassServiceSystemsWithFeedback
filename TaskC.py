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
        self.stationSecondBusy = env.event()
        self.queueFirstLen = []
        self.queueSecondLen = []
        self.firstProcessed = 0
        self.secondProcessed = 0
        self.currentFirstProcess = None
        self.waitTimes = defaultdict(list)
        self.type2First = []
        self.type2Second = []
        self.waitingSecond = 0
        self.statisticsErrors = 0
        
    def SecondProcess(self, reqId, category):
        queueStart = self.env.now
        priority = self.env.now
        if self.stationFirst.count == 0:
            req = self.stationFirst.request(priority = priority)
            station = 1
            # print(f"choose  first")
            self.type2First.append(req)
        elif len(self.type2Second) <= len(self.type2First):
            req = self.stationSecond.request()
            station = 2
            # print(f"choose  second")
            self.type2Second.append(req)
        else:
            req = self.stationFirst.request(priority = priority)
            station = 1
            # print(f"choose  first")
            self.type2First.append(req)
        yield req
        waitTime = self.env.now - queueStart
        print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
            f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_YELLOW}почала{COLOR_ANSI_RESET} обслуговування на приладі ({COLOR_ANSI_GREEN}{station}{COLOR_ANSI_RESET}) " 
            f"(очікувала {COLOR_ANSI_RED}{waitTime}{COLOR_ANSI_RESET} сек)")
        if station == 2:
            self.stationSecondBusy.succeed()
            self.stationSecondBusy = self.env.event()
        yield self.env.timeout(CategoryParams[category]['SERVICETIME'])
        print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
            f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_GREEN}закінчила{COLOR_ANSI_RESET} обслуговування на приладі ({COLOR_ANSI_GREEN}{station}{COLOR_ANSI_RESET})")
        if station == 2:
            if self.currentFirstProcess is not None:
                self.currentFirstProcess.interrupt()
        self.secondProcessed += 1

        if station == 1:
            self.stationFirst.release(req)
            self.type2First.remove(req)
        else:
            self.stationSecond.release(req)
            self.type2Second.remove(req)

        self.waitTimes[category].append(waitTime)
        
    def FirstProcess(self, reqId, category):
        arriveTime = self.env.now
        remainingWork = CategoryParams[category]['SERVICETIME']
        interrupt = False
        startWork = None
        priority = arriveTime

        totalWait = 0
        totalStationWaits = 0

        while remainingWork > 0:
            if self.stationSecond.count > 0 and any(req in self.type2Second for req in self.stationSecond.users):
                with self.stationFirst.request(priority = priority) as req:
                    try:
                        queueStart = self.env.now
                        yield req
                        queueWait = self.env.now - queueStart
                        totalWait += queueWait + totalStationWaits
                        totalStationWaits = 0
                        if self.stationSecond.count > 0 and any(req in self.type2Second for req in self.stationSecond.users): 
                            self.currentFirstProcess = self.env.active_process
                            if not interrupt:
                                print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
                                    f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_YELLOW}почала{COLOR_ANSI_RESET} обслуговування " 
                                    f"(очікувала {COLOR_ANSI_RED}{totalWait}{COLOR_ANSI_RESET} сек)")
                            else:
                                print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
                                    f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_FIOL}відновила обслуговування після перериваня{COLOR_ANSI_RESET} " 
                                    f"(очікувала {COLOR_ANSI_RED}{totalWait}{COLOR_ANSI_RESET} сек) / залишок роботи - {COLOR_ANSI_YELLOW}{remainingWork}{COLOR_ANSI_RESET}")
                            startWork = self.env.now
                            yield self.env.timeout(remainingWork)
                            print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
                                f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_GREEN}закінчила{COLOR_ANSI_RESET} обслуговування")
                            self.firstProcessed += 1
                            remainingWork = 0
                            self.currentFirstProcess = None
                        else:
                            continue
                    except simpy.Interrupt:
                        interrupt = True
                        priority = 0
                        if startWork is None:
                            print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
                            f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_RED}прервана, бо станція 2 вільна{COLOR_ANSI_RESET} ")
                            self.currentFirstProcess = None
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
                        startWork = None
                        self.currentFirstProcess = None
            else: 
                print(f"{COLOR_ANSI_YELLOW}{self.env.now:>8.2f}{COLOR_ANSI_RESET}: Заявка {COLOR_ANSI_BLUE}{reqId:<4}{COLOR_ANSI_RESET} "
                    f"({COLOR_ANSI_GREEN}{category}{COLOR_ANSI_RESET} типу) {COLOR_ANSI_FIOL}чекає{COLOR_ANSI_RESET} поки станція 2 почне роботу")
                stationStart = self.env.now
                self.waitingSecond += 1
                yield self.stationSecondBusy
                self.waitingSecond -= 1
                totalStationWaits += self.env.now - stationStart
                continue
        
        if (self.env.now - (arriveTime + CategoryParams[category]['SERVICETIME'])) == (totalWait):
            self.waitTimes[category].append(totalWait)
        else: 
            self.statisticsErrors += 1
            print(f"{COLOR_ANSI_RED}ERROR IN STATISTICS!{COLOR_ANSI_RESET}")
            print(f"{reqId} (1) wait station + queue wait - {totalWait}")
            print(f"{reqId} (1) Total wait - {self.env.now - (arriveTime + CategoryParams[category]['SERVICETIME']) }")

def RequirementGenerator(env, system, category):
    reqId = 1
    while True:
        yield env.timeout(CategoryParams[category]["ARRIVEINTERVAL"])
        if category == 1: env.process(system.FirstProcess(reqId, category))
        else: env.process(system.SecondProcess(reqId, category))
        reqId += 1

def MonitorQueues(env, system):
    while True:
        currentFirstLen = len(system.stationFirst.queue) + system.waitingSecond
        system.queueFirstLen.append(currentFirstLen)
        currentSecondLen = len(system.stationSecond.queue)
        system.queueSecondLen.append(currentSecondLen)

        if env.now % 25 == 0:
            print(f"{COLOR_ANSI_YELLOW}{env.now:>8.2f}{COLOR_ANSI_RESET}: {COLOR_ANSI_YELLOW}Черга на 2 прилад{COLOR_ANSI_RESET} ({COLOR_ANSI_RED}{currentSecondLen}{COLOR_ANSI_RESET}) "
                  f"/ {COLOR_ANSI_YELLOW}Черга на 1 прилад{COLOR_ANSI_RESET}: {COLOR_ANSI_RED}{currentFirstLen}{COLOR_ANSI_RESET}")
        
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
    if system.statisticsErrors == 0:
        print(f"Середній час очікування заявки типу 2 : {COLOR_ANSI_YELLOW}{np.mean(system.waitTimes[2]):.1f}{COLOR_ANSI_RESET} сек") if system.waitTimes[2] else print(f"Середній час очікування заявки типу 2 : {COLOR_ANSI_RED}Не обслуговано жодну заявку{COLOR_ANSI_RESET}")
        print(f"Середній час очікування заявки типу 1 : {COLOR_ANSI_YELLOW}{np.mean(system.waitTimes[1]):.1f}{COLOR_ANSI_RESET} сек") if system.waitTimes[1] else print(f"Середній час очікування заявки типу 1 : {COLOR_ANSI_RED}Не обслуговано жодну заявку{COLOR_ANSI_RESET}")
    else: print(f"{COLOR_ANSI_RED}ERROR IN STATISTICS!{COLOR_ANSI_RESET}")

if __name__ == '__main__':
    RunSim()
