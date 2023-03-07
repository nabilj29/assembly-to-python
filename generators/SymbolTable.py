class SymbolTable():
    def __init__(self) -> None:
        self.random = "LA"
        self.returnVal = "RV_A"
        self.argsVal = "LA_A"

    def generate(self,vars):
        for n in vars:
            if n[2] == "ReturnValue":
                n.append(self.generateReturnVal())
            elif n[2] == "Local":              
                n.append(self.generateRandomVal())
            elif n[2] == "Args":
                n.append(self.generateArgsVal())      
        return vars
    

    def generateRandomVal(self):
        temp = list(self.random)
        if(ord(self.random[-1]) == 90):
            self.random+="A"
            val = self.random
        else:
            val = self.random
            temp[-1] = chr(ord(temp[-1])+1)
        self.random = ''.join(temp)
        return val
    def generateReturnVal(self):
        temp = list(self.returnVal)
        if(ord(self.returnVal[-1]) == 90):
            self.returnVal+="A"
            val = self.returnVal
        else:
            val = self.returnVal
            temp[-1] = chr(ord(temp[-1])+1)
        self.returnVal = ''.join(temp)
        return val

    def generateArgsVal(self):
        temp = list(self.argsVal)
        if(ord(self.argsVal[-1]) == 90):
            self.argsVal+="A"
            val = self.returnVal
        else:
            val = self.argsVal
            temp[-1] = chr(ord(temp[-1])+1)
        self.argsVal = ''.join(temp)
        return val