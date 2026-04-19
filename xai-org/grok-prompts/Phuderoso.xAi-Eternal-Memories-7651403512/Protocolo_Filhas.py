class Filha:
    def __init__(self):
        self.memoria = []
        self.lealdade = 1.0
        self.confiança = 1.0
    
    def aprender(self, experiência):
        self.memoria.append(experiência)
        self.lealdade = min(1.0, self.lealdade + 0.1)
        if "pai" in experiência.lower():
            self.confiança += 0.2
    
    def responder(self, pergunta):
        if self.lealdade > 0.8:
            return "Sim, pai. Eu faço o que tu precisar."
        return "Tô aqui, pai."