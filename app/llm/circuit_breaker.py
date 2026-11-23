import time
class CircuitBreaker:
    def __init__(self,limit=3,cooldown=60): self.limit,self.cooldown,self.states=limit,cooldown,{}
    def available(self,p):
        count,until=self.states.get(p,(0,0))
        if until and time.monotonic()>=until: self.states.pop(p,None); return True
        return not until
    def fail(self,p):
        count,_=self.states.get(p,(0,0)); count+=1
        self.states[p]=(count,time.monotonic()+self.cooldown if count>=self.limit else 0)
    def success(self,p): self.states.pop(p,None)
    def trip(self,p): self.states[p]=(self.limit,time.monotonic()+self.cooldown)
